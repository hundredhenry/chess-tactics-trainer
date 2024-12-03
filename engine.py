import chess
import chess.engine
import random

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board) -> None:
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.engine_colour = chess.BLACK
        self.pv = 3
        self.fails = 3
        self.tactics_probability = 1.0

    def play_move(self, time_limit: float = 1.0, depth: int = 18) -> list:        
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
                # Play the worst move if no tactic found
                analysis = self.engine.analyse(self.board, chess.engine.Limit(time=time_limit, depth=depth), multipv=self.pv)
                return [analysis[-1]["pv"][0]]
        
        # Fallback to standard engine analysis
        analysis = self.engine.analyse(self.board, chess.engine.Limit(time=time_limit, depth=depth))
        return [analysis["pv"][0]]

    def start_tactic_search(self, time_limit: float, depth: int) -> list:
        limit = chess.engine.Limit(time = time_limit, depth = depth)
        search_depth = 10
        tactic_pv = self.tactic_search(self.board, limit, search_depth)
        print(tactic_pv)

        return tactic_pv[::-1]
    
    def tactic_search(self, board: chess.Board, limit: chess.engine.Limit, search_depth: int) -> list:
        if search_depth == 0 or board.is_game_over():
            return []

        # Generate principal variations for the current position
        analysis = self.engine.analyse(board, limit, multipv=self.pv)

        if board.turn != self.engine_colour:
            best_human_score = analysis[0]["score"].pov(board.turn).score()

            # Checkmate line for human or engine
            if best_human_score is None:
                return analysis[0]["pv"]

            second_human_score = analysis[1]["score"].pov(board.turn).score()

            # Human opponent's best move should be siginificantly better than other moves
            if best_human_score > second_human_score + 150:
                # Play the best move and search for tactics
                best_move = analysis[0]["pv"][0]
                temp_board = board.copy()
                temp_board.push(best_move)
                movestack = self.tactic_search(temp_board, limit, search_depth - 1)
                if movestack:
                    return [best_move] + movestack
            
            return []
        
        best_score = analysis[0]["score"].pov(self.engine_colour).score()
        # Checkmate line for human or engine
        if best_score is None:
            return analysis[0]["pv"]
        
        # Check for a tactic for the engine to influence towards
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score()
            tactic_index = self.pv_tactic_check(board, pv)

            # If a tactic is found and the computer response is reasonable, return the tactic
            if tactic_index and score > best_score - 40 and score < -150:
                return pv[:tactic_index + 1]

            # If no tactic is found in initial PV, play the move and search for tactics
            temp_board = board.copy()
            temp_board.push(pv[0])
            movestack = self.tactic_search(temp_board, limit, search_depth - 1)
            if movestack:
                return [pv[0]] + movestack

        return []
        
    def pv_tactic_check(self, board: chess.Board, pv: list) -> chess.Board:
        temp_board = board.copy()

        for index in range(len(pv)):
            temp_board.push(pv[index])

            # Check if engine is to move
            if temp_board.turn != self.engine_colour:
                continue

            # Check if engine is in a fork
            fork = Tactic.fork(temp_board)
            if len(fork):
                print("Fork")
                return index

            pin = Tactic.absolute_pin(temp_board)
            # Check if engine is in a pin
            if len(pin):
                print("Pin")
                return index
            
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
            forking_piece = board.piece_at(move.to_square)
            # Check that the value of the forking piece is equal to or less than the value of the defended piece
            if PIECE_VALUES[forking_piece.piece_type] <= PIECE_VALUES[board.piece_at(square).piece_type]:
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