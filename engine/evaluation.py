from engine.misc import *
from engine.config import *

class Eval:
    mate_depth = 999
    mate = 100 * 100
    INF = (mate_depth + 1) * mate
    NINF = -INF
    DRAW = 0

    def create(evaluation, checkmate=0):
        return Eval.mate * (Eval.mate_depth  + 1 - evaluation) * checkmate + evaluation * (1 - abs(checkmate))

    def is_forced_checkmate(evaluation):
        return abs(evaluation) >= Eval.mate

    def change_depth(evaluation, depth):
        return evaluation - Eval.mate * depth * sign(evaluation) * (abs(evaluation) >= Eval.mate)

    def str(evaluation):
        if evaluation == Eval.NINF: return 'Black won'
        if evaluation == Eval.INF: return 'White won'
        if abs(evaluation) >= Eval.mate:
            return '#' + ('-' * (evaluation < 0)) + str((Eval.mate_depth + 1 - abs(evaluation) // Eval.mate + 1) // 2)
        return str(evaluation / 100)
        
    def decompose(evaluation):
        is_forced_checkmate = (abs(evaluation) >= Eval.mate)
        return (
            evaluation + (Eval.mate_depth + 1 - evaluation - abs(evaluation) // Eval.mate) * is_forced_checkmate,
            sign(evaluation) * is_forced_checkmate
        )
    
    def aspiration(evaluation, n):
        return evaluation + n * (abs(evaluation) < Eval.mate)

# def endgame_factor(piece_count_self, piece_count_other):
#     return 1 - min(piece_count_self, piece_count_other, TotalPieceCount) / TotalPieceCount


# def king_safety(board, color, endgame):
#     middlegame_safety = PieceTables['KING_MIDDLEGAME'][::1 - 2 * color][list(board.pieces(chess.KING, color))[0]]
#     endgame_safety = PieceTables['KING_ENDGAME'][::1 - 2 * color][list(board.pieces(chess.KING, color))[0]]
#     return endgame * endgame_safety + (1 - endgame) * middlegame_safety


# def pawn_structure(board, color, endgame):
#     return 1 * (1 - endgame)

def evaluate(board, tablebase):
    if dtz := tablebase.get_dtz(board):
        if dtz == 0:
            return Eval.DRAW
        if abs(dtz) > 100:
            return Eval.create(sign(dtz) * tablebase_alpha * tablebase_beta // (abs(dtz) + tablebase_beta - 100))
        return Eval.create(abs(dtz), sign(dtz))

    if (outcome := board.outcome()) != None:
        if outcome.winner == None: return Eval.DRAW
        return Eval.NINF
    
    piece_count_self = 0
    piece_count_other = 0
    positional_piece_count_self = 0
    positional_piece_count_other = 0
    for piece in [chess.PAWN, chess.KNIGHT, chess.BISHOP, chess.ROOK, chess.QUEEN]:
        piece_count_self += PieceValues[piece] * len(board.pieces(piece, board.turn))
        piece_count_other += PieceValues[piece] * len(board.pieces(piece, not board.turn))
        positional_piece_count_self += np.sum(PieceTables[piece][::1 - 2 * board.turn][list(board.pieces(piece, board.turn))])
        positional_piece_count_other += np.sum(PieceTables[piece][::1 - 2 * (not board.turn)][list(board.pieces(piece, not board.turn))])
    # endgame = endgame_factor(piece_count_self, piece_count_other)
    # kings = king_safety(board, board.turn, endgame) - king_safety(board, not board.turn, endgame)
    # pawns = pawn_structure(board, board.turn, endgame) - pawn_structure(board, not board.turn, endgame)
    return Eval.create(
        piece_count_self - piece_count_other +
        positional_piece_count_self - positional_piece_count_other
        # kings +
        # pawns
    )