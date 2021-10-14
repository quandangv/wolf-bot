import sys

excess_roles = []
og_excess = []
EXCESS_ROLES = 3
SEER_REVEAL = 2
THIS_MODULE = sys.modules[__name__]

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

  core.DEFAULT_ROLES = [ 'Wolf', 'Thief', 'Troublemaker', 'Drunk', 'Wolf', 'Villager', 'Seer', 'Clone', 'Minion', 'Insomniac', 'Tanner' ]

  def is_wolf_side(role):
    return issubclass(roles[role], WolfSide)

  def is_village_side(role):
    return issubclass(roles[role], Villager)

  @core.injection
  def add_to_json(obj):
    obj['SEER_REVEAL'] = SEER_REVEAL
    obj['EXCESS_ROLES'] = EXCESS_ROLES
    obj['og_excess'] = og_excess
    obj['excess_roles'] = [ roles[role].__name__ for role in excess_roles ]

  @core.injection
  def extract_from_json(obj):
    excess_roles = [ roles[role].name for role in obj['excess_roles'] ]
    names = [ 'SEER_REVEAL', 'EXCESS_ROLES', 'og_excess' ]
    for name in names:
      if name in obj:
        globals()[name] = obj[name]

  @core.injection
  def default_roles_needed(player_count):
    return player_count + EXCESS_ROLES

  @core.injection
  def needed_players_count(played_roles):
    return max(0, len(played_roles) - EXCESS_ROLES)

  @core.injection
  def before_shuffle():
    og_excess.clear()

  @core.injection
  def after_shuffle(shuffled_roles):
    excess_roles.clear()
    for idx in range(EXCESS_ROLES):
      excess_roles.append(shuffled_roles[-idx - 1])
      og_excess.append(shuffled_roles[-idx - 1])

  @core.injection
  async def on_lynch(most_vote):
    for lynched in players.values():
      if lynched.extern.mention == most_vote:
        lynched_role = lynched.real_role
        await core.main_channel().send(tr('reveal_player').format(lynched.extern.mention, lynched_role))
        lynched_role = roles[lynched_role]
        if issubclass(lynched_role, Villager) or issubclass(lynched_role, Minion):
          winners = [ player for player in players.values() if is_wolf_side(player.real_role) ]
        elif issubclass(lynched_role, Tanner):
          winners = [ lynched ]
        elif issubclass(lynched_role, WolfSide):
          winners = [ player for player in players.values() if is_village_side(player.real_role) ]
        await core.announce_winners(core.main_channel(), winners)
        break

  @core.injection
  async def on_no_lynch():
    wolves = []
    villagers = []
    for p in players.values():
      if is_wolf_side(p.real_role):
        wolves.append(p)
      elif is_village_side(p.real_role):
        villagers.append(p)
    await core.announce_winners(core.main_channel(), wolves if wolves else villagers)

  @core.injection
  async def show_history(channel, roles, commands):
    await channel.send(tr('history').format(roles, join_with_and(og_excess), commands))

  @core.injection
  async def low_reveal_all(channel):
    reveal_item = tr('reveal_item')
    await channel.send(tr('reveal_all').format('\n'.join([ reveal_item.format(player.extern.name, player.real_role) for player in players.values() if player.role ])) + '\n' + tr('excess_roles').format(', '.join([name for name in excess_roles])))

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
    for role in excess_roles:
      if issubclass(roles[role], Wolf):
        for player in channel.players:
          if not player.extern.bot:
            lone_wolf = players[player.extern.id]
            lone_wolf.role.used = False
        await channel.extern.send(tr('wolf_get_reveal').format(command_name('Reveal'), EXCESS_ROLES))
        break

############################ ROLES #############################

  class OneNightRole:
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
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, False)
      core.transfer_to_self(self, 'reveal_count', data, 0)

    @core.check_context('dm')
    @core.single_arg('see_wronguse')
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
        self.used = True
        await on_used()

    @core.check_context('dm')
    @core.single_arg('reveal_wronguse', EXCESS_ROLES)
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
          self.used = True
          await on_used()
        else:
          await confirm(message, tr('reveal_success').format(number, result) + tr('reveal_remaining').format(SEER_REVEAL - self.reveal_count))

  @core.role
  class Clone(Villager):
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, False)

    @core.check_context('dm')
    @core.single_use
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
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, False)

    @core.check_context('dm')
    @core.single_use
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
        self.used = True
        await on_used()
        return await confirm(message, tr('troublemaker_success')
            .format(*[ p.extern.name for p in players]))

  @core.role
  class Thief(Villager):
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, False)

    @core.check_context('dm')
    @core.single_use
    @core.single_arg('thief_wronguse')
    async def Steal(self, me, message, args):
      if me.extern.name == args:
        return await question(message, tr('no_swap_self'))
      player = await find_player(message, args)
      if player:
        record_history(message, player.real_role)
        me.real_role, player.real_role = player.real_role, me.real_role
        self.used = True
        await on_used()
        return await confirm(message, tr('thief_success').format(args, me.real_role))

  @core.role
  class Drunk(Villager):
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, False)

    @core.check_context('dm')
    @core.single_use
    @core.single_arg('drunk_wronguse', EXCESS_ROLES)
    async def Take(self, me, message, args):
      number = await select_excess_card(message, 'drunk_wronguse', 'Take', args)
      if number:
        record_history(message, None)
        me.real_role, excess_roles[number-1] = excess_roles[number-1], me.real_role
        self.used = True
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
      await player.extern.send(tr('wolves_reveal').format(join_with_and(wolves)) if wolves else tr('no_wolves') + tr('minion_kill_self'))

  @core.role
  class Wolf(WolfSide):
    def __init__(self, data = None):
      core.transfer_to_self(self, 'used', data, True)
      core.transfer_to_self(self, 'discussed', data, False)

    @core.check_context('wolf')
    async def EndDiscussion(self, me, message, args):
      self.discussed = True
      for player in core.tmp_channels['wolf'].players:
        if not player.role.discussed:
          await confirm(message, tr('discussion_ended') + tr('discussion_wait_other'))
          break
      else:
        await confirm(message, tr('discussion_ended') + tr('discussion_all_ended'))
      await on_used()

    @core.check_context('wolf')
    @core.single_use
    @core.single_arg('reveal_wronguse', EXCESS_ROLES)
    async def Reveal(self, me, message, args):
      number = await select_excess_card(message, 'reveal_wronguse', 'Reveal', args)
      if number:
        record_history(message, excess_roles[number-1])
        await confirm(message, tr('reveal_success').format(number, excess_roles[number - 1]))
        self.used = True
        await on_used()

    async def on_start(self, player, first_time = True):
      await super().on_start(player, first_time)
      if not 'wolf' in core.tmp_channels:
        core.tmp_channels['wolf'] = await core.Channel.create(tr('wolf'), player)
      else:
        channel = core.tmp_channels['wolf']
        await channel.add(player)
        if not first_time:
          await channel.extern.send(tr('channel_greeting').format(player.extern.mention, channel.extern.name))
