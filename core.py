import random

commands = {}
roles = {}
main_commands = []
players = {}
played_roles = []

ADMIN_AUTH = [ 'common', 'admin', 'setup']
BOT_PREFIX = '!'

############################ ACTIONS ###########################

# These functions must be provided to the module by the @action decorator
def tr(key): raise missing_action_error('tr')
async def send_post(channel, text): raise missing_action_error('send_post')
async def get_available_members(): raise missing_action_error('get_available_members')

def missing_action_error(name):
  return NotImplementedError("Action `{}` not implemented! Implement it using the @action decorator"
      .format(name))

def action(func):
  name = func.__name__
  def accept_name(text):
    if name == text:
      globals()[name] = func
      return True
  if not(accept_name('send_post') or accept_name('get_available_members') or accept_name('tr')):
    raise ValueError("Action not used: {}".format(name))

########################### CLASSES ############################

class Command:
  def __init__(self, name, func, auth, description):
    self.name = name
    self.func = func
    self.auth = auth
    self.description = description

  def make_alias(self, alias):
    return Command(self.name, self.func, self.auth,
        tr('alias').format(alias, self.name) + self.description)

  def is_listed(self, _):
    return True

class AdminCommand(Command):
  def is_listed(self, player):
    return 'admin' in player.auth

class Player:
  def __init__(self, auth):
    self.auth = auth

########################### UTILS ##############################

def cmd(authority):
  def decorator(func):
    [name, description, *aliases] = tr('cmd_' + func.__name__)
    description = description.format(BOT_PREFIX + name)
    command = commands[name] = Command(name, func, authority, description)
    main_commands.append(name)
    for alias in aliases:
      if alias not in commands:
        commands[alias] = command.make_alias(alias)
      else:
        print("ERROR: Can't create alias {} to command {}!".format(alias, name))
    return func
  return decorator

#def role(func):

async def confirm(message, text):
  await send_post(message.channel, tr('confirm').format(message.author.mention) + str(text))

async def question(message, text):
  await send_post(message.channel, tr('question').format(message.author.mention) + str(text))

async def confused(channel, msg):
  await send_post(channel, tr('confused').format('`' + msg + '`'))

def get_player(id):
  if id in players:
    return players[id]
  players[id] = player = Player([ 'common' ])
  return player

def join_with_and(arr):
  return arr[0] if len(arr) == 1 else ", ".join(arr[:-1]) + ", " + tr('_and') + arr[-1]

############################ INIT ##############################

def initialize(admins):
  random.seed()
  for admin in admins:
    players[admin] = Player(ADMIN_AUTH)

########################## COMMANDS ############################

  @cmd('common')
  async def help(message, args):
    if args:
      if args in commands:
        await confirm(message, commands[args][2])
      else:
        await confirm(message, tr('help_notfound').format(args))
    else:
      player = get_player(message.author.id)
      command_list = [ BOT_PREFIX + cmd for cmd in main_commands
          if commands[cmd].is_listed(player)
      ]
      await confirm(message, tr('help_list').format('`, `'.join(command_list)))

  @cmd('admin')
  async def start_immediate(message, args):
    members = [ member.mention async for member in get_available_members() ]
    await confirm(message, tr('start').format(join_with_and(members)))

  @cmd('setup')
  async def add_role(message, args):
    if not args:
      await question(message, tr('add_nothing').format(BOT_PREFIX))
    elif args in roles:
      played_roles.append(args)
    else:
      await confused(message.channel, args)

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
    if cmd in commands:
      player = get_player(message.author.id)
      await commands[cmd].func(message, args)
    else:
      await confused(message.channel, BOT_PREFIX + cmd)
