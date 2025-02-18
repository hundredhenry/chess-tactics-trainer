import chess
import chess.engine

PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

TACTIC_TYPES = {
    "Checkmate": 0,
    "Fork": 1,
    "Absolute Pin": 2,
    "Relative Pin": 3
}

class Tactic:
    def __init__(self, pv: list, type: int) -> None:
        self.pv = pv
        self.type = type
        self.index = 0

    def next_move(self) -> chess.Move:
        move = self.pv[self.index]
        self.index += 1
        return move
    
    def hint_move(self) -> chess.Move:
        return self.pv[self.index]
    
    def moves_left(self) -> int:
        return (len(self.pv) - self.index + 1) // 2

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board, engine_colour: chess.Color) -> None:
        self.board = board
        self.engine_path = engine_path
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.engine_colour = engine_colour
        self.current_tactic = None
        self.default_depth = 10
        self.search_depth = self.default_depth
        self.tactic_cache = {}

    def set_difficulty(self, value: int) -> None:
        if value == 0:
            self.pv = 10
            self.engine_depth = 6
        elif value == 1:
            self.pv = 5
            self.engine_depth = 10
        else:
            self.pv = 3
            self.engine_depth = 15

        self.limit = chess.engine.Limit(time=5.0, depth=self.engine_depth)

    def play_move(self) -> chess.Move:
        if self.current_tactic:
            if self.current_tactic.index < len(self.current_tactic.pv) - 1:
                expected_move = self.current_tactic.next_move()
                if expected_move == self.board.peek():
                    return self.current_tactic.next_move()
            else:
                self.tactic_cache[self.board.fullmove_number] = self.current_tactic
                self.current_tactic = None

        analysis = self.engine.analyse(self.board, self.limit, multipv=self.pv)
        # Starts with the best move
        current_move = analysis[0]["pv"][0]
        best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
        # Checkmate line for engine
        if best_score > 5000:
            return analysis[0]["pv"][0]
        
        # Check if there is a second best move
        if len(analysis) == 1:
            return current_move
        else:
            second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)
        
        # Check if best move is significantly better
        if best_score >= second_score + 300:
            return current_move
        else:
            self.start_tactic_search()
            if self.current_tactic:
                self.search_depth = min(self.default_depth, self.search_depth - 2)
                return self.current_tactic.next_move()
            else:
                self.search_depth += 1
        
        # Find the least winning move
        for infodict in analysis[1:]:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            if score < 0:
                break
            else:
                current_move = pv[0]

        return current_move
    
    def undo_tactic_move(self) -> None:
        if self.current_tactic.index >= 2:
            self.current_tactic.index -= 2
        else:
            self.current_tactic = None

    def start_tactic_search(self) -> None:
        self.tactic_search(self.board, self.search_depth)
    
    def tactic_search(self, board: chess.Board, search_depth: int) -> list:
        # Base case for search depth
        if search_depth == 0 or board.is_game_over():
            return []

        # Generate principal variations for the current position
        min_pv = min(board.legal_moves.count(), self.pv)
        analysis = self.engine.analyse(board, self.limit, multipv=min_pv)
        if board.turn != self.engine_colour:
            return self.play_human_move(analysis, board, search_depth)
        
        best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
        # Checkmate line for human
        if best_score < -5000:
            self.current_tactic = Tactic(analysis[0]["pv"], TACTIC_TYPES["Checkmate"])
            return analysis[0]["pv"]
        
        # Check for a tactic for the engine to influence towards
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            
            # If a tactic is found and the tactic is winning, return the tactic
            tactic_index, tactic_type = self.pv_tactic_check(board, pv)
            if tactic_index >= 0 and score <= -200:
                self.current_tactic = Tactic(pv[:tactic_index + 1], tactic_type)
                return pv[:tactic_index + 1]

            # If no tactic is found in initial PV, play moves above a score cutoff to search for tactics
            if score >= best_score - 30:
                board.push(pv[0])
                movestack = self.tactic_search(board, search_depth - 1)
                board.pop()
                if movestack:
                    return [pv[0]] + movestack

        return []
    
    def play_human_move(self, analysis: dict, board: chess.Board, search_depth: int) -> list:
        best_score = analysis[0]["score"].pov(board.turn).score(mate_score=100000)
        # Return PV if checkmate line for human
        if best_score > 5000:
            self.current_tactic = Tactic(analysis[0]["pv"], TACTIC_TYPES["Checkmate"])
            return analysis[0]["pv"]

        # Check if there is a second best move
        if len(analysis) >= 2:
            second_score = analysis[1]["score"].pov(board.turn).score(mate_score=100000)

        # Check if best move is significantly better
        if len(analysis) == 1 or best_score >= second_score + 200:
            best_move = analysis[0]["pv"][0]
            board.push(best_move)
            tactic_moves = self.tactic_search(board, self.limit, search_depth - 1)
            board.pop()
            if tactic_moves:
                return [best_move] + tactic_moves
        
        return []
        
    def pv_tactic_check(self, board: chess.Board, pv: list) -> tuple:
        temp_board = board.copy(stack=False)

        for index, move in enumerate(pv):
            temp_board.push(move)

            # Skip if it's not engine's turn
            if temp_board.turn == self.engine_colour:
                # Check for any tactical patterns
                if TacticSearch.fork(temp_board):
                    return index, TACTIC_TYPES["Fork"]
                elif TacticSearch.absolute_pin(temp_board):
                    return index, TACTIC_TYPES["Absolute Pin"]
                elif TacticSearch.relative_pin(temp_board):
                    return index, TACTIC_TYPES["Relative Pin"]

        return -1, -1
    
    def reset_engine(self, board: chess.Board) -> None:
        self.engine.quit()
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.current_tactic = None
        self.search_depth = self.default_depth
        self.tactic_cache.clear()

    def close(self) -> None:
        self.engine.quit()

class TacticSearch:
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
                pin_mask = TacticSearch.relative_pin_mask(board, board.turn, pin_square, piece_square)
                last_pos_pin_mask = TacticSearch.relative_pin_mask(last_position, board.turn, pin_square, piece_square)
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