
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

  class ClassicRole:
    async def on_start(self, player, first_time = True):
      if first_time:
        player.alive = True

  @core.role
  class Villager(ClassicRole): pass

  class WolfSide(ClassicRole): pass

  @core.role
  class Wolf(WolfSide):
    def new_night(self):
      # The target of the wolf
      self.used = None

    @core.check_context('wolf')
    @core.check_status
    @core.single_arg('bite_wronguse')
    def Bite(self, me, tmp_channel, message, args):
      player = find_player(message, args)
      if player:
        self.used = player.extern.name
        msg = tr('vote_bite').format(me.extern.mention, self.used)
        for wolf in tmp_channel.players:
          if wolf.used != self.used:
            await tmp_channel.extern.send(msg + tr('wolf_need_consensus'))
            await on_used()
            break
        else:
          await tmp_channel.extern.send(msg + tr('wolf_bite'))
          tmp_channel.target = self.used
          await on_used()

  @core.role
  class Guard(Villager):
    def new_night(self):
      self.
