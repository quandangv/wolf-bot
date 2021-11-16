import sys

THIS_MODULE = sys.modules[__name__]
after_wolf_waiting = []

wolf_phase_players = []
after_wolf_phase_players = []

wolf_phase = True
attack_deaths = []
known_alive = []

GUARD_DEFEND_SELF = True
LONELY_SIDES = [ 'tanner' ]

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
  core.DEFAULT_ROLES = [ 'Villager', 'Guard', 'Wolf', 'Villager', 'Witch', 'Wolf', 'Detective', 'Drunk', 'Villager', 'WolfSheep' ]
  core.game_mode = THIS_MODULE
  core.role_prefix = 'classic_'

  @dictionize.custom_keys('wolf_phase', 'attack_deaths', 'known_alive', 'GUARD_DEFEND_SELF')
  class Dictionize:
    async def dtemplate(self, dict):
      filter_players()
      return THIS_MODULE
    def dplayer_arr(name):
      async def func(self, obj, val):
        setattr(obj, name, [ core.Player.dictionize__.dtemplate(p) for p in val ])
      return func
    d_attack_deaths = dplayer_arr('attack_deaths')
    d_known_alive = dplayer_arr('known_alive')
  globals()['dictionize__'] = Dictionize()

  async def on_wolf_phase_use():
    for player in known_alive:
      if hasattr(player.role, 'wolf_phase') and not player.role.target:
        return
    if not hasattr(core.tmp_channels['wolf'], 'target'):
      return
    globals()['wolf_phase'] = False
    target = core.tmp_channels['wolf'].target

    if isinstance(target, core.Player) and not hasattr(target, 'defended'):
      target.alive = False
      attack_deaths.append(target)
    await core.tmp_channels['wolf'].extern.send(tr('wolf_target_locked'))
    for player in known_alive:
      if hasattr(player.role, 'on_wolves_done'):
        await player.role.on_wolves_done(player)
    for co in after_wolf_waiting:
      await co
    after_wolf_waiting.clear()
    await on_used()

  async def checked_on_used():
    if not wolf_phase:
      await on_used()

  async def find_player(message, name):
    player = await core.find_player(message, name)
    if not player:
      return None
    if player in known_alive:
      return player
    else:
      await question(message, tr('target_dead').format(player.extern.name))

  def wait_after_wolf_phase(func):
    async def handler(*others, message, args):
      co = func(*others, message=message, args=args)
      if not wolf_phase:
        await co
      else:
        await confirm(message, tr('wait'))
        after_wolf_waiting.append(co)
    handler.__name__ = func.__name__
    return handler

  def filter_players():
    known_alive.clear()
    wolf_phase_players.clear()
    after_wolf_phase_players.clear()
    for player in players.values():
      if player.role:
        known_alive.append(player)
        if hasattr(player.role, 'wolf_phase'):
          wolf_phase_players.append(player)
        if hasattr(player.role, 'after_wolf_phase'):
          after_wolf_phase_players.append(player)

  async def go_to_sleep():
    await core.main_channel().send(tr('go_to_sleep'))
    globals()['wolf_phase'] = True
    core.status = 'night'
    for player in core.players.values():
      if hasattr(player, 'defended'):
        del player.defended
      if hasattr(player.role, 'new_night'):
        player.role.new_night()

  def know_dead(player):
    if player in known_alive:
      known_alive.pop(known_alive.index(player))
    core.player_count = len(known_alive)
    player.role = Dead(player.role)

  async def not_endgame():
    wolf_count = 0
    villager_count = 0
    for p in known_alive:
      if isinstance(p.role, Wolf):
        wolf_count += 1
      elif isinstance(p.role, Villager):
        villager_count += 1
    def get_winners(base):
      result = []
      for p in core.players.values():
        if isinstance(p.role, Dead):
          p.role = p.role.role
        if isinstance(p.role, base):
          result.append(p.extern.mention)
      return result
    if not wolf_count:
      await core.main_channel().send(tr('village_victory'))
      await core.announce_winners(get_winners(Villager))
    elif wolf_count >= villager_count:
      await core.main_channel().send(tr('wolf_victory'))
      await core.announce_winners(get_winners(WolfSide))
    else:
      return True

  @core.injection
  def get_role(player):
    return player.role.name

  @core.injection
  def game_info():
    return tr('alive_list').format(len(known_alive), join_with_and([ p.extern.mention for p in known_alive ]))

  @core.injection
  def after_shuffle(shuffled_roles):
    filter_players()

  @core.injection
  def default_roles_needed(player_count):
    return player_count if player_count < 6 else player_count + 2

  @core.injection
  def needed_players_count(played_roles):
    return sum([ roles[role].player_count for role in played_roles ])

  @core.injection
  async def on_lynch(player):
    player.alive = False
    know_dead(player)
    if await not_endgame():
      await go_to_sleep()

  @core.injection
  async def on_no_lynch():
    if await not_endgame():
      await go_to_sleep()

  @core.injection
  async def role_help(message, role):
    await confirm(message, core.roles[role].description.format(THIS_MODULE))

  @core.injection
  def start_night():
    globals()['wolf_phase'] = True
    after_wolf_waiting.clear()
    attack_deaths.clear()

  @core.injection
  async def on_wake_up():
    deaths = []
    for player in known_alive[:]:
      if not player.alive:
        deaths.append(player.extern.mention)
        know_dead(player)
    await core.main_channel().send(tr('wake_up_death').format(join_with_and(deaths)) if deaths else tr('wake_up_no_death'))
    if await not_endgame():
      await core.main_channel().send(core.remind_vote())

############################ ROLES #############################

  class ClassicRole(core.Role):
    player_count = 1
    async def on_start(self, player, first_time = True):
      if first_time:
        player.alive = True
        player.side = self.default_side()
    @core.single_arg('vote_wronguse')
    @core.check_public
    @core.check_status('day')
    async def Vote(self, me, message, args):
      player = await find_player(message, args)
      if player:
        await core.on_voted(me, player)
    @core.check_public
    @core.check_status('day')
    async def VoteNoLynch(self, me, message, args):
      await core.on_voted(me, True)

  class Dead:
    def __init__(self, role):
      self.role = role

    async def other(self, me, message, args):
      await question(message, tr('dead'))
    for cmd in core.ROLE_COMMANDS:
      locals()[cmd] = other

    async def Sleep(self, me, message, args):
      await core.say_good_night(message)

  @core.role
  class Villager(ClassicRole):
    def default_side(self): return 'villager'

  class WolfSide(ClassicRole):
    def default_side(self): return 'wolf'

  @core.role
  class Wolf(WolfSide, core.Wolf):
    wolf_phase = True
    __slots__ = ('target',)
    def new_night(self):
      self.target = None
    async def check_consensus(self, msg, target, wolf_channel):
      self.target = target
      for wolf in wolf_channel.players:
        if not isinstance(wolf.role, Dead) and wolf.role.target != target:
          await wolf_channel.extern.send(msg + tr('wolf_need_consensus'))
          return False
      else:
        wolf_channel.target = self.target
        return True

    async def on_start(self, player, first_time = True):
      await ClassicRole.on_start(self, player, first_time)
      await core.Wolf.on_start(self, player, first_time)

    @core.check_channel('wolf')
    @core.check_status()
    @core.single_arg('kill_wronguse')
    async def Kill(self, me, tmp_channel, message, args):
      if wolf_phase:
        player = await find_player(message, args)
        if player:
          msg = tr('vote_kill').format(me.extern.mention, player.extern.name)
          if await self.check_consensus(msg, player, tmp_channel):
            await tmp_channel.extern.send(msg + tr('wolf_kill').format(self.target.extern.name))
            await on_wolf_phase_use()
      else:
        await question(message, tr('kill_already'))

    @core.check_channel('wolf')
    @core.check_status()
    async def Sleep(self, me, tmp_channel, message, args):
      if wolf_phase:
        msg = tr('vote_no_kill').format(me.extern.mention)
        if await self.check_consensus(msg, True, tmp_channel):
          await tmp_channel.extern.send(msg + tr('wolf_no_kill'))
          await on_wolf_phase_use()
      else:
        await question(message, tr('kill_already'))

  @core.role
  class WolfSheep(Wolf):
    def default_side(self): return 'villager'

  @core.role
  class Guard(Villager):
    get_player_list = True
    wolf_phase = True
    __slots__ = ('target', 'prev_target')
    def __init__(self):
      self.prev_target = None
    def new_night(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use()
    @core.single_arg('defend_wronguse')
    async def Defend(self, me, message, args):
      player = await find_player(message, args)
      if player:
        if player == self.prev_target:
          await question(message, tr('defend_repeat'))
        elif not GUARD_DEFEND_SELF and me.extern.id == player.extern.id:
          await question(message, tr('no_defend_self'))
        else:
          self.target = self.prev_target = player
          player.defended = True
          await confirm(message, tr('defend_success').format(player.extern.name))
          await on_wolf_phase_use()

  @core.role
  class Witch(Villager):
    after_wolf_phase = True
    get_player_list = True
    __slots__ = ('revived', 'poisoned', 'sleep')
    def __init__(self):
      self.revived = False
      self.poisoned = False
      self.sleep = False
    def new_night(self):
      if not self.revived or not self.poisoned:
        self.sleep = False
    async def auto_sleep(self, me):
      if not self.sleep:
        if (self.revived or (not attack_deaths and not wolf_phase)) and self.poisoned:
          self.sleep = True
          await checked_on_used()
        else:
          await me.extern.send(tr('remind_sleep').format(command_name('Sleep')))

    async def on_wolves_done(self, me):
      if attack_deaths:
        msg = tr('witch_death')
        if not self.revived and not self.sleep:
          await me.extern.send(msg + tr('witch_revive').format(*self.commands))
          return
        await me.extern.send(msg)
      else:
        await me.extern.send(tr('witch_no_death').format(*self.commands))
      await self.auto_sleep(me)

    @core.check_dm
    @core.check_status()
    @core.single_use('poisoned')
    @core.single_arg('poison_wronguse')
    async def Poison(self, me, message, args):
      player = await find_player(message, args)
      if player:
        self.poisoned = True
        player.alive = False
        await confirm(message, tr('poison_success').format(args))
        await self.auto_sleep(me)

    @core.check_dm
    @core.check_status()
    @wait_after_wolf_phase
    @core.single_use('revived')
    async def Revive(self, me, message, args):
      if attack_deaths:
        self.revived = True
        attack_deaths.pop().alive = True
        await confirm(message, tr('revive_success'))
        await self.auto_sleep(me)
      else:
        await question(message, tr('revive_no_deaths'))

    @core.check_dm
    @core.check_status()
    async def Sleep(self, me, message, args):
      if not self.sleep:
        self.sleep = True
        await core.say_good_night(message)
        await checked_on_used()

  @core.role
  class Knight(Villager):
    __slots__ = ('killed')
    def __init__(self):
      self.killed = None

    @core.check_public
    @core.check_status('day')
    @core.single_use('killed')
    async def Kill(self, me, message, args):
      player = await find_player(message, args)
      if player:
        self.target = player
        await confirm(message, tr('knight_kill').format(me.extern.mention, player.extern.mention))
        (player if isinstance(player.role, Wolf) else me).alive = False
        await go_to_sleep()

  @core.role
  class Detective(Villager):
    after_wolf_phase = True
    get_player_list = True
    __slots__ = ('sleep',)
    def __init__(self):
      self.sleep = False
    def new_night(self):
      self.sleep = False

    @core.check_dm
    @core.check_status()
    @wait_after_wolf_phase
    @core.single_use('sleep')
    async def Investigate(self, me, message, args):
      players = [arg.strip() for arg in args.split(',')]
      if len(players) != 2 or players[0] == players[1]:
        return await question(message, tr('detective_wronguse').format(command_name('Investigate')))
      players = [ await find_player(message, name) for name in players ]
      if players[0] and players[1]:
        sides = [ p.side for p in players ]
        if sides[0] == sides[1] and not sides[0] in LONELY_SIDES:
          msg = tr('investigate_same')
        else:
          msg = tr('investigate_diff')
        await message.reply(msg.format(players[0].extern.name, players[1].extern.name))
        self.sleep = True
        await on_used()

  @core.role
  class Drunk:
    player_count = -1
    prompted_setup = True
    async def on_start(self, me, first_time = True):
      if first_time:
        msg = tr('excess_roles').format(join_with_and(core.excess_roles))
        for role in core.excess_roles:
          role = roles[role]
          if issubclass(role, Wolf):
            await me.extern.send(msg + tr('drunk_choose_wolf'))
            await self.take(me, role)
            break
        else:
          await me.extern.send(msg + tr('drunk_choose').format(command_name('Take')))

    async def take(self, me, role):
      core.excess_roles.pop(core.excess_roles.index(role.name))
      me.role = role()
      await core.set_role('drunk_took_role', me, role, True)

    @core.check_dm
    async def Take(self, me, message, args):
      if args in roles:
        role = roles[args]
        if role.name in core.excess_roles:
          await self.take(me, role)
          await core.on_setup_answered()
        else:
          await question(message, tr('take_notavailable').format(role.name, join_with_and(core.excess_roles)))
      else:
        await core.confused(message.channel, args)

    @staticmethod
    def check_shuffling(shuffled_roles, player_count):
      wolf_count = 0
      for idx in range(player_count, len(shuffled_roles)):
        if issubclass(roles[shuffled_roles[idx]], Wolf):
          wolf_count += 1
      if wolf_count > 1:
        return True
