import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class EvaluationBenchmark:
    @staticmethod
    def play_tactic_game(difficulty: int, engine_depth: int, benchmark_colour: bool) -> tuple:
        tactic_count = 0
        board = chess.Board()
        tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-bmi2.exe", board, benchmark_colour, False)
        tactics_engine.set_difficulty(difficulty)
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-bmi2.exe")
        engine.configure({"Threads": 8})

        while not board.is_game_over():
            if board.turn == benchmark_colour:
                if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                    tactic_count += 1

                move = tactics_engine.play_move()
                board.push(move)
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))
                board.push(result.move)
                if tactics_engine.current_tactic:
                    if tactics_engine.current_tactic.next_move() != move \
                    or tactics_engine.current_tactic.index > tactics_engine.current_tactic.max_index:
                        tactics_engine.end_tactic()
        
        print(board.result())
        tactics_engine.close()
        engine.quit()

        return tactic_count, len(board.move_stack)

    @staticmethod
    def play_normal_game(benchmark_depth: int, engine_depth: int, benchmark_colour: bool) -> tuple:
        tactic_count = 0
        board = chess.Board()
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-bmi2.exe")
        engine.configure({"Threads": 8})

        while not board.is_game_over():
            if board.turn == benchmark_colour:
                if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                    tactic_count += 1

                result = engine.play(board, chess.engine.Limit(time=10.0, depth=benchmark_depth))
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))

            board.push(result.move)

        print(board.result())
        engine.quit()

        return tactic_count, len(board.move_stack)

if __name__ == "__main__":
    evaluation = EvaluationBenchmark()
    difficulties = [0, 1, 2]
    benchmark_depths = [6, 10, 14]
    engine_depths = [6, 8, 10, 12, 14, 16, 18]
    benchmark_colours = [True, False]
    cumultative_tactic_count1 = 0
    cumultative_move_count1 = 0
    cumultative_tactic_count2 = 0
    cumultative_move_count2 = 0

    for benchmark_colour in benchmark_colours:
        for benchmark_depth in benchmark_depths:
            for engine_depth in engine_depths:
                print(benchmark_depth, engine_depth, benchmark_colour)
                tactic_count, move_count = evaluation.play_normal_game(benchmark_depth, engine_depth, benchmark_colour)
                print(f"Tactic Count: {tactic_count}")
                print(f"Tactic Proportion: {(tactic_count / move_count) * 100}%\n")
                cumultative_tactic_count1 += tactic_count
                cumultative_move_count1 += move_count

    for benchmark_colour in benchmark_colours:
        for difficulty in difficulties:
            for engine_depth in engine_depths:
                print(difficulty, engine_depth, benchmark_colour)
                tactic_count, move_count = evaluation.play_tactic_game(difficulty, engine_depth, benchmark_colour)
                print(f"Tactic Count: {tactic_count}")
                print(f"Tactic Proportion: {(tactic_count / move_count) * 100}%\n")
                cumultative_tactic_count2 += tactic_count
                cumultative_move_count2 += move_count

    score1 = (cumultative_tactic_count1 / cumultative_move_count1) * 100
    score2 = (cumultative_tactic_count2 / cumultative_move_count2) * 100
    print(f"Percentage of Tactics (Benchmark): {score1}%") 
    print(f"Percentage of Tactics (Tactic Engine): {score2}%")