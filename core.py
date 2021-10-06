import random

commands = {}
roles = {}
main_commands = []

players = {}
real_roles = {}
played_roles = []
tmp_channels = {}

BOT_PREFIX = '!'
CREATE_NORMALIZED_ALIASES = True

############################ ACTIONS ###########################

# These functions must be provided to the module by the @action decorator
def tr(key): raise missing_action_error('tr')
def get_available_members(): raise missing_action_error('get_available_members')
async def create_channel(name, *players): raise missing_action_error('create_channel')
async def add_member(channel, player): raise missing_action_error('add_member')
def is_dm_channel(channel): raise missing_action_error('is_dm_channel')
def is_public_channel(channel): raise missing_action_error('is_public_channel')

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
      or accept_name('shuffle_copy') or accept_name('create_channel')
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

  def make_alias(self, alias):
    return Command().decorate(self.name, self.func,
        tr('alias').format(alias, self.name) + self.description)

  def is_listed(self, _, __):
    return True

class AdminCommand(Command):
  def is_listed(self, player, _):
    return player.is_admin

  def decorate(self, name, func, description):
    async def check(message, args):
      if not players[message.author.id].is_admin:
        await question(message, tr('require_admin'))
      else:
        await func(message, args)
    return super().decorate(name, check, description)

class RoleCommand(Command):
  def __init__(self, required_channel):
    self.required_channel = required_channel

  def is_listed(self, player, channel):
    return name_channel(channel) == self.required_channel and player.role and hasattr(player.role, self.name)

  def decorate(self, name, _, description):
    async def check(message, args):
      if name_channel(message.channel) != self.required_channel:
        await question(message, tr(self.required_channel + '_only').format(BOT_PREFIX + name))
        return
      player = players[message.author.id]
      if not player:
        await question(message, tr('self_notfound'))
        return
      if not hasattr(player.role, name):
        await question(message, tr('wrong_role').format(BOT_PREFIX + name))
      else:
        await getattr(player.role, name)(message, args)
    return super().decorate(name, check, description)

class SetupCommand(AdminCommand):
  pass

class Player:
  def __init__(self, is_admin, extern):
    self.is_admin = is_admin
    self.extern = extern
    self.role = None
    self.real_role = None

########################## DECORATORS ##########################

def cmd(base):
  def decorator(func):
    [name, description, *aliases] = tr('cmd_' + func.__name__)
    description = description.format(BOT_PREFIX + name)

    commands[name] = base.decorate(name, func, description)
    main_commands.append(name)
    for alias in aliases:
      if alias not in commands:
        commands[alias] = base.make_alias(alias)
      else:
        print("ERROR: Can't create alias {} to command {}!".format(alias, name))
    return func
  return decorator

def role(base):
  [base.name, base.description, base.greeting, *aliases] = tr('role_' + base.__name__.lower())
  roles[base.name] = base
  if CREATE_NORMALIZED_ALIASES:
    import unidecode
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

def single_arg(message_key):
  def decorator(func):
    async def result(*arr):
      args = arr[-1].strip()
      if not args:
        return await question(arr[-2], tr(message_key).format(BOT_PREFIX))
      await func(*arr[:-1], args)
    result.__name__ = func.__name__
    return result
  return decorator

def single_use(func):
  async def result(self, message, args):
    if self.used:
      return await question(message, tr('ability_used').format(BOT_PREFIX + get_command_name('swap')))
    await func(self, message, args)
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

def player_count():
  return len(played_roles)

def get_command_name(name):
  return tr('cmd_' + name)[0]

async def find_player(message, name):
  for player in players.values():
    if player.extern.name == name:
      if not player.role:
        return await question(message, tr('player_norole').format(player.mention))
      return player
  return await question(message, tr('player_notfound').format(name))

############################ INIT ##############################

def initialize(admins):
  random.seed()
  for admin in admins:
    players[admin.id] = Player(True, admin)

########################## COMMANDS ############################

  @cmd(RoleCommand('dm'))
  def swap(): pass

  @cmd(RoleCommand('dm'))
  def see(): pass

  @cmd(Command())
  async def help(message, args):
    if args:
      if args in commands:
        await confirm(message, commands[args].description)
      else:
        await confused(message.channel, args)
    else:
      player = get_player(message.author)
      command_list = [ BOT_PREFIX + cmd for cmd in main_commands
          if commands[cmd].is_listed(player, message.channel)
      ]
      await confirm(message, tr('help_list').format('`, `'.join(command_list)))

  @cmd(SetupCommand())
  @single_arg('add_nothing')
  async def add_role(message, args):
    if args in roles:
      name = roles[args].name
      played_roles.append(name)
      await confirm(message, tr('add_success').format(name))
    else:
      await confused(message.channel, args)

  @cmd(Command())
  async def list_roles(message, args):
    await confirm(message, tr('list_roles').format(join_with_and(played_roles), player_count()))

  @cmd(AdminCommand())
  async def start_immediate(message, args):
    members = get_available_members()
    current_count = len(members)
    needed_count = player_count()
    if current_count > needed_count:
      await question(message, tr('start_needless').format(current_count, needed_count))
    elif current_count < needed_count:
      await question(message, tr('start_needmore').format(current_count, needed_count))
    else:
      await confirm(message, tr('start').format(join_with_and(
        [member.mention for member in members]
      )))
      for channel in tmp_channels.values():
        channel.delete()
      tmp_channels.clear()

      for idx, role in enumerate(shuffle_copy(played_roles)):
        player = get_player(members[idx])
        player.real_role = player.role = roles[role]()
        await player.extern.dm_channel.send(tr('role').format(role) + player.role.greeting.format(BOT_PREFIX))
        if hasattr(player.role, 'on_start'):
          await player.role.on_start(player)

      for id, channel in tmp_channels.items():
        await channel.send(tr(id + '_channel').format(
            join_with_and([member.extern.mention for member in channel.members])))

  @cmd(AdminCommand())
  async def reveal_all(message, args):
    await confirm(message, join_with_and([ player.extern.name + ':' + player.real_role.name
        for player in players.values() if player.role ]))

############################ ROLES #############################

  @role
  class Villager: pass

  @role
  class Seer(Villager):
    def __init__(self):
      self.used = False

    async def see(self, message, args):
      me = get_player(message.author)
      if me.extern.name == args:
        return await question(message, tr('seer_self'))
      player = await find_player(message, args)
      if player:
        self.used = True
        return await confirm(message, tr('see_success').format(player.extern.mention, player.real_role.name))

  @role
  class Thief(Villager):
    def __init__(self):
      self.used = False

    @single_use
    @single_arg('thief_swap_nothing')
    async def swap(self, message, args):
      me = get_player(message.author)
      if me.extern.name == args:
        return await question(message, tr('thief_self'))
      player = await find_player(message, args)
      if player:
        me.real_role, player.real_role = player.real_role, me.real_role
        self.used = True
        return await confirm(message, tr('thief_success').format(args))

  @role
  class Wolf:
    async def on_start(self, player):
      if not 'wolf' in tmp_channels:
        tmp_channels['wolf'] = await create_channel(tr('wolf'), player)
      else:
        await add_member(tmp_channels['wolf'], player)

########################### EVENTS #############################

async def process_message(message):
  content = message.content
  if content.startswith(BOT_PREFIX):
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
      player = get_player(message.author)
      await commands[cmd].func(message, args)
    else:
      await confused(message.channel, BOT_PREFIX + cmd)
