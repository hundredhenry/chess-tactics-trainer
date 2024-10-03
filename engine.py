import chess
import chess.engine

class ChessEngine:
    def __init__(self, engine_path):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)

    def get_best_move(self, board, time_limit=1.0):
        result = self.engine.play(board, chess.engine.Limit(time=time_limit))
        
        return result.move

    def evaluate_board(self, board, time_limit=1.0):
        result = self.engine.analyse(board, chess.engine.Limit(time=time_limit))

        return result["score"].relative.score() / 100

    def close(self):
        self.engine.quit()

if __name__ == "__main__":
    engine_path = "stockfish-windows-x86-64-avx2.exe"
    board = chess.Board()
    engine = ChessEngine(engine_path)

    print("Initial Board:")
    print(board)

    move = engine.get_best_move(board)
    print(f"Best move: {move}")

    board.push(move)
    print("Board after move:")
    print(board)

    score = engine.evaluate_board(board)
    print(f"Board evaluation: {score}")

    engine.close()