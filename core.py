import random
import asyncio
import sys
import json
import traceback

commands = {}
roles = {}
channel_events = {}
admin_commands = []
other_commands = []

history = []
og_roles = {}
og_excess = []
vote_list = {}
tmp_channels = {}
players = {}
played_roles = []
excess_roles = []
status = None
player_count = 0

lock = asyncio.Lock()
vote_countdown_task = None
vote_countdown_monitor = None

EXCESS_ROLES = 3
SEER_REVEAL = 2

THIS_MODULE = sys.modules[__name__]
BOT_PREFIX = '!'
CREATE_NORMALIZED_ALIASES = True
SUPERMAJORITY = 2/3
DEBUG = False
VOTE_COUNTDOWN = 60
LANDSLIDE_VOTE_COUNTDOWN = 10
ROLE_VARIABLES = [ 'used', 'discussed', 'reveal_count' ]
DEFAULT_ROLES = [ 'Wolf', 'Thief', 'Troublemaker', 'Drunk', 'Wolf', 'Villager', 'Seer', 'Clone', 'Minion', 'Insomniac', 'Tanner' ]

############################ ACTIONS ###########################

# These functions must be provided to the module by the @action decorator
def tr(key): raise missing_action_error('tr')
async def get_available_members(): raise missing_action_error('get_available_members')
async def create_channel(name, *players): raise missing_action_error('create_channel')
async def add_member(channel, player): raise missing_action_error('add_member')
async def debug(message): raise missing_action_error('debug')
def is_dm_channel(channel): raise missing_action_error('is_dm_channel')
def is_public_channel(channel): raise missing_action_error('is_public_channel')
def main_channel(): raise missing_action_error('get_main_channel')

def shuffle_copy(arr): return random.sample(arr, k=len(arr))

def missing_action_error(name):
  return NotImplementedError("Action `{}` not implemented! Implement it using the @action decorator"
      .format(name))

def action(func):
  name = func.__name__
  def accept_name(text):
    if name == text:
      globals()[name] = func
      return True
  if not(accept_name('get_available_members') or accept_name('tr') or accept_name('add_member')
      or accept_name('shuffle_copy') or accept_name('create_channel') or accept_name('main_channel')
      or accept_name('is_dm_channel') or accept_name('is_public_channel') or accept_name('debug')):
    raise ValueError("Action not used: {}".format(name))
  return func

########################### COMMANDS ###########################

def is_debug(): return DEBUG
def check_debug(func):
  async def wrapper(*args):
    if not DEBUG:
      await question(message, tr('debug_command'))
    else:
      await func(*args)
  return (wrapper, is_debug)


########################### CLASSES ############################

class Command:
  def decorate(self, func):
    self.func = func

  def make_alias(self, alias, description):
    cmd = Command()
    cmd.decorate(self.func)
    cmd.name = self.name
    cmd.description = tr('alias').format(alias, self.name) + description
    return cmd

  def is_listed(self, _, __):
    return True

class DebugCommand(Command):
  def is_listed(self, _, __):
    return DEBUG

  def decorate(self, func):
    async def check(message, args):
      if DEBUG:
        await func(message, args)
      else:
        await question(message, tr('debug_command'))
    super().decorate(check)

class AdminCommand(Command):
  def is_listed(self, player, _):
    return player.is_admin

  def decorate(self, func):
    async def check(message, args):
      if not players[message.author.id].is_admin:
        await question(message, tr('require_admin'))
      else:
        await func(message, args)
    super().decorate(check)

class PlayerCommand(Command):
  def is_listed(self, player, _):
    return player.role

  def decorate(self, func):
    async def check(message, args):
      if not message.author.id in players:
        return await question(message, tr('not_playing'))
      player = players[message.author.id]
      if not player.role:
        await question(message, tr('not_playing'))
      else:
        await func(player, message=message, args=args)
    super().decorate(check)

class RoleCommand(PlayerCommand):
  def is_listed(self, player, channel):
    return super().is_listed(player, channel) and hasattr(player.role, self.name)

  def decorate(self, func):
    async def check(player, message, args):
      if not hasattr(player.role, func.__name__):
        return await question(message, tr('wrong_role').format(BOT_PREFIX + self.name))
      await getattr(player.role, func.__name__)(player, message=message, args=args)
    super().decorate(check)

class SetupCommand(AdminCommand):
  def is_listed(self, player, _):
    return not status and super().is_listed(player, None)

  def decorate(self, func):
    async def check(message, args):
      if status:
        return await question(message, tr('forbid_game_started').format(BOT_PREFIX + self.name))
      elif not is_public_channel(message.channel):
        return await question(message, tr('public_only').format(BOT_PREFIX + self.name))
      await func(message, args)
    super().decorate(check)

class Player:
  def __init__(self, is_admin, extern):
    self.is_admin = is_admin
    self.extern = extern
    self.role = None
    self.real_role = None
    self.vote = None

class Channel:
  @classmethod
  async def create(cls, name, *players):
    self = Channel()
    self.extern = await create_channel(name, *( player.extern for player in players ))
    self.players = list(players)
    return self

  async def add(self, player):
    self.players.append(player)
    await add_member(self.extern, player.extern)
  async def delete(self):
    self.players = None
    await self.extern.delete()

########################## DECORATORS ##########################

def cmd(base):
  def decorator(func):
    base.decorate(func)
    commands[func.__name__] = base
    return func
  return decorator

def role(base):
  roles[base.__name__] = base
  return base

def channel_event(func):
  channel_events[func.__name__] = func

def single_arg(message_key, *message_args):
  def decorator(func):
    async def sa_result(*others, message, args):
      try:
        [args] = args.split()
      except ValueError:
        return await question(message, tr(message_key).format(command_name(func.__name__), *message_args))
      await func(*others, message, args)
    sa_result.__name__ = func.__name__
    return sa_result
  return decorator

def single_use(func):
  async def su_result(self, me, message, args):
    if self.used:
      return await question(message, tr('ability_used').format(command_name(func.__name__)))
    await func(self, me, message=message, args=args)
  su_result.__name__ = func.__name__
  return su_result

def check_context(required_channel, required_status = 'night'):
  def decorator(func):
    async def handler(*others, message, args):
      channel_name = name_channel(message.channel)
      if channel_name != required_channel:
        cmd = command_name(func.__name__)
        if channel_name != 'dm':
          await question(message, tr('wrong_role').format(cmd))
        await message.author.send(tr('question').format(message.author.mention) + tr(required_channel + '_only').format(cmd))
      elif required_status != status:
        await question(message, tr(required_status + '_only'))
      else:
        await func(*others, message=message, args=args)
    handler.__name__ = func.__name__
    handler.unchecked = func
    return handler
  return decorator

############################ INIT ##############################

def initialize(admins):
  random.seed()

  for cmd_name, base in list(commands.items()):
    [name, description, *aliases] = tr('cmd_' + cmd_name.lower())
    description = description.format(BOT_PREFIX + name)
    base.name = name
    base.description = description
    commands[name] = base
    if not isinstance(base, RoleCommand) and not isinstance(base, DebugCommand):
      (admin_commands if isinstance(base, AdminCommand) else other_commands).append(BOT_PREFIX + name)
    if aliases:
      commands[name].description += tr('aliases_list').format('`, `!'.join(aliases))
    for alias in aliases:
      if alias not in commands:
        commands[alias] = base.make_alias(alias, description)
      else:
        print("ERROR: Can't create alias {} to command {}!".format(alias, name))

  for base_name, base in list(roles.items()):
    [base.name, base.description, base.greeting, *aliases] = tr('role_' + base_name.lower())
    base.commands = [ command_name(command) for command in dir(base) if command[:1].isupper() ]
    base.greeting = base.greeting.format(*base.commands)
    base.__role__ = True
    roles[base.name] = base
    if CREATE_NORMALIZED_ALIASES:
      import unidecode
      normalized = unidecode.unidecode(base.name)
      if normalized != base.name:
        aliases.append(normalized)
      length = len(aliases)
      for idx in range(length):
        alias = aliases[idx]
        normalized = unidecode.unidecode(alias)
        if normalized != alias:
          aliases.append(normalized)
    for alias in aliases:
      if alias not in roles:
        roles[alias] = base
      else:
        print("ERROR: Can't create alias {} to role {}!".format(alias, base.name))

  for admin in admins:
    players[admin.id] = Player(True, admin)

######################### SERIALIZATION ########################

class RoleEncoder(json.JSONEncoder):
  def encode_role(self, obj):
    result = { name: getattr(obj, name) for name in ROLE_VARIABLES if hasattr(obj, name) }
    result['type'] = type(obj).__name__
    return result

  def default(self, obj):
    if hasattr(obj, '__role__'):
      return self.encode_role(obj)
    if isinstance(obj, Player):
      result = { 'id': obj.extern.id, 'name': obj.extern.name }
      if obj.vote:
        result['vote'] = obj.vote
      if obj.role:
        result['role'] = self.encode_role(obj.role)
        result['real_role'] = roles[obj.real_role].__name__
      return result
    return json.JSONEncoder.default(self, obj)

def state_to_json(fp):
  tmp_channels_export = {}
  for name, channel in tmp_channels.items():
    tmp_channels_export[name] = { 'name': channel.extern.name, 'members': [ player.extern.id for player in channel.players ] }
  obj = {
    'vote_list': vote_list,
    'played_roles': played_roles,
    'status': status,
    'SEER_REVEAL': SEER_REVEAL,
    'EXCESS_ROLES': EXCESS_ROLES,
    'history': history,
    'og_roles': og_roles,
    'og_excess': og_excess,

    'excess_roles': [ roles[role].__name__ for role in excess_roles ],
    'channels': tmp_channels_export,
    'players': list(players.values()),
  }
  return json.dump(obj, fp, cls = RoleEncoder, indent = 2)

async def json_to_state(fp, player_mapping = {}):
  await EndGame(None, None)
  obj = json.load(fp)

  available_players = await get_available_members()
  for decoded_player in obj['players']:
    id = decoded_player['id']
    if id in players:
      player = players[id]
    else:
      id = decoded_player['name']
      if id in player_mapping: id = player_mapping[id]
      for mem in available_players:
        if mem.id == id:
          players[mem.id] = player = Player(False, mem)
          break
      else:
        print("ERROR: Member {} is not available".format(id))
        return
    if 'role' in decoded_player:
      role_obj = decoded_player['role']
      role = roles[role_obj['type']]
      player.role = role() if len(role_obj) == 1 else role(role_obj)
      player.real_role = roles[decoded_player['real_role']].name
    if 'vote' in decoded_player:
      player.vote = decoded_player['vote']

  for name, channel in obj['channels'].items():
    tmp_channels[name] = await Channel.create(channel['name'], *( players[id] for id in channel['members'] ))
  global excess_roles
  excess_roles = [ roles[role].name for role in obj['excess_roles'] ]

  names = ['vote_list', 'played_roles', 'status', 'SEER_REVEAL', 'EXCESS_ROLES', 'history', 'og_roles', 'og_excess' ]
  for name in names:
    if name in obj:
      globals()[name] = obj[name]
  if 'null' in vote_list:
    vote_list[None] = vote_list['null']
    del vote_list['null']

########################## COMMANDS ############################

@cmd(RoleCommand())
def Swap(): pass

@cmd(RoleCommand())
def Steal(): pass

@cmd(RoleCommand())
def Take(): pass

@cmd(RoleCommand())
def See(): pass

@cmd(RoleCommand())
def Reveal(): pass

@cmd(RoleCommand())
def Clone(): pass

@cmd(RoleCommand())
def EndDiscussion(): pass

@cmd(Command())
async def Help(message, args):
  if args:
    if args in commands:
      await confirm(message, commands[args].description.format(THIS_MODULE))
    elif args in roles:
      await confirm(message, roles[args].description.format(THIS_MODULE))
    else:
      await confused(message.channel, args)
  else:
    player = get_player(message.author)
    command_list = other_commands[:]
    if player.is_admin:
      command_list += admin_commands
    if player.role:
      command_list = player.role.commands + command_list
    await confirm(message, tr('help_list').format('`, `'.join(command_list)) + tr('help_detail').format(command_name('Help')))
@cmd(SetupCommand())
async def AddRole(message, args):
  role_list = []
  for role in args.split(','):
    role = role.strip()
    if not role:
      return await question(message, tr('add_wronguse').format(command_name('AddRole')))
    elif role in roles:
      name = roles[role].name
      played_roles.append(name)
      role_list.append(name)
    else:
      return await confused(message.channel, role)
  await message.channel.send(tr('add_success').format(join_with_and(role_list)))

@cmd(SetupCommand())
async def RemoveRole(message, args):
  role_list = []
  for role in args.split(','):
    role = role.strip()
    if not role:
      return await question(message, tr('remove_wronguse').format(command_name('RemoveRole')))
    elif role in roles:
      name = roles[role].name
      if name in played_roles:
        played_roles.pop(played_roles.index(name))
        role_list.append(name)
      else:
        return await question(message, tr('remove_notfound').format(role))
    else:
      return await confused(message.channel, args)
  await message.channel.send(tr('remove_success').format(join_with_and(role_list)))

@cmd(Command())
async def ListRoles(message, args):
  if not played_roles:
    msg = tr('no_roles')
    if players:
      msg += tr('default_roles').format(DEFAULT_ROLES)
    return await confirm(message, msg)
  await confirm(message, tr('list_roles').format(join_with_and(played_roles), needed_players_count()))

@cmd(PlayerCommand())
async def Unvote(me, message, args):
  if not me.vote:
    return await question(message, tr('not_voting'))
  await on_voted(me, None)

@cmd(PlayerCommand())
@single_arg('vote_wronguse')
async def Vote(me, message, args):
  if status != 'day':
    return await question(message, tr('day_only'))
  if not is_public_channel(message.channel):
    return await question(message, tr('public_only').format(command_name('vote')))
  player = await find_player(message, args)
  if player:
    await on_voted(me, player.extern.mention)

@cmd(SetupCommand())
async def StartImmediate(message, args):
  try:
    members = await get_available_members()
    current_count = len(members)
    global played_roles
    if not played_roles:
      played_roles = DEFAULT_ROLES[:current_count + EXCESS_ROLES]
    needed_count = needed_players_count()
    if current_count > needed_count:
      await question(message, tr('start_needless').format(current_count, needed_count))
    elif current_count < needed_count:
      await question(message, tr('start_needmore').format(current_count, needed_count))
    else:
      await message.channel.send(tr('start').format(join_with_and(
        [member.mention for member in members]
      )))
      global status
      global player_count
      status = 'night'
      player_count = current_count
      history.clear()
      og_roles.clear()
      og_excess.clear()

      shuffled_roles = shuffle_copy(played_roles)
      for idx, member in enumerate(members):
        player = get_player(member)
        player.role = roles[shuffled_roles[idx]]()
        player.real_role = player.role.name
        og_roles[player.extern.mention] = player.real_role
        await player.extern.send(tr('role').format(player.role.name) + player.role.greeting)
        if hasattr(player.role, 'on_start'):
          await player.role.on_start(player)

      excess_roles.clear()
      for idx in range(EXCESS_ROLES):
        excess_roles.append(shuffled_roles[-idx - 1])
        og_excess.append(shuffled_roles[-idx - 1])

      for id, channel in tmp_channels.items():
        channel_name = id + '_channel'
        await channel.extern.send(tr(channel_name).format(join_with_and([player.extern.mention for player in channel.players if not player.extern.bot])) + tr('end_discussion_info').format(command_name('EndDiscussion')))
        if channel_name in channel_events:
          await channel_events[channel_name](channel)
      await on_used()
  except BaseException as e:
    await EndGame(None, None)
    raise e

@cmd(Command())
@check_context('public', 'day')
async def VoteDetail(message, args):
  item = tr('vote_detail_item')
  await main_channel().send(tr('vote_detail').format('\n'.join([ item.format(player.extern.mention, player.vote) for player in players.values() if player.vote ])))

@cmd(Command())
@check_context('public', 'day')
async def VoteCount(message, args):
  most_vote = await low_vote_count('vote_detail')
  await main_channel().send(tr('most_vote').format(most_vote) if most_vote else tr('vote_tie'))

async def low_vote_count(key):
  vote_detail = []
  most_vote = None
  max_vote = 0
  vote_item = tr('vote_item')
  for p, votes in vote_list.items():
    if p and votes:
      vote_detail.append(vote_item.format(p, votes))
      if votes > max_vote:
        max_vote = votes
        most_vote = p
      elif votes == max_vote:
        most_vote = None
  await main_channel().send(tr(key).format("\n".join(vote_detail)))
  return most_vote

@cmd(AdminCommand())
async def CloseVote(_, __):
  global vote_countdown_task
  if vote_countdown_task:
    vote_countdown_task.cancel()
    clear_vote_countdown()
  channel = main_channel()
  most_vote = await low_vote_count('vote_result')
  if most_vote:
    await channel.send(tr('lynch').format(most_vote))
    for lynched in players.values():
      if lynched.extern.mention == most_vote:
        lynched_role = lynched.real_role
        await channel.send(tr('reveal_player').format(lynched.extern.mention, lynched_role))
        lynched_role = roles[lynched_role]
        if issubclass(lynched_role, Villager) or issubclass(lynched_role, Minion):
          winners = [ player for player in players.values() if is_wolf_side(player.real_role) ]
        elif issubclass(lynched_role, Tanner):
          winners = [ lynched ]
        elif issubclass(lynched_role, WolfSide):
          winners = [ player for player in players.values() if is_village_side(player.real_role) ]
        await announce_winners(channel, winners)
        break
  else:
    await channel.send(tr('no_lynch'))
    wolves = []
    villagers = []
    for p in players.values():
      if is_wolf_side(p.real_role):
        wolves.append(p)
      elif is_village_side(p.real_role):
        villagers.append(p)
    await announce_winners(channel, wolves if wolves else villagers)

@cmd(Command())
@check_context('public', None)
async def History(message, args):
  if history:
    reveal_item = tr('reveal_item')
    command_item = tr('command_item')
    command_item_empty = tr('command_item_empty')
    roles = '\n'.join([ reveal_item.format(player, role) for player, role in og_roles.items() ])
    commands = '\n'.join([ command_item.format(h[0], h[1], h[2]) if h[2] != None else command_item_empty.format(h[0], h[1]) for h in history ])
    await message.channel.send(tr('history').format(roles, join_with_and(og_excess), commands))
  else:
    await question(message, tr('no_history'))

@cmd(AdminCommand())
async def Save(message, args):
  args = args.strip()
  if '\\' in args or '/' in args:
    return await question(message, tr('invalid_file_name'))
  fp = open(args, 'w')
  state_to_json(fp)
  await confirm(message, tr('save_success').format(args))

@cmd(AdminCommand())
async def Load(message, args):
  args = args.strip()
  if '\\' in args or '/' in args:
    return await question(message, tr('invalid_file_name'))
  fp = open(args, 'r')
  await json_to_state(fp)
  await confirm(message, tr('load_success').format(args))

@cmd(AdminCommand())
async def EndGame(_, __):
  global status
  status = None
  for player in players.values():
    player.real_role = player.role = player.vote = None
  for channel in tmp_channels.values():
    await channel.delete()
  tmp_channels.clear()
  vote_list.clear()

@cmd(AdminCommand())
async def WakeUp(_, __):
  for player in players.values():
    if player.role and hasattr(player.role, 'before_dawn'):
      await player.role.before_dawn(player)
  global status
  status = 'day'
  global vote_list
  vote_list = { None: player_count }
  await main_channel().send(tr('wake_up') + tr('vote').format(command_name('Vote')))

@cmd(DebugCommand())
async def RevealAll(message, args):
  await low_reveal_all(message.channel)

async def low_reveal_all(channel):
  reveal_item = tr('reveal_item')
  await channel.send(tr('reveal_all').format('\n'.join([ reveal_item.format(player.extern.name, player.real_role) for player in players.values() if player.role ])) + '\n' + tr('excess_roles').format(', '.join([name for name in excess_roles])))

############################# UTILS ############################

def name_channel(channel):
  if is_dm_channel(channel):
    return 'dm'
  if is_public_channel(channel):
    return 'public'
  for id, c in tmp_channels.items():
    if channel.id == c.extern.id:
      return id

async def confirm(message, text):
  await message.reply(tr('confirm').format(message.author.mention) + str(text))

async def question(message, text):
  await message.reply(tr('question').format(message.author.mention) + str(text))

async def confused(channel, msg):
  await channel.send(tr('confused').format('`' + msg + '`'))

def get_player(extern):
  id = extern.id
  if id in players:
    return players[id]
  players[id] = player = Player(False, extern)
  return player

def record_history(message, result):
  history.append((message.author.name, message.content, result))

def join_with_and(arr):
  return arr[0] if len(arr) == 1 else ", ".join(arr[:-1]) + ", " + tr('_and') + arr[-1]

def needed_players_count():
  return max(0, len(played_roles) - EXCESS_ROLES)

def command_name(name):
  return BOT_PREFIX + commands[name].name

async def find_player(message, name):
  if name.startswith('@'):
    name = name[1:]
  for player in players.values():
    if player.extern.name == name:
      if not player.role:
        return await question(message, tr('player_norole').format(player.mention))
      return player
  return await question(message, tr('player_notfound').format(name))

async def select_excess_card(message, wronguse_msg, cmd_name, args):
  try:
    number = int(args)
  except ValueError:
    return await question(message, tr(wronguse_msg).format(command_name(cmd_name), EXCESS_ROLES))
  if number < 1 or number > EXCESS_ROLES:
    return await question(message, tr('choice_outofrange').format(EXCESS_ROLES))
  return number

async def set_used(role):
  role.used = True
  await on_used()

def clear_vote_countdown():
  global vote_countdown_task
  vote_countdown_task = None

async def await_vote_countdown():
  if vote_countdown_task:
    try:
      await vote_countdown_task
    except asyncio.CancelledError: pass

def transfer_to_self(self, name, data, default):
  setattr(self, name, data[name] if data else default)

def is_wolf_side(role):
  return issubclass(roles[role], WolfSide)

def is_village_side(role):
  return issubclass(roles[role], Villager)

async def announce_winners(channel, winners):
  if winners:
    await channel.send(tr('winners').format(join_with_and([ p.extern.mention for p in winners ])))
  else:
    await channel.send(tr('no_winners'))
  await low_reveal_all(channel)
  await EndGame(None, None)

############################ ROLES #############################

@role
class Villager: pass

@role
class Tanner: pass

@role
class Insomniac(Villager):
  async def before_dawn(self, player):
    await player.extern.send(tr('insomniac_reveal').format(player.real_role))

@role
class Seer(Villager):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, False)
    transfer_to_self(self, 'reveal_count', data, 0)

  @check_context('dm')
  @single_arg('see_wronguse')
  async def See(self, me, message, args):
    if self.reveal_count:
      return await question(message, tr('seer_reveal_already'))
    if self.used:
      return await question(message, tr('ability_used').format(command_name('See')))
    if me.extern.name == args:
      return await question(message, tr('seer_self'))
    player = await find_player(message, args)
    if player:
      record_history(message, player.real_role)
      await confirm(message, tr('see_success').format(args, player.real_role))
      await set_used(self)

  @check_context('dm')
  @single_arg('reveal_wronguse', EXCESS_ROLES)
  async def Reveal(self, me, message, args):
    if self.used:
      return await question(message, tr('seer_see_already'))
    if self.reveal_count >= SEER_REVEAL:
      return await question(message, tr('out_of_reveal').format(SEER_REVEAL))
    number = await select_excess_card(message, 'reveal_wronguse', 'Reveal', args)
    if number:
      result = excess_roles[number - 1]
      record_history(message, result)
      self.reveal_count += 1
      if self.reveal_count >= SEER_REVEAL:
        await confirm(message, tr('reveal_success').format(number, result) + tr('no_reveal_remaining'))
        await set_used(self)
      else:
        await confirm(message, tr('reveal_success').format(number, result) + tr('reveal_remaining').format(SEER_REVEAL - self.reveal_count))

@role
class Clone(Villager):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, False)

  @check_context('dm')
  @single_use
  @single_arg('clone_wronguse')
  async def Clone(self, me, message, args):
    if me.extern.name == args:
      return await question(message, tr('clone_self'))
    player = await find_player(message, args)
    if player:
      record_history(message, player.real_role)
      me.role = roles[player.real_role]()
      me.real_role = me.role.name
      if hasattr(me.role, 'on_start'):
        await me.role.on_start(me)
      return await confirm(message, tr('clone_success').format(args, me.role.name) + me.role.greeting)

@role
class Troublemaker(Villager):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, False)

  @check_context('dm')
  @single_use
  async def Swap(self, me, message, args):
    players = args.split()
    if len(players) != 2:
      return await question(message, tr('troublemaker_wronguse').format(command_name('Swap')))
    if me.extern.name in players:
      return await question(message, tr('no_swap_self'))
    players = [ await find_player(message, name) for name in players ]
    if players[0] and players[1]:
      record_history(message, None)
      players[0].real_role, players[1].real_role = players[1].real_role, players[0].real_role
      await set_used(self)
      return await confirm(message, tr('troublemaker_success')
          .format(*[ p.extern.name for p in players]))

@role
class Thief(Villager):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, False)

  @check_context('dm')
  @single_use
  @single_arg('thief_wronguse')
  async def Steal(self, me, message, args):
    if me.extern.name == args:
      return await question(message, tr('no_swap_self'))
    player = await find_player(message, args)
    if player:
      record_history(message, player.real_role)
      me.real_role, player.real_role = player.real_role, me.real_role
      await set_used(self)
      return await confirm(message, tr('thief_success').format(args, me.real_role))

@role
class Drunk(Villager):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, False)

  @check_context('dm')
  @single_use
  @single_arg('drunk_wronguse', EXCESS_ROLES)
  async def Take(self, me, message, args):
    number = await select_excess_card(message, 'drunk_wronguse', 'Take', args)
    if number:
      record_history(message, None)
      me.real_role, excess_roles[number-1] = excess_roles[number-1], me.real_role
      await set_used(self)
      return await confirm(message, tr('drunk_success').format(args))

class WolfSide: pass

@role
class Minion(WolfSide):
  async def on_start(self, player):
    wolves = []
    for player in players.values():
      if isinstance(player.role, Wolf):
        wolves.append(player.extern.name)
    await player.extern.send(tr('wolves_reveal').format(join_with_and(wolves)) if wolves else tr('no_wolves') + tr('minion_kill_self'))

@role
class Wolf(WolfSide):
  def __init__(self, data = None):
    transfer_to_self(self, 'used', data, True)
    transfer_to_self(self, 'discussed', data, False)

  @check_context('wolf')
  async def EndDiscussion(self, me, message, args):
    self.discussed = True
    for player in tmp_channels['wolf'].players:
      if not player.role.discussed:
        await confirm(message, tr('discussion_ended') + tr('discussion_wait_other'))
        break
    else:
      await confirm(message, tr('discussion_ended') + tr('discussion_all_ended'))
    await on_used()

  @check_context('wolf')
  @single_use
  @single_arg('reveal_wronguse', EXCESS_ROLES)
  async def Reveal(self, me, message, args):
    number = await select_excess_card(message, 'reveal_wronguse', 'Reveal', args)
    if number:
      record_history(message, excess_roles[number-1])
      await confirm(message, tr('reveal_success').format(number, excess_roles[number - 1]))
      await set_used(self)

  async def on_start(self, player):
    if not 'wolf' in tmp_channels:
      tmp_channels['wolf'] = await Channel.create(tr('wolf'), player)
    else:
      channel = tmp_channels['wolf']
      await channel.add(player)
      await channel.extern.send(tr('channel_greeting').format(player.extern.mention, channel.extern.name))

########################### EVENTS #############################

async def on_used():
  for player in players.values():
    if player.role:
      if (hasattr(player.role, 'used') and not player.role.used) or (hasattr(player.role, 'discussed') and not player.role.discussed):
        return
  await WakeUp(None, None)
  return True

async def on_voted(me, vote):
  async def close_vote_countdown(seconds):
    await asyncio.sleep(seconds)
    clear_vote_countdown()
    async with lock:
      await CloseVote(None, None)

  vote_list[me.vote] -= 1
  me.vote = vote
  my_vote = vote_list[me.vote] = vote_list[me.vote] + 1 if me.vote in vote_list else 1
  not_voted = vote_list[None]
  channel = main_channel()
  if vote:
    await channel.send(tr('vote_success').format(me.extern.mention, vote))
    next_most = 0
    for p, votes in vote_list.items():
      if p and p != me.vote and votes > next_most:
        next_most = votes
    global vote_countdown_task
    if not_voted == 0:
      await CloseVote(None, None)
    elif my_vote - next_most > not_voted:
      if vote_countdown_task:
        vote_countdown_task.cancel()
      await channel.send(tr('landslide_vote_countdown').format(me.vote, LANDSLIDE_VOTE_COUNTDOWN))
      vote_countdown_task = asyncio.create_task(close_vote_countdown(LANDSLIDE_VOTE_COUNTDOWN))
    elif not_voted / player_count <= 1 - SUPERMAJORITY:
      if not vote_countdown_task:
        await channel.send(tr('vote_countdown').format(VOTE_COUNTDOWN))
        vote_countdown_task = asyncio.create_task(close_vote_countdown(VOTE_COUNTDOWN))
  else:
    await channel.send(tr('unvote_success').format(me.extern.mention))
    if vote_countdown_task:
      vote_countdown_task.cancel()
      clear_vote_countdown()
      await channel.send(tr('vote_countdown_cancelled'))

@channel_event
async def wolf_channel(channel):
  for role in excess_roles:
    if issubclass(roles[role], Wolf):
      for player in channel.players:
        if not player.extern.bot:
          lone_wolf = players[player.extern.id]
          lone_wolf.role.used = False
      await channel.extern.send(tr('wolf_get_reveal').format(command_name('Reveal'), EXCESS_ROLES))
      break

############################# MAIN #############################

async def process_message(message):
  content = message.content
  if content.startswith(BOT_PREFIX):
    try:
      async with lock:
        full = content[len(BOT_PREFIX):]
        arr = full.split(" ", 1)
        if len(arr) == 0:
          return
        if len(arr) == 1:
          cmd = arr[0]
          args = ''
        else:
          [cmd, args] = arr
        cmd = cmd.lower()
        if cmd in commands:
          await commands[cmd].func(message=message, args=args)
        else:
          await confused(message.channel, BOT_PREFIX + cmd)
    except:
      await debug(traceback.format_exc())
      await message.reply(tr('exception'))

async def process_and_wait(message):
  await process_message(message)
  await await_vote_countdown()

async def greeting():
  await main_channel().send(tr('greeting').format(command_name('Help'), command_name('StartImmediate')))
