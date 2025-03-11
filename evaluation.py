import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class EvaluationBenchmark:
    @staticmethod
    def play_tactic_game(difficulty: int, engine_depth: int) -> int:
        tactic_count = 0
        board = chess.Board()
        tactics_engine_turn = chess.WHITE
        tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board, tactics_engine_turn, False)
        tactics_engine.set_difficulty(difficulty)
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        game_string = ""

        while not board.is_game_over():
            if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                tactic_count += 1

            if tactics_engine_turn:
                move = tactics_engine.play_move()
                board.push(move)
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))
                board.push(result.move)
                if tactics_engine.current_tactic:
                    if tactics_engine.current_tactic.next_move() != move \
                    or tactics_engine.current_tactic.index > tactics_engine.current_tactic.max_index:
                        tactics_engine.end_tactic()
            
            game_string += result.move.uci() + " "
            tactics_engine_turn = not tactics_engine_turn

        print(game_string + "\n")
        print(board.result())
        tactics_engine.close()
        engine.quit()

        return tactic_count

    @staticmethod
    def play_normal_game(benchmark_depth: int, engine_depth: int) -> int:
        tactic_count = 0
        board = chess.Board()
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        game_string = ""

        while not board.is_game_over():
            if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                tactic_count += 1

            if chess.WHITE:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=benchmark_depth))
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))

            board.push(result.move)
            game_string += result.move.uci() + " "

        print(game_string + "\n")
        print(board.result())
        engine.quit()

        return tactic_count

if __name__ == "__main__":
    evaluation = EvaluationBenchmark()
    difficulties = [0, 1, 2]
    benchmark_depths = [8, 12, 16]
    engine_depths = [5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18]

    for benchmark_depth in benchmark_depths:
        for engine_depth in engine_depths:
            print(benchmark_depth, engine_depth)
            tactic_count = evaluation.play_normal_game(benchmark_depth, engine_depth)
            print("Normal game tactic count: " + str(tactic_count) + "\n")