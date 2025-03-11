import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch

class EvaluationBenchmark:
    @staticmethod
    def play_tactic_game(difficulty: int, engine_depth: int) -> tuple:
        tactic_count = 0
        board = chess.Board()
        tactics_engine_turn = chess.BLACK
        tactics_engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board, tactics_engine_turn, False)
        tactics_engine.set_difficulty(difficulty)
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        engine.configure({"Threads": 8})
        game_string = ""

        while not board.is_game_over():
            if tactics_engine_turn:
                if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                    tactic_count += 1

                move = tactics_engine.play_move()
                board.push(move)
                game_string += move.uci() + " "
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))
                board.push(result.move)
                if tactics_engine.current_tactic:
                    if tactics_engine.current_tactic.next_move() != move \
                    or tactics_engine.current_tactic.index > tactics_engine.current_tactic.max_index:
                        tactics_engine.end_tactic()
                game_string += result.move.uci() + " "
            
            tactics_engine_turn = not tactics_engine_turn
        
        outcome = board.result()
        if outcome == "1-0":
            tactic_count += 1

        print(board.result())
        tactics_engine.close()
        engine.quit()

        return tactic_count, len(board.move_stack)

    @staticmethod
    def play_normal_game(benchmark_depth: int, engine_depth: int) -> tuple:
        tactic_count = 0
        board = chess.Board()
        engine = chess.engine.SimpleEngine.popen_uci(r"./stockfish-windows-x86-64-avx2.exe")
        engine.configure({"Threads": 8})
        game_string = ""

        while not board.is_game_over():
            if chess.BLACK:
                if TacticSearch.relative_pin(board) or TacticSearch.absolute_pin(board) or TacticSearch.fork(board):
                    tactic_count += 1

                result = engine.play(board, chess.engine.Limit(time=10.0, depth=benchmark_depth))
            else:
                result = engine.play(board, chess.engine.Limit(time=10.0, depth=engine_depth))

            board.push(result.move)
            game_string += result.move.uci() + " "

        outcome = board.result()
        if outcome == "1-0":
            tactic_count += 1

        print(board.result())
        engine.quit()

        return tactic_count, len(board.move_stack)

if __name__ == "__main__":
    evaluation = EvaluationBenchmark()
    difficulties = [0, 1, 2]
    benchmark_depths = [8, 12, 16]
    engine_depths = [8, 12, 16]
    cumultative_tactic_count1 = 0
    cumultative_move_count1 = 0
    cumultative_tactic_count2 = 0
    cumultative_move_count2 = 0

    for benchmark_depth in benchmark_depths:
        for engine_depth in engine_depths:
            print(benchmark_depth, engine_depth)
            tactic_count, move_count = evaluation.play_normal_game(benchmark_depth, engine_depth)
            print("Normal game tactic score: " + str(tactic_count / move_count) + "\n")
            cumultative_tactic_count1 += tactic_count
            cumultative_move_count1 += move_count

    for difficulty in difficulties:
        for engine_depth in engine_depths:
            print(difficulty, engine_depth)
            tactic_count, move_count = evaluation.play_tactic_game(difficulty, engine_depth)
            print("Tactic game tactic score: " + str(tactic_count / move_count) + "\n")
            cumultative_tactic_count2 += tactic_count
            cumultative_move_count2 += move_count

    score1 = (cumultative_tactic_count1 / cumultative_move_count1) * 100
    score2 = (cumultative_tactic_count2 / cumultative_move_count2) * 100
    print(f"Percentage of tactics (Benchmark): {score1}%") 
    print(f"Percentage of tactics (Tactic Engine): {score2}%")