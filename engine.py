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
        self.search_limit = chess.engine.Limit(depth=14)
        self.search_pv = 5
        self.err_bound = 50
        self.only_move_bound = 300
        
        # Engine settings
        self.engine_depth = None
        self.bounds = {}
        self.normal_move_limit = None

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
            self.bounds = {'min_bound': -600, 'forcing_bound': 300}
        # Medium
        elif value == 1:
            self.num_pv = 5
            self.engine_depth = 12
            self.bounds = {'min_bound': -350, 'forcing_bound': 200}
        # Hard
        else:
            self.num_pv = 3
            self.engine_depth = 18
            self.bounds = {'min_bound': -300, 'forcing_bound': 200}
        
        self.normal_move_limit = chess.engine.Limit(time=10.0, depth=self.engine_depth)

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
        if best_score >= second_score + self.only_move_bound:
            return current_move
        else:
            return None
    
    def _select_normal_move(self) -> chess.Move:
        """Selects the least losing move based on the position evaluation."""
        analysis = self.engine.analyse(self.board, self.normal_move_limit, multipv=self.num_pv)
        for infodict in analysis:
            pv = infodict["pv"]
            current_move = pv[0]
            score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
            if score <= 0:
                return current_move

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

        analysis = self.engine.analyse(self.board, self.normal_move_limit, multipv=2)
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
                if score >= self.bounds['min_bound']:
                    next_board = board.copy(stack=1)
                    next_board.push(pv[0])
                    search_queue.append((next_board, depth + 1, sequence + [pv[0]]))
            # Otherwise, play normal moves (slightly suboptimal moves are acceptable)
            elif score >= best_score - self.err_bound:
                next_board = board.copy(stack=1)
                next_board.push(pv[0])
                search_queue.append((next_board, depth + 1, sequence + [pv[0]]))
            
        return search_queue

    def _process_player_moves(self, board: chess.Board, depth: int, sequence: list, analysis: list[dict], search_queue: list, best_score: int) -> list:
        """Process player moves in the search stack."""
        best_move_clear = False
        if len(analysis) == 1:
            best_move_clear = best_score <= -self.bounds['forcing_bound']
        elif len(analysis) >= 2:
            second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)
            best_move_clear = best_score <= second_score - self.bounds['forcing_bound']

        # If there's a clear best move, check for tactics
        if best_move_clear:
            pv = analysis[0]["pv"]
            score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
            best_move = pv[0]
            next_board = board.copy(stack=1)
            next_board.push(best_move)

            # Check if the move leads to a tactic
            if len(analysis) == 1:
                tactic_type = self._position_tactic_check(next_board, None)
            else:
                tactic_type = self._position_tactic_check(next_board, pv[1])
                
            if tactic_type >= 0:
                self.current_tactic = Tactic(sequence + [best_move], score, tactic_type)
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
            if depth == 0:
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

    def _position_tactic_check(self, board: chess.Board, engine_move: chess.Move) -> tuple:
        """Check if the given move sequence contains a tactical opportunity."""
       
        if TACTIC_TYPES["Fork"] in self.tactic_types:
            forked_pieces = TacticSearch.fork(board, engine_move)

            if forked_pieces:
                return TACTIC_TYPES["Fork"]
        
        if TACTIC_TYPES["Skewer"] in self.tactic_types:
            skewered_pieces = TacticSearch.skewer(board, engine_move)
            if skewered_pieces:
                return TACTIC_TYPES["Skewer"]
            
        if TACTIC_TYPES["Absolute Pin"] in self.tactic_types:
            pinned_pieces = TacticSearch.absolute_pin(board, engine_move)
            if pinned_pieces:
                return TACTIC_TYPES["Absolute Pin"]
        
        if TACTIC_TYPES["Relative Pin"] in self.tactic_types:
            relative_pins = TacticSearch.relative_pin(board, engine_move)
            if relative_pins:
                return TACTIC_TYPES["Relative Pin"]
        
        return -1
    
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
    def absolute_pin(board: chess.Board, next_move: chess.Move) -> list:
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

                # If pin can be broken by capturing the pinning piece, not a good pin
                if next_move != None:
                    if next_move.to_square == pinning_square:
                        defenders = board.attackers(not board.turn, pinning_square)
                        if len(defenders) == 0:
                            continue

                # If the pinning piece is worth less than the pinned piece, good pin
                if PIECE_VALUES[pinning.piece_type] < PIECE_VALUES[pinned.piece_type]:
                    return [square]

                # If the pinned piece is defended poorly, good pin
                attackers = board.attackers(not board.turn, square)
                defenders = board.attackers(board.turn, square)
                if len(attackers) > len(defenders):
                    return [square]

                # Pinned piece was a crucial defender of another piece under attack, good pin
                defending = board.attacks(square) & board.occupied_co[board.turn]
                if len(defending) > 0:
                    for ally in defending:
                        if board.is_attacked_by(not board.turn, ally):
                            attackers = board.attackers(not board.turn, ally)
                            defenders = board.attackers(board.turn, ally)

                            # Do not include pinner as attacker
                            if pinning_square in attackers:
                                attackers.remove(pinning_square)

                            # Do not include pinned piece as defender
                            defenders.remove(square)

                            if len(attackers) > len(defenders):
                                return [square]
                            
        return []
    
    @staticmethod
    def relative_pin(board: chess.Board, next_move: chess.Move) -> list:
        if not board.move_stack:
            return []
        
        # Previous position
        last_position = board.copy()
        last_position.pop()
        valued_pieces = board.occupied_co[board.turn] & ~board.kings & ~board.pawns
        pinnable_pieces = board.occupied_co[board.turn] & ~board.kings
        
        # Check valuable pieces that could be targets for relative pins
        for valued_square in chess.scan_reversed(valued_pieces):
            valuable = board.piece_at(valued_square)
            # Search through all potential pinned pieces for this piece
            for pin_square in chess.scan_reversed(pinnable_pieces):
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

                    # If pin can be broken by capturing the pinning piece, not a good pin
                    if next_move != None:
                        if next_move.to_square == pinning_square:
                            defenders = board.attackers(not board.turn, pinning_square)
                            if len(defenders) == 0:
                                continue

                    # Skip if the pinning piece is worth more than or equal to valuable piece
                    if PIECE_VALUES[pinning.piece_type] >= PIECE_VALUES[valuable.piece_type]:
                        continue
                    
                    # Good pin if the pinning piece is worth less than the pinned piece
                    if PIECE_VALUES[pinning.piece_type] < PIECE_VALUES[pinned.piece_type]:
                        return [pin_square]

                    # Check if there are more attackers than defenders on the pinned piece
                    attackers = board.attackers(not board.turn, pin_square)
                    defenders = board.attackers(board.turn, pin_square)
                    if len(attackers) > len(defenders):
                        return [pin_square]

                    # If the pinned piece was a crucial defender of another piece under attack, good pin
                    defending = board.attacks(pin_square) & board.occupied_co[board.turn]
                    if len(defending) > 0:
                        for ally in defending:
                            if board.is_attacked_by(not board.turn, ally):
                                attackers = board.attackers(not board.turn, ally)
                                defenders = board.attackers(board.turn, ally)

                                # Do not include pinner as attacker
                                if pinning_square in attackers:
                                    attackers.remove(pinning_square)

                                # Do not include pinned piece as defender
                                defenders.remove(pin_square)
                                
                                if len(attackers) > len(defenders):
                                    return [pin_square]

        return []
    
    @staticmethod
    def skewer(board: chess.Board, next_move: chess.Move) -> list:
        if not board.move_stack:
            return []
        
        valuable_pieces = board.occupied_co[board.turn] & ~board.pawns
        other_pieces = board.occupied_co[board.turn] & ~board.kings

        for skewered_square in chess.scan_reversed(other_pieces):
            skewered = board.piece_at(skewered_square)

            for valued_square in chess.scan_reversed(valuable_pieces):
                valued = board.piece_at(valued_square)
                # Skip if the piece is the same
                if skewered_square == valued_square:
                    continue

                # Skip if the skewered piece is worth more than the valuable piece
                if PIECE_VALUES[skewered.piece_type] > PIECE_VALUES[valued.piece_type]:
                    continue

                skewering_square = TacticSearch.relative_pinner(board, board.turn, valued_square, skewered_square)
                if skewering_square != None:
                    skewering = board.piece_at(skewering_square)

                    # Skip if the skewering piece is worth more than or equal to the valued piece
                    if PIECE_VALUES[skewering.piece_type] >= PIECE_VALUES[valued.piece_type]:
                        continue

                    if next_move != None:
                        # Skip if the skewering piece can be captured
                        if next_move.to_square == skewering_square:
                            defenders = board.attackers(not board.turn, skewered_square)

                            if len(defenders) == 0:
                                return []
                        
                    # Good skewer if the skewered piece is worth more than the skewering piece
                    if PIECE_VALUES[skewering.piece_type] < PIECE_VALUES[skewered.piece_type]:
                        return [skewered_square]
                    
                    if next_move == None:
                        return [skewered_square]

                    temp_board = board.copy(stack=1)
                    temp_board.push(next_move)

                    # More attackers than defenders on the skewered piece, good skewer
                    attackers = temp_board.attackers(temp_board.turn, skewered_square)
                    defenders = temp_board.attackers(not temp_board.turn, skewered_square)
                    if len(attackers) > len(defenders):
                        return [skewered_square]
                    
        return []

    @staticmethod
    def fork(board: chess.Board, next_move: chess.Move) -> list:
        """Detect forks (attacking two or more pieces) """
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        forking_move = board.peek()

        # Check if the forking piece is captured in the next move
        if next_move != None:
            if next_move.to_square == forking_move.to_square:
                defenders = board.attackers(not board.turn, forking_move.to_square)
                if len(defenders) == 0:
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

            # A more valuable piece than the attacking forker is a good target
            if PIECE_VALUES[target_piece.piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                forked_pieces.append(square)
                continue
            
            attackers = board.attackers(not board.turn, square)
            defenders = board.attackers(board.turn, square)
            # If the square has more attackers than defenders, it's a good target
            if len(attackers) > len(defenders):
                forked_pieces.append(square)

        # Not a good fork if less than two pieces are forked and no king is forked
        if len(forked_pieces) < 2 and not king_forked:
            return []
        
        if next_move == None:
            if len(forked_pieces) < 2:
                return []
            
            return forked_pieces

        # Check next move in sequence to ensure validity (forked pieces may move to defend eachother in best sequence)
        if next_move.from_square not in attacked_pieces:
            return forked_pieces

        temp_board = board.copy(stack=False)
        temp_board.push(next_move)
        next_forked_pieces = []
        
        # Remove the piece that was moved from the attacked pieces
        attacked_pieces.remove(next_move.from_square)
        # Check if the piece that was moved is still attacked by the forking piece
        if next_move.to_square in temp_board.attacks(forking_move.to_square):
            attacked_pieces.add(next_move.to_square)

        for square in attacked_pieces:
            attackers = temp_board.attackers(temp_board.turn, square)
            defenders = temp_board.attackers(not temp_board.turn, square)

            # If the square has more attackers than defenders, it's a good target
            if len(attackers) > len(defenders):
                next_forked_pieces.append(square)
            else:
                # Check if the attacked square is attacked by a less valuable piece
                for attacker in attackers:
                    if PIECE_VALUES[temp_board.piece_at(attacker).piece_type] < PIECE_VALUES[temp_board.piece_at(square).piece_type]:
                        next_forked_pieces.append(square)
                        break

        # Unable to capture any of the forked pieces in the next move, not a good fork
        if len(next_forked_pieces) < 1:
            return []
        
        return forked_pieces