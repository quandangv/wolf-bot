import core
import one_night
import classic
import asyncio
import time
import lang.vn as lang
import re

posts = []
members = []
channels = {}
posts_lock = asyncio.Lock()
MAX_ARGS = 10

def generate_send(channel_name):
  async def send(text):
    posts.append('[{}] {}'.format(channel_name, text))
  return send

def low_create_channel(name, *players):
  channel = channels[name] = Channel(name)
  channel.members.extend(players)
  return channel

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

core.DEBUG = True
core.BOT_PREFIX = '!'
core.VOTE_COUNTDOWN = 0.5
core.LANDSLIDE_VOTE_COUNTDOWN = 0.3

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

game = low_create_channel('game')
bot_dm = low_create_channel('@bot')

members = [ anne, bob, carl, david, elsa, frank, george, harry, ignacio ]
admins = [ anne ]

@core.action
async def debug(msg):
  print("ERROR:")
  print(msg)

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
  if key == 'reveal_item':
    return '{}:{}'
  if strip_prefix('cmd_'):
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), key + '_alias' ]
  if strip_prefix('onenight_') or strip_prefix('classic_'):
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), add_formats(key + '_greeting', sample[2]), key + ' alias' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, list):
    sample_result = sample_result[0]
  return add_formats(key, sample_result) + ' '

@core.action
async def get_available_members():
  return members

@core.action
def shuffle_copy(arr):
  return arr[::-1]

one_night.connect(core)
core.initialize(admins)
loop = asyncio.get_event_loop()

async def low_expect_response(coroutine, *response):
  async with posts_lock:
    await coroutine
    try:
      if isinstance(response, str):
        response = [ response ]
      assert len(posts) == len(response), r"""
Expected: {},
     Got: {}""".format(response, posts)
      for idx, r in enumerate(response):
        assert r == posts[idx], r"""At index {},
Expected: {}.
     Got: {}.""".format(idx, r, posts[idx])
    finally:
      posts.clear()
  await core.await_vote_countdown()

async def expect_response(author, message, channel, *response):
  await low_expect_response(core.process_message(Message(author, message, channel)), *response)

def check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  result = [
    expect_response(author, cmd, game, '[game] question({0}) wrong_role({1}) '.format(author.mention, cmd), '[{0}] question({0}) dm_only({1}) '.format(author.mention, cmd)),
    expect_response(author, cmd, bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    expect_response(author, cmd + ' foo,bar', bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] confirm({}) {}'.format(author.mention, success_msg)),
    *([ expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] question({}) ability_used({}) '.format(author.mention, cmd)) ] if single_use else [])
  ]
  return result

def check_private_single_player_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  return [
    expect_response(author, cmd + ' foobar', bot_dm, '[@bot] question({}) player_notfound(foobar) '.format(author.mention)),
    expect_response(author, cmd + ' ' + author.name, bot_dm, '[@bot] question({}) {} '.format(author.mention, no_self_msg)),
    *check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use)
  ]

player_list = 'player_list(anne, bob, carl, david, elsa, frank, george, harry, ignacio) '
loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!save _test_empty', game, '[game] confirm(@anne) save_success(_test_empty) '),
  expect_response(anne, '!info', game, "[game] confirm(@anne) no_roles default_roles(['Wolf', 'Thief', 'Troublemaker', 'Drunk', 'Wolf', 'Villager', 'Seer', 'Clone', 'Minion', 'Insomniac', 'Tanner', 'Villager']) "),
  expect_response(anne, '!help', game, '[game] confirm(@anne) help_list(!help`, `!info`, `!unvote`, `!vote`, `!votenolynch`, `!votedetail`, `!votecount`, `!history`, `!addrole`, `!removerole`, `!startimmediate`, `!closevote`, `!save`, `!load`, `!endgame`, `!wakeup) help_detail(!help) '),
  expect_response(carl, '!help', game, '[game] confirm(@carl) help_list(!help`, `!info`, `!unvote`, `!vote`, `!votenolynch`, `!votedetail`, `!votecount`, `!history) help_detail(!help) '),

  expect_response(anne, '!help help', game, '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
  expect_response(anne, '!help tanner', game, '[game] confirm(@anne) tanner_desc'),
  expect_response(anne, '!help seer', game, '[game] confirm(@anne) seer_desc(2)'),
  expect_response(carl, '!help startimmediate', game, '[game] confirm(@carl) startimmediate_desc(!startimmediate)aliases_list(startimmediate_alias) '),
  expect_response(carl, '!help blabla', game, '[game] confused(`blabla`) '),
  expect_response(anne, '!help_alias help', game, '[game] confirm(@anne) help_desc(!help)aliases_list(help_alias) '),
  expect_response(anne, '!help help_alias', game, '[game] confirm(@anne) alias(help_alias, help) help_desc(!help)'),

  expect_response(anne, '!addrole', game, '[game] question(@anne) add_wronguse(!addrole) '),
  expect_response(anne, '!vote carl', game, '[game] question(@anne) not_playing '),
  expect_response(carl, '!addrole', game, '[game] question(@carl) require_admin '),
  expect_response(anne, '!addrole', game, '[game] question(@anne) add_wronguse(!addrole) '),

  expect_response(anne, '!addrole villager', bot_dm, '[@bot] question(@anne) public_only(!addrole) '),
  expect_response(anne, '!addrole villager, villager, villager', game, '[game] add_success(villager, villager, villager) player_needed(0) '),
  expect_response(anne, '!addrole insomniac', game, '[game] add_success(insomniac) player_needed(1) '),
  expect_response(anne, '!addrole clone,drunk,  troublemaker,thief', game, '[game] add_success(clone, drunk, troublemaker, thief) player_needed(5) '),
  expect_response(anne, '!addrole villager alias, seer', game, '[game] add_success(villager, seer) player_needed(7) '),
  expect_response(anne, '!startimmediate', game, '[game] question(@anne) start_needless(9, 7) '),
  expect_response(anne, '!addrole wolf', game, '[game] add_success(wolf) player_needed(8) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),

  expect_response(anne, '!addrole wolf', game, '[game] add_success(wolf) player_needed(9) '),
  expect_response(anne, '!info', game, '[game] confirm(@anne) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf) player_needed(9) '),
  expect_response(anne, '!startimmediate', game,
    '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf) ',
    '[@anne] role(wolf) wolf_greeting',
    '[@anne] ' + player_list,
    '[@bob] role(wolf) wolf_greeting',
    '[@bob] ' + player_list,
    '[@carl] role(seer) seer_greeting(!reveal, !see)',
    '[@carl] ' + player_list,
    '[@david] role(villager) villager_greeting',
    '[@elsa] role(thief) thief_greeting(!steal)',
    '[@elsa] ' + player_list,
    '[@frank] role(troublemaker) troublemaker_greeting(!swap)',
    '[@frank] ' + player_list,
    '[@george] role(drunk) drunk_greeting(!take)',
    '[@george] ' + player_list,
    '[@harry] role(clone) clone_greeting(!clone)',
    '[@harry] ' + player_list,
    '[@ignacio] role(insomniac) insomniac_greeting',
    '[wolf ] wolf_channel(@anne, @bob) sleep_info(!sleep) '
  )
))

members.append(not_player)

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!help villager ', game, '[game] confirm(@anne) villager_desc'),
  expect_response(anne, '!addrole villager ', game, '[game] question(@anne) forbid_game_started(!addrole) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:wolf\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:thief\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  expect_response(anne, '!swap', game, '[game] question(@anne) wrong_role(!swap) '),
  expect_response(anne, '!swap carl ', bot_dm, '[@bot] question(@anne) wrong_role(!swap) '),
  expect_response(anne, '!swap carl , carl', bot_dm, '[@bot] question(@anne) wrong_role(!swap) '),

  *check_private_single_player_cmd(elsa, '!steal', 'anne', 'thief_wronguse(!steal)', 'no_swap_self', 'thief_success(anne, wolf) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:thief\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  *check_private_single_player_cmd(carl, '!see', 'anne', 'see_wronguse(!see)', 'seer_self', 'see_success(anne, thief) '),
  expect_response(carl, '!reveal', bot_dm, '[@bot] question(@carl) reveal_wronguse(!reveal, 3) '),
  expect_response(carl, '!reveal 2', bot_dm, '[@bot] question(@carl) seer_see_already '),

  expect_response(frank, '!swap frank, elsa', bot_dm, '[@bot] question(@frank) no_swap_self '),
  expect_response(frank, '!swap elsa', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
  expect_response(frank, '!swap ', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!swap) '),
  expect_response(frank, '!swap anne, david', bot_dm, '[@bot] confirm(@frank) troublemaker_success(anne, david) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(frank, '!swap anne, david', bot_dm, '[@bot] question(@frank) ability_used(!swap) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_roles(villager, villager, villager) '),

  expect_response(george, '!take 4', bot_dm, '[@bot] question(@george) choice_outofrange(3) '),
  *check_private_single_arg_cmd(george, '!take', '1', 'drunk_wronguse(!take, 3)', 'no_swap_self', 'drunk_success(1) '),
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:clone\nignacio:insomniac) \nexcess_roles(drunk, villager, villager) '),

  expect_response(harry, '!clone david', bot_dm, '[@harry] clone_success(thief) thief_greeting(!steal)'),
  expect_response(harry, '!steal ignacio', bot_dm, '[@bot] confirm(@harry) thief_success(ignacio, insomniac) '),
  expect_response(harry, '!sleep', bot_dm, '[@bot] confirm(@harry) good_night '),
  expect_response(anne, '!sleep', channels['wolf '], '[wolf ] gone_to_sleep(@anne) sleep_wait_other '),
  expect_response(bob, '!sleep', channels['wolf '], '[wolf ] gone_to_sleep(@bob) all_sleeping ', '[@ignacio] insomniac_reveal(thief) ', '[game] wake_up vote(!vote, !votenolynch) ' ),

  expect_response(harry, '!swap frank', bot_dm, '[@bot] question(@harry) wrong_role(!swap) '),
  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(harry, '!vote frank', bot_dm, '[@harry] question(@harry) public_only(!vote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) remind_unvote(!unvote) '),
  expect_response(harry, '!vote anne', game, '[game] vote_success(@harry, @anne) remind_unvote(!unvote) '),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) remind_unvote(!unvote) '),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) remind_unvote(!unvote) '),

  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!load _test ', game, '[game] confirm(@anne) load_success(_test) '),

  expect_response(elsa, '!vote @harry', game, '[game] vote_success(@elsa, @harry) remind_unvote(!unvote) '),
  expect_response(david, '!vote harry', game, '[game] vote_success(@david, @harry) remind_unvote(!unvote) '),
  expect_response(ignacio, '!vote elsa', game, '[game] vote_success(@ignacio, @elsa) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
  expect_response(not_player, '!votecount', game, '[game] vote_detail(vote_item(@harry, 4) \nvote_item(@anne, 1) \nvote_item(@elsa, 1) ) ', '[game] most_vote(@harry) '),
  expect_response(not_player, '!votedetail', game, '[game] vote_detail(vote_detail_item(anne, @harry) \nvote_detail_item(david, @harry) \nvote_detail_item(elsa, @harry) \nvote_detail_item(frank, @harry) \nvote_detail_item(harry, @anne) \nvote_detail_item(ignacio, @elsa) ) ' ),
  expect_response(bob, '!vote harry', game, '[game] vote_success(@bob, @harry) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@harry, {}) '.format(core.LANDSLIDE_VOTE_COUNTDOWN) ),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) ')
))

members.pop()

loop.run_until_complete(asyncio.gather(
  expect_response(carl, '', game, '[game] vote_result(vote_item(@harry, 5) \nvote_item(@anne, 1) \nvote_item(@elsa, 2) ) ', '[game] lynch(@harry) ', '[game] reveal_player(@harry, insomniac) ', '[game] winners(@bob, @elsa) ', '[game] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:insomniac\nignacio:thief) \nexcess_roles(drunk, villager, villager) ' ),
  expect_response(carl, '!vote elsa', game, '[game] question(@carl) not_playing '),
  expect_response(carl, '!history', game, '[game] history(@anne:wolf\n@bob:wolf\n@carl:seer\n@david:villager\n@elsa:thief\n@frank:troublemaker\n@george:drunk\n@harry:clone\n@ignacio:insomniac, villager, villager, villager, command_item(elsa, !steal anne, wolf) \ncommand_item(carl, !see anne, thief) \ncommand_item_empty(frank, !swap anne, david) \ncommand_item_empty(george, !take 1) \ncommand_item(harry, !clone david, thief) \ncommand_item(harry, !steal ignacio, insomniac) ) '),
))

@core.action
def shuffle_copy(arr):
  return arr[:]

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!removerole', game, '[game] question(@anne) remove_wronguse(!removerole) '),
  expect_response(anne, '!removerole villager', game, '[game] remove_success(villager) player_needed(8) '),
  expect_response(anne, '!removerole villager, villager, villager, wolf', game, '[game] remove_success(villager, villager, villager, wolf) player_needed(4) '),
  expect_response(anne, '!removerole minion', game, '[game] question(@anne) remove_notfound(minion) '),
  expect_response(anne, '!addrole minion, hunter, villager, villager, wolf', game, '[game] add_success(minion, hunter, villager, villager, wolf) player_needed(9) '),
  expect_response(anne, '!startimmediate', game,
    '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(insomniac, clone, drunk, troublemaker, thief, seer, wolf, minion, hunter, villager, villager, wolf) ',
    '[@anne] role(insomniac) insomniac_greeting',
    '[@bob] role(clone) clone_greeting(!clone)',
    '[@bob] ' + player_list,
    '[@carl] role(drunk) drunk_greeting(!take)',
    '[@carl] ' + player_list,
    '[@david] role(troublemaker) troublemaker_greeting(!swap)',
    '[@david] ' + player_list,
    '[@elsa] role(thief) thief_greeting(!steal)',
    '[@elsa] ' + player_list,
    '[@frank] role(seer) seer_greeting(!reveal, !see)',
    '[@frank] ' + player_list,
    '[@george] role(wolf) wolf_greeting',
    '[@george] ' + player_list,
    '[@harry] role(minion) minion_greeting',
    '[@harry] wolves_reveal(george) ',
    '[@ignacio] role(hunter) hunter_greeting',
    '[wolf ] wolf_channel(@george) sleep_info(!sleep) ',
    '[wolf ] wolf_get_reveal(!reveal, 3) '
  )
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!revealall', bot_dm, '[@bot] reveal_all(anne:insomniac\ncarl:drunk\nbob:clone\ndavid:troublemaker\nelsa:thief\nfrank:seer\ngeorge:wolf\nharry:minion\nignacio:hunter) \nexcess_roles(wolf, villager, villager) '),
  expect_response(george, '!reveal 1', game, '[game] question(@george) wrong_role(!reveal) ', '[@george] question(@george) wolf_only(!reveal) ' ),
  expect_response(george, '!reveal 1', channels['wolf '], '[wolf ] confirm(@george) reveal_success(1, wolf) '),
  expect_response(george, '!reveal 1', channels['wolf '], '[wolf ] question(@george) ability_used(!reveal) '),
  expect_response(frank, '!reveal 2', bot_dm, '[@bot] confirm(@frank) reveal_success(2, villager) reveal_remaining(1) '),
  expect_response(frank, '!see george', bot_dm, '[@bot] question(@frank) seer_reveal_already '),
  expect_response(frank, '!reveal 1', bot_dm, '[@bot] confirm(@frank) reveal_success(1, wolf) no_reveal_remaining '),
  expect_response(bob, '!clone george', bot_dm, '[@bob] clone_success(wolf) wolf_greeting', '[wolf ] channel_greeting(@bob, wolf ) ' ),
  expect_response(carl, '!take 1', bot_dm, '[@bot] confirm(@carl) drunk_success(1) '),
  expect_response(david, '!swap elsa, frank', bot_dm, '[@bot] confirm(@david) troublemaker_success(elsa, frank) '),
  expect_response(george, '!sleep', channels['wolf '], '[wolf ] gone_to_sleep(@george) sleep_wait_other '),
  expect_response(bob, '!sleep', channels['wolf '], '[wolf ] gone_to_sleep(@bob) all_sleeping '),
  expect_response(elsa, '!steal harry', bot_dm, '[@anne] insomniac_reveal(insomniac) ', '[game] wake_up vote(!vote, !votenolynch) ', '[@bot] confirm(@elsa) thief_success(harry, minion) ' ),
  expect_response(anne, '!save _test', bot_dm, '[@bot] confirm(@anne) save_success(_test) '),

  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(george, '!vote frank', game, '[game] vote_success(@george, @frank) remind_unvote(!unvote) '),
  expect_response(george, '!vote anne', game, '[game] vote_success(@george, @anne) remind_unvote(!unvote) '),
  expect_response(anne, '!vote george', game, '[game] vote_success(@anne, @george) remind_unvote(!unvote) '),
  expect_response(frank, '!vote george', game, '[game] vote_success(@frank, @george) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote george', game, '[game] vote_success(@elsa, @george) remind_unvote(!unvote) '),
  expect_response(david, '!vote frank', game, '[game] vote_success(@david, @frank) remind_unvote(!unvote) '),
  expect_response(harry, '!vote david', game, '[game] vote_success(@harry, @david) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
  expect_response(harry, '!unvote', game, '[game] unvote_success(@harry) ', '[game] vote_countdown_cancelled ' ),
  expect_response(harry, '!vote elsa', game, '[game] vote_success(@harry, @elsa) remind_unvote(!unvote) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ),
  expect_response(bob, '!vote elsa', game, '[game] vote_success(@bob, @elsa) remind_unvote(!unvote) '),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) '),
  expect_response(not_player, '!votecount', game, '[game] vote_detail(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@george, 3) \nvote_item(@elsa, 3) ) ', '[game] vote_tie ' ),
  expect_response(ignacio, '!vote david', game,
      '[game] vote_success(@ignacio, @david) remind_unvote(!unvote) ',
      '[game] vote_result(vote_item(@frank, 1) \nvote_item(@anne, 1) \nvote_item(@george, 3) \nvote_item(@david, 1) \nvote_item(@elsa, 3) ) ',
      '[game] no_lynch ',
      '[game] winners(@carl, @bob, @elsa, @george) ',
      '[game] reveal_all(anne:insomniac\ncarl:wolf\nbob:wolf\ndavid:troublemaker\nelsa:minion\nfrank:thief\ngeorge:wolf\nharry:seer\nignacio:hunter) \nexcess_roles(drunk, villager, villager) ' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!vote ignacio', game, '[game] vote_success(@anne, @ignacio) remind_unvote(!unvote) '),
  expect_response(bob, '!vote ignacio', game, '[game] vote_success(@bob, @ignacio) remind_unvote(!unvote) '),
  expect_response(carl, '!vote ignacio', game, '[game] vote_success(@carl, @ignacio) remind_unvote(!unvote) '),
  expect_response(david, '!vote ignacio', game, '[game] vote_success(@david, @ignacio) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote ignacio', game, '[game] vote_success(@elsa, @ignacio) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@ignacio, 0.3) '),
  expect_response(frank, '!vote ignacio', game, '[game] vote_success(@frank, @ignacio) remind_unvote(!unvote) '),
  expect_response(george, '!vote ignacio', game, '[game] vote_success(@george, @ignacio) remind_unvote(!unvote) '),
  expect_response(harry, '!vote ignacio', game, '[game] vote_success(@harry, @ignacio) remind_unvote(!unvote) '),
  expect_response(ignacio, '!vote carl', game,
      '[game] vote_success(@ignacio, @carl) remind_unvote(!unvote) ',
      '[game] vote_result(vote_item(@ignacio, 8) \nvote_item(@carl, 1) ) ',
      '[game] hunter_reveal(@ignacio, @carl) ',
      '[game] reveal_player(@carl, wolf) ',
      '[game] winners(@anne, @david, @frank, @harry, @ignacio) ',
      '[game] reveal_all(anne:insomniac\ncarl:wolf\nbob:wolf\ndavid:troublemaker\nelsa:minion\nfrank:thief\ngeorge:wolf\nharry:seer\nignacio:hunter) \nexcess_roles(drunk, villager, villager) '),

  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!votenolynch', game, '[game] no_vote_success(@anne) remind_unvote(!unvote) '),
  expect_response(bob, '!votenolynch', game, '[game] no_vote_success(@bob) remind_unvote(!unvote) '),
  expect_response(carl, '!votenolynch', game, '[game] no_vote_success(@carl) remind_unvote(!unvote) '),
  expect_response(david, '!votenolynch', game, '[game] no_vote_success(@david) remind_unvote(!unvote) '),
  expect_response(elsa, '!votenolynch', game, '[game] no_vote_success(@elsa) remind_unvote(!unvote) ', '[game] landslide_no_vote_countdown(0.3) ' ),
  expect_response(frank, '!votenolynch', game, '[game] no_vote_success(@frank) remind_unvote(!unvote) '),
  expect_response(george, '!votenolynch', game, '[game] no_vote_success(@george) remind_unvote(!unvote) '),
  expect_response(harry, '!votenolynch', game, '[game] no_vote_success(@harry) remind_unvote(!unvote) '),
  expect_response(ignacio, '!votenolynch', game, '[game] no_vote_success(@ignacio) remind_unvote(!unvote) ', '[game] vote_result(vote_item(no_lynch_vote , 9) ) ', '[game] no_lynch ', '[game] winners(@carl, @bob, @elsa, @george) ', '[game] reveal_all(anne:insomniac\ncarl:wolf\nbob:wolf\ndavid:troublemaker\nelsa:minion\nfrank:thief\ngeorge:wolf\nharry:seer\nignacio:hunter) \nexcess_roles(drunk, villager, villager) ' ),
))

core.disconnect()
classic.connect(core)
core.connect(admins)

player_list = 'player_list(anne, bob, carl, david, elsa, frank, george, harry) '
members = [ anne, bob, carl, david, elsa, frank, george, harry ]
loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!startimmediate', game,
      '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry) list_roles(villager, guard, wolf, villager, witch, wolf, detective, drunk, villager, wolfsheep) ',
      '[@anne] role(villager) villager_greeting',
      '[@bob] role(guard) guard_greeting(!defend)',
      '[@bob] ' + player_list,
      '[@carl] role(wolf) wolf_greeting(!kill)',
      '[@carl] ' + player_list,
      '[@david] role(villager) villager_greeting',
      '[@elsa] role(witch) witch_greeting(!poison, !revive, !sleep)',
      '[@elsa] ' + player_list,
      '[@frank] role(wolf) wolf_greeting(!kill)',
      '[@frank] ' + player_list,
      '[@george] role(detective) detective_greeting(!investigate)',
      '[@george] ' + player_list,
      '[@harry] role(drunk) drunk_greeting',
      '[@harry] excess_roles(wolfsheep, villager) drunk_choose_wolf ',
      '[@harry] drunk_took_role(wolfsheep) wolfsheep_greeting(!kill)',
      '[@harry] ' + player_list,
      '[wolf ] wolf_channel(@carl, @frank, @harry) ',
  ),
))

loop.run_until_complete(asyncio.gather(
  expect_response(david, '!sleep', game, '[game] confirm(@david) good_night '),
  expect_response(carl, '!sleep', game, '[game] confirm(@carl) good_night ', '[@carl] question(@carl) wolf_only(!sleep) ' ),
  expect_response(frank, '!kill anne', channels['wolf '], '[wolf ] vote_kill(@frank, anne) wolf_need_consensus '),
  expect_response(bob, '!defend anne', game, '[game] question(@bob) wrong_role(!defend) ', '[@bob] question(@bob) dm_only(!defend) ' ),
  expect_response(bob, '!defend anne', bot_dm, '[@bot] confirm(@bob) defend_success(anne) '),
  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),
  expect_response(george, '!investigate george, carl', bot_dm, '[@bot] confirm(@george) wait '),
  expect_response(bob, '!defend carl', bot_dm, '[@bot] question(@bob) ability_used(!defend) '),
  expect_response(carl, '!kill elsa', channels['wolf '], '[wolf ] vote_kill(@carl, elsa) wolf_need_consensus '),
  expect_response(elsa, '!poison carl', bot_dm, '[@bot] confirm(@elsa) poison_success(carl) ', '[@elsa] remind_sleep(!sleep) '),
  expect_response(harry, '!kill anne', channels['wolf '], '[wolf ] vote_kill(@harry, anne) wolf_need_consensus '),
  expect_response(carl, '!kill anne', channels['wolf '], '[@elsa] witch_no_death ', '[@bot] investigate_diff(george, carl) ', '[game] wake_up_death(@carl) ', '[game] vote(!vote, !votenolynch) ', '[wolf ] vote_kill(@carl, anne) wolf_kill(anne) ' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(bob, '!defend david', bot_dm, '[@bot] question(@bob) ability_used(!defend) '),
  expect_response(carl, '!kill david', channels['wolf '], '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
  expect_response(harry, '!kill david', channels['wolf '], '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
  expect_response(frank, '!kill david', channels['wolf '], '[@elsa] witch_death witch_revive(!revive) ', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ' ),
  expect_response(george, '!investigate frank, carl', bot_dm, '[@bot] investigate_same(frank, carl) '),
  expect_response(elsa, '!revive', bot_dm, '[@bot] confirm(@elsa) revive_success ', '[@elsa] remind_sleep(!sleep) '),
  expect_response(elsa, '!sleep', bot_dm, '[@bot] confirm(@elsa) good_night ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(bob, '!defend david', bot_dm, '[@bot] question(@bob) ability_used(!defend) '),
  expect_response(carl, '!sleep', channels['wolf '], '[wolf ] vote_no_kill(@carl) wolf_need_consensus '),
  expect_response(harry, '!sleep', channels['wolf '], '[wolf ] vote_no_kill(@harry) wolf_need_consensus '),
  expect_response(george, '!investigate elsa, harry', bot_dm, '[@bot] confirm(@george) wait '),
  expect_response(elsa, '!sleep', bot_dm, '[@bot] confirm(@elsa) good_night '),
  expect_response(frank, '!sleep', channels['wolf '], '[@elsa] witch_no_death ', '[@bot] investigate_same(elsa, harry) ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ', '[wolf ] vote_no_kill(@frank) wolf_no_kill ' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(bob, '!defend david', bot_dm, '[@bot] question(@bob) ability_used(!defend) '),
  expect_response(carl, '!kill david', channels['wolf '], '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
  expect_response(harry, '!kill david', channels['wolf '], '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
  expect_response(frank, '!kill david', channels['wolf '], '[@elsa] witch_death witch_revive(!revive) ', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ' ),
  expect_response(carl, '!kill carl', channels['wolf '], '[wolf ] question(@carl) kill_already '),
  expect_response(elsa, '!sleep', bot_dm, '[@bot] confirm(@elsa) good_night '),
  expect_response(george, '!investigate elsa, bob', bot_dm, '[@bot] investigate_same(elsa, bob) ', '[game] wake_up_death(@david) ', '[game] vote(!vote, !votenolynch) ' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(carl, '!kill david', channels['wolf '], '[wolf ] vote_kill(@carl, david) wolf_need_consensus '),
  expect_response(elsa, '!revive', bot_dm, '[@bot] confirm(@elsa) wait '),
  expect_response(elsa, '!sleep', bot_dm, '[@bot] confirm(@elsa) good_night '),
  expect_response(george, '!investigate elsa, bob', bot_dm, '[@bot] confirm(@george) wait '),
  expect_response(harry, '!kill david', channels['wolf '], '[wolf ] vote_kill(@harry, david) wolf_need_consensus '),
  expect_response(frank, '!kill david', channels['wolf '], '[@elsa] witch_death ', '[@bot] confirm(@elsa) revive_success ', '[@bot] investigate_same(elsa, bob) ', '[game] wake_up_no_death ', '[game] vote(!vote, !votenolynch) ', '[wolf ] vote_kill(@frank, david) wolf_kill(david) ' ),
  expect_response(anne, '!save _test', game, '[game] confirm(@anne) save_success(_test) '),

  expect_response(anne, '!vote elsa', game, '[game] vote_success(@anne, @elsa) remind_unvote(!unvote) '),
  expect_response(bob, '!vote elsa', game, '[game] vote_success(@bob, @elsa) remind_unvote(!unvote) '),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) remind_unvote(!unvote) '),
  expect_response(david, '!vote elsa', game, '[game] vote_success(@david, @elsa) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote elsa', game, '[game] vote_success(@elsa, @elsa) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@elsa, 0.3) ' ),
  expect_response(frank, '!vote elsa', game, '[game] vote_success(@frank, @elsa) remind_unvote(!unvote) '),
  expect_response(harry, '!vote elsa', game, '[game] vote_success(@harry, @elsa) remind_unvote(!unvote) '),
  expect_response(george, '!vote elsa', game, '[game] vote_success(@george, @elsa) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@elsa, 8) ) ', '[game] lynch(@elsa) ', '[game] go_to_sleep ' ),
  expect_response(elsa, '!poison david', bot_dm, '[@bot] question(@elsa) dead '),
  expect_response(bob, '!defend anne', bot_dm, '[@bot] question(@bob) defend_repeat '),
  expect_response(bob, '!defend david', bot_dm, '[@bot] confirm(@bob) defend_success(david) '),
  expect_response(carl, '!kill bob', channels['wolf '], '[wolf ] vote_kill(@carl, bob) wolf_need_consensus '),
  expect_response(harry, '!kill bob', channels['wolf '], '[wolf ] vote_kill(@harry, bob) wolf_need_consensus '),
  expect_response(frank, '!kill bob', channels['wolf '], '[wolf ] vote_kill(@frank, bob) wolf_kill(bob) '),
  expect_response(george, '!investigate george, bob', bot_dm, '[@bot] investigate_same(george, bob) ', '[game] wake_up_death(@bob) ', '[game] wolf_victory ', '[game] winners(@carl, @frank, @harry) ', r'''[game] reveal_all(anne:villager
bob:guard
carl:wolf
david:villager
elsa:witch
frank:wolf
george:detective
harry:wolfsheep) 
excess_roles(villager) ''' ),

  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!vote carl', game, '[game] vote_success(@anne, @carl) remind_unvote(!unvote) '),
  expect_response(bob, '!vote carl', game, '[game] vote_success(@bob, @carl) remind_unvote(!unvote) '),
  expect_response(carl, '!vote carl', game, '[game] vote_success(@carl, @carl) remind_unvote(!unvote) '),
  expect_response(david, '!vote carl', game, '[game] vote_success(@david, @carl) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote carl', game, '[game] vote_success(@elsa, @carl) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@carl, 0.3) ' ),
  expect_response(frank, '!vote carl', game, '[game] vote_success(@frank, @carl) remind_unvote(!unvote) '),
  expect_response(harry, '!vote carl', game, '[game] vote_success(@harry, @carl) remind_unvote(!unvote) '),
  expect_response(george, '!vote carl', game, '[game] vote_success(@george, @carl) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@carl, 8) ) ', '[game] lynch(@carl) ', '[game] go_to_sleep ' ),
  expect_response(bob, '!defend elsa', bot_dm, '[@bot] confirm(@bob) defend_success(elsa) '),
  expect_response(elsa, '!poison harry', bot_dm, '[@bot] confirm(@elsa) poison_success(harry) '),
  expect_response(carl, '!kill elsa', channels['wolf '], '[wolf ] question(@carl) dead '),
  expect_response(harry, '!kill elsa', channels['wolf '], '[wolf ] vote_kill(@harry, elsa) wolf_need_consensus '),
  expect_response(frank, '!kill elsa', channels['wolf '], '[@elsa] witch_no_death ', '[wolf ] vote_kill(@frank, elsa) wolf_kill(elsa) ' ),
  expect_response(george, '!investigate elsa, harry', bot_dm, '[@bot] investigate_same(elsa, harry) ', '[game] wake_up_death(@harry) ', '[game] vote(!vote, !votenolynch) ' ),
  expect_response(anne, '!vote frank', game, '[game] vote_success(@anne, @frank) remind_unvote(!unvote) '),
  expect_response(bob, '!vote frank', game, '[game] vote_success(@bob, @frank) remind_unvote(!unvote) '),
  expect_response(carl, '!vote frank', game, '[game] vote_success(@carl, @frank) remind_unvote(!unvote) '),
  expect_response(david, '!vote frank', game, '[game] vote_success(@david, @frank) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote frank', game, '[game] vote_success(@elsa, @frank) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@frank, 0.3) ' ),
  expect_response(frank, '!vote frank', game, '[game] vote_success(@frank, @frank) remind_unvote(!unvote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) remind_unvote(!unvote) '),
  expect_response(george, '!vote frank', game, '[game] vote_success(@george, @frank) remind_unvote(!unvote) ', '[game] vote_result(vote_item(@frank, 8) ) ', '[game] lynch(@frank) ', '[game] village_victory ', '[game] winners(@anne, @bob, @david, @elsa, @george) ', r'''[game] reveal_all(anne:villager
bob:guard
carl:wolf
david:villager
elsa:witch
frank:wolf
george:detective
harry:wolfsheep) 
excess_roles(villager) ''' ),
  expect_response(anne, '!load _test', game, '[game] confirm(@anne) load_success(_test) '),
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!votenolynch', game, '[game] no_vote_success(@anne) remind_unvote(!unvote) '),
  expect_response(bob, '!votenolynch', game, '[game] no_vote_success(@bob) remind_unvote(!unvote) '),
  expect_response(carl, '!votenolynch', game, '[game] no_vote_success(@carl) remind_unvote(!unvote) '),
  expect_response(david, '!votenolynch', game, '[game] no_vote_success(@david) remind_unvote(!unvote) '),
  expect_response(elsa, '!votenolynch', game, '[game] no_vote_success(@elsa) remind_unvote(!unvote) ', '[game] landslide_no_vote_countdown(0.3) ' ),
  expect_response(frank, '!votenolynch', game, '[game] no_vote_success(@frank) remind_unvote(!unvote) '),
  expect_response(harry, '!votenolynch', game, '[game] no_vote_success(@harry) remind_unvote(!unvote) '),
  expect_response(george, '!votenolynch', game, '[game] no_vote_success(@george) remind_unvote(!unvote) ', '[game] vote_result(vote_item(no_lynch_vote , 8) ) ', '[game] no_lynch ', '[game] go_to_sleep ' ),
))

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!addrole villager, guard, wolf, wolfsheep, witch, wolf, detective, drunk, villager, villager', game, '[game] add_success(villager, guard, wolf, wolfsheep, witch, wolf, detective, drunk, villager, villager) player_needed(8) '),
  expect_response(anne, '!startimmediate', game,
      '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry) list_roles(villager, guard, wolf, wolfsheep, witch, wolf, detective, drunk, villager, villager) ',
      '[@anne] role(villager) villager_greeting',
      '[@bob] role(guard) guard_greeting(!defend)',
      '[@bob] ' + player_list,
      '[@carl] role(wolf) wolf_greeting(!kill)',
      '[@carl] ' + player_list,
      '[@david] role(wolfsheep) wolfsheep_greeting(!kill)',
      '[@david] ' + player_list,
      '[@elsa] role(witch) witch_greeting(!poison, !revive, !sleep)',
      '[@elsa] ' + player_list,
      '[@frank] role(wolf) wolf_greeting(!kill)',
      '[@frank] ' + player_list,
      '[@george] role(detective) detective_greeting(!investigate)',
      '[@george] ' + player_list,
      '[@harry] role(drunk) drunk_greeting',
      '[@harry] excess_roles(villager, villager) drunk_choose(!take) ',
      '[@harry] ' + player_list,
  ),
  expect_response(harry, '!take vilager', bot_dm, '[@bot] confused(`vilager`) '),
  expect_response(harry, '!take wolf', bot_dm, '[@bot] question(@harry) take_notavailable(wolf, villager, villager) '),
  expect_response(harry, '!take villager', bot_dm, '[@harry] drunk_took_role(villager) villager_greeting', '[wolf ] wolf_channel(@carl, @david, @frank) '),
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
  expect_response(anne, '!load _test_empty', game, '[game] confirm(@anne) load_success(_test_empty) '),
  expect_response(anne, '!startimmediate', game,
      '[game] start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) list_roles(wolf, thief, troublemaker, drunk, wolf, villager, seer, clone, minion, insomniac, tanner, villager) ',
      '[@anne] role(tanner) tanner_greeting',
      '[@bob] role(thief) thief_greeting(!steal)',
      '[@bob] ' + player_list,
      '[@carl] role(troublemaker) troublemaker_greeting(!swap)',
      '[@carl] ' + player_list,
      '[@david] role(drunk) drunk_greeting(!take)',
      '[@david] ' + player_list,
      '[@elsa] role(villager) villager_greeting',
      '[@frank] role(villager) villager_greeting',
      '[@george] role(seer) seer_greeting(!reveal, !see)',
      '[@george] ' + player_list,
      '[@harry] role(clone) clone_greeting(!clone)',
      '[@harry] ' + player_list,
      '[@ignacio] role(insomniac) insomniac_greeting',
  ),
  expect_response(anne, '!wakeup', game, '[@ignacio] insomniac_reveal(insomniac) ', '[game] wake_up vote(!vote, !votenolynch) ' ),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) remind_unvote(!unvote) '),
  expect_response(bob, '!vote harry', game, '[game] vote_success(@bob, @harry) remind_unvote(!unvote) '),
  expect_response(elsa, '!vote harry', game, '[game] vote_success(@elsa, @harry) remind_unvote(!unvote) '),
  expect_response(david, '!vote harry', game, '[game] vote_success(@david, @harry) remind_unvote(!unvote) '),
  expect_response(carl, '!vote harry', game, '[game] vote_success(@carl, @harry) remind_unvote(!unvote) ', '[game] landslide_vote_countdown(@harry, {}) '.format(core.LANDSLIDE_VOTE_COUNTDOWN) ),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) remind_unvote(!unvote) '),
  expect_response(george, '!vote harry', game, '[game] vote_success(@george, @harry) remind_unvote(!unvote) '),
  expect_response(ignacio, '!vote harry', game, '[game] vote_success(@ignacio, @harry) remind_unvote(!unvote) '),
  expect_response(harry, '!vote harry', game, '[game] vote_success(@harry, @harry) remind_unvote(!unvote) ',
      '[game] vote_result(vote_item(@harry, 9) ) ',
      '[game] lynch(@harry) ',
      '[game] reveal_player(@harry, clone) ',
      '[game] no_winners ',
      r'''[game] reveal_all(anne:tanner
bob:thief
carl:troublemaker
david:drunk
elsa:villager
frank:villager
george:seer
harry:clone
ignacio:insomniac) 
excess_roles(wolf, minion, wolf) ''' ),
))

loop.run_until_complete(core.greeting())
assert posts == [ '[game] greeting(!help, !startimmediate) ' ]
