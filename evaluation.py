import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class Evaluation:
    def play_tactic_game(self):
        self.tactic_count = 0
        board = chess.Board()
        tactics_engine_turn = chess.WHITE
        tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board, tactics_engine_turn)
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        tactic_stack = []

        while not board.is_game_over():
            if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                    print("Tactic Found")
                    self.tactic_count += 1

            if tactics_engine_turn:
                if len(tactic_stack) >= 2:
                    expected_move = tactic_stack.pop()
                    if board.peek() != expected_move:
                        tactic_stack = tactics_engine.play_move()
                else:
                    tactic_stack = tactics_engine.play_move()

                move = tactic_stack.pop()
                board.push(move)
                print(move)
            else:
                result = engine.play(board, chess.engine.Limit(time=1.0, depth=8))
                board.push(result.move)
                print(result.move)

            tactics_engine_turn = not tactics_engine_turn

        print(board.result())
        tactics_engine.close()
        engine.quit()

    def play_normal_game(self):
        self.tactic_count = 0
        board = chess.Board()
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")

        while not board.is_game_over():
            if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                print("Tactic Found")
                self.tactic_count += 1

            result = engine.play(board, chess.engine.Limit(time=1.0, depth=12))
            board.push(result.move)
            print(result.move)

        print(board.result())
        engine.quit()

if __name__ == "__main__":
    evaluation = Evaluation()
    evaluation.play_normal_game()
    normal_tactic_count = evaluation.tactic_count
    evaluation.play_tactic_game()
    modified_tactic_count = evaluation.tactic_count
    print(f"Normal Tactic Count: {normal_tactic_count}")
    print(f"Modified Tactic Count: {modified_tactic_count}")