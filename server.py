from flask import Flask, render_template, request, url_for, redirect
from flask_socketio import SocketIO
import chess
import chess.pgn
from time import sleep
import io
from engine.engine import Engine
from engine.evaluation import Eval

app = Flask('Chess')
socketio = SocketIO(app)

@app.route('/')
def main():
    global engine
    fen = request.args.get('fen')
    if fen:
        engine.stop()
        del engine
        engine = Engine(chess.Board(fen), callback)
        engine.start()
        return redirect(url_for('main'))
    pgn = request.args.get('pgn')
    if pgn:
        engine.stop()
        del engine
        pgn = io.StringIO(pgn)
        engine = Engine(chess.pgn.read_game(pgn).end().board(), callback)
        engine.start()
        return redirect(url_for('main'))
    return render_template('main.html')

@socketio.on('update')
def update(data=None):
    pgn = str(chess.pgn.Game.from_board(engine.board))
    pgn = pgn[pgn.find('1. '):]
    socketio.emit(
        'update',
        dict(
            legal_moves = list(map(lambda move: move.uci(), engine.board.legal_moves)),
            turn = engine.board.turn,
            fen = engine.board.fen(),
            pgn = pgn,
            game_over = engine.board.is_game_over(),
            eval = Eval.str(engine.evaluation),
            depth = engine.depth
        )
    )

@socketio.on('move')
def move(data):
    engine.push(data)

@socketio.on('engine_move')
def engine_move(data):
    sleep(float(data) * (not engine.has_instant_move))
    engine.move()
    socketio.emit(
        'engine_move',
        ''
    )

def callback():
    print(engine.times)
    print(engine.moves)
    print(Eval.str(engine.evaluation))

if __name__ == '__main__':
    engine = Engine(chess.Board(), callback)
    engine.start()
    socketio.run(app, debug=True)
    