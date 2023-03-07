import time
from mindstorms import MSHub, Motor, MotorPair, ColorSensor, DistanceSensor, App
from mindstorms.control import wait_for_seconds, wait_until, Timer
from mindstorms.operator import greater_than, greater_than_or_equal_to, less_than, less_than_or_equal_to, equal_to, not_equal_to
import math

# 在此处创建对象。
hub = MSHub()

# 在此处编写程序。
hub.speaker.beep()

X_STEP = 329
Y_STEP = 330

x_motor = Motor('A')
y_motor = Motor('B')
z_motor = Motor('C')
presser = ColorSensor('E')
presser.light_up_all(0)


x_motor.set_degrees_counted(0)
y_motor.set_degrees_counted(0)

current_x = 0
current_y = 0


def _update_current(x, y):
    global current_x
    global current_y
    current_x = x
    current_y = y


def move_to(x, y):
    global current_x
    global current_y
    if x != current_x:
        x_motor.run_to_degrees_counted(0 - (x * X_STEP))
    if y != current_y:
        y_motor.run_to_degrees_counted(0 - (y * Y_STEP))
    _update_current(x, y)
    return


def press_down():
    z_motor.run_for_degrees(150)
    z_motor.run_for_degrees(-150)


def press_hold():
    z_motor.run_for_degrees(150)
    wait_for_seconds(3)
    z_motor.run_for_degrees(-150)


def scan_light():
    global current_x, current_y
    if current_y == 2 and current_x == 2:
        wait_for_seconds(1.5) # 恰好处于初始点时，先等等再启动扫描
    for times in range(3):
        # for i in [(0, 0), (1, 0), (2, 0), (3, 0), (4, 0), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (4, 3), (3, 3), (2, 3), (1, 3), (0, 3), (0, 4), (1, 4), (2, 4), (3, 4), (4, 4)]: # 地毯式
        for i in [(2, 2), (1, 2), (1, 1), (2, 1), (3, 1), (3, 2), (3, 3), (2, 3), (1, 3), (0, 3), (0, 4), (1, 4), (2, 4), (3, 4), (4, 4), (4, 3), (4, 2), (4, 1), (4, 0), (3, 0), (2, 0), (1, 0), (0, 0), (0, 1), (0, 2)]: # 螺旋式
            (x, y) = i
            move_to(x, y)
            if check_light():
                return (x, y)
    return (4, 4)


def check_light():
    light = False
    for i in range(12):
        if presser.get_ambient_light() > 5:
            light = True
            return light
        wait_for_seconds(0.05)
    return light


EMPTY_PLACE = 0
WALL_SPACE = 666
WIN_SCORE = 90000000000000


class Step:
    def __init__(self, color, layer, x, y):
        self.x = x
        self.y = y
        self.layer = layer
        self.color = color

    def __str__(self):
        return '[' + str(self.color) + '] position to L' + str(self.layer) + '_(' + str(self.x) + ',' + str(self.y) + ')'


# 棋盘
class Checkerboard:
    def __init__(self):
        self.stericBoard = []
        self.addNewLayer()
        self.step_history = []
        self.SUCCESS_TIMES = 4  # 4子连算获胜
        self.SIDE_LENGTH = 5  # 方形棋盘边长5

    def _getNew5x5Layer(self):
        return [[EMPTY_PLACE]*5, [EMPTY_PLACE]*5, [EMPTY_PLACE]*5, [EMPTY_PLACE]*5, [EMPTY_PLACE]*5]

    def addNewLayer(self):
        self.stericBoard.append(self._getNew5x5Layer())

    def _doPlaceChequer(self, color, layer, x, y):
        self.stericBoard[layer][x][y] = color
        self.step_history.append(Step(color, layer, x, y))
        return True

    # 落子(允许不指定Z轴位置)
    def placeChequer(self, color, x, y, layer=None):
        if layer is None:
            layer = 0
            for l in range(len(self.stericBoard), 0, -1):
                if self.stericBoard[l-1][x][y] != EMPTY_PLACE:
                    layer = l
                    break
        board = self.stericBoard
        currentLayerCounts = len(board)
        if layer > currentLayerCounts:
            # 不允许越层落子
            print('Layer too high')
            return False
        elif layer == currentLayerCounts:
            # 落子时尝试创建新的一层
            if board[layer - 1][x][y] > 0:
                self.addNewLayer()
                return self._doPlaceChequer(color, layer, x, y)
            print('No earth at this position', x, y,
                  'on current top layer', currentLayerCounts - 1)
            return False

        if (layer == 0 or board[layer-1][x][y] > 0) and board[layer][x][y] == EMPTY_PLACE:
            # 在已存在的某层落子
            return self._doPlaceChequer(color, layer, x, y)

        print('Check currentPosion', layer, x, y, 'with',
              board[layer][x][y], ', Or Check last Layer', layer-1, x, y, 'with', board[layer-1][x][y],)
        return False

    # 撤销上一步
    def cancel(self):
        step = self.step_history.pop()
        self.stericBoard[step.layer][step.x][step.y] = EMPTY_PLACE

    def _judgeContinuousSame(self, line):
        # print(line)
        current = -1
        counter = 0
        for color in line:
            # print(color)
            if color != EMPTY_PLACE and current == color:
                counter += 1
            else:
                current = color
                counter = 1
            if counter == self.SUCCESS_TIMES:
                return True
        return False

    # 判赢
    # 基于当前step落子位置，横竖斜一共13条线。验证这些线上是否有连续n个子（n=4）
    def judge(self):
        if len(self.step_history) == 0:
            return False
        step = self.step_history[-1]
        layer = step.layer
        x = step.x
        y = step.y
        board = self.stericBoard
        currentLayerCounts = len(board)
        # 1 水平面 x固定
        if self._judgeContinuousSame(board[layer][x]):
            return True
        # 2 水平面 y固定
        if self._judgeContinuousSame([board[layer][0][y], board[layer][1][y], board[layer][2][y], board[layer][3][y], board[layer][4][y]]):
            # 魔鬼数字懒得改了
            return True
        # 3 z轴向
        if self._judgeContinuousSame(map(lambda b: b[x][y], board)):
            return True

        # 4 平面，左下-右上
        if abs((x+y) - (self.SIDE_LENGTH - 1)) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(x + y + 1):
                xi = i
                yi = x + y - i
                if xi < self.SIDE_LENGTH and yi < self.SIDE_LENGTH:
                    line.append(board[layer][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        # 5 平面，左上-右下
        if abs(x-y) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(self.SIDE_LENGTH + 1):
                xi = i
                yi = i + y - x
                if 0 <= xi < self.SIDE_LENGTH and 0 <= yi < self.SIDE_LENGTH:
                    line.append(board[layer][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        # 6 x固定，yz平面A
        if currentLayerCounts >= self.SUCCESS_TIMES:
            line = []
            for i in range(layer + y + 1):
                zi = i
                yi = layer + y - i
                if yi < self.SIDE_LENGTH and zi < currentLayerCounts:
                    line.append(board[zi][x][yi])
            if self._judgeContinuousSame(line):
                return True

        # 7 x固定，yz平面B
        if currentLayerCounts >= self.SUCCESS_TIMES:
            line = []
            for i in range(self.SIDE_LENGTH + 1):
                zi = i
                yi = i + y - layer
                if 0 <= yi < self.SIDE_LENGTH and zi < currentLayerCounts:
                    line.append(board[zi][x][yi])
            if self._judgeContinuousSame(line):
                return True

        # 8 y固定，xz平面A
        if currentLayerCounts >= self.SUCCESS_TIMES:
            line = []
            for i in range(layer + x + 1):
                zi = i
                xi = layer + x - i
                if xi < self.SIDE_LENGTH and zi < currentLayerCounts:
                    line.append(board[zi][xi][y])
            if self._judgeContinuousSame(line):
                return True

        # 9 y固定，xz平面B
        if currentLayerCounts >= self.SUCCESS_TIMES:
            line = []
            for i in range(self.SIDE_LENGTH + 1):
                zi = i
                xi = i + x - layer
                if 0 <= xi < self.SIDE_LENGTH and zi < currentLayerCounts:
                    line.append(board[zi][xi][y])
            if self._judgeContinuousSame(line):
                return True

        # 10 对角线A From 4
        if currentLayerCounts >= self.SUCCESS_TIMES and abs((x+y) - (self.SIDE_LENGTH - 1)) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(x + y + 1):
                xi = i
                yi = x + y - i
                zi = x + layer - i
                if xi < self.SIDE_LENGTH and yi < self.SIDE_LENGTH and 0 <= zi < currentLayerCounts:
                    line.append(board[zi][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        # 11 对角线B From 4
        if currentLayerCounts >= self.SUCCESS_TIMES and abs((x+y) - (self.SIDE_LENGTH - 1)) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(x + y + 1):
                xi = i
                yi = x + y - i
                zi = i + layer - x
                if xi < self.SIDE_LENGTH and yi < self.SIDE_LENGTH and 0 <= zi < currentLayerCounts:
                    line.append(board[zi][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        # 12 对角线A From 5
        if currentLayerCounts >= self.SUCCESS_TIMES and abs(x-y) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(self.SIDE_LENGTH + 1):
                xi = i
                yi = i + y - x
                zi = x + layer - i
                if 0 <= xi < self.SIDE_LENGTH and 0 <= yi < self.SIDE_LENGTH and 0 <= zi < currentLayerCounts:
                    line.append(board[zi][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        # 13 对角线B From 5
        if currentLayerCounts >= self.SUCCESS_TIMES and abs(x-y) <= (self.SIDE_LENGTH - self.SUCCESS_TIMES):
            line = []
            for i in range(self.SIDE_LENGTH + 1):
                xi = i
                yi = i + y - x
                zi = i + layer - x
                if 0 <= xi < self.SIDE_LENGTH and 0 <= yi < self.SIDE_LENGTH and 0 <= zi < currentLayerCounts:
                    line.append(board[zi][xi][yi])
            if self._judgeContinuousSame(line):
                return True

        return False

    # 打印输出
    def draw(self):
        board = self.stericBoard
        # print(board)
        if self.step_history != []:
            print('Current Step:', self.step_history[-1])
        layerTip = ''
        for l in range(len(board)):
            layerTip += '|-L' + str(l) + '--------'
        print(layerTip + '|')
        for index in range(5):
            lineCollection = map(lambda x: str(x[0][index]) + ' ' + str(x[1][index]) + ' ' + str(
                x[2][index]) + ' ' + str(x[3][index]) + ' ' + str(x[4][index]), board)
            line = '| '
            for e in lineCollection:
                line += e + ' | '
            print(line)


def _get_vertical_face_lines(face):
    lineA0 = [WALL_SPACE, face[0][1],
              face[1][2], face[2][3], face[3][4]]
    lineA1 = [face[0][0], face[1][1],
              face[2][2], face[3][3], face[4][4]]
    # lineA2 = [face[1][0], face[2][1],
    #           face[3][2], face[4][3], face[5][4]]
    # lineA3 = [face[2][0], face[3][1],
    #           face[4][2], face[5][3], face[6][4]]
    # lineA4 = [face[3][0], face[4][1],
    #           face[5][2], face[6][3], face[7][4]]
    # lineA5 = [face[4][0], face[5][1],
    #           face[6][2], face[7][3], face[8][4]]
    # lineA6 = [face[5][0], face[6][1],
    #           face[7][2], face[8][3], face[9][4]]
    lineB0 = [WALL_SPACE, face[0][3],
              face[1][2], face[2][1], face[3][0]]
    lineB1 = [face[0][4], face[1][3],
              face[2][2], face[3][1], face[4][0]]
    # lineB2 = [face[1][4], face[2][3],
    #           face[3][2], face[4][1], face[5][0]]
    # lineB3 = [face[2][4], face[3][3],
    #           face[4][2], face[5][1], face[6][0]]
    # lineB4 = [face[3][4], face[4][3],
    #           face[5][2], face[6][1], face[7][0]]
    # lineB5 = [face[4][4], face[5][3],
    #           face[6][2], face[7][1], face[8][0]]
    # lineB6 = [face[5][4], face[6][3],
    #           face[7][2], face[8][1], face[9][0]]
    # return [lineA0, lineA1, lineA2, lineA3, lineA4, lineA5, lineA6,
    #         lineB0, lineB1, lineB2, lineB3, lineB4, lineB5, lineB6]
    return [lineA0, lineA1, lineB0, lineB1]


def _set_wall_space_element(layers, z, faceA, faceB, faceA1, faceA2, faceB1, faceB2):
    if layers[z-1][0][0] == EMPTY_PLACE:
        faceA[z][0] = WALL_SPACE
    if layers[z-1][1][1] == EMPTY_PLACE:
        faceA[z][1] = WALL_SPACE
    if layers[z-1][2][2] == EMPTY_PLACE:
        faceA[z][2] = WALL_SPACE
    if layers[z-1][3][3] == EMPTY_PLACE:
        faceA[z][3] = WALL_SPACE
    if layers[z-1][4][4] == EMPTY_PLACE:
        faceA[z][4] = WALL_SPACE

    if layers[z-1][4][0] == EMPTY_PLACE:
        faceB[z][0] = WALL_SPACE
    if layers[z-1][3][1] == EMPTY_PLACE:
        faceB[z][1] = WALL_SPACE
    if layers[z-1][2][2] == EMPTY_PLACE:
        faceB[z][2] = WALL_SPACE
    if layers[z-1][1][3] == EMPTY_PLACE:
        faceB[z][3] = WALL_SPACE
    if layers[z-1][0][4] == EMPTY_PLACE:
        faceB[z][4] = WALL_SPACE

    if layers[z-1][3][0] == EMPTY_PLACE:
        faceA1[z][1] = WALL_SPACE
    if layers[z-1][2][1] == EMPTY_PLACE:
        faceA1[z][2] = WALL_SPACE
    if layers[z-1][1][2] == EMPTY_PLACE:
        faceA1[z][3] = WALL_SPACE
    if layers[z-1][0][3] == EMPTY_PLACE:
        faceA1[z][4] = WALL_SPACE

    if layers[z-1][4][1] == EMPTY_PLACE:
        faceA2[z][1] = WALL_SPACE
    if layers[z-1][3][2] == EMPTY_PLACE:
        faceA2[z][2] = WALL_SPACE
    if layers[z-1][2][3] == EMPTY_PLACE:
        faceA2[z][3] = WALL_SPACE
    if layers[z-1][1][4] == EMPTY_PLACE:
        faceA2[z][4] = WALL_SPACE

    if layers[z-1][1][0] == EMPTY_PLACE:
        faceB1[z][1] = WALL_SPACE
    if layers[z-1][2][1] == EMPTY_PLACE:
        faceB1[z][2] = WALL_SPACE
    if layers[z-1][3][2] == EMPTY_PLACE:
        faceB1[z][3] = WALL_SPACE
    if layers[z-1][4][3] == EMPTY_PLACE:
        faceB1[z][4] = WALL_SPACE

    if layers[z-1][0][1] == EMPTY_PLACE:
        faceB2[z][1] = WALL_SPACE
    if layers[z-1][1][2] == EMPTY_PLACE:
        faceB2[z][2] = WALL_SPACE
    if layers[z-1][2][3] == EMPTY_PLACE:
        faceB2[z][3] = WALL_SPACE
    if layers[z-1][3][4] == EMPTY_PLACE:
        faceB2[z][4] = WALL_SPACE


class Game():
    def __init__(self):
        self.board = Checkerboard()
        self.trcticBoard = Checkerboard()
        self.COLORS = [2, 1]
        self.nextColor = self.COLORS[1]  # =1

    def _get_next_color(self):
        return self.COLORS[self.nextColor - 1]

    def get_advice(self):
        start = time.time()
        if len(self.board.step_history) == 0:
            return (2, 2, 0, 0, 0)
        last_score = 0 - (100*WIN_SCORE)
        advice = (0, 0, 0, 0, 0)
        for x in range(5):
            for y in range(5):
                color = self.nextColor
                self.trcticBoard.placeChequer(color, x, y)
                score = self._scence_score(self.trcticBoard, color)
                score_enemy = self._scence_score(
                    self.trcticBoard, self._get_next_color())
                self.trcticBoard.cancel()
                if score >= WIN_SCORE:
                    return (x, y, score, score, 0)
                finally_score = score - (10 * score_enemy)  # 防守为主
                if finally_score > last_score:
                    last_score = finally_score
                    advice = (x, y, finally_score, score, score_enemy)
        end = time.time()
        print('Thinking time:', end - start, 's')
        return advice

    # 轮流弈子并实时判赢
    def place(self, x, y):
        color = self.nextColor
        print('Place', color, 'at (', x, ',', y, ')')
        placeSuccess = self.board.placeChequer(color, x, y)
        if not placeSuccess:
            print('Place Error, try another position.')
            return False
        if self.judge():
            print('Game Over!', color, 'player WIN THE GAME!')
            return True
        self.trcticBoard.placeChequer(color, x, y)
        self.nextColor = self._get_next_color()
        return False

    def judge(self):
        return self.board.judge()

    def draw(self):
        return self.board.draw()

    def cancel(self):
        return self.board.cancel()

    def copy(self, layer):
        new_layer = []
        for x in range(len(layer)):
            new_layer.append([])
            for y in range(len(layer[x])):
                new_layer[x].append(layer[x][y])
        return new_layer

    # 场面总分
    # 遍历所有行，并累加分数
    def _scence_score(self, board, color):
        layers = board.stericBoard
        layer_counts = len(layers)
        score = 0
        # 平面直排 and 斜排
        lines = []
        for l in range(layer_counts):
            current_l = self.copy(layers[l])
            if l > 0:
                for x in range(5):
                    for y in range(5):
                        if layers[l-1][x][y] == EMPTY_PLACE:
                            current_l[x][y] = WALL_SPACE
            for x in range(5):
                score += self._line_score(current_l[x], color)
            for y in range(5):
                score += self._line_score([current_l[0][y], current_l[1][y],
                                           current_l[2][y], current_l[3][y], current_l[4][y]], color)

            line_1 = [current_l[0][0], current_l[1][1], current_l
                      [2][2], current_l[3][3], current_l[4][4]]
            line_2 = [current_l[4][0], current_l[3][1], current_l
                      [2][2], current_l[1][3], current_l[0][4]]
            line_3 = [WALL_SPACE, current_l[0][1], current_l
                      [1][2], current_l[2][3], current_l[3][4]]
            line_4 = [WALL_SPACE, current_l[1][0], current_l
                      [2][1], current_l[3][2], current_l[4][3]]
            line_5 = [WALL_SPACE, current_l[3][0], current_l
                      [2][1], current_l[1][2], current_l[0][3]]
            line_6 = [WALL_SPACE, current_l[4][1], current_l
                      [3][2], current_l[2][3], current_l[1][4]]
            lines += [line_1, line_2, line_3, line_4, line_5, line_6]
            # score += self._lines_score(lines, color)

        # 垂面直排/直竖
        for x in range(5):
            for y in range(5):
                empty = [EMPTY_PLACE]*5
                line = []
                for l in range(layer_counts):
                    if layers[l][x][y] != EMPTY_PLACE:
                        line.append(layers[l][x][y])
                element_counts = len(line)
                if len(line) > 4:  # 取后4子
                    line = line[element_counts-4: element_counts]
                line.extend(empty)
                line = line[0:5]
                score += self._line_score(line, color)

        # 垂面斜排
        # X固定垂面 共5
        for x in range(5):
            face = []
            for z in range(5):  # 只计算5层
                # face.append([EMPTY_PLACE]*5)
                if z > layer_counts:
                    face.append([WALL_SPACE]*5)
                elif z == layer_counts:
                    face.append([EMPTY_PLACE]*5)
                    for y in range(5):
                        if layers[z-1][x][y] == EMPTY_PLACE:
                            face[z][y] = WALL_SPACE
                elif z < layer_counts:
                    face.append([layers[z][x][0], layers[z][x][1],
                                layers[z][x][2], layers[z][x][3], layers[z][x][4]])
                    if z != 0:
                        for y in range(5):
                            if layers[z-1][x][y] == EMPTY_PLACE:
                                face[z][y] = WALL_SPACE
            lines += _get_vertical_face_lines(face)
            # score += self._lines_score(lines, color)

        # Y固定垂面 共5
        for y in range(5):
            face = []
            for z in range(5):  # 只计算5层
                # face.append([EMPTY_PLACE]*5)
                if z > layer_counts:
                    face.append([WALL_SPACE]*5)
                elif z == layer_counts:
                    face.append([EMPTY_PLACE]*5)
                    for x in range(5):
                        if layers[z-1][x][y] == EMPTY_PLACE:
                            face[z][x] = WALL_SPACE
                elif z < layer_counts:
                    face.append([layers[z][0][y], layers[z][1][y],
                                layers[z][2][y], layers[z][3][y], layers[z][4][y]])
                    if z != 0:
                        for x in range(5):
                            if layers[z-1][x][y] == EMPTY_PLACE:
                                face[z][x] = WALL_SPACE
            lines += _get_vertical_face_lines(face)
            # score += self._lines_score(lines, color)

        # 对角垂面/斜垂面 斜排 共6
        faceA = []
        faceB = []
        faceA1 = []
        faceA2 = []
        faceB1 = []
        faceB2 = []
        for z in range(5):  # 只计算5层
            if z > layer_counts:
                top_line = [WALL_SPACE]*5
                faceA.append(top_line)
                faceB.append(top_line)
                faceA1.append(top_line)
                faceA2.append(top_line)
                faceB1.append(top_line)
                faceB2.append(top_line)
            elif z == layer_counts:
                top_line = [EMPTY_PLACE]*5
                wall_top_line = [WALL_SPACE, EMPTY_PLACE,
                                 EMPTY_PLACE, EMPTY_PLACE, EMPTY_PLACE]
                faceA.append(top_line)
                faceB.append(top_line)
                faceA1.append(wall_top_line)
                faceA2.append(wall_top_line)
                faceB1.append(wall_top_line)
                faceB2.append(wall_top_line)
                _set_wall_space_element(
                    layers, z, faceA, faceB, faceA1, faceA2, faceB1, faceB2)
            elif z < layer_counts:
                faceA.append([layers[z][0][0], layers[z][1][1],
                              layers[z][2][2], layers[z][3][3], layers[z][4][4]])
                faceB.append([layers[z][4][0], layers[z][3][1],
                              layers[z][2][2], layers[z][1][3], layers[z][0][4]])
                faceA1.append([WALL_SPACE, layers[z][3][0],
                               layers[z][2][1], layers[z][1][2], layers[z][0][3]])
                faceA2.append([WALL_SPACE, layers[z][4][1],
                               layers[z][3][2], layers[z][2][3], layers[z][1][4]])
                faceB1.append([WALL_SPACE, layers[z][1][0],
                               layers[z][2][1], layers[z][3][2], layers[z][4][3]])
                faceB2.append([WALL_SPACE, layers[z][0][1],
                               layers[z][1][2], layers[z][2][3], layers[z][3][4]])
                if z != 0:
                    _set_wall_space_element(
                        layers, z, faceA, faceB, faceA1, faceA2, faceB1, faceB2)

        # lines = _get_vertical_face_lines(faceA)
        # score += self._lines_score(lines, color)
        # lines = _get_vertical_face_lines(faceB)
        # score += self._lines_score(lines, color)
        # lines = _get_vertical_face_lines(faceA1)
        # score += self._lines_score(lines, color)
        # lines = _get_vertical_face_lines(faceA2)
        # score += self._lines_score(lines, color)
        # lines = _get_vertical_face_lines(faceB1)
        # score += self._lines_score(lines, color)
        # lines = _get_vertical_face_lines(faceB2)
        # score += self._lines_score(lines, color)
        lines += _get_vertical_face_lines(faceA)
        lines += _get_vertical_face_lines(faceB)
        lines += _get_vertical_face_lines(faceA1)
        lines += _get_vertical_face_lines(faceA2)
        lines += _get_vertical_face_lines(faceB1)
        lines += _get_vertical_face_lines(faceB2)
        score += self._lines_score(lines, color)

        return score

    def _lines_score(self, lines, color):
        # 从气口开始数
        # 注意[活]会被计算两次
        three_alive = 0  # 活3
        three_asleep = 0  # 眠3
        two_alive = 0  # 活2
        two_asleep = 0  # 眠2
        one_alive = 0  # 活1
        one_asleep = 0  # 眠1
        for line in lines:
            if line[1] == color and line[2] == color and line[3] == color and line[4] == color:
                return WIN_SCORE
            if line[1] == color and line[2] == color and line[3] == color and line[0] == color:
                return WIN_SCORE
            if line[0] == EMPTY_PLACE:
                if line[1] == color and line[2] == color and line[3] == color:  # 连3
                    if line[4] == EMPTY_PLACE:
                        three_alive += 1  # 活3
                    else:
                        three_asleep += 1  # 眠3
                elif line[1] == color and line[2] == color:  # 连2
                    if line[3] == EMPTY_PLACE:
                        two_alive += 1  # 活2
                    else:
                        pass  # two_asleep += 1# 眠2，但是会变成死3，无价值
                elif line[1] == color:  # 连1
                    if line[2] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1
            if line[4] == EMPTY_PLACE:
                if line[1] == color and line[2] == color and line[3] == color:  # 连3
                    if line[0] == EMPTY_PLACE:
                        three_alive += 1  # 活3
                    else:
                        three_asleep += 1  # 眠3
                elif line[2] == color and line[3] == color:  # 连2
                    if line[1] == EMPTY_PLACE:
                        two_alive += 1  # 活2
                    else:
                        pass  # two_asleep += 1# 眠2，但是会变成死3，无价值
                elif line[3] == color:  # 连1
                    if line[2] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1
            if line[1] == EMPTY_PLACE:
                if line[0] == color:  # 连1
                    one_asleep += 1  # 眠1

                if line[2] == color and line[3] == color and line[4] == color:  # 连3
                    three_asleep += 1  # 眠3
                elif line[2] == color and line[3] == color:  # 连2
                    if line[4] == EMPTY_PLACE:
                        two_alive += 1  # 活2
                    elif line[0] == EMPTY_PLACE:
                        two_asleep += 1  # 眠2
                    else:
                        pass  # 眠2，但是会变成死3，无价值
                elif line[2] == color:  # 连1
                    if line[3] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1
            if line[3] == EMPTY_PLACE:
                if line[4] == color:  # 连1
                    one_asleep += 1  # 眠1

                if line[0] == color and line[1] == color and line[2] == color:  # 连3
                    three_asleep += 1  # 眠3
                elif line[1] == color and line[2] == color:  # 连2
                    if line[0] == EMPTY_PLACE:
                        two_alive += 1  # 活2
                    elif line[4] == EMPTY_PLACE:
                        two_asleep += 1  # 眠2
                    else:
                        pass  # 眠2，但是会变成死3，无价值
                elif line[2] == color:  # 连1
                    if line[1] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1
            if line[2] == EMPTY_PLACE:
                if line[0] == color and line[1] == color:  # 连2
                    if line[3] == color:
                        three_asleep += 1  # [**.*]型眠3
                    elif line[3] == EMPTY_PLACE:
                        two_asleep += 1  # 眠2
                    else:
                        pass  # 眠2，但是会变成死3，无价值
                elif line[1] == color:  # 连1
                    if line[0] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1
                if line[3] == color and line[4] == color:  # 连2
                    if line[1] == color:
                        three_asleep += 1  # [**.*]型眠3
                    elif line[1] == EMPTY_PLACE:
                        two_asleep += 1  # 眠2
                    else:
                        pass  # 眠2，但是会变成死3，无价值
                elif line[3] == color:  # 连1
                    if line[4] == EMPTY_PLACE:
                        one_alive += 1  # 活1
                    else:
                        one_asleep += 1  # 眠1

        return three_alive * 100000000 + three_asleep * 100000000 + two_alive * 1000000 + two_asleep * 10000 + one_alive * 100 + one_asleep * 1

    def _line_score(self, line, color):
        # 从气口开始数
        # 注意[活]会被计算两次
        three_alive = 0  # 活3
        three_asleep = 0  # 眠3
        two_alive = 0  # 活2
        two_asleep = 0  # 眠2
        one_alive = 0  # 活1
        one_asleep = 0  # 眠1
        if line[1] == color and line[2] == color and line[3] == color and line[4] == color:
            return WIN_SCORE
        if line[1] == color and line[2] == color and line[3] == color and line[0] == color:
            return WIN_SCORE
        if line[0] == EMPTY_PLACE:
            if line[1] == color and line[2] == color and line[3] == color:  # 连3
                if line[4] == EMPTY_PLACE:
                    three_alive += 1  # 活3
                else:
                    three_asleep += 1  # 眠3
            elif line[1] == color and line[2] == color:  # 连2
                if line[3] == EMPTY_PLACE:
                    two_alive += 1  # 活2
                else:
                    pass  # two_asleep += 1# 眠2，但是会变成死3，无价值
            elif line[1] == color:  # 连1
                if line[2] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1
        if line[4] == EMPTY_PLACE:
            if line[1] == color and line[2] == color and line[3] == color:  # 连3
                if line[0] == EMPTY_PLACE:
                    three_alive += 1  # 活3
                else:
                    three_asleep += 1  # 眠3
            elif line[2] == color and line[3] == color:  # 连2
                if line[1] == EMPTY_PLACE:
                    two_alive += 1  # 活2
                else:
                    pass  # two_asleep += 1# 眠2，但是会变成死3，无价值
            elif line[3] == color:  # 连1
                if line[2] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1
        if line[1] == EMPTY_PLACE:
            if line[0] == color:  # 连1
                one_asleep += 1  # 眠1

            if line[2] == color and line[3] == color and line[4] == color:  # 连3
                three_asleep += 1  # 眠3
            elif line[2] == color and line[3] == color:  # 连2
                if line[4] == EMPTY_PLACE:
                    two_alive += 1  # 活2
                elif line[0] == EMPTY_PLACE:
                    two_asleep += 1  # 眠2
                else:
                    pass  # 眠2，但是会变成死3，无价值
            elif line[2] == color:  # 连1
                if line[3] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1
        if line[3] == EMPTY_PLACE:
            if line[4] == color:  # 连1
                one_asleep += 1  # 眠1

            if line[0] == color and line[1] == color and line[2] == color:  # 连3
                three_asleep += 1  # 眠3
            elif line[1] == color and line[2] == color:  # 连2
                if line[0] == EMPTY_PLACE:
                    two_alive += 1  # 活2
                elif line[4] == EMPTY_PLACE:
                    two_asleep += 1  # 眠2
                else:
                    pass  # 眠2，但是会变成死3，无价值
            elif line[2] == color:  # 连1
                if line[1] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1
        if line[2] == EMPTY_PLACE:
            if line[0] == color and line[1] == color:  # 连2
                if line[3] == color:
                    three_asleep += 1  # [**.*]型眠3
                elif line[3] == EMPTY_PLACE:
                    two_asleep += 1  # 眠2
                else:
                    pass  # 眠2，但是会变成死3，无价值
            elif line[1] == color:  # 连1
                if line[0] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1
            if line[3] == color and line[4] == color:  # 连2
                if line[1] == color:
                    three_asleep += 1  # [**.*]型眠3
                elif line[1] == EMPTY_PLACE:
                    two_asleep += 1  # 眠2
                else:
                    pass  # 眠2，但是会变成死3，无价值
            elif line[3] == color:  # 连1
                if line[4] == EMPTY_PLACE:
                    one_alive += 1  # 活1
                else:
                    one_asleep += 1  # 眠1

        return three_alive * 100000000 + three_asleep * 100000000 + two_alive * 1000000 + two_asleep * 10000 + one_alive * 100 + one_asleep * 1


def vs_cpu():
    g = Game()
    g.place(2, 2)
    move_to(2, 2)
    press_down()
    wait_for_seconds(1)
    while True:
        cpu_x, cpu_y = scan_light()
        if g.place(cpu_x, cpu_y):
            break
        press_down()
        move_to(2, 2)
        x, y, _, _, _ = g.get_advice()
        if g.place(x, y):
            break
        move_to(x, y)
        press_down()


vs_cpu()
