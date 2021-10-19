import sys

THIS_MODULE = sys.modules[__name__]
wolf_phase_players = []
after_wolf_phase_players = []
after_wolf_waiting = []
wolf_phase = True
night_deaths = []

GUARD_DEFEND_SELF = True

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
  core.DEFAULT_ROLES = [ 'Villager', 'Guard', 'Wolf', 'Villager', 'Witch', 'Wolf' ]

  async def on_wolf_phase_use():
    for player in wolf_phase_players:
      if not player.role.target:
        return
    wolf_phase = False
    target = core.tmp_channels['wolf'].target
    if not hasattr(target, 'defended'):
      target.alive = False
      night_deaths.append(target)
    for co in after_wolf_waiting:
      await co
    after_wolf_waiting.clear()
    for player in after_wolf_phase_players:
      if hasattr(player.role, 'on_wolves_done'):
        await player.role.on_wolves_done(player)

  async def find_player(message, name):
    player = await core.find_player(message, name)
    if player.alive:
      return player
    else:
      await question(message, tr('target_dead').format(player.extern.name))

  def after_wolf_phase(func):
    async def handler(*others, message, args):
      co = func(*others, message=message, args=args)
      if wolf_phase:
        await co
      else:
        await confirm(message, tr('wait'))
        after_wolf_waiting.append(co)

  def filter_players():
    wolf_phase_players.clear()
    after_wolf_phase_players.clear()
    for player in players.values():
      if hasattr(player.role, 'wolf_phase'):
        wolf_phase_players.append(player)
      if hasattr(player.role, 'after_wolf_phase'):
        after_wolf_phase_players.append(player)

  @core.injection
  def add_to_json(obj):
    obj['night_deaths'] = night_deaths
    obj['wolf_phase'] = wolf_phase
    obj['GUARD_DEFEND_SELF'] = GUARD_DEFEND_SELF

  @core.injection
  def extract_from_json(obj):
    names = [ 'night_deaths', 'wolf_phase', 'GUARD_DEFEND_SELF' ]
    for name in names:
      if name in obj:
        globals()[name] = obj[name]
    filter_players()

  @core.injection
  def after_shuffle(shuffled_roles):
    filter_players()

  @core.injection
  def default_roles_needed(player_count):
    return player_count

  @core.injection
  def needed_players_count(played_roles):
    return len(played_roles)

  @core.injection
  def on_lynch(player):
    player.alive = False
    # go to sleep

  @core.injection
  async def role_help(message, role):
    await confirm(message, core.roles[role].description.format(THIS_MODULE))

  @core.injection
  def start_night():
    global wolf_phase
    wolf_phase = True
    after_wolf_waiting.clear()
    night_deaths.clear()

  class ClassicRole(core.Role):
    async def on_start(self, player, first_time = True):
      if first_time:
        player.alive = True

  @core.role
  class Villager(ClassicRole): pass

  class WolfSide(ClassicRole): pass

  @core.role
  class Wolf(WolfSide, core.Wolf):
    wolf_phase = True
    __slots__ = ('target',)
    def new_night(self):
      self.target = None

    @core.check_channel('wolf')
    @core.check_status()
    @core.single_arg('bite_wronguse')
    async def Kill(self, me, tmp_channel, message, args):
      player = await find_player(message, args)
      if player:
        self.target = player
        msg = tr('vote_bite').format(me.extern.mention, self.target.extern.name)
        for wolf in tmp_channel.players:
          if wolf.role.target != self.target:
            await tmp_channel.extern.send(msg + tr('wolf_need_consensus'))
            break
        else:
          await tmp_channel.extern.send(msg + tr('wolf_bite').format(self.target.extern.name))
          tmp_channel.target = self.target
          await on_wolf_phase_use()

    async def on_start(self, player, first_time = True):
      await ClassicRole.on_start(self, player, first_time)
      await core.Wolf.on_start(self, player, first_time)

  @core.role
  class Guard(Villager):
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
        if not GUARD_DEFEND_SELF and me.extern.id == player.extern.id:
          await question(message, tr('no_defend_self'))
        else:
          if self.prev_target:
            del self.prev_target.defended
          self.target = self.prev_target = player
          player.defended = True
          await confirm(message, tr('defend_success').format(player.extern.name))
          await on_wolf_phase_use()

  @core.role
  class Witch(Villager):
    after_wolf_phase = True
    __slots__ = ('revived', 'poisoned')
    def __init__(self):
      self.revived = False
      self.poisoned = False

    async def on_wolves_done(self, me):
      if night_deaths:
        msg = tr('witch_death')
        if not self.revived:
          msg += tr('witch_revive').format(*self.commands)
        await me.extern.send(msg)
      else:
        await me.extern.send(tr('witch_no_death').format(*self.commands))

    @core.check_dm
    @core.check_status()
    @core.single_use('poisoned')
    @core.single_arg('poison_wronguse')
    async def Poison(self, me, message, args):
      pass

    @core.check_dm
    @core.check_status()
    @core.single_use('revived')
    @core.single_arg('revive_wronguse')
    async def Revive(self, me, message, args):
      pass

    @core.check_dm
    @core.check_status()
    async def Sleep(self, me, message, args):
      pass
