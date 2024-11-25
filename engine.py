import chess
import chess.engine
import random

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board) -> None:
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.engine_colour = chess.BLACK
        self.pv = 3
        self.fails = 0
        self.tactics_probability = 0.3

    def play_move(self, time_limit: float = 1.0, depth: int = 5) -> list:        
        # Try tactical play based on probability
        if random.random() < self.tactics_probability:
            tactic_moves = self.start_tactic_search(time_limit, depth)
            if len(tactic_moves):
                # Reset fails, reduce probability and return tactic moves
                self.fails = 0
                return tactic_moves
            else:
                # Increase probability for next attempt if no tactic found
                self.fails += 1
                self.tactics_probability = min(0.8, self.tactics_probability + 0.1 * self.fails)
                # Play worst move if no tactic found
                analysis = self.engine.analyse(self.board, chess.engine.Limit(time=time_limit, depth=depth), multipv=self.pv)
                return [analysis[len(analysis) - 1]["pv"][0]]
        
        # Fallback to standard engine analysis
        analysis = self.engine.analyse(self.board, chess.engine.Limit(time=time_limit, depth=depth))
        return [analysis["pv"][0]]

    def start_tactic_search(self, time_limit: float, depth: int) -> list:
        limit = chess.engine.Limit(time = time_limit, depth = depth)
        tactic_pv = self.tactic_search(self.board, limit, depth)

        return tactic_pv[::-1]
    
    def tactic_search(self, board: chess.Board, limit: chess.engine.Limit, depth: int) -> list:
        if depth == 0 or board.is_game_over():
            return []

        analysis = self.engine.analyse(board, limit, multipv=self.pv)
        best_score = analysis[0]["score"].pov(self.engine_colour).score()

        if board.turn != self.engine_colour:
            best_move = analysis[0]["pv"][0]
            temp_board = board.copy()
            temp_board.push(best_move)
            movestack = self.tactic_search(temp_board, limit, depth - 1)
            if movestack:
                return [best_move] + movestack
            else:
                return []
        
        # Check for a tactic for the engine to influence towards
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score()
            tactic = self.pv_tactic_check(board, pv)

            # If a tactic is found and the tactic gives an advantage of 100 centipawns over the best move, play the tactic
            if tactic and score < best_score - 100:
                return pv

            # If no tactic is found in initial PV, play the move and search for tactics
            temp_board = board.copy()
            temp_board.push(pv[0])
            movestack = self.tactic_search(temp_board, limit, depth - 1)
            if movestack:
                print([pv[0]] + movestack)
                return [pv[0]] + movestack

        return []
        
    def pv_tactic_check(self, board: chess.Board, pv: list) -> chess.Board:
        temp_board = board.copy()

        for move in pv:
            temp_board.push(move)

            # Check if engine is in checkmate
            if temp_board.is_checkmate():
                print("Checkmate")
                return temp_board

            # Check if engine is in a fork
            fork = Tactic.fork(temp_board)
            if len(fork):
                print("Fork")
                return temp_board

            pin = Tactic.absolute_pin(temp_board)
            # Check if engine is in a pin
            if len(pin):
                print("Pin")
                return temp_board
            
        return None

    def close(self) -> None:
        self.engine.quit()

class Tactic:
    @staticmethod
    def absolute_pin(board: chess.Board) -> list:
        if not board.move_stack:
            return []

        pinned_pieces = []
        # Previous position
        last_position = board.copy()
        last_position.pop()

        # Search through all pieces
        for square in chess.scan_reversed(board.occupied_co[board.turn]):
            piece = board.piece_at(square)
            # Skip king
            if piece.piece_type == chess.KING or piece.piece_type == chess.PAWN:
                continue
            # If the pin was not present in the last position, move is a pin
            if board.is_pinned(board.turn, square) and not last_position.is_pinned(board.turn, square):
                # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                if all(move.from_square != square for move in board.legal_moves):
                    attackers = board.attackers(not board.turn, square)
                    defenders = board.attackers(board.turn, square)
                    if len(attackers) >= len(defenders):
                        pinned_pieces.append(square)

        return pinned_pieces
    
    @staticmethod
    def fork(board: chess.Board) -> list:
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        move = board.peek()

        # Check if the square the forking piece has moved to is defended
        if len(board.attackers(board.turn, move.to_square)):
            return []

        # Check the pieces that the forking piece is attacking
        attacked_pieces = board.attacks(move.to_square) & board.occupied_co[board.turn] 
        # Attacking less than two pieces, not a fork
        if len(attacked_pieces) < 2:
            return []
        
        # Check if the attacked pieces are defended
        forked_squares = []
        for square in attacked_pieces:
            attackers = board.attackers(not board.turn, square)
            defenders = board.attackers(board.turn, square)
            if len(attackers) > len(defenders):
                forked_squares.append(square)
        # Attacking less than two undefended pieces, not a fork
        if len(forked_squares) < 2:
            return []

        return forked_squares

if __name__ == "__main__":
    board = chess.Board("3n2k1/p4r1p/1pR1p1p1/5q2/3P4/4QP2/P3N1P1/6K1 w - - 0 1")
    engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board)
    temp_board = board.copy()
    engine.close()