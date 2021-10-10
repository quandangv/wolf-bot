import core
import asyncio
import time
import lang.vn as lang
import re

posts = []
members = []
channels = {}
posts_lock = asyncio.Lock()

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
    self.name = name
    self.send = generate_send(name)
    self.members = []
    channels[name] = self

  def delete(self):
    del channels[self.name]
    del self.name
    del self.send

class Message:
  def __init__(self, author, content, channel):
    self.content = content
    self.author = author
    self.channel = channel

class Member:
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.mention = '@' + name
    self.dm_channel = low_create_channel(self.mention, self)

core.DEBUG = True
core.BOT_PREFIX = '!'
core.VOTE_COUNTDOWN = 0.5

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
  def strip_prefix(prefix):
    nonlocal key
    if key.startswith(prefix):
      key = key[len(prefix):]
      return True

  def add_formats(key, sample):
    arg_count = 0
    tokens = []
    while True:
      batch = re.findall('{' + str(arg_count) + '.*?}', sample)
      if not batch: break
      for token in batch:
        if not token in tokens:
          tokens.append(token)
      arg_count += 1

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
    sample = getattr(lang, 'cmd_' + key)
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), key + '_alias' ]
  if strip_prefix('role_'):
    sample = getattr(lang, 'role_' + key)
    return [ add_formats(key, sample[0]), add_formats(key + '_desc', sample[1]), add_formats(key + '_greeting', sample[2]), key + ' alias' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, list):
    sample_result = sample_result[0]
  return add_formats(key, sample_result) + ' '

@core.action
def get_available_members():
  return members

@core.action
def shuffle_copy(arr):
  return arr[::-1]

core.initialize(admins)
loop = asyncio.get_event_loop()

async def low_expect_response(coroutine, response):
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
      del posts[:]
  if core.vote_countdown_task:
    await core.vote_countdown_task

async def expect_response(author, message, channel, response):
  await low_expect_response(core.process_message(Message(author, message, channel)), response)

def check_private_single_arg_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg, single_use = True):
  result = [
    expect_response(author, cmd, game, '[game] question({}) dm_only({}) '.format(author.mention, cmd)),
    expect_response(author, cmd, bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
    expect_response(author, cmd + ' foo bar', bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg)),
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

loop = asyncio.get_event_loop()
loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!help', game, '[game] confirm(@anne) help_list(!help`, `!add_role`, `!remove_role`, `!list_roles`, `!start_immediate`, `!close_vote`, `!end_game`, `!reveal_all) '),
  expect_response(carl, '!help', game, '[game] confirm(@carl) help_list(!help`, `!list_roles`, `!reveal_all) '),

  expect_response(anne, '!help help', game, '[game] confirm(@anne) help_desc(!help)'),
  expect_response(anne, '!help tanner', game, '[game] confirm(@anne) tanner_desc'),
  expect_response(anne, '!help seer', game, '[game] confirm(@anne) seer_desc(2)'),
  expect_response(carl, '!help start_immediate', game, '[game] confirm(@carl) start_immediate_desc(!start_immediate)'),
  expect_response(carl, '!help blabla', game, '[game] confused(`blabla`) '),
  expect_response(anne, '!help_alias help', game, '[game] confirm(@anne) help_desc(!help)'),
  expect_response(anne, '!help help_alias', game, '[game] confirm(@anne) alias(help_alias, help) help_desc(!help)'),

  expect_response(anne, '!add_role', game, '[game] question(@anne) add_wronguse(!) '),
  expect_response(anne, '!vote carl', game, '[game] question(@anne) not_playing '),
  expect_response(carl, '!add_role', game, '[game] question(@carl) require_admin '),

  expect_response(anne, '!add_role villager', bot_dm, '[@bot] question(@anne) public_only(!add_role) '),
  expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) '),
  expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) '),
  expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) '),
  expect_response(anne, '!add_role insomniac', game, '[game] confirm(@anne) add_success(insomniac) '),
  expect_response(anne, '!add_role clone', game, '[game] confirm(@anne) add_success(clone) '),
  expect_response(anne, '!add_role drunk', game, '[game] confirm(@anne) add_success(drunk) '),
  expect_response(anne, '!add_role troublemaker', game, '[game] confirm(@anne) add_success(troublemaker) '),
  expect_response(anne, '!add_role thief', game, '[game] confirm(@anne) add_success(thief) '),
  expect_response(anne, '!add_role villager alias', game, '[game] confirm(@anne) add_success(villager alias) '),
  expect_response(anne, '!add_role seer', game, '[game] confirm(@anne) add_success(seer) '),
  expect_response(anne, '!start_immediate', game, '[game] question(@anne) start_needless(9, 7) '),
  expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) '),
  expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) '),
  expect_response(anne, '!list_roles', game, '[game] confirm(@anne) list_roles(villager, villager, villager, insomniac, clone, drunk, troublemaker, thief, villager, seer, wolf, wolf, 9) '),
  expect_response(anne, '!start_immediate', game, [
    '[game] confirm(@anne) start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) ',
    '[@anne] role(wolf) wolf_greeting',
    '[@bob] role(wolf) wolf_greeting',
    '[wolf ] channel_greeting(@bob, wolf ) ',
    '[@carl] role(seer) seer_greeting(!)',
    '[@david] role(villager) villager_greeting',
    '[@elsa] role(thief) thief_greeting(!)',
    '[@frank] role(troublemaker) troublemaker_greeting(!)',
    '[@george] role(drunk) drunk_greeting(!)',
    '[@harry] role(clone) clone_greeting(!)',
    '[@ignacio] role(insomniac) insomniac_greeting',
    '[wolf ] wolf_channel(@anne, @bob) '
  ])
))

members.append(not_player)

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!add_role villager ', game, '[game] question(@anne) forbid_game_started(!add_role) '),
  expect_response(anne, '!reveal_all', bot_dm, '[@bot] reveal_all(anne:wolf\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:thief\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_cards(villager, villager, villager) '),

  expect_response(anne, '!swap', game, '[game] question(@anne) dm_only(!swap) '),
  expect_response(anne, '!swap carl', bot_dm, '[@bot] question(@anne) wrong_role(!swap) '),

  *check_private_single_player_cmd(elsa, '!steal', 'anne', 'thief_wronguse(!)', 'no_swap_self', 'thief_success(anne, wolf) '),
  expect_response(anne, '!reveal_all', bot_dm, '[@bot] reveal_all(anne:thief\ncarl:seer\nbob:wolf\ndavid:villager\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_cards(villager, villager, villager) '),

  *check_private_single_player_cmd(carl, '!see', 'anne', 'see_wronguse(!)', 'seer_self', 'see_success(anne, thief) '),
  expect_response(carl, '!reveal', bot_dm, '[@bot] question(@carl) reveal_wronguse(!, 3) '),
  expect_response(carl, '!reveal 2', bot_dm, '[@bot] question(@carl) seer_see_already '),

  expect_response(frank, '!swap frank elsa', bot_dm, '[@bot] question(@frank) no_swap_self '),
  expect_response(frank, '!swap elsa', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!) '),
  expect_response(frank, '!swap ', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!) '),
  expect_response(frank, '!swap anne david', bot_dm, '[@bot] confirm(@frank) troublemaker_success(anne, david) '),
  expect_response(frank, '!swap anne david', bot_dm, '[@bot] question(@frank) ability_used(!swap) '),
  expect_response(anne, '!reveal_all', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:drunk\nharry:clone\nignacio:insomniac) \nexcess_cards(villager, villager, villager) '),

  expect_response(george, '!take 4', bot_dm, '[@bot] question(@george) choice_outofrange(3) '),
  *check_private_single_arg_cmd(george, '!take', '1', 'drunk_wronguse(!, 3)', 'no_swap_self', 'drunk_success(1) '),
  expect_response(anne, '!reveal_all', bot_dm, '[@bot] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:clone\nignacio:insomniac) \nexcess_cards(drunk, villager, villager) '),

  *check_private_single_player_cmd(harry, '!clone', 'david', 'clone_wronguse(!)', 'clone_self', 'clone_success(david, thief) thief_greeting(!)', False),
  expect_response(harry, '!steal ignacio', bot_dm, [ '[@ignacio] insomniac_reveal(thief) ', '[game] wake_up vote(!) ', '[@bot] confirm(@harry) thief_success(ignacio, insomniac) ' ]),

  expect_response(harry, '!swap frank', bot_dm, '[@bot] question(@harry) night_only '),
  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(harry, '!vote frank', bot_dm, '[@bot] question(@harry) public_only(!vote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) '),
  expect_response(harry, '!vote anne', game, '[game] vote_success(@harry, @anne) '),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) '),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) '),
  expect_response(elsa, '!vote david', game, '[game] vote_success(@elsa, @david) '),
  expect_response(david, '!vote frank', game, '[game] vote_success(@david, @frank) '),
  expect_response(ignacio, '!vote elsa', game, '[game] vote_success(@ignacio, @elsa) '),
  expect_response(bob, '!vote harry', game, [ '[game] vote_success(@bob, @harry) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ]),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) ')
))

members.pop()

loop.run_until_complete(asyncio.gather(
  expect_response(carl, '', game, [ '[game] vote_result(vote_item(@anne, harry) \nvote_item(@carl, elsa) \nvote_item(@bob, harry) \nvote_item(@david, frank) \nvote_item(@elsa, david) \nvote_item(@frank, harry) \nvote_item(@harry, anne) \nvote_item(@ignacio, elsa) ) ', '[game] lynch(harry) ', '[game] end_game(@bob, @elsa) ', '[game] reveal_player(@harry, insomniac) ', '[game] reveal_all(anne:villager\ncarl:seer\nbob:wolf\ndavid:thief\nelsa:wolf\nfrank:troublemaker\ngeorge:villager\nharry:insomniac\nignacio:thief) \nexcess_cards(drunk, villager, villager) ' ]),
  expect_response(carl, '!vote elsa', game, '[game] question(@carl) not_playing ')
))

@core.action
def shuffle_copy(arr):
  return arr[:]

loop.run_until_complete(asyncio.gather(
  expect_response(anne, '!remove_role villager', game, '[game] confirm(@anne) remove_success(villager) '),
  expect_response(anne, '!remove_role villager', game, '[game] confirm(@anne) remove_success(villager) '),
  expect_response(anne, '!remove_role villager', game, '[game] confirm(@anne) remove_success(villager) '),
  expect_response(anne, '!remove_role wolf', game, '[game] confirm(@anne) remove_success(wolf) '),
  expect_response(anne, '!remove_role minion', game, '[game] question(@anne) remove_notfound(minion) '),
  expect_response(anne, '!add_role minion', game, '[game] confirm(@anne) add_success(minion) '),
  expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) '),
  expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) '),
  expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) '),
  expect_response(anne, '!start_immediate', game, [
    '[game] confirm(@anne) start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) ',
    '[@anne] role(insomniac) insomniac_greeting',
    '[@bob] role(clone) clone_greeting(!)',
    '[@carl] role(drunk) drunk_greeting(!)',
    '[@david] role(troublemaker) troublemaker_greeting(!)',
    '[@elsa] role(thief) thief_greeting(!)',
    '[@frank] role(villager) villager_greeting',
    '[@george] role(seer) seer_greeting(!)',
    '[@harry] role(wolf) wolf_greeting',
    '[@ignacio] role(minion) minion_greeting',
    '[@ignacio] wolves_reveal(harry) ',
    '[wolf ] wolf_channel(@harry) ',
    '[wolf ] wolf_get_reveal(!, 3) '
  ]),
  expect_response(anne, '!reveal_all', bot_dm, '[@bot] reveal_all(anne:insomniac\ncarl:drunk\nbob:clone\ndavid:troublemaker\nelsa:thief\nfrank:villager\ngeorge:seer\nharry:wolf\nignacio:minion) \nexcess_cards(wolf, villager, villager) '),
  expect_response(harry, '!reveal 1', game, '[game] question(@harry) dm_only(!reveal) '),
  expect_response(harry, '!reveal 1', bot_dm, '[@bot] confirm(@harry) reveal_success(1, wolf) '),
  expect_response(harry, '!reveal 1', bot_dm, '[@bot] question(@harry) ability_used(!reveal) '),
  expect_response(george, '!reveal 2', bot_dm, '[@bot] confirm(@george) reveal_success(2, villager) '),
  expect_response(george, '!see harry', bot_dm, '[@bot] question(@george) seer_reveal_already '),
  expect_response(george, '!reveal 1', bot_dm, '[@bot] confirm(@george) reveal_success(1, wolf) '),
  expect_response(bob, '!clone harry', bot_dm, [ '[wolf ] channel_greeting(@bob, wolf ) ', '[@bot] confirm(@bob) clone_success(harry, wolf) wolf_greeting' ]),
  expect_response(carl, '!take 1', bot_dm, '[@bot] confirm(@carl) drunk_success(1) '),
  expect_response(david, '!swap elsa george', bot_dm, '[@bot] confirm(@david) troublemaker_success(elsa, george) '),
  expect_response(elsa, '!steal ignacio', bot_dm, [ '[@anne] insomniac_reveal(insomniac) ', '[game] wake_up vote(!) ', '[@bot] confirm(@elsa) thief_success(ignacio, minion) ' ]),
  expect_response(not_player, '!vote frank', bot_dm, '[@bot] question(@not_player) not_playing '),
  expect_response(harry, '!vote frank', bot_dm, '[@bot] question(@harry) public_only(!vote) '),
  expect_response(harry, '!vote frank', game, '[game] vote_success(@harry, @frank) '),
  expect_response(harry, '!vote anne', game, '[game] vote_success(@harry, @anne) '),
  expect_response(anne, '!vote harry', game, '[game] vote_success(@anne, @harry) '),
  expect_response(frank, '!vote harry', game, '[game] vote_success(@frank, @harry) '),
  expect_response(elsa, '!vote david', game, '[game] vote_success(@elsa, @david) '),
  expect_response(david, '!vote frank', game, '[game] vote_success(@david, @frank) '),
  expect_response(ignacio, '!vote elsa', game, '[game] vote_success(@ignacio, @elsa) '),
  expect_response(bob, '!vote harry', game, [ '[game] vote_success(@bob, @harry) ', '[game] vote_countdown({}) '.format(core.VOTE_COUNTDOWN) ]),
  expect_response(carl, '!vote elsa', game, '[game] vote_success(@carl, @elsa) '),
  expect_response(george, '!vote elsa', game, [ '[game] vote_success(@george, @elsa) ', '[game] vote_result(vote_item(@anne, harry) \nvote_item(@carl, elsa) \nvote_item(@bob, harry) \nvote_item(@david, frank) \nvote_item(@elsa, david) \nvote_item(@frank, harry) \nvote_item(@george, elsa) \nvote_item(@harry, anne) \nvote_item(@ignacio, elsa) ) ', '[game] lynch(harry) ', '[game] end_game(@anne, @david, @frank, @george, @ignacio) ', '[game] reveal_player(@harry, wolf) ', '[game] reveal_all(anne:insomniac\ncarl:wolf\nbob:wolf\ndavid:troublemaker\nelsa:minion\nfrank:villager\ngeorge:thief\nharry:wolf\nignacio:seer) \nexcess_cards(drunk, villager, villager) ' ]),
))
