import discord
import os
import json
import core
import importlib
import asyncio
from server_conf import *
random = core.random

intents = discord.Intents.default()
intents.members = True
intents.presences = True
client = discord.Client(intents=intents)
guild = None

MAX_MESSAGE_LEN = 2000

########################### EVENTS #############################

@client.event
async def on_ready():
  global guild
  print("We have logged in as {0.user}".format(client))
  debug_channel = client.get_channel(DEBUG_CHANNEL)
  guild = client.get_channel(GAME_CHANNEL).guild
  core.initialize([guild.get_member(id) for id in ADMINS])

@client.event
async def on_message(message):
  if message.author == client.user:
    return
  await core.process_and_wait(message)

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
async def get_available_members():
  result = []
  async def process(id):
    """Properly retrieve the online status of a member.
    The status property of member objects may contain incorrect value."""
    member = guild.get_member(id)
    if not member or member.id == client.user.id:
      return
    if member.status in {discord.Status.online, discord.Status.idle}:
      result.append(member)
  for member in guild.members:
    await process(member.id)
  return result

@core.action
async def create_channel(name, *players):
  overwrites = { p: discord.PermissionOverwrite(read_messages=True, send_messages = True) for p in players }
  await guild.create_text_channel(name, overwrites)

@core.action
async def add_member(channel, player):
  await channel.set_permission(player, read_messages = True, send_messages = True)

@core.action
def is_dm_channel(channel):
  return isinstance(channel, discord.DMChannel)

@core.action
def is_public_channel(channel):
  return channel.id == GAME_CHANNEL

@core.action
def main_channel():
  return client.get_channel(GAME_CHANNEL)

########################## EXECUTION ###########################

client.run(TOKEN)

