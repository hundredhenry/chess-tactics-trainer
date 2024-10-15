import chess
import chess.engine

class Engine:
    def __init__(self, engine_path, board):
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.board = board

    def find_move(self, time_limit):
        result = self.engine.play(self.board, chess.engine.Limit(time=time_limit))

        return result.move
    
    def close(self):
        self.engine.quit()