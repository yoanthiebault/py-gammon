"""
Definitions for the main object in a game.
"""
__all__ = ['Board', 'Roll', 'Turn', 'SOUTH', 'NORTH']

import random, operator
from util import KeyedMixin

SOUTH = 'S'
NORTH = 'N'


class Board(object):
    """
    A Board has 24 Points with at most 15 Pieces in play at a time.
    Each Point can have 0 or more Pieces.

    White's home is lower-right and can only move up the array.
    Black's home is upper-right and can only move down the array.
    
    Points are positioned in the array like this:
    
    [ 12 | 11 | 10 |  9 |  8 |  7 ][  6 |  5 |  4 |  3 |  2 |  1 ] [ white jail / black home ]
    [ 13 | 14 | 15 | 16 | 17 | 18 ][ 19 | 20 | 21 | 22 | 23 | 24 ] [ black jail / white home ]
    
    Point 0 is both the jail for white and the home for black.  Point
    25 is both the jail for black and home for white.  A
    representation of a new Board:

    [ 12:W5 | 11    | 10    |  9    |  8:B3 |  7    ] [  6:B5 |  5    |  4    |  3    |  2    |  1:W2 ] [  0:W0:B0 ]
    [ 13:B5 | 14    | 15    | 16    | 17:W3 | 18    ] [ 19:W5 | 20    | 21    | 22    | 23    | 24:B2 ] [ 25:B0:W0 ]
    """

    @property
    def points(I):
        """
        The read-only collection of Point instances that make up a
        Board.  While this collection is read-only, the Point
        instances are not since Pieces can be pushed & popped.
        """
        return I._points

    def __init__(I):
        """
        Create board initialized for a new game.
        """
        I._points = tuple(Point(i) for i in range(26))
        num = 0
        for pt, count in ((1,2), (12,5), (17,3), (19,5)):
            for i in range(count):
                I.points[pt].push(Piece(SOUTH, num))
                num += 1
        num = 0
        for pt, count in ((24,2), (13,5), (8,3), (6,5)):
            for i in range(count):
                I.points[pt].push(Piece(NORTH, num))
                num += 1

    @staticmethod
    def from_str(s):
        """
        Return a new Board from string representation of a Board.
        """
        is_digit = ('0','1','2','3','4','5','6','7','8','9').__contains__
        brd = Board()
        for pt in brd.points:
            while pt.pieces:
                pt.pop()
        counts = {SOUTH: 0, NORTH: 0}
        for line in s.split('\n'):
            for i in line.split():
                if is_digit(i[0]):
                    l = i.split(':')
                    if len(l) > 1:
                        pt = int(l[0])
                        for pieces in l[1:]:
                            color = pieces[0]
                            count = int(pieces[1:])
                            for j in range(count):
                                brd.points[pt].push(Piece(color, counts[color]))
                                counts[color] += 1
        return brd

    def __str__(I):
        l = []
        out = l.append
        out(" 12 11 10 9  8  7  6  5  4  3  2  1   jailed_south: {}, homed_north: {}\n".format(len(I.jailed(SOUTH)), len(I.homed(NORTH))))
        for height in range(1,6):
            for column in range(12,0,-1):
                out(" ")
                if len(I.points[column].pieces) >= height:
                    out(I.points[column].color)
                else:
                    out(" ")
                out(" ")
            out("\n")
        for column in range(12,0,-1):
            out(" ")
            if len(I.points[column].pieces) >= 6:
                out(str(len(I.points[column].pieces)-5))
            else:
                out(" ")
            out(" ")
        out("\n")
        for column in range(13,25):
            out(" ")
            if len(I.points[column].pieces) >= 6:
                out(str(len(I.points[column].pieces)-5))
            else:
                out(" ")
            out(" ")
        out("\n")
        for height in range(5,0,-1):
            for column in range(13,25):
                out(" ")
                if len(I.points[column].pieces) >= height:
                    out(I.points[column].color)
                else:
                    out(" ")
                out(" ")
            out("\n")
        out(" 13 14 15 16 17 18 19 20 21 22 23 24  jailed_north: {}, homed_south: {}".format(len(I.jailed(NORTH)), len(I.homed(SOUTH))))
        return ''.join(l)

    def copy(I):
        """
        Return a deep copy of this Board.
        """
        new = Board()
        new._points = tuple(pt.copy() for pt in I.points)
        return new

    def move(I, src, dst):
        """
        Return new Board with a piece from src moved to dst.
          * src: a Point instance or position
          * dts: a Point instance or position
        """
        new = I.copy()
        if not isinstance(dst, int):
            dst = dst.num
        if dst < 0:
            dst = 0
        elif dst > 25:
            dst = 25
        assert dst >= 0 and dst <= 25, 'valid points are [0..25]'
        dst = new.points[dst]
        if not isinstance(src, int):
            src = src.num
        assert src >= 0 and src <= 25, 'valid points are [0..25]'
        src = new.points[src]
        sharing_allowed = dst in (new.home(SOUTH), new.home(NORTH))
        color = SOUTH if (dst.num>src.num) else NORTH
        if not sharing_allowed:
            assert not dst.blocked(src.color), 'cannot move to a blocked point'
        if dst.pieces and src.color != dst.color and not sharing_allowed:
            # Move exposed piece to jail.
            new.jail(dst.color).push(dst.pop(SOUTH if color == NORTH else NORTH))
        dst.push(src.pop(color))
        return new

    def possible_moves(I, roll, point):
        # TODO: this function seems to be a pseudo duplicate of _all_choices. It may be removed.
        """
        Return list of available Points to move to, accounting for all
        combinations of unused dies.
        """
        if isinstance(point, int):
            assert point >= 0 and point <= 25, 'valid points are [0..25]'
            point = I.points[point]
        assert point.pieces, 'there are no pieces on this point'
        piece = point.pieces[0]
        direction = 1 if piece.color == SOUTH else -1
        dies = roll.dies
        if not dies:
            return []
        if len(dies) == 1:
            paths = [[dies[0]]]
        elif dies[0] == dies[1]:
            paths = [len(dies) * [dies[0]]]
        else:
            paths = [(dies[0], dies[1]), (dies[1], dies[0])]
        multiple_jailed = len(I.jailed(piece.color)) > 1
        moves = []
        min_point = 1
        max_point = 24
        if I.can_go_home(piece.color):
            if piece.color == NORTH:
                min_point -= 1
            else:
                max_point += 1
        for hops in paths:
            if multiple_jailed:
                hops = hops[:1]
            num = point.num
            for hop in hops:
                num += direction * hop
                if num < min_point or num > max_point or I.points[num].blocked(piece.color):
                    break
                if num not in moves:
                    moves.append(num)
        return sorted(moves)

    def can_go_home(I, color):
        """
        True if there are no pieces outside given color's home quadrant.
        """
        points = range(7, 26) if color == NORTH else range(19)
        for point in points:
            if color == I.points[point].color:
                return False
        return True

    def last_checkers_position(self, color):
        positions = range(0,25) if color == SOUTH else range(25,0,-1)
        for position in positions:
            if self.points[position].color == color:
                return position
        return 25 if color == SOUTH else 0

    def finished(I):
        """
        True once all pieces for a color are home.
        """
        return 15 == len(I.homed(SOUTH)) or \
            15 == len(I.homed(NORTH))

    def jail(I, color):
        """
        Return Point that represents jail for given color.
        """
        return I.points[0 if color == SOUTH else 25]

    def jailed(I, color):
        """
        List of pieces in jail for given color.
        """
        return tuple(i for i in I.jail(color).pieces if i.color == color)

    def home(I, color):
        """
        Return Point that represents home for given color.
        """
        return I.points[0 if color == NORTH else 25]

    def homed(I, color):
        """
        List of pieces that made it home.
        """
        return tuple(i for i in I.home(color).pieces if i.color == color)

    def strongholds(I, color):
        """
        List of points with two or more pieces for given color.
        """
        return [pt for pt in I.points if pt.color == color and len(pt.pieces) > 1]

    def safe(I, color):
        """
        List of points past last enemy piece.
        """
        if color == SOUTH:
            enemy = NORTH
            behind = operator.gt
            enemy_line = I.points[max(i for i in range(25, 1, -1) if I.points[i].color == enemy)]
        else:
            enemy = SOUTH
            behind = operator.lt
            enemy_line = I.points[min(i for i in range(0, 24, 1) if I.points[i].color == enemy)]
        return [pt for pt in I.points if behind(pt, enemy_line) and pt.pieces]

    def exposed(I, color):
        """
        List of points for given color that contain 1 piece that are not safe.
        """
        safe = I.safe(color)
        jail = I.jail(color)
        return [pt for pt in I.points if pt.color == color and len(pt.pieces) == 1 and pt not in safe and pt != jail]


class Point(KeyedMixin, object):
    """
    A Point represents a position on the Board.
    """

    @property
    def pieces(I):
        """
        The read-only collection of Pieces that are at this Point.
        Points can be modified via push() & pop().
        """
        return I._pieces

    def __init__(I, num):
        I._pieces = ()
        I.num = num
        I.key = num # Satisfy KeyedMixin

    def __str__(I):
        """
        A version of repr(Point) with whitespace to make str(Board) nicer.
        """
        s = "{:2d}".format(I.num)
        if I.pieces:
            s += ":{}{}".format(I.color, len(I.pieces))
        else:
            s += '   '
        return s

    def __repr__(I):
        color = 'NA'
        if I.pieces:
            color = "{}{}".format(I.color, len(I.pieces))
        return "{}:{}".format(I.num, color)

    def copy(I):
        """
        Return a deep copy of this Point.
        """
        new = Point(I.num)
        new._pieces = tuple(p.copy() for p in I.pieces)
        return new

    def push(I, piece):
        """
        Add given Piece to this Point.
        """
        if piece not in I.pieces:
            I._pieces += (piece,)
            if I.num not in (0,25): # Making exception for jail/home.
                a = str(set(i.color for i in I.pieces))
                b = str(set([piece.color]))
                message = "only pieces of same color allowed in a point"+a+" "+b
                assert set(i.color for i in I.pieces) == set([piece.color]), \
                    message


    def pop(I, color):
        """
        Remove top Piece and return it.
        """
        assert I.pieces, 'no pieces at this point'
        assert color, 'no specified color'
        index = 0
        for piece in I.pieces:
            if piece.color == color:
                I._pieces = I.pieces[:index] + I.pieces[(index+1):]
                return piece
            index += 1
        assert False, 'no pieces of this color '+str(color)+' at '+str(I.num)

    def blocked(I, color):
        """
        True if this Point contains more than one opposing Piece,
        excluding home/jail since they should never be blocked.
        """
        return I.num not in (0,25) and color != I.color and len(I.pieces) > 1

    @property
    def color(I):
        """
        None if there are no Pieces here.  Otherwise, the color of one
        of the Pieces here.  The special jail & home Points are
        treated specially in that only the jail's color is ever considered.
        """
        val = None
        if I.pieces:
            colors = set(i.color for i in I.pieces)
            if I.num == 0:
                if SOUTH in colors:
                    val = SOUTH
            elif I.num == 25:
                if NORTH in colors:
                    val = NORTH
            elif len(colors) == 1:
                val = I.pieces[0].color
            else:
                raise ValueError("multiple colors occupy same point: {}".format(I))
        return val


class Piece(object):
    """
    Points contain zero or more Pieces.
    """

    @property
    def color(I):
        'The side this Piece belongs to.'
        return I._color

    @property
    def num(I):
        'The number of this Piece in range [0..14]'
        return I._num

    def __init__(I, color, num):
        assert num >= 0 and num <= 15, \
            "number out of range [0,15]: {}".format(num)
        assert color in (SOUTH, NORTH), \
            "color must be '{}' or '{}': {}".format(SOUTH, NORTH, color)
        I._color = color
        I._num = num

    def __repr__(I):
        return "{}:{}".format(I.color, I.num)

    def __hash__(I):
        return (100 if I.color == SOUTH else 200) + I.num

    def copy(I):
        """
        Return a deep copy of this Piece.
        """
        return Piece(I.color, I.num)


class Roll(object):
    """
    A Roll of two dies.
    """
    @property
    def dies(I):
        'Collection of unused dies.'
        return I._dies

    def __init__(I, d1=None, d2=None):
        if d1 is None:
            d1 = random.choice(range(1, 7))
        if d2 is None:
            d2 = random.choice(range(1, 7))
        assert d1 >= 1 and d1 <= 6, "invalid roll: {}".format(d1)
        assert d2 >= 1 and d2 <= 6, "invalid roll: {}".format(d2)
        # Preserve original roll.
        I.d1, I.d2 = d1, d2
        # Capture number of unused dies/moves.
        if d1 != d2:
            I._dies = (d1, d2)
        else:
            I._dies = (d1,d1,d1,d1)

    def __repr__(I):
        return "{}x{}".format(I.d1, I.d2)

    def __hash__(I):
        return (10 * I.d1) + I.d2

    def __eq__(I, other):
        return I.d1 == other.d1 and I.d2 == other.d2

    @staticmethod
    def from_str(s):
        return Roll(*[int(i) for i in s.split('x')])

    def copy(I):
        """
        Return a deep copy of this Roll.
        """
        new = Roll(I.d1, I.d2)
        new._dies = tuple(I.dies)
        return new

    def use(I, move):
        """
        Mark die(s) as used to satisfy given move.
        """
        working = list(I.dies)
        if move in working:
            # NOTE: list.remove() will only remove one matching entry,
            # which works out well for us since we don't want to
            # remove multiple dies when doubles are rolled.
            working.remove(move)
        else:
            while working and move >= max(working):
                # Consume dies until move is satisfied.  We don't care
                # about the order since will either be doubles or both
                # dies will be needed when not doubles.
                move -= working.pop()
            if move != 0:
                raise ValueError('impossible move')
        I._dies = tuple(working)

    def unuse(I, move):
        """
        Mark dies as unused for given move - useful for undo or automated tests.
        """
        # assert die in (I.d1, I.d2), 'die not part of this roll'
        working = list(I.dies)
        if move in (I.d1, I.d2):
            if move == I.d2:
                working.append(move)
            else:
                working.insert(0, move)
        else:
            # Whether doubles or not, will need at least two dies to satisfy this move.
            working.extend([I.d1, I.d2])
            move -= I.d1 + I.d2
            while move > 0:
                # Should only get here when there are doubles.  Unuse
                # a die until the move is satisfied
                working.append(I.d1)
                move -= I.d1
            if move != 0 or len(working) > 4:
                raise ValueError('impossible to unuse')
        I._dies = tuple(working)


class Turn(object):
    """
    A Turn captures the Roll and the moves made by the player.
    """

    def __init__(I, roll, moves):
        I.roll = roll
        I.moves = moves

    def __str__(I):
        return "{}: {}".format(I.roll, I.moves)

    def __eq__(I, other):
        return I.roll == other.roll and I.moves == other.moves

    @staticmethod
    def to_json(obj):
        """
        Hook for json.dump() & json.dumps().
        """
        if isinstance(obj, Turn):
            return dict(roll=str(obj.roll), moves=obj.moves)
        raise TypeError("not json-serializable: {}<{}>".format(type(obj), obj))

    @staticmethod
    def from_json(obj):
        """
        Hook for json.load() & json.loads().
        """
        if isinstance(obj, dict) and 'roll' in obj:
            return Turn(Roll.from_str(obj['roll']), [tuple(i) for i in obj['moves']])
        return obj

    def __eq__(I, other):
        return I.roll == other.roll and I.moves == other.moves
