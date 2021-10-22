import sys

THIS_MODULE = sys.modules[__name__]
EXCESS_ROLES = 3
SEER_REVEAL = 2

def connect(core):
  tr = core.tr
  roles = core.roles
  players = core.players
  confirm = core.confirm
  question = core.question
  command_name = core.command_name
  find_player = core.find_player
  record_history = core.record_history
  on_used = core.on_used
  join_with_and = core.join_with_and
  dictionize = core.dictionize
  core.DEFAULT_ROLES = [ 'Wolf', 'Thief', 'Troublemaker', 'Drunk', 'Wolf', 'Villager', 'Seer', 'Clone', 'Minion', 'Insomniac', 'Tanner', 'Villager' ]

  @dictionize.custom_keys('EXCESS_ROLES', 'SEER_REVEAL')
  class Dictionize:
    async def dtemplate(self, dict):
      return THIS_MODULE
  globals()['dictionize__'] = Dictionize()

  async def is_wolf_side(role):
    if not role in roles:
      await core.debug("ERROR: Role '{}' does not exist".format(role))
      return False
    return issubclass(roles[role], WolfSide)

  async def is_village_side(role):
    if not role in roles:
      await core.debug("ERROR: Role '{}' does not exist".format(role))
      return False
    return issubclass(roles[role], Villager)

  @core.injection
  def default_roles_needed(player_count):
    return player_count + EXCESS_ROLES

  @core.injection
  def needed_players_count(played_roles):
    return max(0, len(played_roles) - EXCESS_ROLES)

  @core.injection
  async def on_lynch(player):
    lynched_role = player.real_role
    await core.main_channel().send(tr('reveal_player').format(player.extern.mention, lynched_role))
    lynched_role = roles[lynched_role]
    if issubclass(lynched_role, Villager) or issubclass(lynched_role, Minion):
      winners = [ player for player in players.values() if await is_wolf_side(player.real_role) ]
    elif issubclass(lynched_role, Tanner):
      winners = [ player ]
    elif issubclass(lynched_role, WolfSide):
      winners = [ player for player in players.values() if await is_village_side(player.real_role) ]
    await core.announce_winners(core.main_channel(), winners)

  @core.injection
  async def on_no_lynch():
    wolves = []
    villagers = []
    for p in players.values():
      if await is_wolf_side(p.real_role):
        wolves.append(p)
      elif await is_village_side(p.real_role):
        villagers.append(p)
    await core.announce_winners(core.main_channel(), wolves if wolves else villagers)

  @core.injection
  async def show_history(channel, roles, commands):
    await channel.send(tr('history').format(roles, join_with_and(core.og_excess), commands))

  @core.injection
  async def role_help(message, role):
    await confirm(message, core.roles[role].description.format(THIS_MODULE))

  async def select_excess_card(message, wronguse_msg, cmd_name, args):
    try:
      number = int(args)
    except ValueError:
      return await question(message, tr(wronguse_msg).format(command_name(cmd_name), EXCESS_ROLES))
    if number < 1 or number > EXCESS_ROLES:
      return await question(message, tr('choice_outofrange').format(EXCESS_ROLES))
    return number

  @core.channel_event
  async def wolf_channel(channel):
    for role in core.excess_roles:
      if issubclass(roles[role], Wolf):
        for player in channel.players:
          if not player.extern.bot:
            lone_wolf = players[player.extern.id]
            lone_wolf.role.target = None
        await channel.extern.send(tr('wolf_get_reveal').format(command_name('Reveal'), EXCESS_ROLES))
        break

############################ ROLES #############################

  class OneNightRole(core.Role):
    async def on_start(self, player, first_time = True):
      player.real_role = self.name

  @core.role
  class Villager(OneNightRole): pass

  @core.role
  class Tanner(OneNightRole): pass

  @core.role
  class Insomniac(Villager):
    async def before_dawn(self, player):
      await player.extern.send(tr('insomniac_reveal').format(player.real_role))

  @core.role
  class Seer(Villager):
    __slots__ = ('target', 'reveal_count')
    def __init__(self):
      self.target = None
      self.reveal_count = 0

    @core.check_dm
    @core.check_status()
    @core.single_arg('see_wronguse')
    async def See(self, me, message, args):
      if self.reveal_count:
        return await question(message, tr('seer_reveal_already'))
      if self.target:
        return await question(message, tr('ability_used').format(command_name('See')))
      if me.extern.name == args:
        return await question(message, tr('seer_self'))
      player = await find_player(message, args)
      if player:
        record_history(message, player.real_role)
        await confirm(message, tr('see_success').format(args, player.real_role))
        self.target = player.extern.name
        await on_used()

    @core.check_dm
    @core.check_status()
    @core.single_arg('reveal_wronguse', EXCESS_ROLES)
    async def Reveal(self, me, message, args):
      if self.target:
        return await question(message, tr('seer_see_already'))
      if self.reveal_count >= SEER_REVEAL:
        return await question(message, tr('out_of_reveal').format(SEER_REVEAL))
      number = await select_excess_card(message, 'reveal_wronguse', 'Reveal', args)
      if number:
        result = core.excess_roles[number - 1]
        record_history(message, result)
        self.reveal_count += 1
        if self.reveal_count >= SEER_REVEAL:
          await confirm(message, tr('reveal_success').format(number, result) + tr('no_reveal_remaining'))
          self.target = number
          await on_used()
        else:
          await confirm(message, tr('reveal_success').format(number, result) + tr('reveal_remaining').format(SEER_REVEAL - self.reveal_count))

  @core.role
  class Clone(Villager):
    __slots__ = ('target',)
    def __init__(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use()
    @core.single_arg('clone_wronguse')
    async def Clone(self, me, message, args):
      if me.extern.name == args:
        return await question(message, tr('clone_self'))
      player = await find_player(message, args)
      if player:
        record_history(message, player.real_role)
        me.role = roles[player.real_role]()
        me.real_role = me.role.name
        if hasattr(me.role, 'on_start'):
          await me.role.on_start(me, False)
        return await confirm(message, tr('clone_success').format(args, me.role.name) + me.role.greeting)

  @core.role
  class Troublemaker(Villager):
    __slots__ = ('target',)
    def __init__(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use()
    async def Swap(self, me, message, args):
      players = args.split()
      if len(players) != 2 or players[0] == players[1]:
        return await question(message, tr('troublemaker_wronguse').format(command_name('Swap')))
      if me.extern.name in players:
        return await question(message, tr('no_swap_self'))
      players = [ await find_player(message, name) for name in players ]
      if players[0] and players[1]:
        record_history(message, None)
        players[0].real_role, players[1].real_role = players[1].real_role, players[0].real_role
        self.target = players[0].extern.name
        await on_used()
        return await confirm(message, tr('troublemaker_success')
            .format(*[ p.extern.name for p in players]))

  @core.role
  class Thief(Villager):
    __slots__ = ('target',)
    def __init__(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use()
    @core.single_arg('thief_wronguse')
    async def Steal(self, me, message, args):
      if me.extern.name == args:
        return await question(message, tr('no_swap_self'))
      player = await find_player(message, args)
      if player:
        record_history(message, player.real_role)
        me.real_role, player.real_role = player.real_role, me.real_role
        self.target = player.extern.name
        await on_used()
        return await confirm(message, tr('thief_success').format(args, me.real_role))

  @core.role
  class Drunk(Villager):
    __slots__ = ('target',)
    def __init__(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use()
    @core.single_arg('drunk_wronguse', EXCESS_ROLES)
    async def Take(self, me, message, args):
      number = await select_excess_card(message, 'drunk_wronguse', 'Take', args)
      if number:
        record_history(message, None)
        me.real_role, core.excess_roles[number-1] = core.excess_roles[number-1], me.real_role
        self.target = number
        await on_used()
        return await confirm(message, tr('drunk_success').format(args))

  class WolfSide(OneNightRole): pass

  @core.role
  class Minion(WolfSide):
    async def on_start(self, player, first_time = True):
      await super().on_start(player, first_time)
      wolves = []
      for player in players.values():
        if isinstance(player.role, Wolf):
          wolves.append(player.extern.name)
      await player.extern.send(tr('wolves_reveal').format(join_with_and(wolves)) if wolves else tr('no_wolves'))

  @core.role
  class Wolf(WolfSide):
    __slots__ = ('target', 'sleep')
    def __init__(self):
      self.target = True
      self.sleep = False

    @core.check_channel('wolf')
    @core.check_status()
    async def Sleep(self, me, tmp_channel, message, args):
      self.sleep = True
      msg = tr('gone_to_sleep').format(me.extern.mention)
      for player in tmp_channel.players:
        if not player.role.sleep:
          await message.channel.send(msg + tr('sleep_wait_other'))
          break
      else:
        await message.channel.send(msg + tr('all_sleeping'))
      await on_used()

    @core.check_channel('wolf')
    @core.check_status()
    @core.single_use()
    @core.single_arg('reveal_wronguse', EXCESS_ROLES)
    async def Reveal(self, me, tmp_channel, message, args):
      number = await select_excess_card(message, 'reveal_wronguse', 'Reveal', args)
      if number:
        record_history(message, core.excess_roles[number-1])
        await confirm(message, tr('reveal_success').format(number, core.excess_roles[number - 1]))
        self.target = number
        await on_used()

    async def on_start(self, player, first_time = True):
      await super().on_start(player, first_time)
      if not 'wolf' in core.tmp_channels:
        channel = core.tmp_channels['wolf'] = await core.Channel.create(tr('wolf'), player)
        channel.discussing = True
      else:
        channel = core.tmp_channels['wolf']
        await channel.add(player)
        if not first_time:
          await channel.extern.send(tr('channel_greeting').format(player.extern.mention, channel.extern.name))
