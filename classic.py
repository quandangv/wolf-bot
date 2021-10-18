import sys

THIS_MODULE = sys.modules[__name__]
wolf_phase_players = []
after_wolf_phase_players = []
after_wolf_waiting = []
wolf_phase = True

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
  core.DEFAULT_ROLES = [ 'Villager', 'Guard', 'Wolf', 'Villager', 'Villager', 'Wolf' ]

  async def on_wolf_phase_use():
    for player in wolf_phase_players:
      if not player.role.target:
        return
    wolf_phase = False
    for co in after_wolf_waiting:
      await co

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

  @core.injection
  def after_shuffle(shuffled_roles):
    wolf_phase_players.clear()
    for player in players.values():
      if hasattr(player.role, 'wolf_phase'):
        wolf_phase_players.append(player)
      if hasattr(player.role, 'after_wolf_phase'):
        after_wolf_phase_players.append(player)

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

  class ClassicRole:
    async def on_start(self, player, first_time = True):
      if first_time:
        player.alive = True

  @core.role
  class Villager(ClassicRole): pass

  class WolfSide(ClassicRole): pass

  @core.role
  class Wolf(WolfSide, core.Wolf):
    def __init__(self):
      self.wolf_phase = True
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
    def __init__(self):
      self.prev_target = None
    def new_night(self):
      self.target = None

    @core.check_dm
    @core.check_status()
    @core.single_use
    @core.single_arg('defend_wronguse')
    async def Defend(self, me, message, args):
      player = await find_player(message, args)
      if player:
        if player == self.prev_target:
          await question(message, tr('defend_repeat'))
        if not GUARD_DEFEND_SELF and me.extern.id == player.extern.id:
          await question(message, tr('no_defend_self'))
        else:
          self.target = self.prev_target = player
          player.defended = True
          await confirm(message, tr('defend_success').format(player.extern.name))
          await on_wolf_phase_use()
