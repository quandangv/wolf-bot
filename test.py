import core
import asyncio
import lang.vn as lang

posts = []
members = []

@core.action
def tr(key):
  def strip_prefix(prefix):
    nonlocal key
    if key.startswith(prefix):
      key = key[len(prefix):]
      return True
  if strip_prefix('cmd_'):
    return [ key, key + '_desc' ]
  sample_result = getattr(lang, key)
  if isinstance(sample_result, tuple):
    sample_result = sample_result[0]
  arg_count = sample_result.count('{') - sample_result.count('{{') * 2
  return (key if arg_count == 0 else '{}({})'.format(key, ', '.join(['{}'] * arg_count))) + ' '

@core.action
async def send_post(channel, text):
  posts.append('[{}] {}'.format(channel, text))

@core.action
async def get_available_members():
  for member in members:
    yield member

class Message:
  def __init__(self, author, content, channel):
    self.content = content
    self.channel = channel
    self.author = author

class Member:
  def __init__(self, id, name):
    self.id = id
    self.name = name
    self.mention = '@' + name

anne = Member(0, 'anne')
bob = Member(1, 'bob')
carl = Member(2, 'carl')
david = Member(3, 'david')

members = [ anne, bob, carl, david ]
admins = [ anne.id ]

core.BOT_PREFIX = '!'
core.initialize(admins)

loop = asyncio.get_event_loop()

def low_expect_response(coroutine, response):
  loop.run_until_complete(coroutine)

  assert len(posts) == 1, "Expected a single response. Actual: " + str(posts)
  assert posts[0] == response, r"""
Unexpected response: {}.
           Expected: {}.""".format(posts[0], response)
  del posts[:]

def expect_response(author, message, channel, response):
  low_expect_response(core.process_message(Message(author, message, channel)), response)

expect_response(anne, '!help', 'game', "[game] confirm(@anne) help_list(!help`, `!start_immediate`, `!add_role) ")
expect_response(carl, '!help', 'game', "[game] confirm(@carl) help_list(!help) ")
expect_response(anne, '!start_immediate', 'game', "[game] confirm(@anne) start(@anne, @bob, @carl, _and @david) ")
expect_response(carl, '!start_immediate', 'game', "[game] question(@carl) require_admin ")
