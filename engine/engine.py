from chess.svg import board
from engine.misc import *
from engine.config import *
from engine.evaluation import *
import chess
import chess.polyglot
import chess.syzygy
import multiprocessing as mp
import random
import time


class Engine:
    def __init__(self, board=None, callback=None):
        self.board = board or chess.Board()
        self.manager = mp.Manager()
        self.transposition_table = self.manager.dict()
        self.e = mp.Value('i', 0)
        self.d = mp.Value('i', 0)
        self.m = mp.Array('c', bytes(';' * 1024, 'utf-8'))
        self.t = mp.Array('c', bytes(';' * 1024, 'utf-8'))
        self.root_process = None
        self.tablebase = chess.syzygy.open_tablebase(tablebase_file)

        self.alpha = Eval.create(0) if self.board.fen() == 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' else Eval.NINF
        self.beta = Eval.create(50) if self.board.fen() == 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1' else Eval.INF

        self.callback = callback
    
    def start(self):
        self.root_process = mp.Process(
            target=Engine.search,
            args=(
                self.board.copy(),self.e, self.d, self.m, self.t,
                self.transposition_table, self.tablebase, self.alpha, self.beta, self.callback
            )
        )
        self.root_process.start()
    
    def stop(self):
        self.root_process.terminate()

    def push(self, move):
        self.stop()
        if self.board.turn == chess.WHITE:
            self.alpha = Eval.NINF
            self.beta = Eval.aspiration(self.e.value, 50)
        else:
            self.alpha = -Eval.aspiration(-self.e.value, 50)
            self.beta = Eval.INF
        self.board.push_uci(move)
        self.start()
    
    def move(self):
        self.push(move := (Engine.opening_move(self.board) or self.moves[0]))
        return move

    @property
    def times(self):
        result = self.t.value.decode().split(';')[:-1]
        if len(result) == 1024: return []
        return list(map(float, result))

    @property
    def evaluation(self):
        return self.e.value
    
    @property
    def depth(self):
        return self.d.value
    
    @property
    def moves(self):
        result = self.m.value.decode().split(';')[:-1]
        if len(result) == 1024: return []
        return result

    @property
    def has_instant_move(self):
        return Engine.opening_move(self.board) != None or self.tablebase.get_dtz(self.board) != None

    @staticmethod
    def search(board, evaluation, depth, moves, times, transposition_table, tablebase, alpha=Eval.NINF, beta=Eval.INF, callback=None):
        d = 0
        start_time = time.time()
        new_times = []
        while True:
            if board.turn == chess.WHITE:
                evaluation.value, new_moves = Engine.negamax(board, d, transposition_table, tablebase, alpha, beta)
            else:
                evaluation.value, new_moves = Engine.negamax(board, d, transposition_table, tablebase, alpha, beta)
                evaluation.value = -evaluation.value
            moves.value = bytes(';'.join(new_moves) + ';', 'utf-8')
            depth.value = d
            new_times.append(str(time.time() - start_time))
            times.value = bytes(';'.join(new_times) + ';', 'utf-8')
            d += 1
            if callback: callback()

    @staticmethod
    def negamax(board, depth, transposition_table, tablebase, alpha=Eval.NINF, beta=Eval.INF):
        alpha_original = alpha
        if (transposition := transposition_table.get(hash := chess.polyglot.zobrist_hash(board))) != None and transposition[0] >= depth:
            if transposition[2] == 0:
                return transposition[1], transposition[3]
            elif transposition[2] == -1:
                alpha = max(alpha, transposition[1])
            else:
                beta = min(beta, transposition[1])
            if alpha >= beta:
                return transposition[1], []
        
        if depth == 0 or board.outcome() != None:
            return Engine.quiesce(board, alpha, beta, tablebase), []
        
        evaluation = Eval.NINF
        moves = []
    
        for move in Engine.order_moves(board, board.legal_moves):
            board.push(move)
            new_evaluation, new_moves = Engine.negamax(board, depth - 1, transposition_table, tablebase, -Eval.change_depth(beta, -1), -Eval.change_depth(alpha, -1))
            board.pop()
            if evaluation < (new_evaluation := -Eval.change_depth(new_evaluation, 1)):
                evaluation = new_evaluation
                moves = [move.uci()] + new_moves
                if alpha < evaluation:
                    alpha = evaluation
                    if beta <= alpha:
                        evaluation = beta
                        break
        
        if evaluation <= alpha_original:
            transposition_table[hash] = (depth, evaluation, 1, moves)
        elif evaluation >= beta:
            transposition_table[hash] = (depth, evaluation, -1, moves)
        else:
            transposition_table[hash] = (depth, evaluation, 0, moves)

        return evaluation, moves
    
    def quiesce(board, alpha, beta, tablebase):
        if board.outcome() != None:
            return evaluate(board, tablebase)
        evaluation = evaluate(board, tablebase)
        if evaluation >= beta: return beta
        if alpha < evaluation:
            alpha = evaluation
        for move in Engine.order_moves(board, board.legal_moves):
            if not Engine.is_quiesce_move(board, move): continue
            board.push(move)
            new_evaluation = -Eval.change_depth(Engine.quiesce(board, -Eval.change_depth(beta, -1), -Eval.change_depth(alpha, -1), tablebase), 1)
            board.pop()
            if evaluation < new_evaluation:
                evaluation = new_evaluation
                if alpha < evaluation:
                    alpha = evaluation
                    if beta <= alpha:
                        evaluation = beta
                        break
        return evaluation

    @staticmethod
    def order_moves(board, moves):
        def sort_key(move):
            moving_piece = board.piece_type_at(move.from_square)
            captured_piece = board.piece_type_at(move.to_square)
            score = (MoveOrdering.CAPTURED_PIECE * PieceValues[captured_piece] - PieceValues[moving_piece]) * (captured_piece != None)
            score += PieceValues[move.promotion]
            score += MoveOrdering.ATTACKERS * len(board.attackers(board.turn, move.to_square)) - len(board.attackers(not board.turn, move.to_square))
            return -score
        return sorted(moves, key=sort_key)
    
    @staticmethod
    def is_quiesce_move(board, move):
        if board.gives_check(move) or board.is_check(): return True
        board.push(move)
        move_count = board.legal_moves.count()
        board.pop()
        if move_count <= Quiesce.FORCING_MOVES: return True
        if not board.is_capture(move): return False
        return PieceValues[board.piece_type_at(move.to_square)] - PieceValues[board.piece_type_at(move.from_square)] >= Quiesce.CAPTURE_THRESHOLD
    
    @staticmethod
    def opening_move(board):
        with chess.polyglot.open_reader(opening_book_file) as reader:
            book = np.array([[entry.move, entry.weight] for entry in reader.find_all(board)])
        if len(book) == 0: return
        move = random.choices(book[:,0], weights=book[:,1])
        return move[0].uci()