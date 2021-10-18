
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
  GUARD_DEFEND_SELF = True

  async def find_player(message, name):
    player = await find_player(message, name)
    if player.alive:
      return player
    else:
      await question(message, tr('target_dead').format(player.extern.name))

  class ClassicRole:
    async def on_start(self, player, first_time = True):
      if first_time:
        player.alive = True

  @core.role
  class Villager(ClassicRole): pass

  class WolfSide(ClassicRole): pass

  @core.role
  class Wolf(WolfSide):
    def __init__(self):
      self.wolf_phase = True
    def new_night(self):
      self.target = None

    @core.check_channel('wolf')
    @core.check_status
    @core.single_arg('bite_wronguse')
    async def Kill(self, me, tmp_channel, message, args):
      player = find_player(message, args)
      if player:
        self.target = player
        msg = tr('vote_bite').format(me.extern.mention, self.target)
        for wolf in tmp_channel.players:
          if wolf.target != self.target:
            await tmp_channel.extern.send(msg + tr('wolf_need_consensus'))
            await on_used()
            break
        else:
          await tmp_channel.extern.send(msg + tr('wolf_bite'))
          tmp_channel.target = self.target
          await on_used()

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
    async def Defend(self, me, tmp_channel, message, args):
      player = find_player(message, args)
      if player:
        if player == prev_target:
          await question(message, tr('defend_repeat'))
        if not GUARD_DEFEND_SELF and me.extern.id == player.extern.id:
          await question(message, tr('no_defend_self'))
        self.target = self.prev_target = player

    def wolf_phase_end(self, wolf_channel):
      if self.target == wolf_channel.target:
        self.target.alive = True
