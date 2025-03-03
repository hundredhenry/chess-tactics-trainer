import chess
import chess.engine

# Material values for each piece
PIECE_VALUES = {
    chess.PAWN: 100,
    chess.KNIGHT: 300,
    chess.BISHOP: 300,
    chess.ROOK: 500,
    chess.QUEEN: 900,
    chess.KING: 20000
}

# Tactic type with numeric identifiers
TACTIC_TYPES = {
    "Checkmate": 0,
    "Fork": 1,
    "Absolute Pin": 2,
    "Relative Pin": 3
}

class Tactic:
    """Represents a tactic with a sequence of moves and a tactic type"""

    def __init__(self, pv: list, type: int) -> None:
        """Initialize a tactic with a principal variation and type."""
        self.pv = pv
        self.type = type
        self.index = 0
        self.max_index = len(pv) - 1

    def next_move(self) -> chess.Move:
        """Get the next move in the tactic sequence and advance the index."""
        move = self.pv[self.index]
        self.index += 1
        print(self.index)
        return move
    
    def hint_move(self) -> chess.Move:
        """View the next move without advancing the index."""
        return self.pv[self.index]
    
    def moves_left(self) -> int:
        """Calculate the number of player moves remaining in the tactic."""
        return ((self.max_index - self.index) // 2) + 1

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board, engine_colour: chess.Color) -> None:
        """Initialize the tactics engine."""
        self.board = board
        self.engine_path = engine_path
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.engine_colour = engine_colour
        self.current_tactic = None
        self.search_depth = 8
        self.tactic_cache = {}
        self.tactic_types = list(TACTIC_TYPES.values())

        # Engine settings
        self.num_pv = None
        self.engine_depth = None
        self.limit = None

    def set_difficulty(self, value: int) -> None:
        """Configure engine parameters based on difficulty level."""
        # Easy
        if value == 0:
            self.num_pv = 5
            self.engine_depth = 6
        # Medium
        elif value == 1:
            self.num_pv = 3
            self.engine_depth = 10
        # Hard
        else:
            self.num_pv = 1
            self.engine_depth = 15

        self.limit = chess.engine.Limit(time=10.0, depth=self.engine_depth)

    def set_tactic_types(self, types: list[int]) -> None:
        """Set the types of tactics to search for."""
        self.tactic_types = types
    
    def _select_normal_move(self, analysis: list[dict], best_score: int) -> chess.Move:
        current_move = analysis[0]["pv"][0]

        """Selects the best move based on the position evaluation."""
        if len(analysis) == 1:
            return current_move
        
        second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)

        # If best move is significantly better, return it
        if best_score >= second_score + 300:
            return current_move
        
        # Otherwise, find the least winning move
        for infodict in analysis[1:]:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            if score < 0:
                break
            else:
                current_move = pv[0]

        return current_move

    def play_move(self) -> chess.Move:
        """Determine the move for the engine to play."""
        # Check if we're in the middle of a tactic
        if self.current_tactic:
            return self.current_tactic.next_move()

        num_pv = max(self.num_pv, 2)
        analysis = self.engine.analyse(self.board, self.limit, multipv=num_pv)
        best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
        # Checkmate line for engine
        if best_score > 5000:
            return analysis[0]["pv"][0]
        
        # Tactic search
        self.tactic_search()

        # Check if a tactic was found
        if self.current_tactic:
            return self.current_tactic.next_move()

        return self._select_normal_move(analysis, best_score)
    
    def undo_tactic_move(self) -> None:
        """Undo a tactic move."""
        if self.current_tactic.index >= 2:
            self.current_tactic.index -= 2
        elif self.current_tactic.index == 1:
            self.current_tactic.index -= 1
            self.tactic_cache[self.board.ply() + 2] = self.current_tactic
            self.current_tactic = None
        else:
            self.tactic_cache[self.board.ply()] = self.current_tactic
            self.current_tactic = None

    def _process_engine_moves(self, board: chess.Board, depth: int, sequence: list, mistake: bool, analysis: list[dict], search_stack: list, best_score: int) -> None:
        """Process engine moves in the search stack."""
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)

            # For initial position, consider deliberate mistakes to create tactical opportunities
            if depth == self.search_depth and not mistake:
                if -300 <= score < best_score - 100:
                    next_board = board.copy(stack=1)
                    next_board.push(pv[0])
                    search_stack.append((next_board, depth - 1, sequence + [pv[0]], True))
            # Otherwise, play normal moves (slightly suboptimal moves are acceptable)
            elif score >= best_score - 30:
                next_board = board.copy(stack=1)
                next_board.push(pv[0])
                search_stack.append((next_board, depth - 1, sequence + [pv[0]], mistake))

    def _process_player_moves(self, board: chess.Board, depth: int, sequence: list, mistake: bool, analysis: list[dict], search_stack: list, best_score: int) -> None:
        """Process player moves in the search stack."""
        best_move_clear = False

        if len(analysis) == 1:
            best_move_clear = True
        elif len(analysis) >= 2:
            second_score = analysis[1]["score"].pov(not self.engine_colour).score(mate_score=100000)
            best_move_clear = best_score >= second_score + 250

        # If there's a clear best move, check for tactics
        if best_move_clear:
            pv = analysis[0]["pv"]
            score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
            best_move = pv[0]
            
            next_board = board.copy(stack=1)
            next_board.push(best_move)

            # Check if the move leads to a tactic
            tactic_index, tactic_type = self._pv_tactic_check(next_board, pv[1:])
            
            if tactic_index >= 0 and score <= -250:
                self.current_tactic = Tactic(sequence + pv[:tactic_index + 1], tactic_type)
                return
            
            # Continue search if no tactic found
            search_stack.append((next_board, depth - 1, sequence + [best_move], mistake))

    def tactic_search(self, puzzle_mode: bool = False) -> None:
        """Search for tactical opportunities in the current position."""
        initial_board = self.board.copy(stack=1)
        # In puzzle mode, we start with the mistake already made
        initial_mistake = puzzle_mode
        search_stack = [(initial_board, self.search_depth, [], initial_mistake)]

        while search_stack:
            board, depth, sequence, mistake = search_stack.pop()
            # Base case for search - depth reached or game over
            if depth == 0 or board.is_game_over():
                continue

            # Generate principal variations for the current position
            if depth == self.search_depth and board.turn == self.engine_colour and not mistake:
                num_pv = board.legal_moves.count()
            else:
                num_pv = min(board.legal_moves.count(), self.num_pv)

            analysis = self.engine.analyse(board, self.limit, multipv=num_pv)
            best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
            # Engine getting checkmated line
            if best_score < -5000 and TACTIC_TYPES["Checkmate"] in self.tactic_types:
                self.current_tactic = Tactic(sequence + analysis[0]["pv"], TACTIC_TYPES["Checkmate"])
                break

            # Engine turn
            if board.turn == self.engine_colour:
                self._process_engine_moves(board, depth, sequence, mistake, analysis, search_stack, best_score)
            # Human turn
            else:
                self._process_player_moves(board, depth, sequence, mistake, analysis, search_stack, best_score)
        
    def _pv_tactic_check(self, board: chess.Board, pv: list) -> tuple:
        """Check if the given move sequence contains a tactical opportunity."""
        temp_board = board.copy(stack=1)

        for index, move in enumerate(pv):
            # Only check for tactics on the engine's turn
            if temp_board.turn == self.engine_colour:
                # Check for each type of tactic
                if TACTIC_TYPES["Fork"] in self.tactic_types:
                    forked_pieces = TacticSearch.fork(temp_board)
                    if forked_pieces:
                        return index, TACTIC_TYPES["Fork"]
                        
                if TACTIC_TYPES["Absolute Pin"] in self.tactic_types:
                    pinned_pieces = TacticSearch.absolute_pin(temp_board)
                    if pinned_pieces:
                        return index, TACTIC_TYPES["Absolute Pin"]
                        
                if TACTIC_TYPES["Relative Pin"] in self.tactic_types:
                    relative_pins = TacticSearch.relative_pin(temp_board)
                    if relative_pins:
                        return index, TACTIC_TYPES["Relative Pin"]
                
            # Apply the move and continue
            temp_board.push(move)

        return -1, -1
    
    def reset_engine(self, board: chess.Board, engine_colour: chess.Color) -> None:
        """Reset the engine with a new board and colour."""
        self.engine.quit()
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.engine_colour = engine_colour
        self.current_tactic = None
        self.tactic_cache.clear()

    def close(self) -> None:
        """Close the engine process."""
        self.engine.quit()

class TacticSearch:
    """Static methods for detecting different types of chess tactics."""

    @staticmethod
    def relative_pin_mask(board: chess.Board, colour: chess.Color, square: chess.Square, piece: chess.Square) -> chess.Bitboard:
        """Calculate the pin mask for a potential relative pin. Modified version of python-chess pin_mask method for absolute pins."""
        square_mask = chess.BB_SQUARES[square]

        for attacks, sliders in [(chess.BB_FILE_ATTACKS, board.rooks | board.queens),
                                (chess.BB_RANK_ATTACKS, board.rooks | board.queens),
                                (chess.BB_DIAG_ATTACKS, board.bishops | board.queens)]:
            rays = attacks[piece][0]
            if rays & square_mask:
                snipers = rays & sliders & board.occupied_co[not colour]
                for sniper in chess.scan_reversed(snipers):
                    # If the square is the only thing in between piece and sniper
                    if chess.between(piece, sniper) & (board.occupied | square_mask) == square_mask:
                        return chess.ray(piece, sniper)
                    
                break

        # No pin found
        return chess.BB_ALL

    @staticmethod
    def absolute_pin(board: chess.Board) -> list:
        """Detect absolute pins (pinned to king)."""
        if not board.move_stack:
            return []

        pinned_pieces = []
        pinning_move = board.peek()
        # Previous position
        last_position = board.copy()
        last_position.pop()
        # Find all pieces except kings
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings
        
        # Check each piece for a pin
        for square in chess.scan_reversed(filtered_pieces):
            # If the pin was not present in the last position, move is a new pin
            if board.is_pinned(board.turn, square) and not last_position.is_pinned(board.turn, square):
                pinned_piece = board.piece_at(square)
                pinning_piece = board.piece_at(pinning_move.to_square)

                # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                if all(move.from_square != square for move in board.legal_moves):
                    pinned_pieces.append(square)
                elif PIECE_VALUES[pinned_piece.piece_type] > PIECE_VALUES[pinning_piece.piece_type]:
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
        # Find all pieces except kings and pawns
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings & ~board.pawns

        # Check valuable pieces that could be targets for relative pins
        for piece_square in chess.scan_reversed(filtered_pieces):
            piece = board.piece_at(piece_square)
            # Search through all potential pinned pieces for this piece
            for pin_square in chess.scan_reversed(filtered_pieces):
                # Skip if the piece is the same
                if piece_square == pin_square:
                    continue

                pinned = board.piece_at(pin_square)
                # Skip if the pinned piece is more valuable than the piece being pinned to
                if PIECE_VALUES[pinned.piece_type] > PIECE_VALUES[piece.piece_type]:
                    continue

                # Check if the piece is pinned
                pin_mask = TacticSearch.relative_pin_mask(board, board.turn, pin_square, piece_square)
                last_pos_pin_mask = TacticSearch.relative_pin_mask(last_position, board.turn, pin_square, piece_square)
                # If the pin was not present in the last position, move is a new pin
                if pin_mask != chess.BB_ALL and last_pos_pin_mask == chess.BB_ALL:
                    # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                    if all(move.from_square != piece_square for move in board.legal_moves):
                        pinned_pieces.append(piece_square)

        return pinned_pieces
            
    @staticmethod
    def fork(board: chess.Board) -> list:
        """Detect forks (attacking two or more undefended pieces)."""
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        forking_move = board.peek()

        # Check if the square the forking piece has moved to is defended
        if len(board.attackers(board.turn, forking_move.to_square)) > 0:
            return []

        # Check the pieces that the forking piece is attacking
        attacked_pieces = board.attacks(forking_move.to_square) & board.occupied_co[board.turn] 
        # Attacking less than two pieces, not a fork
        if len(attacked_pieces) < 2:
            return []
        
        # Check if the attacked pieces are defended
        forked_squares = []
        forking_piece = board.piece_at(forking_move.to_square)
        king_forked = False

        for square in attacked_pieces:
            defenders = board.attackers(board.turn, square)
            target_piece = board.piece_at(square)
            # A king is always a good fork target since it must move
            if target_piece.piece_type == chess.KING:
                king_forked = True
                forked_squares.append(square)
            # A more valuable piece than the attacking forker is a good target
            elif PIECE_VALUES[target_piece.piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                forked_squares.append(square)
            # An undefended piece is a good target
            elif len(defenders) == 0:
                forked_squares.append(square)

        # If there are less than two undefended/less valuable pieces AND the king is not forked, it's not a good fork
        if len(forked_squares) < 2:
            if not king_forked:
                return []
            
            # King fork exception, check if the next move results in a capture/fork
            for move in board.legal_moves:
                temp_board = board.copy(stack=False)
                temp_board.push(move)
                # Skip if forking piece can be captured
                if move.to_square == forking_move.to_square:
                    return []
                
                # Update attacked pieces if one of them has moved to block the check
                for index, attacked in enumerate(attacked_pieces):
                    if move.from_square == attacked:
                        attacked_pieces.remove(attacked)
                        attacked_pieces.add(move.to_square)
                        break
                
                new_forked = []
                for square in attacked_pieces:
                    # Interesting that this is inverted, but it works
                    attackers = temp_board.attackers(not board.turn, square)
                    defenders = temp_board.attackers(board.turn, square)

                    # Check if the square is still being attacked
                    if len(attackers) > 0:
                        # If the square is still undefended, it's a good fork target
                        if len(defenders) == 0:
                            new_forked.append(square)
                        else:
                            # Check if one of the attackers is less valuable than the attacked square
                            for attacker in attackers:
                                if PIECE_VALUES[temp_board.piece_at(square).piece_type] > PIECE_VALUES[temp_board.piece_at(attacker).piece_type]:
                                    new_forked.append(square)
                                    break

                if len(new_forked) == 0:
                    return []

        return forked_squares