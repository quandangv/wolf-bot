confirm = [ "Okay {}, ", "", "K, ", "Fine, ", "Right, " ]
question = [ "Oh {}, ", "", "Ah {}, " ]
confused = [ "What does `{}` means?", "`{}` doesn't exists" ]
_and = "and "

alias = "`{}` is an alias of `{}`.\n"
aliases_list = ". Also known as `!{}`"
wolf = [ "Wolves", "Cute little wolves", "Woof", "WOLVES" ]
exception = "We are experiencing technical problems, the error log has been sent to the Debug channel"

role = [ "Hello! you are a **{}**. ", "Today you play as a **{}**. ", "Congrats! you got to be a **{}**! " ]
wolf_channel = [ "Hello fellow wolves, your pack includes {}. ", "Hi wolves! {} let's greet eachother! ", "Hi {}. welcome to the wolf pack! " ]
channel_greeting = [ "Welcome {} to the **{}** group!", "Hi {}! Say hello to the **{}** group" ]
sleep_info = [
    "When finishing discussion, everyone need to send `{}` to end the night",
    "When discussions are finished, everybody need to send `{}`"
]
greeting = [
    "Hi everyone! You can send `{0}` for instructions, while admins can send `{1}` to start the game",
    "Greetings to the villager! Villagers can send `{0}` to learn more about the commands, while admin villagers can send `{1}` to start the game"
]
remind_sleep = "If you don't need to take any other actions remember to send `{}`"
remind_unvote = [
    "If you want to cancel the vote, send `{}`",
    "To cancel the vote, send `{}`"
]

wake_up = [
    "Good morning! Let's hang some wolves! ",
    "Everybody wake up! We have ... no deaths tonight. ",
    "Hello everybody! What a nice day to be lynching somebody!"
]
wake_up_death = [
    "Everybody wake up! I found the dead body of **{}**",
    "Good morning! The sun is high while **{}** has died",
    "Morning! The moon has set and **{}** is dead",
    "Let's mourn for the tragedy of **{}**, who has died last night"
]
wake_up_no_death = [
    "What a nice day! Everybody wake up and no one died",
    "The villagers discover the dead body of a pet cat, but luckily no one was harmed",
    "The villagers discover the dead body of a pet dog, but luckily no one was harmed",
    "The villagers discover the dead body of a pet penguin, but luckily no one was harmed",
    "Congrats to everyone for surviving another night!"
]
go_to_sleep = [
    "And so, everyone go to sleep",
    "The day is fading, everyone need to go to bed",
    "With nothing else to do, everyone in the village went to sleep"
]
winners = [
    "Congratulations to {} for winning the game!",
    "{} snatched the victory of the game"
]
no_winners = [
    "Hahaha no one win this game",
    "Everyone lost :)"
]
wolf_victory = [
    "The wolves revealed themselves and brutally murdered everyone",
    "Wasting no time, the wolves lunged at the remaining villagers..."
]
village_victory = [
    "From then on, the villagers lived in peace",
    "There were no deaths the following nights, so everyone know the village is finally cleared"
]
lynch = [
    "And thus {} was thrown into the fire",
    "{} was so disappointed with the village that they lost the will to live",
    "The village hung {}, and buried",
    "Everyone forced {0} out of the village. From the, no one see {0} ever again"
]
no_lynch = [
    "The village doesn't want to kill today",
    "Today the village doesn't kill anyone",
    "Failing to find any wolves, the village went to sleep"
]
most_vote = "{} have the most votes"
vote_tie = "Multiple people have the same number of votes"
wolf_need_consensus = [ ". The pack needs to reach a consensus on who to kill", ". The wolves need to agree on who to kill" ]
wolf_kill = [ ". The wolves decided to kill **{}**", ". The wolf pack moves to kill **{}**" ]
wolf_no_kill = ". The wolves decide to abstain from killing"
witch_no_death = "You don't see any deaths tonight"
witch_death = "You feel death tonigh"
witch_revive = ". Send `{1}` to revive the dead"
player_list = [ "The game includes: **{}**", "The players in the game are: **{}**" ]
alive_list = [ ". There are **{}** players alive: {}", ". There are **{}** remaining players: {}" ]
drunk_choose = [ "Send `{}  role` to select an excess role", "Select an excess role by sending `{}  role`" ]
drunk_choose_wolf = "You must take the wolf role"

reveal_player = [ "{} is a **{}**!", "{} plays as a **{}**" ]
reveal_item = "- {} is a **{}**"
wolves_reveal = "The wolves among us are {}"
no_wolves = [ "The village have no wolf. ", "No wolves was found in the village! ", "The wolves are feasting in the village nextdoor, we have none. " ]
reveal_all = "The roles of everyone are: \n{}"
excess_roles = "Excess roles are **{}**"
no_history = "gameplay history can't be found"
history = "Initial roles:\n{}\nExcess roles:{}\nExecuted commands:\n{}"
command_item = "- {} commanded `{}`, gets **{}**"
command_item_empty = "- {} commanded `{}`"

vote = [
    "Send `{} player` to vote on killing them, or `{}` to vote on abstaining from killing",
    "If you hate  someone, just send `{} them`, or send `{}` if you don't want to kill"
]
help_list = [
    "available commands are `{}`",
    "other than killing villagers, you can also `{}`. (just kidding)",
    "Try sending one of `{}`"
]
help_detail = ". To learn more about each command `{0}  command-name`"
list_roles = [ "We play with **{}** this game", "The village have **{}**" ]
player_needed = [ "; **{}** players needed", "; we need **{}** players" ]
no_roles = [ "They village is empty", "There is no role set up" ]
default_roles = ". These default roles will be used **{}**"
wolf_get_reveal = "You are a lonely wolf. You can use `{} excess-role-index` to reveal one of {} the excess roles"
hunter_reveal = "Before being hung, {} proved that they are a **hunter** by shooting {} dead with their rifle"
reveal_remaining = ". You have **{}** reveals left"
no_reveal_remaining = ". You have no reveals left"
sleep_wait_other = ", others in the group are still awake"
all_sleeping = ", everybody the the group have gone to sleep"
wait = [ "I'll answer you later", "please wait a moment" ]

start = [ "Starting a game with {}. ", "A game between {} will start now. ", "{}, let's play! ", "The game has started! Tonight wolves will appear among {}. " ]
start_needmore = [ "there are currently **{}** players while we need **{}** players", "we need **{1}** players, there are currently only **{0}** players" ]
start_needless = [ "there are currently **{}** players, we have only set enough roles for **{}**", "roles in the village are for **{1}** player, but we have **{0}** players" ]
start_toolittle = "there's not enough roles to play"

vote_countdown = "Most have casted their vote! Other players have **{}** seconds to cast their vote"
landslide_vote_countdown = "{} will soon be lynched, everyone have **{}** seconds to change their minds!"
landslide_no_vote_countdown = "Most have decided not to kill, everyone have **{}** seconds to change their minds"
vote_countdown_cancelled = "You now have more time to vote"
vote_result = "The village have finished voting! The result is:\n{}"
vote_item = "- {} with **{}** votes"
vote_detail_item = "- **{}** votes for {}"
vote_detail_item_nokill = "- **{}** votes not to kill"
no_lynch_vote = "**No kill**"
remove_notfound = "there is currently no {} in the game"
take_notavailable = "you can't choose **{}**, you have to choose between **{}**"

add_wronguse = "send `{0}  role` to add a role to the game. For example, `{0} villager`"
remove_wronguse = "send `{0}  role` to remove a role from the game. For example, `{0} seer`"
thief_wronguse = "send `{0}  player` to switch their role with yours. For examples, `{0} quandangv`"
troublemaker_wronguse = "send `{0}  player-1, player-2` to swap their roles. For examples, `{0} quandangv, mymy`"
see_wronguse = "send `{0}  player` to see their roles. For examples, `{0} quandangv`"
drunk_wronguse = "there are **{1}** excess roles, choose a number from **1** to **{1}** and send `{0}  card-number` to take the corresponding role. For examples, `{0} 1`"
reveal_wronguse = "there are **{1}** excess roles, choose a number from **1** to **{1}** and send `{0}  card-number` to reveal the corresponding role. For examples, `{0} {1}`"
clone_wronguse = "send `{0}  player` to clone their role. For example, `{0} quandangv`"
vote_wronguse = "send `{0}  player` to vote for lynching them. For example, `{0} quandangv`"
kill_wronguse = "send `{0}  player` to vote for the wolves to kill them. For example, `{0} quandangv`"
defend_wronguse = "send `{0}  player` to defend them during the night. For example, `{0} quandangv`"
poison_wronguse = "send `{0}  player` to poison them. For example, `{0} quandangv`"
detective_wronguse = "send `{0}  player-1,  player-2` to investigate their roles. For example, `{0} quandangv, mymy`"

add_success = [ "Added **{}** to the list of roles", "A wild **{}** has appeared" ]
remove_success = [ "Removed a **{}** from the villager", "A **{}** has left the villager" ]
thief_success = "you stole the role of **{1}** from {0}"
troublemaker_success = "you swapped the roles of {} and {}"
see_success = [ "The role of {} is **{}**", "{} is a **{}**" ]
drunk_success = "you took the excess card number **{}**"
clone_success = "You cloned a role of **{}**. "
vote_success = [ "{} wants to throw {} into the fire! ", "{} demanded to hang {}! ", "{} voted to hang {}. " ]
no_vote_success = [ "{} suggest that the village avoid killing. ", "{} doesn't want to kill today. " ]
unvote_success = "{} changed their mind and retracted their vote"
insomniac_reveal = [ "After a long night, you checked your role and found: you are now a **{}**!", "Before dawn, you quickly looked at your role and see it is now **{}**!" ]
reveal_success = "the excess card number **{}** is **{}**"
gone_to_sleep = [ "{} went to sleep", "{} jumped on their bed and fall asleep", "{} doesn't want wrinkles, so they went to sleep early" ]
save_success = "the current state is saved as **{}**"
load_success = "the current state is loaded from **{}**"
vote_detail = "The current votes are:\n{}"
vote_kill = [ "Today {} wants **{}**'s meat", "{} wants to bite **{}**", "{} demanded that the wolves attack **{}**" ]
vote_no_kill = [ "Today {} goes vegan", "{} doesn't want to kill anyone", "{} suggests that the wolves don't kill" ]
defend_success = "you will defend **{}** tonight"
poison_success = "you poisoned **{}**"
revive_success = "you revived"
investigate_same = "{} **=** {}"
investigate_diff = "{} **≠** {}"
drunk_took_role = "you have become a **{}**. "
knight_kill = "{} pulled out their lance and swiftly end {}'s life"

no_swap_self = "you can't swap your own role"
seer_self = "you shouldn't see yourself"
clone_self = "you shouldn't clone yourself"
require_admin = "you need to be an admin to used that command"
not_playing = "you're not in the game, you may not use that command"
forbid_game_started = [ "you may not use `{}` when the game have started", "the game have started, you may not use `{}`" ]
wrong_role = [ "you don't have the ability of `{}`", "you're not allowed to `{}`", "i'm not letting you use `{}`" ]
dm_only = "uhhhhhm! If your role have the ability to `{}`, you must use it in moderator's dm"
wolf_only = "uhhhhm! If your role allow you to `{}`, you must use it in wolf's group"
public_only = "`{}` must be used in the public group"
player_notfound = [ "Who is '{}'?", "I can't find '{}'" ]
player_norole = "can't find {}'s role, I think they're not in the game"
debug_command = [ "this command is for debugging, you can't use it" ]
night_only = [ "you can only use this command at night, come back after sunset", "you need to wait for the night to use this command" ]
day_only = [ "you can only use this command during the day, wait for the village to wake up", "you need to wait for the day to use this command" ]
ability_used = [ "you have used `{}` already", "`{}` was used already" ]
choice_outofrange = "you have to choose a number from **1** to **{}**"
seer_reveal_already = "you have revealed an excess card, you can't also use your seeing ability"
seer_see_already = "you have used your seeing ability, you can't also reveal an excess card"
out_of_reveal = "you have revealed **{}** excess cards, you can't reveal anymore"
invalid_file_name = "invalid file name!"
defend_repeat = "you have defended this person last night"
no_defend_self = "you can't defend yourself"
target_dead = [ "the target is dead", "**{}** have died" ]
good_night = [ "good night", "sweet dreams", "sleep well", "hope you live to tomorrow", "hope the wolves spare you" ]
revive_no_deaths = "no one died tonight"
kill_already = "you can't change your target anymore"
dead = [ "you are dead", "go back to your grave" ]
not_voting = "you can't unvote when you haven't vote"

cmd_help = ( "help", "`{0}` lists available commands.\nWhile `{0}  command` provides information about that command\nAlso `{0}  role` will explain that role" )
cmd_startimmediate = ( "startimmediate", "`{0}` to immediately start a game with all members" )
cmd_addrole = ( "add", "`{0}  role` will add a role into the game" )
cmd_removerole = ( "remove", "`{0}  role` to remove a role from the game" )
cmd_info = ( "info", "`{0}` to list the roles in the village and other infos" )
cmd_endgame = ( "endgame", "`{0}` to force stop a game" )
cmd_sleep = ( "sleep", "`{0}` when you don't want to use your role" )
cmd_closevote = ( "closevote", "`{0}` to force stop a vote" )
cmd_wakeup = ( "wakeup", "`{0}` to force the village to wake up" )
cmd_vote = ( "lynch", "`{0}  player` to vote for lynching that player" )
cmd_votenolynch = ( "nolynch", "`{0}` to vote for no lynching" )
cmd_unvote = ( "unvote", "`{0}` to retract your vote" )
cmd_clone = ( "clone", "`{0}  player` to clone the role of a player" )
cmd_reveal = ( "reveal", "`{0}  excess-role-number` to privately view an excess role" )
cmd_see = ( "see", "`{0}  player` to see the role of that player" )
cmd_swap = ( "swap", "`{0}  player1, player2` to swap the role of those players" )
cmd_steal = ( "steal", "`{0}  player` to replace your role with theirs" )
cmd_take = ( "take", "`{0}  excess-role-number` to take an excess role as your own" )
cmd_save = ( "save", "`{0}  file-name` to save the state of the game" )
cmd_load = ( "load", "`{0}  file-name` to load the state of a game" )
cmd_revealall = ( "revealall", "`{0}` prints everything about the current game (Debug mode only)" )
cmd_votecount = ( "votecount", "`{0}` to view the vote count of each players" )
cmd_votedetail = ( "votedetail", "`{0}` to view the vote of everyone" )
cmd_history = ( "history", "`{0}` to view all the events of the previous game" )
cmd_kill = ( "kill", "Wolves use `{0}  target` to choose their target to kill" )
cmd_defend = ( "defend", "Guards use `{0}  player` to defend them against attacks at night. A player can't be defended two nights in a row" )
cmd_revive = ( "revive", "When there is a death at night, witches can use `{0}` to revive" )
cmd_poison = ( "poison", "Witches can use `{0}  player` to kill that player" )
cmd_investigate = ( "investigate", "Detectives can use `{0}  player1, player2` to find out if they are on the same side" )

onenight_villager = ( "dân thường", "Một con dân thường không có chức năng. Nhờ vậy, bạn sẽ được yên giấc vào ban đêm", "Ban đêm bạn không phải làm gì cả. Sáng dậy, bạn có thể vote người để treo cổ", "dân làng", "dân" )
onenight_wolf = ( "sói", "Sói chống lại dân làng. Chúng sẽ thắng nếu người bị treo cổ là phe dân", "Bạn sẽ được thêm vào group sói. Ban ngày, hãy tìm cách treo cổ một người dân để chiến thắng" )
onenight_tanner = ( "kẻ chán đời", "Một người với mục tiêu duy nhất là bị treo cổ. Nếu làng treo cổ nó, nó sẽ thắng và mọi người đều thua", "Sáng hôm sau, hãy cố gắng thuyết phục làng treo cổ mình", "chán đời" )
onenight_insomniac = ( "cú đêm", "Đây là người ngủ trễ nhất làng. Trước khi ngủ, họ sẽ được xem lại chức năng của mình", "Bạn sẽ được thông báo chức năng cuối cùng của mình trước khi trời sáng", "kẻ mất ngủ" )
onenight_thief = ( "trộm", "Người này sẽ đánh cắp chức năng của một người khác trong làng, thay thế bằng chức năng hiện có của mình", "Hãy dùng lệnh `{}  người-khác` để ăn cắp lá bài của họ", "kẻ trộm" )
onenight_seer = ( "tiên tri", "Người này được soi chức năng của một người trong làng, hoặc soi {0.SEER_REVEAL} lá bài bên ngoài", "Hãy dùng lệnh `{0}  STT-lá-bài` để xem một lá bài bên ngoài, hoặc dùng lệnh `{1}  người-khác` để soi chức năng của họ" )
onenight_clone = ( "nhân bản", "Người này sẽ sao chép chức năng của một người khác trong làng", "Dùng lệnh `{}  người-khác` để sao chép chức năng của họ" )
onenight_troublemaker = ( "phá rối", "Vào ban đêm, kẻ này sẽ tráo đổi chức năng của 2 người trong làng", "Hãy dùng lệnh `{}  người-1, người-2` để tráo chức năng của họ", "kẻ phá rối" )
onenight_drunk = ( "kẻ say rượu", "Người này không biết chức năng của mình, và sẽ lấy một trong những lá bài bên ngoài để làm chức năng", "Hãy dùng lệnh `{}  STT-lá-bài` để đổi chức năng của mình lấy một lá bài bên ngoài", "say rượu" )
onenight_minion = ( "phản bội", "Người này thuộc phe sói và biết được sói là ai. Nếu làng treo cổ người này, phe sói sẽ thắng", "Hãy tìm cách treo cổ dân làng hoặc treo cổ chính mình", "kẻ phản bội" )
onenight_hunter = ( "thợ săn", "Thợ săn luôn mang theo câu súng săn của mình. Nếu bị dân làng treo cổ, họ sẽ dùng súng bắn chết người mình đã bỏ phiếu giết", "Hãy chọn kỹ người để bỏ phiếu giết. Nếu bị dân làng treo cổ, bạn sẽ bắn chết người đó" )

classic_guard = ( "bảo vệ", "Mỗi đêm bảo vệ sẽ chọn một người để bảo vệ khỏi bị tấn công", "Hãy dùng lệnh `{}  người-chơi` để chọn người mình bảo vệ", "bv" )
classic_wolf = ( "sói", "Mỗi đêm các sói sẽ bàn bạc với nhau và giết một người", "Hãy dùng lệnh `{}  mục-tiêu` để chọn người mình muốn giết" )
classic_villager = ( "dân thường", "Một con dân thường không có chức năng. Nhờ vậy, bạn sẽ được yên giấc vào ban đêm", "Ban đêm bạn không phải làm gì cả. Sáng dậy, bạn có thể vote người để treo cổ", "dân làng", "dân" )
classic_witch = ( "phù thủy", "Người này sẽ có một bình thuốc cứu người và một bình giết người để sử dụng trong đêm. Mỗi bình chỉ được dùng một lần trong game", "Mỗi đêm bạn sẽ được biết có người chết hay không. Dùng lệnh `{1}` để cứu họ, hoặc lệnh `{0} mục-tiêu` để giết, còn không thì bạn phải nhắn `{2}`", "pt" )
classic_detective = ( "thám tử", "Thám tử sẽ điều tra 2 người mỗi đêm, biết được họ có cùng phe với nhau không", "Mỗi đêm bạn hãy dùng lệnh `{}  người-chơi-1, người-chơi-2` để chọn hai người để điều tra xem họ có cùng phe với nhau không" )
classic_wolfsheep = ( "sói trắng", "Đây là một con sói, nhưng mang dáng vóc và hành vi của dân làng, giúp nó qua mặt được các chức năng soi và điều tra", "Hãy dùng lệnh `{}  mục-tiêu` để chọn người mình muốn giết" )
classic_drunk = ( "kẻ say rượu", "Khi chơi chức năng này, trò chơi sẽ được set dư ra 2 lá bài. Đêm đầu tiên, kẻ say rượu sẽ được xem 2 lá bài dư và chọn một trong hai làm chức năng của mình. Nếu một trong 2 chức năng đó là sói, người chơi phải chọn sói", "", "say rượu" )
classic_knight = ( "hiệp sĩ", "Một lần trong game, vào ban ngày, hiệp sĩ có thể tiết lộ chức năng của mình và rút gươm giết một người. Cả làng sẽ lập tức đi ngủ", "Khi trời sáng, bạn có thể dùng lệnh `{}  mục tiêu` để giết một người và buộc cả làng đi ngủ", "kỵ sĩ" )
