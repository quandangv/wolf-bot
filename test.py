import core
import asyncio
import lang.vn as lang

posts = []
members = []
channels = {}

def generate_send(channel_name):
  async def send(text):
    posts.append('[{}] {}'.format(channel_name, text))
  return send

def low_create_channel(name, *players):
  channel = channels[name] = Channel(name)
  channel.members.extend(players)
  return channel

core.DEBUG = True

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
  if key == '_and':
    return ''
  if strip_prefix('cmd_'):
    return [ key, key + '_desc ', key + '_alias' ]
  if strip_prefix('role_'):
    return [ key, key + '_desc ', key + '_greeting', key + '_alias' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, tuple):
    sample_result = sample_result[0]
  if '{0}' in sample_result:
    arg_count = 2
    while ('{' + str(arg_count-1) + '}') in sample_result:
      arg_count = arg_count + 1
    arg_count = arg_count - 1
  else:
    arg_count = sample_result.count('{') - sample_result.count('{{') * 2
  return (key if arg_count == 0 else '{}({})'.format(key, ', '.join(['{}'] * arg_count))) + ' '

@core.action
def get_available_members():
  return members

@core.action
def shuffle_copy(arr):
  return arr[::-1]

class Channel:
  def __init__(self, name):
    self.name = name
    self.send = generate_send(name)
    self.members = []
    channels[name] = self

  def delete():
    del channels[name]
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

anne = Member(0, 'anne')
bob = Member(1, 'bob')
carl = Member(2, 'carl')
david = Member(3, 'david')
elsa = Member(4, 'elsa')
frank = Member(5, 'frank')
george = Member(6, 'george')
harry = Member(7, 'harry')
ignacio = Member(8, 'ignacio')

game = low_create_channel('game')
bot_dm = low_create_channel('@bot')

members = [ anne, bob, carl, david, elsa, frank, george, harry, ignacio ]
admins = [ anne ]

core.BOT_PREFIX = '!'
core.initialize(admins)

loop = asyncio.get_event_loop()

def low_expect_response(coroutine, response):
  loop.run_until_complete(coroutine)

  if isinstance(response, str):
    assert len(posts) == 1, r"""
Expected: [{}].
  Actual: {}""".format(response, posts)
    assert posts[0] == response, r"""
Unexpected response: {}.
           Expected: {}.""".format(posts[0], response)
  else:
    assert len(posts) == len(response), "Expected {} responses, got {} responses: {}".format(len(response), len(posts), posts)
    for idx, r in enumerate(response):
      assert r == posts[idx], r"""At index {},
Expected: {}.
     Got: {}.""".format(idx, r, posts[idx])
    
  del posts[:]

def expect_response(author, message, channel, response):
  low_expect_response(core.process_message(Message(author, message, channel)), response)

def check_private_single_arg_single_use_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg):
  expect_response(author, cmd, game, '[game] question({}) dm_only({}) '.format(author.mention, cmd))
  expect_response(author, cmd, bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg))
  expect_response(author, cmd + ' foo bar', bot_dm, '[@bot] question({}) {} '.format(author.mention, wronguse_msg))
  expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] confirm({}) {} '.format(author.mention, success_msg))
  expect_response(author, cmd + ' ' + target, bot_dm, '[@bot] question({}) ability_used({}) '.format(author.mention, cmd))

def check_private_single_player_single_use_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg):
  expect_response(author, cmd + ' foobar', bot_dm, '[@bot] question({}) player_notfound(foobar) '.format(author.mention))
  expect_response(author, cmd + ' ' + author.name, bot_dm, '[@bot] question({}) {} '.format(author.mention, no_self_msg))
  check_private_single_arg_single_use_cmd(author, cmd, target, wronguse_msg, no_self_msg, success_msg)

expect_response(anne, '!help', game, '[game] confirm(@anne) help_list(!help`, `!add_role`, `!list_roles`, `!start_immediate`, `!reveal_all) ')
expect_response(carl, '!help', game, '[game] confirm(@carl) help_list(!help`, `!list_roles`, `!reveal_all) ')

expect_response(anne, '!help help', game, '[game] confirm(@anne) help_desc ')
expect_response(carl, '!help start_immediate', game, '[game] confirm(@carl) start_immediate_desc ')
expect_response(carl, '!help blabla', game, '[game] confused(`blabla`) ')
expect_response(anne, '!help_alias help', game, '[game] confirm(@anne) help_desc ')
expect_response(anne, '!help help_alias', game, '[game] confirm(@anne) alias(help_alias, help) help_desc ')

expect_response(anne, '!add_role', game, '[game] question(@anne) add_wronguse(!) ')
expect_response(carl, '!add_role', game, '[game] question(@carl) require_admin ')

expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role villager', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role drunk', game, '[game] confirm(@anne) add_success(drunk) ')
expect_response(anne, '!add_role troublemaker', game, '[game] confirm(@anne) add_success(troublemaker) ')
expect_response(anne, '!add_role thief', game, '[game] confirm(@anne) add_success(thief) ')
expect_response(anne, '!add_role villager_alias', game, '[game] confirm(@anne) add_success(villager) ')
expect_response(anne, '!add_role seer', game, '[game] confirm(@anne) add_success(seer) ')
expect_response(anne, '!start_immediate', game, '[game] question(@anne) start_needless(9, 7) ')
expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) ')
expect_response(anne, '!add_role wolf', game, '[game] confirm(@anne) add_success(wolf) ')
expect_response(anne, '!list_roles', game, '[game] confirm(@anne) list_roles(villager, villager, villager, villager, villager, drunk, troublemaker, thief, villager, seer, wolf, wolf, 9) ')
expect_response(anne, '!start_immediate', game, ['[game] confirm(@anne) start(@anne, @bob, @carl, @david, @elsa, @frank, @george, @harry, @ignacio) ', '[@anne] role(wolf) wolf_greeting', '[@bob] role(wolf) wolf_greeting', '[@carl] role(seer) seer_greeting', '[@david] role(villager) villager_greeting', '[@elsa] role(thief) thief_greeting', '[@frank] role(troublemaker) troublemaker_greeting', '[@george] role(drunk) drunk_greeting', '[@harry] role(villager) villager_greeting', '[@ignacio] role(villager) villager_greeting', '[wolf ] wolf_channel(@anne, @bob) '])

expect_response(anne, '!reveal_all', bot_dm, '[@bot] confirm(@anne) anne:wolf, carl:seer, bob:wolf, david:villager, elsa:thief, frank:troublemaker, george:drunk, harry:villager, ignacio:villager; excess: villager, villager, villager')

expect_response(anne, '!swap', game, '[game] question(@anne) dm_only(!swap) ')
expect_response(anne, '!swap carl', bot_dm, '[@bot] question(@anne) wrong_role(!swap) ')

check_private_single_player_single_use_cmd(elsa, '!swap', 'anne', 'thief_wronguse(!)', 'no_swap_self', 'thief_success(anne)')
expect_response(anne, '!reveal_all', bot_dm, '[@bot] confirm(@anne) anne:thief, carl:seer, bob:wolf, david:villager, elsa:wolf, frank:troublemaker, george:drunk, harry:villager, ignacio:villager; excess: villager, villager, villager')

check_private_single_player_single_use_cmd(carl, '!see', 'anne', 'see_wronguse(!)', 'seer_self', 'see_success(anne, thief)')

expect_response(frank, '!swap frank elsa', bot_dm, '[@bot] question(@frank) no_swap_self ')
expect_response(frank, '!swap elsa', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!) ')
expect_response(frank, '!swap ', bot_dm, '[@bot] question(@frank) troublemaker_wronguse(!) ')
expect_response(frank, '!swap anne david', bot_dm, '[@bot] confirm(@frank) troublemaker_success(anne, david) ')
expect_response(frank, '!swap anne david', bot_dm, '[@bot] question(@frank) ability_used(!swap) ')
expect_response(anne, '!reveal_all', bot_dm, '[@bot] confirm(@anne) anne:villager, carl:seer, bob:wolf, david:thief, elsa:wolf, frank:troublemaker, george:drunk, harry:villager, ignacio:villager; excess: villager, villager, villager')

check_private_single_arg_single_use_cmd(george, '!swap', '1', 'drunk_wronguse(!, 3)', 'no_swap_self', 'drunk_success(1)')
expect_response(anne, '!reveal_all', bot_dm, '[@bot] confirm(@anne) anne:villager, carl:seer, bob:wolf, david:thief, elsa:wolf, frank:troublemaker, george:villager, harry:villager, ignacio:villager; excess: drunk, villager, villager')
