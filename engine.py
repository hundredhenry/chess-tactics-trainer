import os
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
    "Relative Pin": 3,
    "Skewer": 4
}

class Tactic:
    """Represents a tactic with a sequence of moves and a tactic type"""

    def __init__(self, sequence: list, score: int, type: int) -> None:
        """Initialize a tactic with a principal variation and type."""
        self.sequence = sequence
        self.type = type
        self.score = score
        self.index = 0
        self.max_index = len(sequence) - 1

    def next_move(self) -> chess.Move:
        """Get the next move in the tactic sequence and advance the index."""
        move = self.sequence[self.index]
        self.index += 1
        return move
    
    def hint_move(self) -> chess.Move:
        """View the next move without advancing the index."""
        return self.sequence[self.index]
    
    def moves_left(self) -> int:
        """Calculate the number of player moves remaining in the tactic."""
        return ((self.max_index - self.index) // 2) + 1
    
    def pretty_print(self) -> None:
        """Pretty print the tactic sequence."""
        print(f"=== Tactic Found: {list(TACTIC_TYPES.keys())[self.type]} ===")
        print(f"Sequence Length: {len(self.sequence)} moves")
        print(f"Position Evaluation: {self.score}")
        print("Principal Variation:")
        for move in self.sequence:
            print(move.uci(), end=" ")
        print("\n")

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board, engine_colour: chess.Color) -> None:
        """Initialize the tactics engine."""
        self.board = board
        self.engine_path = engine_path
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.optimum_engine_settings()
        self.engine_colour = engine_colour
        self.current_tactic = None
        self.tactic_types = list(TACTIC_TYPES.values())

        # Search settings
        self.max_search_depth = 20
        self.search_limit = chess.engine.Limit(depth=12)
        self.search_pv = 5
        
        # Engine settings
        self.engine_depth = None
        self.bounds = {}
        self.limit = None

    def optimum_engine_settings(self) -> None:
        """Set the engine settings to optimum values depending on the system."""
        logical_core_count = os.cpu_count()
        hash_size_per_core = 64  # MiB
        max_hash_size = logical_core_count * hash_size_per_core
        self.engine.configure({"Threads": logical_core_count, "Hash": max_hash_size})

    def set_difficulty(self, value: int) -> None:
        """Configure engine parameters based on difficulty level."""
        # Easy
        if value == 0:
            self.num_pv = 7
            self.engine_depth = 8
            self.bounds = {'min_mistake': 400, 'advantage': 300}
        # Medium
        elif value == 1:
            self.num_pv = 5
            self.engine_depth = 12
            self.bounds = {'min_mistake': 300, 'advantage': 200}
        # Hard
        else:
            self.num_pv = 3
            self.engine_depth = 18
            self.bounds = {'min_mistake': 250, 'advantage': 200}
        
        self.limit = chess.engine.Limit(time=10.0, depth=self.engine_depth)

    def set_tactic_types(self, types: list[int]) -> None:
        """Set the types of tactics to search for."""
        self.tactic_types = types
    
    def only_move(self, analysis: list[dict] = None, best_score: int = None) -> chess.Move:
        """Check if there's an obvious move to play."""
        current_move = analysis[0]["pv"][0]
        if len(analysis) == 1:
            return current_move
        
        second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)

        # If best move has minor piece advantage, return it
        if best_score >= second_score + 300:
            return current_move
        else:
            return None
    
    def _select_normal_move(self) -> chess.Move:
        """Selects the least winning move based on the position evaluation."""
        analysis = self.engine.analyse(self.board, self.limit, multipv=self.num_pv)
        current_move = analysis[0]["pv"][0]
        for infodict in analysis[1:]:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            if score < 0:
                break
            else:
                current_move = pv[0]

        return current_move
    
    def _select_tactic_move(self) -> chess.Move:
        """Selects the next move in the tactic sequence if valid."""
        # Check if tactic is complete after engine move
        next_tactic_move = self.current_tactic.next_move()
        if self.current_tactic.index > self.current_tactic.max_index:
            self.end_tactic()
        
        return next_tactic_move

    def play_move(self) -> chess.Move:
        """Determine the move for the engine to play."""
        # Check if we're in the middle of a tactic
        if self.current_tactic:
            return self._select_tactic_move()

        analysis = self.engine.analyse(self.board, self.limit, multipv=2)
        best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
        # Checkmate line for engine
        if best_score > 10000:
            return analysis[0]["pv"][0]
        
        # Only move available
        move = self.only_move(analysis, best_score)
        if move:
            return move
        
        # Tactic search
        self.tactic_search()

        # Check if a tactic was found
        if self.current_tactic:
            return self.current_tactic.next_move()

        return self._select_normal_move()
    
    def undo_tactic_move(self) -> None:
        """Undo a tactic move."""
        if self.current_tactic.index >= 2:
            self.current_tactic.index -= 2
        elif self.current_tactic.index == 1:
            self.current_tactic.index -= 1
            self.end_tactic()
        else:
            self.end_tactic()

    def end_tactic(self) -> None:
        """End the current tactic."""
        self.current_tactic = None
        self.tactic_search()

    def _process_engine_moves(self, board: chess.Board, depth: int, sequence: list, analysis: list[dict], search_queue: list, best_score: int) -> list:
        """Process engine moves in the search stack."""
        for infodict in analysis:
            pv = infodict["pv"]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            # For initial position, consider all moves above the min mistake threshold
            if depth == 0:
                min_bound = best_score - self.bounds['min_mistake']
                if score >= min_bound:
                    next_board = board.copy(stack=1)
                    next_board.push(pv[0])
                    search_queue.append((next_board, depth + 1, sequence + [pv[0]]))
            # Otherwise, play normal moves (slightly suboptimal moves are acceptable)
            elif score >= best_score - 50:
                next_board = board.copy(stack=1)
                next_board.push(pv[0])
                search_queue.append((next_board, depth + 1, sequence + [pv[0]]))
            
        return search_queue

    def _process_player_moves(self, board: chess.Board, depth: int, sequence: list, analysis: list[dict], search_queue: list, best_score: int) -> list:
        """Process player moves in the search stack."""
        best_move_clear = False
        if len(analysis) == 1:
            best_move_clear = best_score <= -self.bounds['advantage']
        elif len(analysis) >= 2:
            second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)
            best_move_clear = best_score <= second_score - self.bounds['advantage']

        # If there's a clear best move, check for tactics
        if best_move_clear:
            pv = analysis[0]["pv"]
            score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
            best_move = pv[0]
            next_board = board.copy(stack=1)
            next_board.push(best_move)

            # Check if the move leads to a tactic
            tactic_index, tactic_type = self._variation_tactic_check(next_board, pv[1:])
            if tactic_index >= 0:
                self.current_tactic = Tactic(sequence + pv[:tactic_index + 1], score, tactic_type)
                self.current_tactic.pretty_print()
                return []
            else:
                # Continue search if no tactic found
                search_queue.append((next_board, depth + 1, sequence + [best_move]))
        
        return search_queue

    def tactic_search(self) -> None:
        """Search for tactical opportunities in the current position."""
        initial_board = self.board.copy(stack=1)
        search_queue = [(initial_board, 0, [])]

        while search_queue:
            board, depth, sequence = search_queue.pop(0)
            # Base case for search - max depth reached or game over
            if depth == self.max_search_depth or board.is_game_over():
                print("Game over or max depth reached.")
                continue

            # If inital position and no mistake made yet, consider more moves
            if depth == 0 and board.turn == self.engine_colour:
                num_pv = board.legal_moves.count()
            elif board.turn == self.engine_colour:
                num_pv = min(board.legal_moves.count(), self.search_pv)
            else:
                num_pv = min(board.legal_moves.count(), 2)
            
            analysis = self.engine.analyse(board, self.search_limit, multipv=num_pv)
            best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
            # Engine getting checkmated line
            if best_score < -10000 and TACTIC_TYPES["Checkmate"] in self.tactic_types:
                self.current_tactic = Tactic(sequence + analysis[0]["pv"], best_score, TACTIC_TYPES["Checkmate"])
                self.current_tactic.pretty_print()
                return

            # Engine turn
            if board.turn == self.engine_colour:
                search_queue = self._process_engine_moves(board, depth, sequence, analysis, search_queue, best_score)
            # Human turn
            else:
                search_queue = self._process_player_moves(board, depth, sequence, analysis, search_queue, best_score)

    def _variation_tactic_check(self, board: chess.Board, pv: list) -> tuple:
        """Check if the given move sequence contains a tactical opportunity."""
        temp_board = board.copy(stack=1)

        for index, move in enumerate(pv):
            # Only check for tactics on the engine's turn
            if temp_board.turn == self.engine_colour:
                # Check for each type of tactic
                if TACTIC_TYPES["Fork"] in self.tactic_types:
                    if index >= len(pv):
                        forked_pieces = TacticSearch.fork(temp_board)
                    else:
                        forked_pieces = TacticSearch.fork(temp_board, pv[index])

                    if forked_pieces:
                        return index, TACTIC_TYPES["Fork"]
                    
                if TACTIC_TYPES["Skewer"] in self.tactic_types:
                    skewered_pieces = TacticSearch.skewer(temp_board)
                    if skewered_pieces:
                        return index, TACTIC_TYPES["Skewer"]
                    
                if TACTIC_TYPES["Relative Pin"] in self.tactic_types:
                    relative_pins = TacticSearch.relative_pin(temp_board)
                    if relative_pins:
                        return index, TACTIC_TYPES["Relative Pin"]
                        
                if TACTIC_TYPES["Absolute Pin"] in self.tactic_types:
                    pinned_pieces = TacticSearch.absolute_pin(temp_board, pv[index])
                    if pinned_pieces:
                        return index, TACTIC_TYPES["Absolute Pin"]
                
            # Apply the move and continue
            temp_board.push(move)

        return -1, -1
    
    def reset_engine(self, board: chess.Board, engine_colour: chess.Color) -> None:
        """Reset the engine with a new board and colour."""
        self.engine.quit()
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.optimum_engine_settings()
        self.engine_colour = engine_colour
        self.current_tactic = None

    def close(self) -> None:
        """Close the engine process."""
        self.engine.quit()

class TacticSearch:
    """Static methods for detecting different types of chess tactics."""
    @staticmethod
    def absolute_pinner(board: chess.Board, colour: chess.Color, square: chess.Square) -> chess.Square:
        """Calculate the pinning square for a potential absolute pin. Modified version of python-chess pin_mask function."""
        king = board.king(colour)
        square_mask = chess.BB_SQUARES[square]

        for attacks, sliders in [(chess.BB_FILE_ATTACKS, board.rooks | board.queens),
                                 (chess.BB_RANK_ATTACKS, board.rooks | board.queens),
                                 (chess.BB_DIAG_ATTACKS, board.bishops | board.queens)]:
            rays = attacks[king][0]
            if rays & square_mask:
                snipers = rays & sliders & board.occupied_co[not colour]
                for sniper in chess.scan_reversed(snipers):
                    # If the square is the only thing in between piece and sniper
                    if chess.between(sniper, king) & (board.occupied | square_mask) == square_mask:
                        return sniper

                break
        
        # No pin found
        return None

    @staticmethod
    def relative_pinner(board: chess.Board, colour: chess.Color, square: chess.Square, piece: chess.Square) -> chess.Square:
        """Calculate the pinning square for a potential relative pin. Modified version of python-chess pin_mask function."""
        square_mask = chess.BB_SQUARES[square]

        for attacks, sliders in [(chess.BB_FILE_ATTACKS, board.rooks | board.queens),
                                (chess.BB_RANK_ATTACKS, board.rooks | board.queens),
                                (chess.BB_DIAG_ATTACKS, board.bishops | board.queens)]:
            rays = attacks[piece][0]
            if rays & square_mask:
                snipers = rays & sliders & board.occupied_co[not colour]
                for sniper in chess.scan_reversed(snipers):
                    if chess.between(piece, sniper) & (board.occupied | square_mask) == square_mask:
                        return sniper
                    
                break

        # No pin found
        return None

    @staticmethod
    def absolute_pin(board: chess.Board, next_move: chess.Move = None) -> list:
        """Detect absolute pins (pinned to king)."""
        if not board.move_stack:
            return []

        # Previous position
        last_position = board.copy()
        last_position.pop()
        # Find all pieces except kings
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings
        
        # Check each piece for a pin
        for square in chess.scan_reversed(filtered_pieces):
            pinning_square = TacticSearch.absolute_pinner(board, board.turn, square)
            last_pos_pin = TacticSearch.absolute_pinner(last_position, board.turn, square)

            # If the pin was not present in the last position, move is a new pin
            if pinning_square != None and last_pos_pin == None:
                pinning = board.piece_at(pinning_square)
                pinned = board.piece_at(square)

                if next_move is not None:
                    # If pin can be broken by capturing the pinning piece, not a valid pin
                    if next_move.to_square == pinning_square:
                        continue

                # If the pinning piece is worth less than the pinned piece, good pin
                if PIECE_VALUES[pinning.piece_type] < PIECE_VALUES[pinned.piece_type]:
                    return [square]

                # If the pinned piece is undefended, good pin
                if len(board.attackers(board.turn, square)) == 0:
                    return [square]

                # If the pinned piece was a crucial defender of another piece under attack, good pin
                defending = board.attacks(square) & board.occupied_co[board.turn]
                if len(defending) > 0:
                    for ally in defending:
                        if board.is_attacked_by(not board.turn, ally):
                            attackers = board.attackers(not board.turn, ally)
                            defenders = board.attackers(board.turn, ally)

                            if len(attackers) > len(defenders) - 1:
                                return [square]
                            
        return []
    
    @staticmethod
    def relative_pin(board: chess.Board) -> list:
        if not board.move_stack:
            return []
        
        pinned_pieces = []
        # Previous position
        last_position = board.copy()
        last_position.pop()
        # Find all pieces except kings and pawns
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings & ~board.pawns

        # Check valuable pieces that could be targets for relative pins
        for valued_square in chess.scan_reversed(filtered_pieces):
            valuable = board.piece_at(valued_square)
            # Search through all potential pinned pieces for this piece
            for pin_square in chess.scan_reversed(filtered_pieces):
                # Skip if the piece is the same
                if valued_square == pin_square:
                    continue

                pinned = board.piece_at(pin_square)
                # Skip if the pinned piece is worth more than the valuable piece
                if PIECE_VALUES[pinned.piece_type] > PIECE_VALUES[valuable.piece_type]:
                    continue

                # Check if the piece is pinned
                pinning_square = TacticSearch.relative_pinner(board, board.turn, pin_square, valued_square)
                last_pos_pin = TacticSearch.relative_pinner(last_position, board.turn, pin_square, valued_square)

                # If the pin was not present in the last position, move is a new pin
                if pinning_square != None and last_pos_pin == None:
                    pinning = board.piece_at(pinning_square)
                    # Skip if the pinning piece is worth more than or equal to valuable piece
                    if PIECE_VALUES[pinning.piece_type] >= PIECE_VALUES[valuable.piece_type]:
                        continue
                             
                    is_valid_pin = True
                    # Check if the pin can be broken by capturing the pinning piece with a less or equal valuable piece
                    for move in board.legal_moves:
                        if move.to_square == pinning_square:
                            pinning_defenders = board.attackers(board.turn, pinning_square)
                            if len(pinning_defenders) == 0:
                                is_valid_pin = False
                                break

                            if (PIECE_VALUES[board.piece_at(move.from_square).piece_type] <= PIECE_VALUES[pinning.piece_type] or
                                board.piece_at(move.from_square).piece_type == chess.KING):
                                is_valid_pin = False
                                break
                    
                    if is_valid_pin:
                        pinned_pieces.append(pin_square)
                        return pinned_pieces

        return []
    
    @staticmethod
    def skewer(board: chess.Board) -> list:
        if not board.move_stack:
            return []
        
        skewered_pieces = []
        # Find all pieces except pawns
        filtered_pieces = board.occupied_co[board.turn] & ~board.pawns

        for skewered_square in chess.scan_reversed(filtered_pieces):
            skewered = board.piece_at(skewered_square)

            for valued_square in chess.scan_reversed(filtered_pieces):
                valued = board.piece_at(valued_square)
                # Skip if the piece is the same
                if skewered_square == valued_square:
                    continue

                # Skip if the skewered piece is worth more than the valuable piece
                if PIECE_VALUES[skewered.piece_type] > PIECE_VALUES[valued.piece_type]:
                    continue

                pinning_square = TacticSearch.relative_pinner(board, board.turn, valued_square, skewered_square)
                if pinning_square != None:
                    pinning = board.piece_at(pinning_square)
                    # Skip if the pinning piece is worth more than or equal to the valued piece
                    if PIECE_VALUES[pinning.piece_type] >= PIECE_VALUES[valued.piece_type]:
                        continue

                    # Skip if the pinning piece is worth less than the skewered piece
                    if PIECE_VALUES[pinning.piece_type] < PIECE_VALUES[skewered.piece_type]:
                        continue

                    # Skip if the skewered piece is defended
                    skewered_defenders = board.attackers(board.turn, skewered_square)
                    # Do not consider if the skewered piece is defended by the valued piece
                    if valued_square in skewered_defenders:
                        if len(skewered_defenders) > 1:
                            continue
                    else:
                        if len(skewered_defenders) > 0:
                            continue

                    is_valid_skewer = True

                    # Skip if the skewer can be broken by capturing the skewer piece with a less or equal valuable piece
                    for move in board.legal_moves:
                        # Might need something like king fork exception for skewers when the king can defend the skewered piece
                        if move.to_square == pinning_square:
                            skewering_defenders = board.attackers(board.turn, pinning_square)
                            if len(skewering_defenders) == 0:
                                is_valid_skewer = False
                                break
                                
                            if (PIECE_VALUES[board.piece_at(move.from_square).piece_type] <= PIECE_VALUES[pinning.piece_type] or
                                board.piece_at(move.from_square).piece_type == chess.KING):
                                is_valid_skewer = False
                                break
                    
                    if is_valid_skewer:
                        skewered_pieces.append(skewered_square)
                        return skewered_pieces

        return []

    @staticmethod
    def fork(board: chess.Board, next_move: chess.Move = None) -> list:
        """Detect forks (attacking two or more pieces) """
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        forking_move = board.peek()

        # Check if the square the forking piece has moved to is defended
        if len(board.attackers(board.turn, forking_move.to_square)) > 0:
            return []

        # Generate the pieces that the forking piece is attacking
        attacked_pieces = board.attacks(forking_move.to_square) & board.occupied_co[board.turn]
        # Attacking less than two pieces, not a fork
        if len(attacked_pieces) < 2:
            return []

        # Check if the attacked pieces are defended
        forking_piece = board.piece_at(forking_move.to_square)
        forked_pieces = []
        king_forked = False

        for square in attacked_pieces:
            target_piece = board.piece_at(square)

            # A king is always a good fork target since it means the fork is forceful
            if target_piece.piece_type == chess.KING:
                king_forked = True
                forked_pieces.append(square)
                continue

            defenders = board.attackers(board.turn, square)
            # A more valuable piece than the attacking forker is a good target
            if PIECE_VALUES[target_piece.piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                forked_pieces.append(square)
            # An undefended piece is a good target
            elif len(defenders) == 0:
                forked_pieces.append(square)

        if len(forked_pieces) >= 2 or king_forked:
            # Check next move in sequence to ensure validity (forked pieces may move to defend eachother in best sequence)
            if next_move is None:
                if len(forked_pieces) < 2:
                    return []
                
                return forked_pieces

            if next_move.from_square in attacked_pieces:
                temp_board = board.copy(stack=False)
                temp_board.push(next_move)
                new_forked_pieces = temp_board.attacks(forking_move.to_square) & temp_board.occupied_co[not temp_board.turn]

                for square in new_forked_pieces:
                    attackers = temp_board.attackers(temp_board.turn, square)
                    defenders = temp_board.attackers(not temp_board.turn, square)

                    # If the square is undefended, it's stil a good fork target
                    if len(defenders) == 0:
                        continue
                    else:
                        valuable_attack = False
                        # Check if the attacked square is attacked by a less valuable piece
                        for attacker in attackers:
                            if PIECE_VALUES[temp_board.piece_at(attacker).piece_type] < PIECE_VALUES[temp_board.piece_at(square).piece_type]:
                                valuable_attack = True
                                break

                        if not valuable_attack:
                            new_forked_pieces.remove(square)

                # Unable to capture any of the forked pieces in the next move, not a good fork
                if len(new_forked_pieces) < 1:
                    return []
            else:
                if len(forked_pieces) < 2:
                    return []
        else:
            return []
        
        return forked_pieces