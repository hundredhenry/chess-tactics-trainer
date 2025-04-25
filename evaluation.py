import chess
import chess.engine
from engine import TacticsEngine
from engine import TacticSearch
import csv
import os

if os.name == 'nt':
    ENGINE_PATH = "./engines/stockfish-windows-x86-64-bmi2.exe"
elif os.name == 'posix':
    ENGINE_PATH = "./engines/stockfish-linux"

logical_core_count = os.cpu_count()
hash_size_per_core = 64  # MiB
max_hash_size = logical_core_count * hash_size_per_core
print(f"Logical Core Count: {logical_core_count}")
print(f"Max Hash Size: {max_hash_size} MiB")

class EvaluationBenchmark:
    @staticmethod
    def play_tactic_game(difficulty: int, benchmark_colour: bool) -> tuple:
        board = chess.Board()

        tactics_engine = TacticsEngine(ENGINE_PATH, board, benchmark_colour)
        tactics_engine.set_difficulty(difficulty)
        
        engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
        engine.configure({"Threads": logical_core_count, "Hash": max_hash_size, "Skill Level": 20})

        tactic_count = 0
        fork_count = 0
        skewer_count = 0
        absolute_pin_count = 0
        relative_pin_count = 0

        while not board.is_game_over():
            if board.turn == benchmark_colour:
                move = tactics_engine.play_move()

                if TacticSearch.fork(board, move):
                    tactic_count += 1
                    fork_count += 1
                elif TacticSearch.skewer(board, move):
                    tactic_count += 1
                    skewer_count += 1
                elif TacticSearch.absolute_pin(board, move):
                    tactic_count += 1
                    absolute_pin_count += 1
                elif TacticSearch.relative_pin(board, move):   
                    tactic_count += 1
                    relative_pin_count += 1

                board.push(move)
            else:
                result = engine.play(board, chess.engine.Limit(depth=20))
                board.push(result.move)

                if tactics_engine.current_tactic:
                    if tactics_engine.current_tactic.next_move() != move \
                    or tactics_engine.current_tactic.index > tactics_engine.current_tactic.max_index:
                        tactics_engine.end_tactic()
        
        tactics_engine.close()
        engine.quit()

        return board.result(), tactic_count, fork_count, skewer_count, absolute_pin_count, relative_pin_count, len(board.move_stack)

    @staticmethod
    def play_normal_game(benchmark_skill: int, benchmark_colour: bool) -> tuple:
        board = chess.Board()
        benchmark_engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
        benchmark_engine.configure({"Threads": logical_core_count, "Hash": max_hash_size, "Skill Level": benchmark_skill})

        test_engine = chess.engine.SimpleEngine.popen_uci(ENGINE_PATH)
        test_engine.configure({"Threads": logical_core_count, "Hash": max_hash_size, "Skill Level": 20})

        tactic_count = 0
        fork_count = 0
        skewer_count = 0
        absolute_pin_count = 0
        relative_pin_count = 0

        while not board.is_game_over():
            if board.turn == benchmark_colour:
                result = benchmark_engine.play(board, chess.engine.Limit(depth=18))
                
                if TacticSearch.fork(board, result.move):
                    tactic_count += 1
                    fork_count += 1
                elif TacticSearch.skewer(board, result.move):
                    tactic_count += 1
                    skewer_count += 1
                elif TacticSearch.absolute_pin(board, result.move):
                    tactic_count += 1
                    absolute_pin_count += 1
                elif TacticSearch.relative_pin(board, result.move):   
                    tactic_count += 1
                    relative_pin_count += 1
            else:
                result = test_engine.play(board, chess.engine.Limit(depth=20))
                
            board.push(result.move)

        benchmark_engine.quit()
        test_engine.quit()

        return board.result(), tactic_count, fork_count, skewer_count, absolute_pin_count, relative_pin_count, len(board.move_stack)
    
    @staticmethod
    def run_tactics_engine_benchmark():
        os.makedirs("benchmarks", exist_ok=True)

        csv_file = "benchmarks/tactics_engine_benchmark.csv"
        fieldnames = ["Difficulty", "Engine Colour", "Result", "Tactic Count", "Total Moves", "Tactics Percentage", "Fork Count", "Skewer Count", "Absolute Pin Count", "Relative Pin Count"]

        with open(csv_file, mode="w", newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            difficulties = [0, 1, 2]
            colours = [chess.WHITE, chess.BLACK]
            games_per_config = 5

            print("Running Tactics Engine Benchmark...")

            for difficulty in difficulties:
                difficulty_name = ["Easy", "Medium", "Hard"][difficulty]
                print(f"Testing Difficulty: {difficulty_name}")

                for colour in colours:
                    colour_name = "White" if colour == chess.WHITE else "Black"
                    print(f"Testing Engine Colour: {colour_name}")

                    for game_num in range(1, games_per_config + 1):
                        print(f"Game {game_num} of {games_per_config}...")

                        result, tactic_count, fork_count, skewer_count, absolute_pin_count, relative_pin_count, total_moves = EvaluationBenchmark.play_tactic_game(difficulty, colour)
                        tactics_percentage = (tactic_count / total_moves) * 100 if total_moves > 0 else 0
                        writer.writerow({
                            "Difficulty": difficulty_name,
                            "Engine Colour": colour_name,
                            "Result": result,
                            "Tactic Count": tactic_count,
                            "Total Moves": total_moves,
                            "Tactics Percentage": tactics_percentage,
                            "Fork Count": fork_count,
                            "Skewer Count": skewer_count,
                            "Absolute Pin Count": absolute_pin_count,
                            "Relative Pin Count": relative_pin_count
                        })

        print("Tactics Engine Benchmark completed!")

    @staticmethod
    def run_normal_engine_benchmark():
        os.makedirs("benchmarks", exist_ok=True)

        csv_file = "benchmarks/normal_engine_benchmark.csv"
        fieldnames = ["Skill Level", "Engine Colour", "Result", "Tactic Count", "Total Moves", "Tactics Percentage", "Fork Count", "Skewer Count", "Absolute Pin Count", "Relative Pin Count"]

        with open(csv_file, mode="w", newline='') as file:
            writer = csv.DictWriter(file, fieldnames=fieldnames)
            writer.writeheader()

            benchmark_skills = [1, 5, 10]  # Skill levels from 0 to 20
            colours = [chess.WHITE, chess.BLACK]
            games_per_config = 5

            print("Running Normal Engine Benchmark...")

            for skill in benchmark_skills:
                print(f"Testing Skill Level: {skill}")

                for colour in colours:
                    colour_name = "White" if colour == chess.WHITE else "Black"
                    print(f"Testing Engine Colour: {colour_name}")

                    for game_num in range(1, games_per_config + 1):
                        print(f"Game {game_num} of {games_per_config}...")

                        result, tactic_count, fork_count, skewer_count, absolute_pin_count, relative_pin_count, total_moves = EvaluationBenchmark.play_normal_game(skill, colour)
                        tactics_percentage = (tactic_count / total_moves) * 100 if total_moves > 0 else 0
                        writer.writerow({
                            "Skill Level": skill,
                            "Engine Colour": colour_name,
                            "Result": result,
                            "Tactic Count": tactic_count,
                            "Total Moves": total_moves,
                            "Tactics Percentage": tactics_percentage,
                            "Fork Count": fork_count,
                            "Skewer Count": skewer_count,
                            "Absolute Pin Count": absolute_pin_count,
                            "Relative Pin Count": relative_pin_count
                        })

        print("Normal Engine Benchmark completed!")                        

if __name__ == "__main__":
    # Run the benchmarks
    EvaluationBenchmark.run_normal_engine_benchmark()
    EvaluationBenchmark.run_tactics_engine_benchmark()

    print("All benchmarks completed!")

