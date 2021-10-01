import discord
import random
import os
import json
from server_conf import *

intents = discord.Intents.default()
intents.members = True
intents.presences = True
client = discord.Client(intents=intents)
commands = {}
roles = {}
main_commands = []
players = {}
played_roles = []

MAX_MESSAGE_LEN = 2000
ADMIN_AUTH = [ 'common', 'admin', 'setup']

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

############################ INIT ##############################

random.seed()

def load_language(language):
  file = 'lang/{}.json'.format(language)
  if not os.path.isfile(file):
    file = 'lang/vn.json'
    print("Could not find language file at lang/{}.json, fallback to vietnamese".format(language))
  with open(file, 'r', encoding = 'utf-8') as f:
    return json.load(f)
lang = load_language(LANGUAGE)

def init_players(admins):
  for admin in admins:
    players[admin] = Player(ADMIN_AUTH)
init_players(ADMINS)

########################### EVENTS #############################

@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))
  channel = client.get_channel(int(GAME_CHANNEL))
  debug_channel = client.get_channel(DEBUG_CHANNEL)

@client.event
async def on_message(message):
  if message.author == client.user:
    return

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
    #await debug("Received command ```{}``` with arguments ```{}```".format(cmd, args))
    if cmd in commands:
      player = get_player(message.author.id)
      await commands[cmd].func(message, args)
    else:
      await send_confused(message.channel, BOT_PREFIX + cmd)

########################### UTILS ##############################

async def send_confused(channel, msg):
  await send_post(channel, tr('confused').format('`' + msg + '`'))

async def debug(msg):
  await client.get_channel(DEBUG_CHANNEL).send(msg)

def tr(key):
  result = lang[key]
  return result if isinstance(result, str) else result[random.randrange(len(result))]

def cmd(authority):
  def decorator(func):
    [name, description, *aliases] = lang['commands'][func.__name__]
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

async def send_post(channel, post):
  if len(post) <= MAX_MESSAGE_LEN:
    return await channel.send(post)
  else:
    await channel.send(post[:MAX_MESSAGE_LEN])
    await send_post(channel, post[MAX_MESSAGE_LEN:])

async def confirm(message, text):
  await send_post(message.channel, tr('confirm').format(message.author.mention) + str(text))

async def question(message, text):
  await send_post(message.channel, tr('question').format(message.author.mention) + str(text))

def get_player(id):
  if id in players:
    return players[id]
  player = [[ 'common' ]]
  player[id] = player
  return player

def is_online(guild, id):
  """Properly retrieve the online status of a member.
  The status property of member objects may contain incorrect value."""
  member = guild.get_member(id)
  return member.status in [discord.Status.online, discord.Status.idle] if member else False

def join_with_and(arr):
  return arr[0] if len(arr) == 1 else ", ".join(arr[:-1]) + ", " + lang['and'] + arr[-1]

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
  guild = message.channel.guild
  members = [member.mention
      async for member in guild.fetch_members()
        if is_online(guild, member.id) and member.id != client.user.id
  ]
  await confirm(message, tr('start').format(join_with_and(members)))

@cmd('setup')
async def add_role(message, args):
  if not args:
    await question(message, tr('add_nothing').format(BOT_PREFIX))
  elif args in roles:
    played_roles.append(args)
  else:
    await send_confused(message.channel, args)

############################ ROLES #############################

########################## EXECUTION ###########################

client.run(TOKEN)

