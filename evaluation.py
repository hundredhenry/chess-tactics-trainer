import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class Evaluation:
    def play_tactic_game(self):
        self.tactic_count = 0
        board = chess.Board()
        tactics_engine_turn = chess.WHITE
        tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board, tactics_engine_turn, False)
        tactics_engine.set_difficulty(1)
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")

        while not board.is_game_over():
            if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                print("Tactic Found")
                self.tactic_count += 1

            if tactics_engine_turn:
                move = tactics_engine.play_move()
                board.push(move)
                print(move)
            else:
                result = engine.play(board, chess.engine.Limit(time=1.0, depth=8))
                board.push(result.move)
                if tactics_engine.current_tactic:
                    if tactics_engine.current_tactic.next_move() != move \
                    or tactics_engine.current_tactic.index > tactics_engine.current_tactic.max_index:
                        tactics_engine.end_tactic()
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

            if chess.WHITE:
                result = engine.play(board, chess.engine.Limit(time=1.0, depth=15))
            else:
                result = engine.play(board, chess.engine.Limit(time=1.0, depth=8))

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