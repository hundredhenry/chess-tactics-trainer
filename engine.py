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
    def __init__(self, engine_path: str, board: chess.Board, engine_colour: chess.Color) -> None:
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.engine_colour = engine_colour
        self.pv = 5
        self.search_depth = 5

    def play_move(self) -> list:        
        # Try tactical play based on probability
        tactic_moves = self.start_tactic_search()
        if len(tactic_moves) > 0:
            # Reset search depth if tactic found
            self.search_depth -= 2
            return tactic_moves
        else:
            # Increase search depth if no tactic found
            self.search_depth += 1
            # Play random move if no tactic found
            analysis = self.engine.analyse(self.board, chess.engine.Limit(time=1.0, depth=15), multipv=self.pv)
            score = analysis[0]["score"].pov(self.engine_colour).score()
            if score is None:
                return analysis[0]["pv"][0]
            
            random_int = random.randint(0, len(analysis) - 1)
            print("No tactic found, playing random move:", analysis[random_int]["pv"][0])
            return [analysis[random_int]["pv"][0]]

    def start_tactic_search(self) -> list:
        limit = chess.engine.Limit(time=5.0, depth=12)
        tactic_pv = self.tactic_search(self.board, limit, self.search_depth)
        print("Tactic PV:", tactic_pv)

        return tactic_pv[::-1]
    
    def tactic_search(self, board: chess.Board, limit: chess.engine.Limit, search_depth: int) -> list:
        # Base case for search depth
        if search_depth == 0 or board.is_game_over():
            return []

        # Generate principal variations for the current position
        min_pv = min(board.legal_moves.count(), self.pv)
        analysis = self.engine.analyse(board, limit, multipv=min_pv)
        if board.turn != self.engine_colour:
            return self.play_human_move(analysis, board, limit, search_depth)
        
        best_score = analysis[0]["score"].pov(self.engine_colour).score()
        # Checkmate line for human or engine
        if best_score is None:
            return analysis[0]["pv"]
        
        # Check for a tactic for the engine to influence towards
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score()
            # Checkmate line, skip
            if score is None:
                continue
            
            # If a tactic is found and the tactic is winning, return the tactic
            tactic_index = self.pv_tactic_check(board, pv)
            if tactic_index and score < -100:
                return pv[:tactic_index + 1]

            # If no tactic is found in initial PV, play moves above a score cutoff to search for tactics
            if score > best_score - 30:
                board.push(pv[0])
                movestack = self.tactic_search(board, limit, search_depth - 1)
                board.pop()
                if movestack:
                    return [pv[0]] + movestack

        return []
    
    def play_human_move(self, analysis: dict, board: chess.Board, limit: chess.engine.Limit, search_depth: int) -> list:
        best_human_score = analysis[0]["score"].pov(board.turn).score()
        second_human_score = analysis[1]["score"].pov(board.turn).score() if len(analysis) > 1 else None

        # Checkmate line for human or engine or no second best move
        if best_human_score is None or second_human_score is None:
            return analysis[0]["pv"]

        # Human opponent's best move should be siginificantly better than other moves
        if best_human_score > second_human_score + 200:
            # Play the best move and search for tactics
            best_move = analysis[0]["pv"][0]
            board.push(best_move)
            movestack = self.tactic_search(board, limit, search_depth - 1)
            board.pop()
            if movestack:
                return [best_move] + movestack
        
        return []
        
    def pv_tactic_check(self, board: chess.Board, pv: list) -> chess.Board:
        temp_board = board.copy(stack=False)

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

            absolute_pin = Tactic.absolute_pin(temp_board)
            # Check if engine is in a pin
            if len(absolute_pin):
                print("Absolute Pin")
                return index
            
            relative_pin = Tactic.relative_pin(temp_board)
            # Check if engine is in a relative pin
            if len(relative_pin):
                print("Relative Pin")
                return index
            
        return None

    def close(self) -> None:
        self.engine.quit()

class Tactic:
    @staticmethod
    def relative_pin_mask(board: chess.Board, colour: chess.Color, square: chess.Square, piece: chess.Square) -> chess.Bitboard:      
        square_mask = chess.BB_SQUARES[square]

        for attacks, sliders in [(chess.BB_FILE_ATTACKS, board.rooks | board.queens),
                                (chess.BB_RANK_ATTACKS, board.rooks | board.queens),
                                (chess.BB_DIAG_ATTACKS, board.bishops | board.queens)]:
            rays = attacks[piece][0]
            if rays & square_mask:
                snipers = rays & sliders & board.occupied_co[not colour]
                for sniper in chess.scan_reversed(snipers):
                    if chess.between(piece, sniper) & (board.occupied | square_mask) == square_mask:
                        return chess.ray(piece, sniper)
                break

        return chess.BB_ALL

    @staticmethod
    def absolute_pin(board: chess.Board) -> list:
        if not board.move_stack:
            return []

        pinned_pieces = []
        pinning_move = board.peek()
        # Previous position
        last_position = board.copy()
        last_position.pop()

        # Filter out kings and pawns
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings & ~board.pawns

        # Search through all pieces
        for square in chess.scan_reversed(filtered_pieces):
            # If the pin was not present in the last position, move is a pin
            if board.is_pinned(board.turn, square) and not last_position.is_pinned(board.turn, square):
                # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                if all(move.from_square != square for move in board.legal_moves):
                    # Make sure the pinning piece is not attacked
                    if len(board.attackers(board.turn, pinning_move.to_square)) == 0:
                        pinned_pieces.append(square)

        return pinned_pieces
    
    @staticmethod
    def relative_pin(board: chess.Board) -> list:
        if not board.move_stack:
            return []
        
        pinned_pieces = []
        pinning_move = board.peek()
        # Previous position
        last_position = board.copy()
        last_position.pop()

        # Filter out kings and pawns
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings & ~board.pawns

        # Search through all valuable minor pieces
        for piece_square in chess.scan_reversed(filtered_pieces):
            piece = board.piece_at(piece_square)

            # Search through all potential pinned pieces
            for pin_square in chess.scan_reversed(filtered_pieces):
                # Skip if the piece is the same
                if piece_square == pin_square:
                    continue

                pinned = board.piece_at(pin_square)
                # Skip if the pinned piece is more valuable
                if PIECE_VALUES[pinned.piece_type] > PIECE_VALUES[piece.piece_type]:
                    continue

                # Check if the piece is pinned
                pin_mask = Tactic.relative_pin_mask(board, board.turn, pin_square, piece_square)
                last_pos_pin_mask = Tactic.relative_pin_mask(last_position, board.turn, pin_square, piece_square)
                # If the pin was not present in the last position, move is a pin
                if pin_mask != chess.BB_ALL and last_pos_pin_mask == chess.BB_ALL:
                    # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                    if all(move.from_square != piece_square for move in board.legal_moves):
                        # Make sure the pinning piece is not attacked
                        if len(board.attackers(board.turn, pinning_move.to_square)) == 0:
                            pinned_pieces.append(piece_square)

        return pinned_pieces
            
    
    @staticmethod
    def fork(board: chess.Board) -> list:
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        forking_move = board.peek()

        # Check if the square the forking piece has moved to is defended
        if len(board.attackers(board.turn, forking_move.to_square)):
            return []

        # Check the pieces that the forking piece is attacking
        attacked_pieces = board.attacks(forking_move.to_square) & board.occupied_co[board.turn] 
        # Attacking less than two pieces, not a fork
        if len(attacked_pieces) < 2:
            return []
        
        # Check if the attacked pieces are defended
        forked_squares = []
        for square in attacked_pieces:
            forking_piece = board.piece_at(forking_move.to_square)
            defenders = board.attackers(board.turn, square)
            # Check that the value of the forked piece is greater than the forking piece
            if PIECE_VALUES[board.piece_at(square).piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                forked_squares.append(square)
            # Or check that the forking piece is not defended
            elif len(defenders) == 0:
                forked_squares.append(square)

        # Attacking less than two undefended pieces, not a fork
        if len(forked_squares) < 2:
            return []

        return forked_squares

if __name__ == "__main__":
    board = chess.Board("8/5k2/8/6R1/4NP2/4B1K1/6Pr/8 b - - 0 1")
    engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board)
    engine.play_move()
    engine.close()