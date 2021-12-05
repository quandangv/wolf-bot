import random
import asyncio
import json
import traceback
import dictionize
import unidecode
import sys

THIS_MODULE = sys.modules[__name__]
commands = {}
roles = {}
channel_events = {}
admin_commands = []
other_commands = []
cmd_names = []
lock = asyncio.Lock()
vote_countdown_task = None
vote_countdown_monitor = None
game_mode = None
role_prefix = None

history = []
og_roles = {}
vote_list = {}
tmp_channels = {}
players = {}
played_roles = []
status = None
player_count = 0
excess_roles = []
og_excess = []

BOT_PREFIX = '!'
SUPERMAJORITY = 2/3
DEBUG = False
VOTE_COUNTDOWN = 60
LANDSLIDE_VOTE_COUNTDOWN = 10
DEFAULT_ROLES = None
PLAYER_PERSISTENT_ATTR = ['extern', 'role', 'vote']

########################### EVENTS #############################

async def start_game(message, player_list):
  try:
    current_count = len(player_list)
    if not current_count:
      return await question(message, tr('start_noplayer'))
    if not played_roles:
      globals()['played_roles'] = [ roles[DEFAULT_ROLES[idx]].name for idx in range(default_roles_needed(current_count))]
    needed_count = needed_players_count(played_roles)
    if current_count > needed_count:
      await question(message, tr('start_needless').format(current_count, needed_count))
    elif current_count < needed_count:
      await question(message, tr('start_needmore').format(current_count, needed_count))
    else:
      await message.channel.send(tr('start').format(join_with_and(
        [player.extern.mention for player in player_list]
      )) + list_roles())
      globals()['status'] = 'night'
      globals()['player_count'] = current_count
      history.clear()
      og_roles.clear()

      while True:
        shuffled_roles = shuffle_copy(played_roles)
        for role in shuffled_roles:
          role = roles[role]
          if hasattr(role, 'check_shuffling') and role.check_shuffling(shuffled_roles, player_count):
            break
        else:
          break

      og_excess.clear()
      excess_roles.clear()
      for idx in range(len(shuffled_roles) - player_count):
        excess_roles.append(shuffled_roles[-idx - 1])
      globals()['og_excess'] = excess_roles[:]
      player_names = tr('player_names').format(', '.join([p.extern.name for p in player_list]))
      prompted_setup = False
      for idx, player in enumerate(player_list):
        await set_role('role', player, roles[shuffled_roles[idx]], True)
        if getattr(player.role, 'get_player_names', False):
          await player.extern.send(player_names)
        if hasattr(player.role, 'new_night'):
          player.role.new_night()
        og_roles[player.extern.mention] = player.role.name
        prompted_setup = prompted_setup or hasattr(player.role, 'prompted_setup')
      after_shuffle(shuffled_roles)

      async def finish_game_setup():
        for id, channel in tmp_channels.items():
          channel_name = id + '_channel'
          msg = tr(channel_name).format(join_with_and([player.extern.mention for player in channel.players]))
          if hasattr(channel, 'discussing'):
            msg += tr('sleep_info').format(cmd_names['Sleep'])
          msg += '\n' + player_names
          await channel.extern.send(msg)
          if channel_name in channel_events:
            await channel_events[channel_name](channel)
        await on_used()
        start_night()
      if not prompted_setup:
        await finish_game_setup()
      else:
        async def on_setup_answered():
          for player in players.values():
            if player.role and hasattr(player.role, 'prompted_setup'):
              return
          await finish_game_setup()
        globals()['on_setup_answered'] = on_setup_answered
  except BaseException as e:
    await end_game()
    raise e

async def set_role(greeting_key, player, role, first_time):
  player.role = role()
  await player.extern.send(tr(greeting_key).format(role.name) + role.greeting)
  if hasattr(player.role, 'on_start'):
    await player.role.on_start(player, first_time)

async def on_used():
  if status == 'night':
    for player in players.values():
      if player.role:
        if (hasattr(player.role, 'target') and not player.role.target) or (hasattr(player.role, 'sleep') and not player.role.sleep):
          return
    await wake_up()
    return True

async def on_voted(me, vote):
  async def close_vote_countdown(seconds):
    await asyncio.sleep(seconds)
    clear_vote_countdown()
    async with lock:
      await close_vote()

  vote_list[me.vote] -= 1
  me.vote = vote
  my_vote_count = vote_list[me.vote] = vote_list[me.vote] + 1 if me.vote in vote_list else 1
  not_voted = vote_list[None]
  channel = main_channel()
  if vote:
    await channel.send((tr('no_vote_success').format(me.extern.mention) if isinstance(vote, bool) else tr('vote_success').format(me.extern.mention, vote.extern.mention)) + tr('remind_unvote').format(cmd_names['Unvote']))
    next_most = 0
    for p, votes in vote_list.items():
      if p and p != me.vote and p != True and votes > next_most:
        next_most = votes
    global vote_countdown_task
    if not_voted == 0:
      await close_vote()
    elif my_vote_count - next_most > not_voted:
      if vote_countdown_task:
        if vote_countdown_task.time > LANDSLIDE_VOTE_COUNTDOWN:
          vote_countdown_task.cancel()
        else:
          return
      await channel.send(tr('landslide_vote_countdown').format(me.vote.extern.mention, LANDSLIDE_VOTE_COUNTDOWN) if me.vote != True else tr('landslide_no_vote_countdown').format(LANDSLIDE_VOTE_COUNTDOWN))
      vote_countdown_task = asyncio.create_task(close_vote_countdown(LANDSLIDE_VOTE_COUNTDOWN))
      vote_countdown_task.time = LANDSLIDE_VOTE_COUNTDOWN
    elif not_voted / player_count <= 1 - SUPERMAJORITY:
      if not vote_countdown_task:
        await channel.send(tr('vote_countdown').format(VOTE_COUNTDOWN))
        vote_countdown_task = asyncio.create_task(close_vote_countdown(VOTE_COUNTDOWN))
        vote_countdown_task.time = VOTE_COUNTDOWN
  else:
    await channel.send(tr('unvote_success').format(me.extern.mention))
    if vote_countdown_task:
      vote_countdown_task.cancel()
      clear_vote_countdown()
      await channel.send(tr('vote_countdown_cancelled'))

############################ ACTIONS ###########################

# These functions are for intergration with a messenger
# They must be provided to the module via the @action decorator

def action(func):
  accepted_names = [ 'get_available_members', 'shuffle_copy', 'is_dm_channel', 'tr', 'add_member', 'create_channel', 'main_channel', 'is_public_channel', 'debug', 'sort_players' ]
  name = func.__name__
  if not name in accepted_names:
    raise ValueError("Invalid action: {}".format(name))
  else:
    globals()[name] = func
  return func

def tr(key): raise missing_action_error('tr')
async def get_available_members(): raise missing_action_error('get_available_members')
async def create_channel(name, *players): raise missing_action_error('create_channel')
async def add_member(channel, player): raise missing_action_error('add_member')
async def debug(message): raise missing_action_error('debug')
def is_dm_channel(channel): raise missing_action_error('is_dm_channel')
def is_public_channel(channel): raise missing_action_error('is_public_channel')
def main_channel(): raise missing_action_error('get_main_channel')
def shuffle_copy(arr): return random.sample(arr, k=len(arr))
def sort_players(players): return players

def missing_action_error(name):
  return NotImplementedError("Action `{}` not implemented! Implement it using the @action decorator".format(name))

########################### CLASSES ############################

old_dtypical = dictionize.simple_dtypical
def my_dtypical(self, obj, key, val):
  if isinstance(val, str) and val.startswith('@@'):
    val = Player.dictionize__.dtemplate(val)
  old_dtypical(self, obj, key, val)
dictionize.simple_dtypical = my_dtypical

class Role:
  @dictionize.slots_keys
  class _Dictionize:
    def etemplate(self, obj):
      return { 'type': type(obj).__name__ }
    async def dtemplate(self, dict):
      return roles[dict['type']]()
    async def d_type(*_): pass
  dictionize__ = _Dictionize()

class Player:
  def __init__(self, extern):
    self.extern = extern
    self.role = None
    self.vote = None
  def persistent(self):
    return self.role

  @dictionize.dict_keys
  @dictionize.sub_hint('role', Role.dictionize__)
  @dictionize.e_ignore('extern')
  class FullDictionize:
    def __init__(self, available_players):
      self.available_players = available_players
    def etemplate(self, obj):
      return {'id': obj.extern.id, 'name': obj.extern.name }
    async def dtemplate(self, dict):
      id = dict['id']
      if id in players:
        return players[id]
      for mem in self.available_players:
        if mem.id == id:
          player = players[mem.id] = Player(mem)
          return player
      raise ValueError("ERROR: Member {} is not available".format(id))
    async def d_real_role(self, obj, val):
      obj.real_role = val and roles[val].name
  @dictionize.no_keys
  class RefDictionize:
    def etemplate(self, obj): return '@@' + str(obj.extern.id)
    def dtemplate(self, obj): return players[int(obj[2:])]
  dictionize__ = RefDictionize()
  full_dictionize__ = FullDictionize({})

class Channel:
  @staticmethod
  async def create(name, *players):
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

  @dictionize.dict_keys
  @dictionize.e_ignore('extern', 'players')
  class Dictionize:
    def etemplate(self, obj):
      return { 'name': obj.extern.name, 'members': [ player.extern.id for player in obj.players ] }
    async def dtemplate(self, dict):
      return await Channel.create(dict['name'], *( players[id] for id in dict['members'] ))
  dictionize__ = Dictionize()

class Command:
  __slots__ = ( 'func', 'name', 'description' )
  def __init__(self, func, name, description):
    self.func = func
    self.name = name
    self.description = description

########################## DECORATORS ##########################

def command(func):
  cmd_names.append(func.__name__)
  func.cmd_types = []
  return func

def role(base):
  roles[base.__name__] = base
  return base

def channel_event(func):
  channel_events[func.__name__] = func

############################ INIT ##############################

def initialize(admins):
  globals()['admins'] = admins
  random.seed()
  name_dict = {}
  global cmd_names
  for cmd_name in cmd_names:
    [name, description, *aliases] = tr('cmd_' + cmd_name.lower())
    description = description.format(BOT_PREFIX + name)
    func = globals()[cmd_name]
    name_dict[cmd_name] = BOT_PREFIX + name
    commands[name] = Command(func, name, description)
    if not 'role' in func.cmd_types and not 'debug' in func.cmd_types:
      (admin_commands if 'admin' in func.cmd_types else other_commands).append(BOT_PREFIX + name)
    if aliases:
      commands[name].description += tr('aliases_list').format('`, `!'.join(aliases))
    for alias in aliases:
      if alias not in commands:
        commands[alias] = Command(func, alias, tr('alias').format(alias, name) + description)
      else:
        print("ERROR: Can't create alias {} to command {}!".format(alias, name))
  cmd_names = name_dict
  connect(admins)

def connect(admins):
  for base_name, base in list(roles.items()):
    [base.name, base.description, base.greeting, *aliases] = tr(role_prefix + base_name.lower())
    base.commands = [ cmd_names[cmd] for cmd in dir(base) if cmd[:1].isupper() ]
    base.greeting = base.greeting.format(*base.commands)
    base.__role__ = True
    def add_role(name):
      if name not in roles:
        roles[name] = base
      else:
        print("ERROR: Can't add role {}!".format(name))
    add_role(base.name)
    for alias in aliases:
      add_role(alias)

    aliases.append(base.name)
    length = len(aliases)
    for idx in range(length):
      alias = aliases[idx]
      normalized = unidecode.unidecode(alias)
      if normalized != alias:
        aliases.append(normalized)
        add_role(normalized)
    for alias in aliases:
      no_space = alias.replace(' ', '')
      if no_space != alias:
        add_role(no_space)

######################### SERIALIZATION ########################

@dictionize.custom_keys('players', 'excess_roles', 'og_excess', 'played_roles', 'status', 'og_roles', 'history', 'tmp_channels', 'player_count')
class Dictionize:
  async def dtemplate(self, dict):
    return THIS_MODULE
  def e_players(self, dict, val):
    dict['players'] = [ dictionize.encode(p, Player.full_dictionize__) for p in val.values() if p.persistent() ]
  async def d_players(self, obj, val):
    player_hint = Player.FullDictionize(await get_available_members())
    for p in val:
      await player_hint.dtemplate(p)
    for p in val:
      await dictionize.decode_fields(players[p['id']], p, player_hint)
  async def d_tmp_channels(self, obj, val):
    for name, val in val.items():
      tmp_channels[name] = await dictionize.decode(val, Channel.dictionize__)
  async def d_excess_roles(self, obj, val):
    obj.excess_roles = [ roles[role].name for role in val ]
dictionize__ = Dictionize()

def state_to_json(fp):
  obj = dictionize.encode(THIS_MODULE, dictionize__)
  if game_mode:
    obj.update(dictionize.encode(game_mode, game_mode.dictionize__))
  return json.dump(obj, fp, cls = dictionize.Encoder, indent = 2)

async def json_to_state(fp):
  await end_game()
  obj = json.load(fp)
  await dictionize.decode(obj, dictionize__)
  if game_mode:
    await dictionize.decode(obj, game_mode.dictionize__)
  if 'null' in vote_list:
    vote_list[None] = vote_list['null']
    del vote_list['null']
  vote_list.clear()
  if status == 'day':
    for p in players.values():
      if p.role:
        vote_list[p.vote] = vote_list[p.vote] + 1 if p.vote in vote_list else 1

##################### COMMANDS DECORATORS ######################

def copy_cmd_info(src, dest):
  dest.__name__ = src.__name__
  if hasattr(src, 'cmd_types'):
    dest.cmd_types = src.cmd_types
  return dest

def debug_cmd(func):
  async def check(message, args):
    await (func(message, args) if DEBUG else question(message, tr('debug_command')))
  func.cmd_types.append('debug')
  return copy_cmd_info(func, check)

def admin_cmd(func):
  async def check(message, args):
    await (func(message, args) if message.author.id in admins else question(message, tr('require_admin')))
  func.cmd_types.append('admin')
  return copy_cmd_info(func, check)

def setup_cmd(func):
  async def check(message, args):
    if status:
      return await question(message, tr('forbid_game_started').format(cmd_names[func.__name__]))
    if not is_public_channel(message.channel):
      return await question(message, tr('public_only').format(cmd_names[func.__name__]))
    await func(message, args)
  func.cmd_types.append('setup')
  return copy_cmd_info(func, check)

def single_arg(message_key, *message_args):
  def decorator(func):
    async def sa_result(*others, message, args):
      arr = split_args(args)
      if len(arr) == 1:
        await func(*others, message=message, args=arr[0])
      else:
        await question(message, tr(message_key).format(cmd_names[func.__name__], *message_args))
    return copy_cmd_info(func, sa_result)
  return decorator

def single_use(var_name = 'target'):
  def decorator(func):
    async def su_result(self, *others, message, args):
      if getattr(self, var_name):
        return await question(message, tr('ability_used').format(cmd_names[func.__name__]))
      await func(self, *others, message=message, args=args)
    return copy_cmd_info(func, su_result)
  return decorator

def check_status(required_status = 'night'):
  def decorator(func):
    async def handler(*others, message, args):
      if required_status != status:
        await question(message, tr(required_status + '_only'))
      else:
        await func(*others, message=message, args=args)
    return copy_cmd_info(func, handler)
  return decorator

def check_public(func):
  async def p_handler(*others, message, args):
    if is_public_channel(message.channel):
      await func(*others, message=message, args=args)
    else:
      await warn_wrong_channel(message, 'public', func.__name__)
  return copy_cmd_info(func, p_handler)

def check_dm(func):
  async def dm_handler(*others, message, args):
    if is_dm_channel(message.channel):
      await func(*others, message=message, args=args)
    else:
      await warn_wrong_channel(message, 'dm', func.__name__)
  return copy_cmd_info(func, dm_handler)

def check_channel(channel_name):
  def decorator(func):
    async def c_handler(*others, message, args):
      tmp_channel = tmp_channels[channel_name]
      if message.channel.id == tmp_channel.extern.id:
        await func(*others, tmp_channel, message=message, args=args)
      else:
        await warn_wrong_channel(message, channel_name, func.__name__)
    return copy_cmd_info(func, c_handler)
  return decorator

def get_role(id):
  if not id in players:
    return None
  player = players[id]
  return player.role

def make_role_cmd(name):
  async def check(message, args):
    role = get_role(message.author.id)
    if not role:
      return await question(message, tr('not_playing'))
    elif not hasattr(role, name):
      return await question(message, tr('wrong_role').format(cmd_names[name]))
    await getattr(role, name)(players[message.author.id], message=message, args=args)
  check.__name__ = name
  command(check)
  check.cmd_types.append('role')
  globals()[name] = check

########################## COMMANDS ############################

ROLE_COMMANDS = [ 'Kill', 'Defend', 'See', 'Swap', 'Steal', 'Take', 'Clone', 'Reveal', 'Revive', 'Poison', 'Investigate', 'Vote', 'VoteNoLynch', 'Unvote' ]
for cmd_name in ROLE_COMMANDS:
  make_role_cmd(cmd_name)

@command
async def Help(message, args):
  if args:
    args = args.strip()
    if args in commands:
      await confirm(message, commands[args].description)
    elif args in roles:
      await role_help(message, args)
    else:
      await confused(message.channel, args)
  else:
    command_list = other_commands[:]
    if message.author.id in admins:
      command_list += admin_commands
    role = get_role(message.author.id)
    if role:
      command_list = role.commands + command_list
    await message.author.send(tr('help_list').format('`, `'.join(command_list)) + tr('help_detail').format(cmd_names['Help']))

@command
async def Sleep(message, args):
  if not message.author.id in players:
    return await say_good_night(message)
  player = players[message.author.id]
  if not player.role or not hasattr(player.role, 'Sleep'):
    return await say_good_night(message)
  else:
    await player.role.Sleep(player, message=message, args=args)

@admin_cmd
@setup_cmd
@command
async def AddRole(message, args):
  role_list = []
  if args:
    for role in split_args(args):
      role = role.lower()
      if not role:
        return await question(message, tr('add_wronguse').format(cmd_names['AddRole']))
      elif role in roles:
        name = roles[role].name
        played_roles.append(name)
        role_list.append(name)
      else:
        return await confused(message.channel, role)
    await message.channel.send(tr('add_success').format(join_with_and(role_list)) + player_needed_msg())
  else:
    await question(message, tr('add_wronguse').format(cmd_names['AddRole']))

@admin_cmd
@setup_cmd
@command
async def RemoveRole(message, args):
  role_list = []
  if args:
    for role in split_args(args):
      role = role.lower()
      if not role:
        return await question(message, tr('remove_wronguse').format(cmd_names['RemoveRole']))
      elif role in roles:
        name = roles[role].name
        if name in played_roles:
          played_roles.pop(played_roles.index(name))
          role_list.append(name)
        else:
          return await question(message, tr('remove_notfound').format(role))
      else:
        return await confused(message.channel, args)
    await message.channel.send(tr('remove_success').format(join_with_and(role_list)) + player_needed_msg())
  else:
    await question(message, tr('remove_wronguse').format(cmd_names['RemoveRole']))

@setup_cmd
@command
async def Start(message, args):
  await start_game(message, players.values())

@admin_cmd
@setup_cmd
@command
async def StartImmediate(message, args):
  def get_player(extern):
    id = extern.id
    if id in players:
      return players[id]
    players[id] = player = Player(extern)
    return player
  await start_game(message, [get_player(member) for member in await get_available_members()])

@command
async def Info(message, args):
  if not played_roles:
    msg = tr('no_roles')
    if players:
      msg += tr('default_roles').format(DEFAULT_ROLES)
    return await confirm(message, msg)
  await confirm(message, list_roles() + (game_info() if status else player_needed_msg()))

@check_public
@command
async def VoteDetail(message, args):
  item = tr('vote_detail_item')
  await main_channel().send(tr('vote_detail').format('\n'.join([
        item.format(player.extern.name, player.vote.extern.mention)
      if isinstance(player.vote, Player) else
        tr('vote_detail_item_nolynch').format(player.extern.name)
      for player in players.values()
        if player.vote
  ])))

@check_public
@check_status('day')
@command
async def VoteCount(message, args):
  most_vote = await low_vote_count('vote_detail')
  await main_channel().send(tr('most_vote').format(most_vote.extern.mention) if most_vote else tr('vote_tie'))

async def low_vote_count(key):
  vote_detail = []
  most_vote = None
  max_vote = 0
  vote_item = tr('vote_item')
  for p, votes in vote_list.items():
    if p and votes:
      vote_detail.append(vote_item.format(p.extern.mention if p != True else tr('no_lynch_vote'), votes))
      if votes > max_vote:
        max_vote = votes
        most_vote = p
      elif votes == max_vote:
        most_vote = None
  await main_channel().send(tr(key).format("\n".join(vote_detail)))
  return most_vote

@admin_cmd
@command
async def CloseVote(_, __):
  await close_vote()
async def close_vote():
  if vote_countdown_task:
    vote_countdown_task.cancel()
    clear_vote_countdown()
  most_vote = await low_vote_count('vote_result')
  if isinstance(most_vote, Player) and hasattr(most_vote.role, 'on_lynched'):
    if await most_vote.role.on_lynched(most_vote):
      return
  if most_vote and most_vote != True:
    await main_channel().send(tr('lynch').format(most_vote.extern.mention))
    await on_lynch(most_vote)
  else:
    await main_channel().send(tr('no_lynch'))
    await on_no_lynch()

@check_public
@check_status(None)
@command
async def History(message, args):
  if history:
    reveal_item = tr('reveal_item')
    command_item = tr('command_item')
    command_item_empty = tr('command_item_empty')
    roles = '\n'.join([ reveal_item.format(player, role) for player, role in og_roles.items() ])
    commands = '\n'.join([ command_item.format(h[0], h[1], h[2]) if h[2] != None else command_item_empty.format(h[0], h[1]) for h in history ])
    await show_history(message.channel, roles, commands)
  else:
    await question(message, tr('no_history'))

@admin_cmd
@command
async def Save(message, args):
  args = args.strip()
  if '\\' in args or '/' in args:
    return await question(message, tr('invalid_file_name'))
  fp = open('saves/' + args, 'w')
  state_to_json(fp)
  await confirm(message, tr('save_success').format(args))

@admin_cmd
@command
async def Load(message, args):
  if DEBUG:
    global players
    players.clear()
  args = args.strip()
  if '\\' in args or '/' in args:
    return await question(message, tr('invalid_file_name'))
  fp = open('saves/' + args, 'r')
  await json_to_state(fp)
  await confirm(message, tr('load_success').format(args))

@admin_cmd
@command
async def EndGame(_, __):
  await end_game()
async def end_game():
  global status
  status = None
  for player in players.values():
    for attr in list(vars(player).keys()):
      if not attr in PLAYER_PERSISTENT_ATTR:
        delattr(player, attr)
    player.role = player.vote = None
  for channel in tmp_channels.values():
    await channel.delete()
  tmp_channels.clear()
  vote_list.clear()

@admin_cmd
@command
async def WakeUp(_, __):
  await wake_up()
async def wake_up():
  for player in players.values():
    if hasattr(player.role, 'before_dawn'):
      await player.role.before_dawn(player)
  global status
  status = 'day'
  await on_wake_up()
  global vote_list
  vote_list = { None: player_count }
  for p in players.values():
    p.vote = None

@debug_cmd
@command
async def RevealAll(message, args):
  await low_reveal_all(message.channel)

async def low_reveal_all(channel):
  reveal_item = tr('reveal_item')
  msg = tr('reveal_all').format('\n'.join([ reveal_item.format(player.extern.name, role_str(player)) for player in sort_players(players.values()) if player.role ]))
  if excess_roles:
    msg += '\n' + tr('excess_roles').format(', '.join([name for name in excess_roles]))
  await channel.send(msg)

############################# UTILS ############################

def warn(msg):
  msg = repr(traceback.extract_stack()) + '\nWARNING: ' + msg

def list_roles():
  return tr('list_roles').format(join_with_and(played_roles))
def player_needed_msg():
  return tr('player_needed').format(needed_players_count(played_roles))

def split_args(args):
  return [ arg.strip() for arg in args.split(',') ] if args else []

def remind_vote():
  return tr('vote').format(cmd_names['Vote'], cmd_names['VoteNoLynch'])

async def say_good_night(message):
  await confirm(message, tr('good_night'))

def disconnect():
  roles.clear()
  channel_events.clear()
  generate_injections()
  played_roles.clear()

async def confirm(message, text):
  await message.reply(tr('confirm').format(message.author.mention) + str(text))

async def question(message, text):
  await message.reply(tr('question').format(message.author.mention) + str(text))

async def confused(channel, msg):
  await channel.send(tr('confused').format('`' + msg + '`'))

async def warn_wrong_channel(message, required_channel, raw_cmd):
  cmd = cmd_names[raw_cmd]
  if not is_dm_channel(message.channel):
    if raw_cmd == 'Sleep':
      await say_good_night(message)
    else:
      await question(message, tr('wrong_role').format(cmd))
  await message.author.send(tr('question').format(message.author.mention) + tr(required_channel + '_only').format(cmd))

def record_history(message, result):
  history.append((message.author.name, message.content, result))

def join_with_and(arr):
  if hasattr(arr, '__len__'):
    return arr[0] if len(arr) == 1 else ", ".join(arr[:-1]) + ", " + tr('_and') + arr[-1]
  warn("Invalid argument for join_with_and: " + repr(arr))
  return repr(arr)

async def base_find_player(message, name):
  if name.startswith('@'):
    name = name[1:]
  for player in players.values():
    if player.extern.name == name:
      if not player.role:
        return await question(message, tr('player_norole').format(player.extern.mention))
      return player
  await question(message, tr('player_notfound').format(name))

def clear_vote_countdown():
  globals()['vote_countdown_task'] = None

async def await_vote_countdown():
  if vote_countdown_task:
    try:
      await vote_countdown_task
    except asyncio.CancelledError: pass

async def announce_winners(winners):
  channel = main_channel()
  if winners:
    await channel.send(tr('winners').format(join_with_and(winners)))
  else:
    await channel.send(tr('no_winners'))
  await low_reveal_all(channel)
  await end_game()

########################## INJECTIONS ##########################

# This decorator is meant to be used by game mode integrations
# It allows you to easily modify any variable in this module

def injection(func):
  globals()[func.__name__] = func
  return func

def generate_injections():
  def after_shuffle(shuffled_roles): pass
  def default_roles_needed(player_count): raise missing_injection_error('default_roles_needed')
  def needed_players_count(played_roles): raise missing_injection_error('needed_players_count')
  async def on_lynch(player): raise missing_injection_error('on_lynch')
  async def on_no_lynch(): pass
  async def show_history(channel, roles, commands): raise missing_injection_error('show_history')
  async def role_help(message, role): raise missing_injection_error('role_help')
  async def find_player(message, name): return await base_find_player(message, name)
  def game_info(): return ''
  def start_night(): pass
  async def on_wake_up(): raise missing_injection_error('on_wake_up')
  def role_str(player): raise missing_injection_error('role_str')
  # Don't try this at home
  globals().update(locals())
generate_injections()

def missing_injection_error(name):
  return NotImplementedError("Function `{}` not implemented! Implement it using the @injection decorator".format(name))

######################### COMMON ROLES #########################

class Wolf:
  async def on_start(self, player, first_time = True):
    if not 'wolf' in tmp_channels:
      tmp_channels['wolf'] = await Channel.create(tr('wolf'), player)
    else:
      channel = tmp_channels['wolf']
      await channel.add(player)
      if not first_time:
        await channel.extern.send(tr('channel_greeting').format(player.extern.mention, channel.extern.name))

class Voter:
  @single_arg('vote_wronguse')
  @check_public
  @check_status('day')
  async def Vote(self, me, message, args):
    player = await find_player(message, args)
    if player:
      await on_voted(me, player)
  @check_public
  @check_status('day')
  async def VoteNoLynch(self, me, message, args):
    await on_voted(me, True)
  @check_public
  @check_status('day')
  async def Unvote(self, me, message, args):
    if not me.vote:
      return await question(message, tr('not_voting'))
    await on_voted(me, None)

############################# MAIN #############################

async def process_message(message):
  content = message.content
  if content.startswith(BOT_PREFIX):
    try:
      async with lock:
        full = content[len(BOT_PREFIX):]
        arr = full.split(maxsplit=1)
        if len(arr) == 0:
          return
        if len(arr) == 1:
          cmd = arr[0]
          args = None
        else:
          [cmd, args] = arr
        cmd = unidecode.unidecode(cmd.lower())
        if cmd in commands:
          await commands[cmd].func(message=message, args=args)
        else:
          await confused(message.channel, BOT_PREFIX + cmd)
    except:
      await debug(traceback.format_exc())
      await message.reply(tr('exception'))

async def process_and_wait(message):
  await process_message(message)
  try:
    await await_vote_countdown()
  except:
    await debug(traceback.format_exc())

async def greeting():
  await main_channel().send(tr('greeting').format(cmd_names['Help'], cmd_names['StartImmediate']))
