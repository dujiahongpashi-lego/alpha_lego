# alpha_lego
四子棋对战AI。运行在LEGO SPIKE PRIME HUB（含全自动版、含搭建图纸）

适配【计客智能四子棋】智能玩具产品

注：乐高45678套组和51515套组是目前（2023年3月）已知的唯二的SPIKE PRIME HUB硬件的官方获取渠道

下棋对战AI的核心代码实现采用了常规的场面打分策略。并未使用多层级决策树、剪枝等算法。

- `./图纸` 乐高自动下棋机的studio2.0搭建图纸
- `fourInARowGame.py` 控制台输出版程序代码：可运行于PC和乐高SPIKE PRIME HUB。Esp32没测试，理论上应该也行。
- `fourInARowGame_LED.py` 运行于乐高SPIKE PRIME HUB，下棋时“哪里亮了点哪里”。运行时，用Hub上的左右按钮输入对手落点。
- `autoGameMachine.py` 自动下棋机代码。搭建部分请参考图纸。适用于四子棋智能玩具的CPU对战模式。

GitHub不常来，任何问题请在相关视频的下方留言。