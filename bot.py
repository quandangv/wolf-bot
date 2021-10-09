import discord
import os
import json
import core
import importlib
from server_conf import *
random = core.random

intents = discord.Intents.default()
intents.members = True
intents.presences = True
client = discord.Client(intents=intents)

MAX_MESSAGE_LEN = 2000

########################### EVENTS #############################

@client.event
async def on_ready():
  print("We have logged in as {0.user}".format(client))
  debug_channel = client.get_channel(DEBUG_CHANNEL)
  build = client.get_channel(GAME_CHANNEL).guild
  core.initialize([guild.get_member(id) for id in ADMINS])

@client.event
async def on_message(message):
  if message.author == client.user:
    return
  await core.process_message(message)

############################ INIT ##############################

def load_language(language):
  path = 'lang.{}'.format(language)
  if not importlib.util.find_spec(path):
    path = 'lang.vn'
    print("Could not find language module at {}, fallback to vietnamese".format(path))
  return importlib.import_module(path)
lang = load_language(LANGUAGE)

########################### UTILS ##############################

def core_injection(func):
  setattr(core, func.__name__, func)
  return func

async def debug(msg):
  await client.get_channel(DEBUG_CHANNEL).send(msg)

@core.action
def tr(key):
  result = getattr(lang, key)
  return result[random.randrange(len(result))] if isinstance(result, list) else result

@core.action
async def send_post(channel, text):
  if len(text) <= MAX_MESSAGE_LEN:
    return await channel.send(text)
  else:
    await channel.send(text[:MAX_MESSAGE_LEN])
    await send_post(channel, text[MAX_MESSAGE_LEN:])

@core.action
def get_available_members():
  def is_available(id):
    """Properly retrieve the online status of a member.
    The status property of member objects may contain incorrect value."""
    member = guild.get_member(id)
    return member.status in {discord.Status.online, discord.Status.idle} if member else False

  return [member for member in guild.members:
    if is_available(member.id) and member.id != client.user.id ]

########################## EXECUTION ###########################

client.run(TOKEN)

