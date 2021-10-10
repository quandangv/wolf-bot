import random
import asyncio
import sys

lock = asyncio.Lock()
commands = {}
roles = {}
channel_events = {}
main_commands = []
vote_list = {}

players = {}
played_roles = []
excess_roles = []
tmp_channels = {}
status = None
player_count = 0

vote_countdown_task = None
vote_countdown_monitor = None

THIS_MODULE = sys.modules[__name__]
BOT_PREFIX = '!'
CREATE_NORMALIZED_ALIASES = True
EXCESS_CARDS = 3
DEBUG = False
SUPERMAJORITY = 2/3
VOTE_COUNTDOWN = 60
LANDSLIDE_VOTE_COUNTDOWN = 10
SEER_REVEAL = 2

############################ ACTIONS ###########################

# These functions must be provided to the module by the @action decorator
def tr(key): raise missing_action_error('tr')
def get_available_members(): raise missing_action_error('get_available_members')
async def create_channel(name, *players): raise missing_action_error('create_channel')
async def add_member(channel, player): raise missing_action_error('add_member')
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
      or accept_name('is_dm_channel') or accept_name('is_public_channel')):
    raise ValueError("Action not used: {}".format(name))
  return func

########################### CLASSES ############################

class Command:
  def decorate(self, name, func, description):
    self.name = name
    self.func = func
    self.description = description
    return self

  def make_alias(self, alias, description):
    return Command().decorate(self.name, self.func,
        tr('alias').format(alias, self.name) + description)

  def is_listed(self, _, __):
    return True

class DebugCommand(Command):
  def is_listed(self, _, __):
    return DEBUG

  def decorate(self, name, func, description):
    async def check(message, args):
      if DEBUG:
        await func(message, args)
      else:
        await question(message, tr('debug_command'))
    return super().decorate(name, check, description)

class AdminCommand(Command):
  def is_listed(self, player, _):
    return player.is_admin

  def decorate(self, name, func, description):
    async def check(message, args):
      if not players[message.author.id].is_admin:
        await question(message, tr('require_admin'))
      elif not is_public_channel(message.channel):
        await question(message, tr('public_only').format(BOT_PREFIX + name))
      else:
        await func(message, args)
    return super().decorate(name, check, description)

class PlayerCommand(Command):
  def is_listed(self, player, _):
    return player.role

  def decorate(self, name, func, description):
    async def check(message, args):
      if not message.author.id in players:
        return await question(message, tr('not_playing'))
      player = players[message.author.id]
      if not player.role:
        await question(message, tr('not_playing'))
      else:
        await func(player, message, args)
    return super().decorate(name, check, description)

class RoleCommand(PlayerCommand):
  def __init__(self, required_channel, required_status = 'night'):
    self.required_channel = required_channel
    self.required_status = required_status

  def is_listed(self, player, channel):
    return super().is_listed(player, channel) and name_channel(channel) == self.required_channel and hasattr(player.role, self.name)

  def decorate(self, name, _, description):
    async def check(player, message, args):
      if name_channel(message.channel) != self.required_channel:
        return await question(message, tr(self.required_channel + '_only').format(BOT_PREFIX + name))
      if self.required_status != status:
        return await question(message, tr(self.required_status + '_only'))
      if not hasattr(player.role, name):
        return await question(message, tr('wrong_role').format(BOT_PREFIX + name))
      await getattr(player.role, name)(player, message, args)
    return super().decorate(name, check, description)

class SetupCommand(AdminCommand):
  def is_listed(self, player, _):
    return not status and super().is_listed(player, None)

  def decorate(self, name, func, description):
    async def check(message, args):
      if status:
        return await question(message, tr('forbid_game_started').format(BOT_PREFIX + name))
      await func(message, args)
    return super().decorate(name, check, description)

class Player:
  def __init__(self, is_admin, extern):
    self.is_admin = is_admin
    self.extern = extern
    self.role = None
    self.real_role = None
    self.vote = None

########################## DECORATORS ##########################

def cmd(base):
  def decorator(func):
    [name, description, *aliases] = tr('cmd_' + func.__name__)
    description = description.format(BOT_PREFIX + name)

    commands[name] = base.decorate(name, func, description)
    if aliases:
      commands[name].description += tr('aliases_list').format(join_with_and(aliases))
    main_commands.append(name)
    for alias in aliases:
      if alias not in commands:
        commands[alias] = base.make_alias(alias, description)
      else:
        print("ERROR: Can't create alias {} to command {}!".format(alias, name))
    return func
  return decorator

def role(base):
  [base.name, base.description, base.greeting, *aliases] = tr('role_' + base.__name__.lower())
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
  return base

def channel_event(func):
  channel_events[func.__name__] = func

def single_arg(message_key, *message_args):
  def decorator(func):
    async def result(*arr):
      try:
        [arg] = arr[-1].split()
      except ValueError:
        return await question(arr[-2], tr(message_key).format(BOT_PREFIX, *message_args))
      await func(*arr[:-1], arg)
    result.__name__ = func.__name__
    return result
  return decorator

def single_use(func):
  async def result(self, me, message, args):
    if self.used:
      return await question(message, tr('ability_used').format(get_command_name(func.__name__)))
    await func(self, me, message, args)
  result.__name__ = func.__name__
  return result

############################# UTILS ############################

def name_channel(channel):
  if is_dm_channel(channel):
    return 'dm'
  if is_public_channel(channel):
    return 'public'
  for id, c in tmp_channels.items():
    if channel == c:
      return id

async def confirm(message, text):
  await message.channel.send(tr('confirm').format(message.author.mention) + str(text))

async def question(message, text):
  await message.channel.send(tr('question').format(message.author.mention) + str(text))

async def confused(channel, msg):
  await channel.send(tr('confused').format('`' + msg + '`'))

def get_player(extern):
  id = extern.id
  if id in players:
    return players[id]
  players[id] = player = Player(False, extern)
  return player

def join_with_and(arr):
  return arr[0] if len(arr) == 1 else ", ".join(arr[:-1]) + ", " + tr('_and') + arr[-1]

def needed_players_count():
  return max(0, len(played_roles) - EXCESS_CARDS)

def get_command_name(name):
  return BOT_PREFIX + tr('cmd_' + name)[0]

async def find_player(message, name):
  for player in players.values():
    if player.extern.name == name:
      if not player.role:
        return await question(message, tr('player_norole').format(player.mention))
      return player
  return await question(message, tr('player_notfound').format(name))

async def select_excess_card(message, wronguse_msg, args):
  try:
    number = int(args)
  except ValueError:
    return await question(message, tr(wronguse_msg).format(BOT_PREFIX, EXCESS_CARDS))
  if number < 1 or number > EXCESS_CARDS:
    return await question(message, tr('choice_outofrange').format(EXCESS_CARDS))
  return number

async def set_used(role):
  role.used = True
  await on_used()

async def on_used():
  for player in players.values():
    if player.role and hasattr(player.role, 'used') and not player.role.used:
      return
  await wake_up()

def clear_vote_countdown():
  global vote_countdown_task
  vote_countdown_task = None

async def wake_up():
  for player in players.values():
    if player.role and hasattr(player.role, 'before_dawn'):
      await player.role.before_dawn(player)
  global status
  status = 'day'
  global vote_list
  vote_list = { None: player_count }
  await main_channel().send(tr('wake_up') + tr('vote').format(BOT_PREFIX))

async def on_voted(me, vote):
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

    async def close_vote_countdown(seconds):
      await asyncio.sleep(seconds)
      clear_vote_countdown()
      async with lock:
        await close_vote(None, None)

    global vote_countdown_task
    if not_voted == 0:
      await close_vote(None, None)
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
  if len(channel.members) == 1:
    lone_wolf = get_player(channel.members[0])
    lone_wolf.role.used = False
    await channel.send(tr('wolf_get_reveal').format(BOT_PREFIX, EXCESS_CARDS))

async def await_vote_countdown():
  if vote_countdown_task:
    try:
      await vote_countdown_task
    except asyncio.CancelledError: pass

async def announce_winners(channel, winners):
  await channel.send(tr('end_game').format(join_with_and([ p.extern.mention for p in winners ])))
  await low_reveal_all(channel)
  await end_game(None, None)

############################ INIT ##############################

def initialize(admins):
  random.seed()
  for admin in admins:
    players[admin.id] = Player(True, admin)

########################## COMMANDS ############################

  @cmd(RoleCommand('dm'))
  def swap(): pass

  @cmd(RoleCommand('dm'))
  def steal(): pass

  @cmd(RoleCommand('dm'))
  def take(): pass

  @cmd(RoleCommand('dm'))
  def see(): pass

  @cmd(RoleCommand('dm'))
  def reveal(): pass

  @cmd(RoleCommand('dm'))
  def clone(): pass

  @cmd(Command())
  async def help(message, args):
    if args:
      if args in commands:
        await confirm(message, commands[args].description.format(THIS_MODULE))
      elif args in roles:
        await confirm(message, roles[args].description.format(THIS_MODULE))
      else:
        await confused(message.channel, args)
    else:
      player = get_player(message.author)
      command_list = [ BOT_PREFIX + cmd for cmd in main_commands
          if commands[cmd].is_listed(player, message.channel)
      ]
      await confirm(message, tr('help_list').format('`, `'.join(command_list)))

  @cmd(SetupCommand())
  async def add_role(message, args):
    role_list = []
    async def add_single(role):
      role = role.strip()
      if not role:
        await question(message, tr('add_wronguse').format(BOT_PREFIX))
      elif role in roles:
        name = roles[role].name
        played_roles.append(name)
        role_list.append(name)
        return True
      else:
        await confused(message.channel, role)
    args = args.split(',')
    for role in args:
      if not await add_single(role):
        return
    await confirm(message, tr('add_success').format(join_with_and(role_list)))

  @cmd(SetupCommand())
  async def remove_role(message, args):
    args = args.strip()
    if not args:
      await question(message, tr('remove_wronguse').format(BOT_PREFIX))
    elif args in roles:
      name = roles[args].name
      if name in played_roles:
        played_roles.pop(played_roles.index(name))
        await confirm(message, tr('remove_success').format(args))
      else:
        await question(message, tr('remove_notfound').format(args))
    else:
      await confused(message.channel, args)

  @cmd(Command())
  async def list_roles(message, args):
    if not played_roles:
      return await confirm(message, tr('no_roles'))
    await confirm(message, tr('list_roles').format(join_with_and(played_roles), needed_players_count()))

  @cmd(PlayerCommand())
  async def unvote(me, message, args):
    if not me.vote:
      return await question(message, tr('not_voting'))
    await on_voted(me, None)

  @cmd(PlayerCommand())
  @single_arg('vote_wronguse')
  async def vote(me, message, args):
    if status != 'day':
      return await question(message, tr('day_only'))
    if not is_public_channel(message.channel):
      return await question(message, tr('public_only').format(get_command_name('vote')))
    player = await find_player(message, args)
    if player:
      await on_voted(me, player.extern.mention)

  @cmd(AdminCommand())
  async def start_immediate(message, args):
    members = get_available_members()
    current_count = len(members)
    needed_count = needed_players_count()
    if current_count > needed_count:
      await question(message, tr('start_needless').format(current_count, needed_count))
    elif current_count < needed_count:
      await question(message, tr('start_needmore').format(current_count, needed_count))
    else:
      await confirm(message, tr('start').format(join_with_and(
        [member.mention for member in members]
      )))
      global status
      global player_count
      status = 'night'
      player_count = current_count

      shuffled_roles = shuffle_copy(played_roles)
      for idx, member in enumerate(members):
        player = get_player(member)
        player.real_role = player.role = roles[shuffled_roles[idx]]()
        await player.extern.dm_channel.send(tr('role').format(player.role.name) + player.role.greeting.format(BOT_PREFIX))
        if hasattr(player.role, 'on_start'):
          await player.role.on_start(player)

      excess_roles.clear()
      for idx in range(EXCESS_CARDS):
        excess_roles.append(roles[shuffled_roles[-idx - 1]]())

      for id, channel in tmp_channels.items():
        channel_name = id + '_channel'
        await channel.send(tr(channel_name).format(
            join_with_and([member.mention for member in channel.members])))
        if channel_name in channel_events:
          await channel_events[channel_name](channel)

  global close_vote
  @cmd(AdminCommand())
  async def close_vote(_, __):
    global vote_countdown_task
    if vote_countdown_task:
      vote_countdown_task.cancel()
      clear_vote_countdown()
    channel = main_channel()
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
    await channel.send(tr('vote_result').format("\n".join(vote_detail)))
    if most_vote:
      await channel.send(tr('lynch').format(most_vote))
      for lynched in players.values():
        if lynched.extern.mention == most_vote:
          role = lynched.real_role
          if isinstance(role, Villager) or isinstance(role, Minion):
            winners = [ player for player in players.values() if isinstance(player.real_role, WolfSide) ]
          elif isinstance(role, Tanner):
            winners = [ lynched ]
          elif isinstance(role, WolfSide):
            winners = [ player for player in players.values() if isinstance(player.real_role, Villager) ]
          await channel.send(tr('reveal_player').format(lynched.extern.mention, role.name))
          await announce_winners(channel, winners)
          break
    else:
      await channel.send(tr('no_lynch'))
      wolves = []
      villagers = []
      for p in players.values():
        if isinstance(p.real_role, WolfSide):
          wolves.append(p)
        elif isinstance(p.real_role, Villager):
          villagers.append(p)
      await announce_winners(channel, wolves if wolves else villagers)

  global end_game
  @cmd(AdminCommand())
  async def end_game(_, __):
    global status
    status = None
    for player in players.values():
      player.real_role = player.role = player.vote = None
    for channel in tmp_channels.values():
      channel.delete()
    tmp_channels.clear()
    vote_list.clear()

  @cmd(DebugCommand())
  async def reveal_all(message, args):
    await low_reveal_all(message.channel)

  global low_reveal_all
  async def low_reveal_all(channel):
    reveal_item = tr('reveal_item')
    await channel.send(tr('reveal_all').format('\n'.join([ reveal_item.format(player.extern.name, player.real_role.name) for player in players.values() if player.role ])) + '\n' + tr('excess_cards').format(', '.join([role.name for role in excess_roles])))

############################ ROLES #############################

  @role
  class Villager: pass

  @role
  class Tanner: pass

  @role
  class Insomniac(Villager):
    async def before_dawn(self, player):
      await player.extern.dm_channel.send(tr('insomniac_reveal').format(player.real_role.name))

  @role
  class Seer(Villager):
    def __init__(self):
      self.used = False
      self.reveal_count = 0

    @single_arg('reveal_wronguse', EXCESS_CARDS)
    async def reveal(self, me, message, args):
      if self.used:
        return await question(message, tr('seer_see_already'))
      if self.reveal_count >= SEER_REVEAL:
        return await question(message, tr('out_of_reveal').format(SEER_REVEAL))
      number = await select_excess_card(message, 'reveal_wronguse', args)
      if number:
        await confirm(message, tr('reveal_success').format(number, excess_roles[number - 1].name))
        self.reveal_count += 1
        if self.reveal_count >= SEER_REVEAL:
          await set_used(self)

    @single_arg('see_wronguse')
    async def see(self, me, message, args):
      if self.reveal_count:
        return await question(message, tr('seer_reveal_already'))
      if self.used:
        return await question(message, tr('ability_used').format(get_command_name('see')))
      if me.extern.name == args:
        return await question(message, tr('seer_self'))
      player = await find_player(message, args)
      if player:
        await set_used(self)
        return await confirm(message, tr('see_success').format(args, player.real_role.name))

  @role
  class Clone(Villager):
    def __init__(self):
      self.used = False

    @single_use
    @single_arg('clone_wronguse')
    async def clone(self, me, message, args):
      if me.extern.name == args:
        return await question(message, tr('clone_self'))
      player = await find_player(message, args)
      if player:
        me.role = me.real_role = roles[player.real_role.name]()
        if hasattr(me.role, 'on_start'):
          await me.role.on_start(me)
        return await confirm(message, tr('clone_success').format(args, me.role.name) + me.role.greeting.format(BOT_PREFIX))

  @role
  class Troublemaker(Villager):
    def __init__(self):
      self.used = False

    @single_use
    async def swap(self, me, message, args):
      players = args.split()
      if len(players) != 2:
        return await question(message, tr('troublemaker_wronguse').format(BOT_PREFIX))
      if me.extern.name in players:
        return await question(message, tr('no_swap_self'))
      players = [ await find_player(message, name) for name in players ]
      if players[0] and players[1]:
        players[0].real_role, players[1].real_role = players[1].real_role, players[0].real_role
        await set_used(self)
        return await confirm(message, tr('troublemaker_success')
            .format(*[ p.extern.name for p in players]))

  @role
  class Thief(Villager):
    def __init__(self):
      self.used = False

    @single_use
    @single_arg('thief_wronguse')
    async def steal(self, me, message, args):
      if me.extern.name == args:
        return await question(message, tr('no_swap_self'))
      player = await find_player(message, args)
      if player:
        me.real_role, player.real_role = player.real_role, me.real_role
        await set_used(self)
        return await confirm(message, tr('thief_success').format(args, me.real_role.name))

  @role
  class Drunk(Villager):
    def __init__(self):
      self.used = False

    @single_use
    @single_arg('drunk_wronguse', EXCESS_CARDS)
    async def take(self, me, message, args):
      number = await select_excess_card(message, 'drunk_wronguse', args)
      if number:
        number -= 1
        me.real_role, excess_roles[number] = excess_roles[number], me.real_role
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
      await player.extern.dm_channel.send(tr('wolves_reveal').format(join_with_and(wolves)))

  @role
  class Wolf(WolfSide):
    def __init__(self):
      self.used = True

    @single_use
    @single_arg('reveal_wronguse', EXCESS_CARDS)
    async def reveal(self, me, message, args):
      number = await select_excess_card(message, 'reveal_wronguse', args)
      if number:
        await confirm(message, tr('reveal_success').format(number, excess_roles[number - 1].name))
        await set_used(self)

    async def on_start(self, player):
      if not 'wolf' in tmp_channels:
        tmp_channels['wolf'] = await create_channel(tr('wolf'), player.extern)
      else:
        channel = tmp_channels['wolf']
        await add_member(channel, player.extern)
        await channel.send(tr('channel_greeting').format(player.extern.mention, channel.name))

########################### EVENTS #############################

async def process_message(message):
  content = message.content
  if content.startswith(BOT_PREFIX):
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
        await commands[cmd].func(message, args)
      else:
        await confused(message.channel, BOT_PREFIX + cmd)

async def process_and_wait(message):
  await process_message(message)
  await await_vote_countdown()
