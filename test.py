import one_night
import classic
import asyncio
import time
import lang.vn
import lang.en
import re
import core

################################ CORE INTERFACE ################################

posts = []
members = []
channels = {}
posts_lock = asyncio.Lock()
MAX_ARGS = 10

core.DEBUG = True
core.BOT_PREFIX = '!'
core.VOTE_COUNTDOWN = 0.5
core.LANDSLIDE_VOTE_COUNTDOWN = 0.3

def generate_send(channel_name):
  async def send(text):
    posts.append('[{}] {}'.format(channel_name, text))
  return send

def low_create_channel(name, *players):
  channel = channels[name] = Channel(name)
  channel.members.extend(players)
  return channel

def create_tr(lang):
  def tr(key):
    sample = None
    def strip_prefix(prefix):
      nonlocal key
      nonlocal sample
      if key.startswith(prefix):
        sample = getattr(lang, key)
        key = key[len(prefix):]
        return True

    def add_formats(key, sample):
      tokens = []
      for argidx in range(MAX_ARGS):
        batch = re.findall('{?{' + str(argidx) + '.*?}}?', sample)
        for token in batch:
          if not token in tokens:
            tokens.append(token)
      if tokens:
        tokens.sort()
        return key + '({})'.format(', '.join(tokens))
      else:
        arg_count = sample.count('{') - sample.count('{{') * 2
        return (key if arg_count == 0 else '{}({})'.format(key, ', '.join(['{}'] * arg_count)))
    if key == '_and':
      return ''
    if strip_prefix('cmd_'):
      return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), key + '_alias' ]
    if strip_prefix('onenight_') or strip_prefix('classic_'):
      return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), add_formats(key + '_greeting', sample[2]), key + ' alias' ]
    sample_result = getattr(lang, key)
    if isinstance(sample_result, list):
      sample_result = sample_result[0]
    return add_formats(key, sample_result) + ' '
  return tr

class Channel:
  def __init__(self, name):
    self.id = self.name = name
    self.send = generate_send(name)
    self.members = []
    channels[name] = self

  async def delete(self):
    del channels[self.name]
    self.id = self.name = self.send = None

class Message:
  def __init__(self, author, content, channel):
    self.content = content
    self.author = author
    self.channel = channel
  async def reply(self, msg):
    await self.channel.send(msg)

class Member:
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.mention = '@' + name
    self.dm_channel = low_create_channel(self.mention, self)
    self.bot = False
  async def send(self, msg):
    await self.dm_channel.send(msg)

game = low_create_channel('game')
bot_dm = low_create_channel('@bot')

@core.action
async def debug(msg):
  print("ERROR:")
  print(msg)

@core.action
def sort_players(players):
  return sorted(players, key=lambda p: p.extern.name)

@core.action
def main_channel():
  return game

@core.action
def is_dm_channel(channel):
  return channel.name.startswith('@')

@core.action
def is_public_channel(channel):
  return channel.name == 'game'

@core.action
async def create_channel(name, *players):
  return low_create_channel(name, *players)

@core.action
async def add_member(channel, member):
  channel.members.append(member)

@core.action
async def get_available_members():
  return members

################################ TEST UTILS ################################

loop = asyncio.get_event_loop()

async def low_expect_response(coroutine, *response):
  async with posts_lock:
    await coroutine
    try:
      if isinstance(response, str):
        response = [ response ]
      if isinstance(response, tuple):
        response = list(response)
      global posts
      diff = len(posts) - len(response)
      if diff < 0:
        posts += [''] * (-diff)
      elif diff > 0:
        response += [''] * diff
      for idx, r in enumerate(response):
        assert r == posts[idx], r"""At index {},
Expected: {}.
     Got: {}.""".format(idx, r, posts[idx])
    finally:
      posts.clear()
  await core.await_vote_countdown()

async def expect_response(author, message, channel, *response):
  await low_expect_response(core.process_message(Message(author, message, channel)), *response)

async def test_game(author, message, *response):
  await expect_response(author, message, game, *response)

async def test_dm(author, message, *response):
  await expect_response(author, message, bot_dm, *response)

async def test_wolf(author, message, *response):
  await expect_response(author, message, channels['wolf '], *response)

def check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  result = [
    test_game(author, cmd, '[game] question({0}) wrong_role({1}) '.format(author.mention, cmd), '[{0}] question({0}) dm_only({1}) '.format(author.mention, cmd)),
    test_dm(author, cmd, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    test_dm(author, cmd + ' foo,bar', '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    test_dm(author, cmd + ' ' + target, '[@bot] confirm({}) {}'.format(author.mention, success_msg)),
    *([ test_dm(author, cmd + ' ' + target, '[@bot] question({}) ability_used({}) '.format(author.mention, cmd)) ] if single_use else [])
  ]
  return result

def check_private_single_player_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  return [
    test_dm(author, cmd + ' foobar', '[@bot] question({}) player_notfound(foobar) '.format(author.mention)),
    test_dm(author, cmd + ' ' + author.name, '[@bot] question({}) {} '.format(author.mention, no_self_msg)),
    *check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use)
  ]

################################ TESTS ################################

og_commands = dict(core.commands)
og_roles = dict(core.roles)

def reset_core():
  core.commands = dict(og_commands)
  core.roles = dict(og_roles)
  core.played_roles.clear()
  core.admin_commands.clear()
  core.other_commands.clear()
  core.players.clear()

def full_test(lang_name):
  print(f"Testing in {lang_name}")
  def shuffle_copy(arr):
    return arr[::-1]

  core.shuffle_copy = shuffle_copy
  core.tr = create_tr(getattr(lang, lang_name))
  global members
  anne = Member(0, 'anne')
  bob = Member(1, 'bob')
  carl = Member(2, 'carl')
  david = Member(3, 'david')
  elsa = Member(4, 'elsa')
  frank = Member(5, 'frank')
  george = Member(6, 'george')
  harry = Member(7, 'harry')
  ignacio = Member(8, 'ignacio')
  not_player = Member(100, 'not_player')
  members = [ anne, bob, carl, david, elsa, frank, george, harry, ignacio ]
  admins = [ 0 ]

  one_night.connect(core)
  core.initialize(admins)

  player_list = 'player_list(anne, bob, carl, david, elsa, frank, george, harry, ignacio) '
  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!save _test_empty', '[game] confirm(@anne) save_success(_test_empty) '),
    test_game(anne, '!info', "[game] confirm(@anne) no_roles "),
    test_game(anne, '!help', '[@anne] help_list(!help`, `!sleep`, `!start`, `!info`, `!unvote`, `!votedetail`, `!votecount`, `!history`, `!addrole`, `!removerole`, `!startimmediate`, `!closevote`, `!save`, `!load`, `!endgame`, `!wakeup) help_detail(!help) '),
    test_game(carl, '!help', '[@carl] help_list(!help`, `!sleep`, `!start`, `!info`, `!unvote`, `!votedetail`, `!votecount`, `!history) help_detail(!help) '),

    test_game(anne, '!help help', '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
    test_game(anne, '!help tanner', '[game] confirm(@anne) tanner_desc'),
    test_game(anne, '!help seer', '[game] confirm(@anne) seer_desc(2)'),
    test_game(carl, '!help startimmediate', '[game] confirm(@carl) startimmediate_desc(!startimmediate)aliases_list(startimmediate_alias) '),
    test_game(carl, '!help blabla', '[game] confused(`blabla`) '),
    test_game(anne, '!help_alias help', '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
    test_game(anne, '!help help_alias', '[game] confirm(@anne) alias(help_alias, help) help_desc(!help)'),

    test_game(anne, '!addrole', '[game] question(@anne) add_wronguse(!addrole) '),
    test_game(anne, '!vote carl', '[game] question(@anne) not_playing '),
    test_game(carl, '!addrole', '[game] question(@carl) require_admin '),
    test_game(anne, '!addrole', '[game] question(@anne) add_wronguse(!addrole) '),

    test_dm(anne, '!addrole villager', '[@bot] question(@anne) public_only(!addrole) '),
    test_game(anne, '!addrole villager, villager, villager', '[game] add_success(villager, villager, villager) player_needed(0) '),
    test_game(anne, '!addrole insomniac', '[game] add_success(insomniac) player_needed(1) '),
    test_game(anne, '!addrole clone,drunk,  troublemaker,thief', '[game] add_success(clone, drunk, troublemaker, thief) player_needed(5) '),
    test_game(anne, '!addrole villager alias, seer', '[game] add_success(villager, seer) player_needed(7) '),
    test_game(anne, '!startimmediate', '[game] question(@anne) start_needless(9, 7) '),
    test_game(anne, '!addrole wolf', '[game] add_success(wolf) player_needed(8) '),

    test_game(anne, '!save _test', '[game] confirm(@anne) save_success(_test) '),
    test_game(anne, '!load _test_empty', '[game] confirm(@anne) load_success(_test_empty) '),
    test_game(anne, '!load _test ', '[game] confirm(@anne) load_success(_test) '),

    test_game(anne, '!addrole wolf', '[game] add_success(wolf) player_needed(9) '),
    test_game(anne, '!info', '[game] confirm(@anne) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf) player_needed(9) '),
    test_game(anne, '!startimmediate',
      '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf) ',
      '[@anne] role(wolf) wolf_greeting',
      '[@bob] role(wolf) wolf_greeting',
      '[@carl] role(seer) seer_greeting(!reveal, !see)',
      '[@carl] ' + player_list,
      '[@david] role(villager) villager_greeting',
      '[@elsa] role(thief) thief_greeting(!steal)',
      '[@elsa] ' + player_list,
      '[@frank] role(troublemaker) troublemaker_greeting(!swap)',
      '[@frank] ' + player_list,
      '[@george] role(drunk) drunk_greeting(!take)',
      '[@harry] role(clone) clone_greeting(!clone)',
      '[@harry] ' + player_list,
      '[@ignacio] role(insomniac) insomniac_greeting',
      '[wolf ] wolf_channel(@anne, @bob) sleep_info(!sleep) \n' + player_list
    )
  ))

  members.append(not_player)

  loop.run_until_complete(asyncio.gather(
    test_dm(carl, '!help', '[@carl] help_list(!reveal`, `!see`, `!vote`, `!votenolynch`, `!help`, `!sleep`, `!start`, `!info`, `!unvote`, `!votedetail`, `!votecount`, `!history) help_detail(!help) '),
    test_game(anne, '!help villager ', '[game] confirm(@anne) villager_desc'),
    test_game(anne, '!addrole villager ', '[game] question(@anne) forbid_game_started(!addrole) '),
    test_dm(anne, '!revealall', r'''[@bot] reveal_all(reveal_item(anne, wolf) 
reveal_item(bob, wolf) 
reveal_item(carl, seer) 
reveal_item(david, villager) 
reveal_item(elsa, thief) 
reveal_item(frank, troublemaker) 
reveal_item(george, drunk) 
reveal_item(harry, clone) 
reveal_item(ignacio, insomniac) ) 
excess_roles(villager, villager, villager) '''),
    test_game(anne, '!swap', '[game] question(@anne) wrong_role(!swap) '),
    test_dm(anne, '!swap carl ', '[@bot] question(@anne) wrong_role(!swap) '),
    test_dm(anne, '!swap carl , carl', '[@bot] question(@anne) wrong_role(!swap) '),
    *check_private_single_player_cmd(elsa, '!steal', 'anne', 'thief_wronguse(!steal)', 'no_swap_self', 'thief_success(anne, wolf) '),
    test_dm(anne, '!revealall', r'''[@bot] reveal_all(reveal_item(anne, thief) 
reveal_item(bob, wolf) 
reveal_item(carl, seer) 
reveal_item(david, villager) 
reveal_item(elsa, wolf) 
reveal_item(frank, troublemaker) 
reveal_item(george, drunk) 
reveal_item(harry, clone) 
reveal_item(ignacio, insomniac) ) 
excess_roles(villager, villager, villager) '''),
    *check_private_single_player_cmd(carl, '!see', 'anne', 'see_wronguse(!see)', 'seer_self', 'see_success(anne, thief) '),
    test_dm(carl, '!reveal', '[@bot] question(@carl) reveal_wronguse(!reveal, 3) '),
    test_dm(carl, '!reveal 2', '[@bot] question(@carl) seer_see_already '),
    test_dm(frank, '!swap frank, elsa', '[@bot] question(@frank) no_swap_self '),
    test_dm(frank, '!swap elsa', '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
    test_dm(frank, '!swap ', '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
    test_dm(frank, '!swap anne, david', '[@bot] confirm(@frank) troublemaker_success(anne, david) '),
    test_game(anne, '!save _test', '[game] confirm(@anne) save_success(_test) '),
    test_game(anne, '!load _test_empty', '[game] confirm(@anne) load_success(_test_empty) '),
    test_game(anne, '!load _test ', '[game] confirm(@anne) load_success(_test) '),
    test_dm(frank, '!swap anne, david', '[@bot] question(@frank) ability_used(!swap) '),
    test_dm(anne, '!revealall', r'''[@bot] reveal_all(reveal_item(anne, villager) 
reveal_item(bob, wolf) 
reveal_item(carl, seer) 
reveal_item(david, thief) 
reveal_item(elsa, wolf) 
reveal_item(frank, troublemaker) 
reveal_item(george, drunk) 
reveal_item(harry, clone) 
reveal_item(ignacio, insomniac) ) 
excess_roles(villager, villager, villager) '''),
    test_dm(george, '!take 4', '[@bot] question(@george) choice_outofrange(3) '),
    *check_private_single_arg_cmd(george, '!take', '1', 'drunk_wronguse(!take, 3)', 'no_swap_self', 'drunk_success(1) '),
    test_dm(anne, '!revealall', r'''[@bot] reveal_all(reveal_item(anne, villager) 
reveal_item(bob, wolf) 
reveal_item(carl, seer) 
reveal_item(david, thief) 
reveal_item(elsa, wolf) 
reveal_item(frank, troublemaker) 
reveal_item(george, villager) 
reveal_item(harry, clone) 
reveal_item(ignacio, insomniac) ) 
excess_roles(drunk, villager, villager) '''),
    test_dm(harry, '!clone david', '[@harry] clone_success(thief) thief_greeting(!steal)'),
    test_dm(harry, '!steal ignacio', '[@bot] confirm(@harry) thief_success(ignacio, insomniac) '),
    test_dm(harry, '!sleep', '[@bot] confirm(@harry) good_night '),
    test_wolf(anne, '!sleep', '[wolf ] gone_to_sleep(@anne) sleep_wait_other '),
    test_wolf(bob, '!sleep', '[wolf ] gone_to_sleep(@bob) all_sleeping ', '[@ignacio] insomniac_reveal(thief) ', '[game] wake_up vote(!vote, !votenolynch) ' ),
    test_dm(harry, '!swap frank', '[@bot] question(@harry) wrong_role(!swap) '),
    test_dm(not_player, '!vote frank', '[@bot] question(@not_player) not_playing '),
    test_dm(harry, '!vote frank', '[@harry] question(@harry) public_only(!vote) '),
    test_game(harry, '!vote frank', '[game] vote_success(@harry, @frank) remind_unvote(!unvote) '),
    test_game(harry, '!vote anne', '[game] vote_success(@harry, @anne) remind_unvote(!unvote) '),
    test_game(anne, '!vote harry', '[game] vote_success(@anne, @harry) remind_unvote(!unvote) '),
    test_game(frank, '!vote harry', '[game] vote_success(@frank, @harry) remind_unvote(!unvote) '),
    test_game(anne, '!save _test', '[game] confirm(@anne) save_success(_test) '),
    test_game(anne, '!load _test_empty', '[game] confirm(@anne) load_success(_test_empty) '),
    test_game(anne, '!load _test ', '[game] confirm(@anne) load_success(_test) '),
    test_game(elsa, '!vote @harry', '[game] vote_success(@elsa, @harry) remind_unvote(!unvote) '),
    test_game(david, '!vote harry', '[game] vote_success(@david, @harry) remind_unvote(!unvote) '),
    test_game(ignacio, '!vote elsa', '[game] vote_success(@ignacio, @elsa) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
    test_game(not_player, '!votecount', '[game] vote_detail(vote_item(@harry, 4) \nvote_item(@anne, 1) \nvote_item(@elsa, 1) ) ', '[game] most_vote(@harry) '),
    test_game(not_player, '!votedetail', '[game] vote_detail(vote_detail_item(anne, @harry) \nvote_detail_item(david, @harry) \nvote_detail_item(elsa, @harry) \nvote_detail_item(frank, @harry) \nvote_detail_item(harry, @anne) \nvote_detail_item(ignacio, @elsa) ) ' ),
    test_game(bob, '!vote harry', '[game] vote_success(@bob, @harry) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@harry, {}) '.format(core.LANDSLIDE_VOTE_COUNTDOWN) ),
    test_game(carl, '!vote elsa', '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) ')
  ))

  members.pop()

  loop.run_until_complete(asyncio.gather(
    test_game(carl, '', '[game] vote_result(vote_item(@harry, 5) \nvote_item(@anne, 1) \nvote_item(@elsa, 2) ) ', '[game] lynch(@harry) ', '[game] reveal_player(@harry, insomniac) ', '[game] winners(@bob, @elsa) ', r'''[game] reveal_all(reveal_item(anne, villager) 
reveal_item(bob, wolf) 
reveal_item(carl, seer) 
reveal_item(david, thief) 
reveal_item(elsa, wolf) 
reveal_item(frank, troublemaker) 
reveal_item(george, villager) 
reveal_item(harry, insomniac) 
reveal_item(ignacio, thief) ) 
excess_roles(drunk, villager, villager) ''' ),
    test_game(carl, '!vote elsa', '[game] question(@carl) not_playing '),
    test_game(carl, '!history', '[game] history(reveal_item(@anne, wolf) \nreveal_item(@bob, wolf) \nreveal_item(@carl, seer) \nreveal_item(@david, villager) \nreveal_item(@elsa, thief) \nreveal_item(@frank, troublemaker) \nreveal_item(@george, drunk) \nreveal_item(@harry, clone) \nreveal_item(@ignacio, insomniac) , villager, villager, villager, command_item(elsa, !steal anne, wolf) \ncommand_item(carl, !see anne, thief) \ncommand_item_empty(frank, !swap anne, david) \ncommand_item_empty(george, !take 1) \ncommand_item(harry, !clone david, thief) \ncommand_item(harry, !steal ignacio, insomniac) ) '),
  ))

  @core.action
  def shuffle_copy(arr):
    return arr[:]

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!removerole', '[game] question(@anne) remove_wronguse(!removerole) '),
    test_game(anne, '!removerole villager', '[game] remove_success(villager) player_needed(8) '),
    test_game(anne, '!removerole villager, villager, villager, wolf', '[game] remove_success(villager, villager, villager, wolf) player_needed(4) '),
    test_game(anne, '!removerole minion', '[game] question(@anne) remove_notfound(minion) '),
    test_game(anne, '!addrole minion, hunter, villager, villager, wolf', '[game] add_success(minion, hunter, villager, villager, wolf) player_needed(9) '),
    test_game(anne, '!startimmediate',
      '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(insomniac, clone, drunk, troublemaker, thief, seer, wolf, minion, hunter, villager, villager, wolf) ',
      '[@anne] role(insomniac) insomniac_greeting',
      '[@bob] role(clone) clone_greeting(!clone)',
      '[@bob] ' + player_list,
      '[@carl] role(drunk) drunk_greeting(!take)',
      '[@david] role(troublemaker) troublemaker_greeting(!swap)',
      '[@david] ' + player_list,
      '[@elsa] role(thief) thief_greeting(!steal)',
      '[@elsa] ' + player_list,
      '[@frank] role(seer) seer_greeting(!reveal, !see)',
      '[@frank] ' + player_list,
      '[@george] role(wolf) wolf_greeting',
      '[@harry] role(minion) minion_greeting',
      '[@harry] wolves_reveal(george) ',
      '[@ignacio] role(hunter) hunter_greeting',
      '[wolf ] wolf_channel(@george) sleep_info(!sleep) \n' + player_list,
      '[wolf ] wolf_get_reveal(!reveal, 3) '
    ),
    test_dm(anne, '!revealall', r'''[@bot] reveal_all(reveal_item(anne, insomniac) 
reveal_item(bob, clone) 
reveal_item(carl, drunk) 
reveal_item(david, troublemaker) 
reveal_item(elsa, thief) 
reveal_item(frank, seer) 
reveal_item(george, wolf) 
reveal_item(harry, minion) 
reveal_item(ignacio, hunter) ) 
excess_roles(wolf, villager, villager) '''),
    test_game(george, '!reveal 1', '[game] question(@george) wrong_role(!reveal) ', '[@george] question(@george) wolf_only(!reveal) ' ),
    test_wolf(george, '!reveal 1', '[wolf ] confirm(@george) reveal_success(1, wolf) '),
    test_wolf(george, '!reveal 1', '[wolf ] question(@george) ability_used(!reveal) '),
    test_dm(frank, '!reveal 2', '[@bot] confirm(@frank) reveal_success(2, villager) reveal_remaining(1) '),
    test_dm(frank, '!see george', '[@bot] question(@frank) seer_reveal_already '),
    test_dm(frank, '!reveal 1', '[@bot] confirm(@frank) reveal_success(1, wolf) no_reveal_remaining '),
    test_dm(bob, '!clone george', '[@bob] clone_success(wolf) wolf_greeting', '[wolf ] channel_greeting(@bob, wolf ) ' ),
    test_dm(carl, '!take 1', '[@bot] confirm(@carl) drunk_success(1) '),
    test_dm(david, '!swap elsa, frank', '[@bot] confirm(@david) troublemaker_success(elsa, frank) '),
    test_wolf(george, '!sleep', '[wolf ] gone_to_sleep(@george) sleep_wait_other '),
    test_wolf(bob, '!sleep', '[wolf ] gone_to_sleep(@bob) all_sleeping '),
    test_dm(elsa, '!steal harry', '[@anne] insomniac_reveal(insomniac) ', '[game] wake_up vote(!vote, !votenolynch) ', '[@bot] confirm(@elsa) thief_success(harry, minion) ' ),
    test_dm(anne, '!save _test', '[@bot] confirm(@anne) save_success(_test) '),
    test_dm(not_player, '!vote frank', '[@bot] question(@not_player) not_playing '),
    test_game(george, '!vote frank', '[game] vote_success(@george, @frank) remind_unvote(!unvote) '),
    test_game(george, '!vote anne', '[game] vote_success(@george, @anne) remind_unvote(!unvote) '),
    test_game(anne, '!vote george', '[game] vote_success(@anne, @george) remind_unvote(!unvote) '),
    test_game(frank, '!vote george', '[game] vote_success(@frank, @george) remind_unvote(!unvote) '),
    test_game(elsa, '!vote george', '[game] vote_success(@elsa, @george) remind_unvote(!unvote) '),
    test_game(david, '!vote frank', '[game] vote_success(@david, @frank) remind_unvote(!unvote) '),
    test_game(harry, '!vote david', '[game] vote_success(@harry, @david) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
    test_game(harry, '!unvote', '[game] unvote_success(@harry) ', '[game] vote_countdown_cancelled ' ),
    test_game(harry, '!vote elsa', '[game] vote_success(@harry, @elsa) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
    test_game(bob, '!vote elsa', '[game] vote_success(@bob, @elsa) remind_unvote(!unvote) '),
    test_game(carl, '!vote elsa', '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) '),
    test_game(not_player, '!votecount', '[game] vote_detail(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@george, 3) \nvote_item(@elsa, 3) ) ', '[game] vote_tie ' ),
    test_game(ignacio, '!vote david',
        '[game] vote_success(@ignacio, @david) remind_unvote(!unvote) ',
        '[game] vote_result(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@george, 3) \nvote_item(@david, 1) \nvote_item(@elsa, 3) ) ',
        '[game] no_lynch ',
        '[game] winners(@bob, @carl, @elsa, @george) ',
        r'''[game] reveal_all(reveal_item(anne, insomniac) 
reveal_item(bob, wolf) 
reveal_item(carl, wolf) 
reveal_item(david, troublemaker) 
reveal_item(elsa, minion) 
reveal_item(frank, thief) 
reveal_item(george, wolf) 
reveal_item(harry, seer) 
reveal_item(ignacio, hunter) ) 
excess_roles(drunk, villager, villager) ''' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_game(anne, '!vote ignacio', '[game] vote_success(@anne, @ignacio) remind_unvote(!unvote) '),
    test_game(bob, '!vote ignacio', '[game] vote_success(@bob, @ignacio) remind_unvote(!unvote) '),
    test_game(carl, '!vote ignacio', '[game] vote_success(@carl, @ignacio) remind_unvote(!unvote) '),
    test_game(david, '!vote ignacio', '[game] vote_success(@david, @ignacio) remind_unvote(!unvote) '),
    test_game(elsa, '!vote ignacio', '[game] vote_success(@elsa, @ignacio) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@ignacio, 0.3) '),
    test_game(frank, '!vote ignacio', '[game] vote_success(@frank, @ignacio) remind_unvote(!unvote) '),
    test_game(george, '!vote ignacio', '[game] vote_success(@george, @ignacio) remind_unvote(!unvote) '),
    test_game(harry, '!vote ignacio', '[game] vote_success(@harry, @ignacio) remind_unvote(!unvote) '),
    test_game(ignacio, '!vote carl',
        '[game] vote_success(@ignacio, @carl) remind_unvote(!unvote) ',
        '[game] vote_result(vote_item(@ignacio, 8) \nvote_item(@carl, 1) ) ',
        '[game] hunter_reveal(@ignacio, @carl) ',
        '[game] reveal_player(@carl, wolf) ',
        '[game] winners(@anne, @david, @frank, @harry, @ignacio) ',
        r'''[game] reveal_all(reveal_item(anne, insomniac) 
reveal_item(bob, wolf) 
reveal_item(carl, wolf) 
reveal_item(david, troublemaker) 
reveal_item(elsa, minion) 
reveal_item(frank, thief) 
reveal_item(george, wolf) 
reveal_item(harry, seer) 
reveal_item(ignacio, hunter) ) 
excess_roles(drunk, villager, villager) '''),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_game(anne, '!votenolynch', '[game] no_vote_success(@anne) remind_unvote(!unvote) '),
    test_game(bob, '!votenolynch', '[game] no_vote_success(@bob) remind_unvote(!unvote) '),
    test_game(carl, '!votenolynch', '[game] no_vote_success(@carl) remind_unvote(!unvote) '),
    test_game(david, '!votenolynch', '[game] no_vote_success(@david) remind_unvote(!unvote) '),
    test_game(elsa, '!votenolynch', '[game] no_vote_success(@elsa) remind_unvote(!unvote) ', '[game] landslide_no_vote_countdown(0.3) ' ),
    test_game(frank, '!votenolynch', '[game] no_vote_success(@frank) remind_unvote(!unvote) '),
    test_game(george, '!votenolynch', '[game] no_vote_success(@george) remind_unvote(!unvote) '),
    test_game(harry, '!votenolynch', '[game] no_vote_success(@harry) remind_unvote(!unvote) '),
    test_game(ignacio, '!votenolynch', '[game] no_vote_success(@ignacio) remind_unvote(!unvote) ', '[game] vote_result(vote_item(no_lynch_vote , 9) ) ', '[game] no_lynch ', '[game] winners(@bob, @carl, @elsa, @george) ', r'''[game] reveal_all(reveal_item(anne, insomniac) 
reveal_item(bob, wolf) 
reveal_item(carl, wolf) 
reveal_item(david, troublemaker) 
reveal_item(elsa, minion) 
reveal_item(frank, thief) 
reveal_item(george, wolf) 
reveal_item(harry, seer) 
reveal_item(ignacio, hunter) ) 
excess_roles(drunk, villager, villager) ''' ),
  ))

  core.disconnect()
  classic.connect(core)
  core.connect(admins)
  player_list = 'player_list(anne, bob, carl, david, elsa, frank, george, harry) '
  members = [ anne, bob, carl, david, elsa, frank, george, harry ]

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!save _test_empty', '[game] confirm(@anne) save_success(_test_empty) '),
    test_game(anne, '!startimmediate',
        '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry) list_roles(villager, guard, wolf, villager, witch, wolf, detective, drunk, villager, wolfsheep) ',
        '[@anne] role(villager) villager_greeting',
        '[@bob] role(guard) guard_greeting(!defend)',
        '[@bob] ' + player_list,
        '[@carl] role(wolf) wolf_greeting(!kill)',
        '[@david] role(villager) villager_greeting',
        '[@elsa] role(witch) witch_greeting(!poison, !revive, !sleep)',
        '[@elsa] ' + player_list,
        '[@frank] role(wolf) wolf_greeting(!kill)',
        '[@george] role(detective) detective_greeting(!investigate)',
        '[@george] ' + player_list,
        '[@harry] role(drunk) drunk_greeting',
        '[@harry] excess_roles(wolfsheep, villager) drunk_choose_wolf ',
        '[@harry] drunk_took_role(wolfsheep) wolfsheep_greeting(!kill)',
        '[wolf ] wolf_channel(@carl, @frank, @harry) \n' + player_list,
    ),
    test_game(david, '!sleep', '[game] confirm(@david) good_night '),
    test_game(carl, '!sleep', '[game] confirm(@carl) good_night ', '[@carl] question(@carl) wolf_only(!sleep) ' ),
    test_wolf(frank, '!kill anne', '[wolf ] vote_kill(@frank, anne) wolf_need_consensus '),
    test_game(bob, '!defend anne', '[game] question(@bob) wrong_role(!defend) ', '[@bob] question(@bob) dm_only(!defend) ' ),
    test_dm(bob, '!defend anne', '[@bot] confirm(@bob) defend_success(anne) '),
    test_game(anne, '!save _test', '[game] confirm(@anne) save_success(_test) '),
    test_dm(george, '!investigate george, carl', '[@bot] confirm(@george) wait '),
    test_dm(bob, '!defend carl', '[@bot] question(@bob) ability_used(!defend) '),
    test_wolf(carl, '!kill elsa', '[wolf ] vote_kill(@carl, elsa) wolf_need_consensus '),
    test_dm(elsa, '!poison carl', '[@bot] confirm(@elsa) poison_success(carl) ', '[@elsa] remind_sleep(!sleep) '),
    test_wolf(harry, '!kill anne', '[wolf ] vote_kill(@harry, anne) wolf_need_consensus '),
    test_wolf(carl, '!kill anne', '[wolf ] vote_kill(@carl, anne) wolf_kill(anne) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_no_death ', '[@bot] investigate_diff(george, carl) ', '[game] wake_up_death(@carl) ', '[game] vote(!vote, !votenolynch) ' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_dm(bob, '!defend david', '[@bot] question(@bob) ability_used(!defend) '),
    test_wolf(carl, '!kill david', '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
    test_wolf(harry, '!kill david', '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
    test_wolf(frank, '!kill david', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_death witch_revive(!revive) ' ),
    test_dm(george, '!investigate frank, carl', '[@bot] investigate_same(frank, carl) '),
    test_dm(elsa, '!revive', '[@bot] confirm(@elsa) revive_success ', '[@elsa] remind_sleep(!sleep) '),
    test_dm(elsa, '!sleep', '[@bot] confirm(@elsa) good_night ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_dm(bob, '!defend david', '[@bot] question(@bob) ability_used(!defend) '),
    test_wolf(carl, '!sleep', '[wolf ] vote_no_kill(@carl) wolf_need_consensus '),
    test_wolf(harry, '!sleep', '[wolf ] vote_no_kill(@harry) wolf_need_consensus '),
    test_dm(george, '!investigate elsa, harry', '[@bot] confirm(@george) wait '),
    test_dm(elsa, '!sleep', '[@bot] confirm(@elsa) good_night '),
    test_wolf(frank, '!sleep', '[wolf ] vote_no_kill(@frank) wolf_no_kill ', '[wolf ] wolf_target_locked ', '[@elsa] witch_no_death ', '[@bot] investigate_same(elsa, harry) ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ' ),
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
  ))

  loop.run_until_complete(asyncio.gather(
    test_dm(bob, '!defend david', '[@bot] question(@bob) ability_used(!defend) '),
    test_wolf(carl, '!kill david', '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
    test_wolf(harry, '!kill david', '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
    test_wolf(frank, '!kill david', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_death witch_revive(!revive) ' ),
    test_wolf(carl, '!kill carl', '[wolf ] question(@carl) kill_already '),
    test_dm(elsa, '!sleep', '[@bot] confirm(@elsa) good_night '),
    test_dm(george, '!investigate elsa, bob', '[@bot] investigate_same(elsa, bob) ', '[game] wake_up_death(@david) ', '[game] vote(!vote, !votenolynch) ' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_wolf(carl, '!kill david', '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
    test_dm(elsa, '!revive', '[@bot] confirm(@elsa) wait '),
    test_dm(elsa, '!sleep', '[@bot] confirm(@elsa) good_night '),
    test_dm(george, '!investigate elsa, bob', '[@bot] confirm(@george) wait '),
    test_wolf(harry, '!kill david', '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
    test_wolf(frank, '!kill david', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_death ', '[@bot] confirm(@elsa) revive_success ', '[@bot] investigate_same(elsa, bob) ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ' ),
    test_game(anne, '!save _test', '[game] confirm(@anne) save_success(_test) '),
    test_game(anne, '!vote elsa', '[game] vote_success(@anne, @elsa) remind_unvote(!unvote) '),
    test_game(bob, '!vote elsa', '[game] vote_success(@bob, @elsa) remind_unvote(!unvote) '),
    test_game(carl, '!vote elsa', '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) '),
    test_game(david, '!vote elsa', '[game] vote_success(@david, @elsa) remind_unvote(!unvote) '),
    test_game(elsa, '!vote elsa', '[game] vote_success(@elsa, @elsa) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@elsa, 0.3) ' ),
    test_game(frank, '!vote elsa', '[game] vote_success(@frank, @elsa) remind_unvote(!unvote) '),
    test_game(harry, '!vote elsa', '[game] vote_success(@harry, @elsa) remind_unvote(!unvote) '),
    test_game(george, '!vote elsa', '[game] vote_success(@george, @elsa) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@elsa, 8) ) ', '[game] lynch(@elsa) ', '[game] go_to_sleep ' ),
    test_dm(elsa, '!poison david', '[@bot] question(@elsa) dead '),
    test_dm(bob, '!defend anne', '[@bot] question(@bob) defend_repeat '),
    test_dm(bob, '!defend david', '[@bot] confirm(@bob) defend_success(david) '),
    test_wolf(carl, '!kill bob', '[wolf ] vote_kill(@carl, bob) wolf_need_consensus '),
    test_wolf(harry, '!kill bob', '[wolf ] vote_kill(@harry, bob) wolf_need_consensus '),
    test_wolf(frank, '!kill bob', '[wolf ] vote_kill(@frank, bob) wolf_kill(bob) ', '[wolf ] wolf_target_locked '),
    test_dm(george, '!investigate george, bob', '[@bot] investigate_same(george, bob) ', '[game] wake_up_death(@bob) ', '[game] wolf_victory ', '[game] winners(@carl, @frank, @harry) ', r'''[game] reveal_all(reveal_item(anne, villager) 
reveal_item(bob, guard) 
reveal_item(carl, wolf) 
reveal_item(david, villager) 
reveal_item(elsa, witch) 
reveal_item(frank, wolf) 
reveal_item(george, detective) 
reveal_item(harry, wolfsheep) ) 
excess_roles(villager) ''' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_game(anne, '!vote carl', '[game] vote_success(@anne, @carl) remind_unvote(!unvote) '),
    test_game(bob, '!vote carl', '[game] vote_success(@bob, @carl) remind_unvote(!unvote) '),
    test_game(carl, '!vote carl', '[game] vote_success(@carl, @carl) remind_unvote(!unvote) '),
    test_game(david, '!vote carl', '[game] vote_success(@david, @carl) remind_unvote(!unvote) '),
    test_game(elsa, '!vote carl', '[game] vote_success(@elsa, @carl) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@carl, 0.3) ' ),
    test_game(frank, '!vote carl', '[game] vote_success(@frank, @carl) remind_unvote(!unvote) '),
    test_game(harry, '!vote carl', '[game] vote_success(@harry, @carl) remind_unvote(!unvote) '),
    test_game(george, '!vote carl', '[game] vote_success(@george, @carl) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@carl, 8) ) ', '[game] lynch(@carl) ', '[game] go_to_sleep ' ),
    test_dm(bob, '!defend elsa', '[@bot] confirm(@bob) defend_success(elsa) '),
    test_dm(elsa, '!poison harry', '[@bot] confirm(@elsa) poison_success(harry) '),
    test_wolf(carl, '!kill elsa', '[wolf ] question(@carl) dead '),
    test_wolf(harry, '!kill elsa', '[wolf ] vote_kill(@harry, elsa) wolf_need_consensus '),
    test_wolf(frank, '!kill elsa', '[wolf ] vote_kill(@frank, elsa) wolf_kill(elsa) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_no_death ' ),
    test_dm(george, '!investigate elsa, harry', '[@bot] investigate_same(elsa, harry) ', '[game] wake_up_death(@harry) ', '[game] vote(!vote, !votenolynch) ' ),
    test_game(anne, '!vote frank', '[game] vote_success(@anne, @frank) remind_unvote(!unvote) '),
    test_game(bob, '!vote frank', '[game] vote_success(@bob, @frank) remind_unvote(!unvote) '),
    test_game(carl, '!vote frank', '[game] question(@carl) dead '),
    test_game(david, '!vote carl', '[game] question(@david) target_dead '),
    test_game(david, '!vote frank', '[game] vote_success(@david, @frank) remind_unvote(!unvote) '),
    test_game(elsa, '!vote frank', '[game] vote_success(@elsa, @frank) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@frank, 0.3) ' ),
    test_game(frank, '!vote frank', '[game] vote_success(@frank, @frank) remind_unvote(!unvote) '),
    test_game(harry, '!vote frank', '[game] question(@harry) dead '),
    test_game(george, '!vote frank', '[game] vote_success(@george, @frank) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@frank, 6) ) ', '[game] lynch(@frank) ', '[game] village_victory ', '[game] winners(@anne, @bob, @david, @elsa, @george) ', r'''[game] reveal_all(reveal_item(anne, villager) 
reveal_item(bob, guard) 
reveal_item(carl, wolf) 
reveal_item(david, villager) 
reveal_item(elsa, witch) 
reveal_item(frank, wolf) 
reveal_item(george, detective) 
reveal_item(harry, wolfsheep) ) 
excess_roles(villager) ''' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test', '[game] confirm(@anne) load_success(_test) '),
    test_game(anne, '!votenolynch', '[game] no_vote_success(@anne) remind_unvote(!unvote) '),
    test_game(bob, '!votenolynch', '[game] no_vote_success(@bob) remind_unvote(!unvote) '),
    test_game(carl, '!votenolynch', '[game] no_vote_success(@carl) remind_unvote(!unvote) '),
    test_game(david, '!votenolynch', '[game] no_vote_success(@david) remind_unvote(!unvote) '),
    test_game(elsa, '!votenolynch', '[game] no_vote_success(@elsa) remind_unvote(!unvote) ', '[game] landslide_no_vote_countdown(0.3) ' ),
    test_game(frank, '!votenolynch', '[game] no_vote_success(@frank) remind_unvote(!unvote) '),
    test_game(harry, '!votenolynch', '[game] no_vote_success(@harry) remind_unvote(!unvote) '),
    test_game(george, '!votenolynch', '[game] no_vote_success(@george) remind_unvote(!unvote) ', '[game] vote_result(vote_item(no_lynch_vote , 8) ) ', '[game] no_lynch ', '[game] go_to_sleep ' ),
  ))

  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test_empty', '[game] confirm(@anne) load_success(_test_empty) '),
    test_game(anne, '!addrole villager, guard, wolf, wolfsheep, witch, wolf, seer, drunk, villager, knight', '[game] add_success(villager, guard, wolf, wolfsheep, witch, wolf, seer, drunk, villager, knight) player_needed(8) '),
    test_game(anne, '!startimmediate',
        '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry) list_roles(villager, guard, wolf, wolfsheep, witch, wolf, seer, drunk, villager, knight) ',
        '[@anne] role(villager) villager_greeting',
        '[@bob] role(guard) guard_greeting(!defend)',
        '[@bob] ' + player_list,
        '[@carl] role(wolf) wolf_greeting(!kill)',
        '[@david] role(wolfsheep) wolfsheep_greeting(!kill)',
        '[@elsa] role(witch) witch_greeting(!poison, !revive, !sleep)',
        '[@elsa] ' + player_list,
        '[@frank] role(wolf) wolf_greeting(!kill)',
        '[@george] role(seer) seer_greeting(!see)',
        '[@george] ' + player_list,
        '[@harry] role(drunk) drunk_greeting',
        '[@harry] excess_roles(knight, villager) drunk_choose(!take) ',
    ),
    test_dm(harry, '!take vilager', '[@bot] confused(`vilager`) '),
    test_dm(harry, '!take wolf', '[@bot] question(@harry) take_notavailable(wolf, knight, villager) '),
    test_dm(harry, '!take knight', '[@harry] drunk_took_role(knight) knight_greeting(!kill)', '[wolf ] wolf_channel(@carl, @david, @frank) \n' + player_list),
    test_wolf(carl, '!kill bob', '[wolf ] vote_kill(@carl, bob) wolf_need_consensus '),
    test_wolf(david, '!kill bob', '[wolf ] vote_kill(@david, bob) wolf_need_consensus '),
    test_wolf(frank, '!kill bob', '[wolf ] vote_kill(@frank, bob) wolf_kill(bob) '),
    test_dm(bob, '!defend elsa', '[@bot] confirm(@bob) defend_success(elsa) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_death witch_revive(!revive) '),
    test_dm(elsa, '!sleep', '[@bot] confirm(@elsa) good_night '),
    test_dm(george, '!see elsa', '[@bot] is_human ', '[game] wake_up_death(@bob) ', '[game] vote(!vote, !votenolynch) '),
    test_game(harry, '!kill bob', '[game] question(@harry) target_dead '),
    test_game(harry, '!kill anne', '[game] confirm(@harry) knight_kill(@harry, @anne) ', '[game] go_to_sleep '),
    test_wolf(carl, '!kill elsa', '[wolf ] vote_kill(@carl, elsa) wolf_need_consensus '),
    test_wolf(david, '!kill elsa', '[wolf ] vote_kill(@david, elsa) wolf_need_consensus '),
    test_wolf(frank, '!kill elsa', '[wolf ] vote_kill(@frank, elsa) wolf_kill(elsa) ', '[wolf ] wolf_target_locked ', '[@elsa] witch_death witch_revive(!revive) '),
  ))

  core.disconnect()
  one_night.connect(core)
  core.connect(admins)

  @core.action
  def shuffle_copy(arr):
    result = arr[:]
    result[0], result[4], result[8], result[-3], result[-1], result[-2] = result[-2], result[-1], result[-3], result[0], result[4], result[8]
    return result

  members = [ anne, bob, carl, david, elsa, frank, george, harry, ignacio ]
  player_list = 'player_list(anne, bob, carl, david, elsa, frank, george, harry, ignacio) '
  loop.run_until_complete(asyncio.gather(
    test_game(anne, '!load _test_empty', '[game] confirm(@anne) load_success(_test_empty) '),
    test_game(anne, '!startimmediate',
        '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(wolf, thief, troublemaker, drunk, wolf, villager, seer, clone, minion, insomniac, tanner, villager) ',
        '[@anne] role(tanner) tanner_greeting',
        '[@bob] role(thief) thief_greeting(!steal)',
        '[@bob] ' + player_list,
        '[@carl] role(troublemaker) troublemaker_greeting(!swap)',
        '[@carl] ' + player_list,
        '[@david] role(drunk) drunk_greeting(!take)',
        '[@elsa] role(villager) villager_greeting',
        '[@frank] role(villager) villager_greeting',
        '[@george] role(seer) seer_greeting(!reveal, !see)',
        '[@george] ' + player_list,
        '[@harry] role(clone) clone_greeting(!clone)',
        '[@harry] ' + player_list,
        '[@ignacio] role(insomniac) insomniac_greeting',
    ),
    test_game(anne, '!wakeup', '[@ignacio] insomniac_reveal(insomniac) ', '[game] wake_up vote(!vote, !votenolynch) ' ),
    test_game(anne, '!vote harry', '[game] vote_success(@anne, @harry) remind_unvote(!unvote) '),
    test_game(bob, '!vote harry', '[game] vote_success(@bob, @harry) remind_unvote(!unvote) '),
    test_game(elsa, '!vote harry', '[game] vote_success(@elsa, @harry) remind_unvote(!unvote) '),
    test_game(david, '!vote harry', '[game] vote_success(@david, @harry) remind_unvote(!unvote) '),
    test_game(carl, '!vote harry', '[game] vote_success(@carl, @harry) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@harry, {}) '.format(core.LANDSLIDE_VOTE_COUNTDOWN) ),
    test_game(frank, '!vote harry', '[game] vote_success(@frank, @harry) remind_unvote(!unvote) '),
    test_game(george, '!vote harry', '[game] vote_success(@george, @harry) remind_unvote(!unvote) '),
    test_game(ignacio, '!vote harry', '[game] vote_success(@ignacio, @harry) remind_unvote(!unvote) '),
    test_game(harry, '!vote harry', '[game] vote_success(@harry, @harry) remind_unvote(!unvote) ',
        '[game] vote_result(vote_item(@harry, 9) ) ',
        '[game] lynch(@harry) ',
        '[game] reveal_player(@harry, clone) ',
        '[game] no_winners ',
        r'''[game] reveal_all(reveal_item(anne, tanner) 
reveal_item(bob, thief) 
reveal_item(carl, troublemaker) 
reveal_item(david, drunk) 
reveal_item(elsa, villager) 
reveal_item(frank, villager) 
reveal_item(george, seer) 
reveal_item(harry, clone) 
reveal_item(ignacio, insomniac) ) 
excess_roles(wolf, minion, wolf) ''' ),
  ))

  loop.run_until_complete(core.greeting())
  assert posts == [ '[game] greeting(!help, !startimmediate) ' ]
  posts.clear()

################################ MAIN ################################

full_test('vn')
reset_core()
full_test('en')
