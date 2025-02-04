import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class Evaluation:
    def __init__(self):
        self.board = chess.Board()
        self.tactics_engine_turn = chess.WHITE
        self.engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        self.tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", self.board, self.tactics_engine_turn)
        self.tactic_stack = []
        self.tactic_count = 0

    def play_tactic_game(self):
        while not self.board.is_game_over():
            if TacticSearch.relative_pin(self.board) or TacticSearch.absolute_pin(self.board) or TacticSearch.fork(self.board):
                    print("Tactic Found")
                    self.tactic_count += 1

            if self.tactics_engine_turn:
                if len(self.tactic_stack) >= 2:
                    expected_move = self.tactic_stack.pop()
                    if self.board.peek() != expected_move:
                        self.tactic_stack = self.tactics_engine.play_move()
                else:
                    self.tactic_stack = self.tactics_engine.play_move()

                move = self.tactic_stack.pop()
                self.board.push(move)
            else:
                result = self.engine.play(self.board, chess.engine.Limit(time=1.0, depth=8))
                self.board.push(result.move)

            self.tactics_engine_turn = not self.tactics_engine_turn

        print(self.board.result())
        self.close()

    def play_normal_game(self):
        while not self.board.is_game_over():
            if TacticSearch.relative_pin(self.board) or TacticSearch.absolute_pin(self.board) or TacticSearch.fork(self.board):
                print("Tactic Found")
                self.tactic_count += 1

            result = self.engine.play(self.board, chess.engine.Limit(time=1.0, depth=12))
            self.board.push(result.move)

        print(self.board.result())
        self.close()

    def close(self):
        self.engine.quit()
        self.tactics_engine.close()

if __name__ == "__main__":
    evaluation = Evaluation()
    evaluation.play_normal_game()
    print("Tactic Count: ", evaluation.tactic_count)


        