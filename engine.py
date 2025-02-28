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
        return ((len(self.pv) - 1 - self.index) // 2) + 1

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board, engine_colour: chess.Color) -> None:
        self.board = board
        self.engine_path = engine_path
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.engine_colour = engine_colour
        self.current_tactic = None
        self.search_depth = 8
        self.tactic_cache = {}
        self.tactic_types = [0, 1, 2, 3]

    def set_difficulty(self, value: int) -> None:
        if value == 0: # Easy
            self.num_pv = 5
            self.engine_depth = 6
        elif value == 1: # Medium
            self.num_pv = 3
            self.engine_depth = 10
        else: # Hard
            self.num_pv = 1
            self.engine_depth = 15

        self.limit = chess.engine.Limit(time=10.0, depth=self.engine_depth)

    def set_tactic_types(self, types: list[int]) -> None:
        self.tactic_types = types

    def play_move(self) -> chess.Move:
        if self.current_tactic:
            if self.current_tactic.index < len(self.current_tactic.pv) - 1 and self.current_tactic.next_move() == self.board.peek():
                engine_move = self.current_tactic.next_move()
                # Reset tactic if no moves left
                if self.current_tactic.index == len(self.current_tactic.pv) - 1:
                    self.current_tactic = None

                return engine_move
            # Cache and reset the tactic
            self.tactic_cache[self.board.fullmove_number] = self.current_tactic
            self.current_tactic = None

        num_pv = 2 if self.num_pv < 2 else self.num_pv
        analysis = self.engine.analyse(self.board, self.limit, multipv=num_pv)
        # Starts with the best move
        current_move = analysis[0]["pv"][0]
        best_score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
        # Checkmate line for engine
        if best_score > 5000:
            return analysis[0]["pv"][0]
        
        # Tactic search
        self.tactic_search()
        if self.current_tactic:
            return self.current_tactic.next_move()
        
        # Check if there is a second best move
        if len(analysis) == 1:
            return current_move
        else:
            second_score = analysis[1]["score"].pov(self.engine_colour).score(mate_score=100000)
        
        # Check if best move is significantly better
        if best_score >= second_score + 300:
            return current_move
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

    def tactic_search(self, puzzle: bool = False) -> None:
        # Stack used to store the board, depth and move sequence
        if puzzle:
            search_stack = [(self.board.copy(stack=1), self.search_depth, [], True)]
        else:
            search_stack = [(self.board.copy(stack=1), self.search_depth, [], False)]

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
                for infodict in analysis:
                    pv = infodict["pv"]
                    score = infodict["score"].pov(self.engine_colour).score(mate_score=100000)
                    if depth == self.search_depth and not mistake: # Initial mistake move
                        if -300 <= score < best_score - 100:
                            next_board = board.copy(stack=1)
                            next_board.push(pv[0])
                            search_stack.append((next_board, depth - 1, sequence + [pv[0]], True))
                    else:
                        if score >= best_score - 30: # Normal engine move search
                            next_board = board.copy(stack=1)
                            next_board.push(pv[0])
                            search_stack.append((next_board, depth - 1, sequence + [pv[0]], mistake))
            # Human turn
            else:
                if len(analysis) >= 2:
                    second_score = analysis[1]["score"].pov(not self.engine_colour).score(mate_score=100000)
                
                if len(analysis) == 1 or best_score >= second_score + 250:
                    pv = analysis[0]["pv"]
                    score = analysis[0]["score"].pov(self.engine_colour).score(mate_score=100000)
                    best_move = pv[0]
                    next_board = board.copy(stack=1)
                    next_board.push(best_move)

                    # If a tactic is found and the tactic is winning, return the tactic
                    tactic_index, tactic_type = self.pv_tactic_check(next_board, pv[1:])
                    if tactic_index >= 0 and score <= -250:
                        self.current_tactic = Tactic(sequence + pv[:tactic_index + 1], tactic_type)
                        break
                    else:
                        search_stack.append((next_board, depth - 1, sequence + [best_move], mistake))
        
    def pv_tactic_check(self, board: chess.Board, pv: list) -> tuple:
        temp_board = board.copy(stack=1)

        for index, move in enumerate(pv):
            # Skip if it's not engine's turn
            if temp_board.turn == self.engine_colour:
                # Check for tactical patterns based on enabled types
                if TACTIC_TYPES["Fork"] in self.tactic_types and TacticSearch.fork(temp_board):
                    return index, TACTIC_TYPES["Fork"]
                elif TACTIC_TYPES["Absolute Pin"] in self.tactic_types and TacticSearch.absolute_pin(temp_board):
                    return index, TACTIC_TYPES["Absolute Pin"]
                elif TACTIC_TYPES["Relative Pin"] in self.tactic_types and TacticSearch.relative_pin(temp_board):
                    return index, TACTIC_TYPES["Relative Pin"]
                
            temp_board.push(move)

        return -1, -1
    
    def reset_engine(self, board: chess.Board, engine_colour: chess.Color) -> None:
        self.engine.quit()
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(self.engine_path)
        self.engine_colour = engine_colour
        self.current_tactic = None
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
        # Filter out kings
        filtered_pieces = board.occupied_co[board.turn] & ~board.kings
        
        # Search through all pieces
        for square in chess.scan_reversed(filtered_pieces):
            # If the pin was not present in the last position, move is a new pin
            if board.is_pinned(board.turn, square) and not last_position.is_pinned(board.turn, square):
                # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                if all(move.from_square != square for move in board.legal_moves):
                    pinned_pieces.append(square)
                # Otherwise make sure the pinning piece is defended
                elif len(board.attackers(not board.turn, pinning_move.to_square)):
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
                # If the pin was not present in the last position, move is a new pin
                if pin_mask != chess.BB_ALL and last_pos_pin_mask == chess.BB_ALL:
                    # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                    if all(move.from_square != piece_square for move in board.legal_moves):
                        pinned_pieces.append(piece_square)
                    # Otherwise make sure the pinning piece is defended
                    elif len(board.attackers(not board.turn, pinning_move.to_square)):
                        pinned_pieces.append(piece_square)

        return pinned_pieces
            
    @staticmethod
    def fork(board: chess.Board) -> list:
        if not board.move_stack:
            return []

        # Get the move that the forking piece has made
        forking_move = board.peek()
        king_forked = False

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
        forking_piece = board.piece_at(forking_move.to_square)
        for square in attacked_pieces:
            defenders = board.attackers(board.turn, square)
            # Check if the king is forked
            if board.piece_at(square).piece_type == chess.KING:
                king_forked = True
                forked_squares.append(square)
            # Check that the value of the forked piece is greater than the forking piece
            elif PIECE_VALUES[board.piece_at(square).piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                forked_squares.append(square)
            # Or check that the forking piece is not defended
            elif len(defenders) == 0:
                forked_squares.append(square)

        if king_forked:
            for move in board.legal_moves:
                temp_board = board.copy(stack=False)
                temp_board.push(move)
                # Skip if forking piece is captured
                if move.to_square == forking_move.to_square:
                    continue

                new_attacked = temp_board.attacks(forking_move.to_square) & temp_board.occupied_co[temp_board.turn]
                new_forked = []
                for square in new_attacked:
                    defenders = board.attackers(board.turn, square)
                    if PIECE_VALUES[board.piece_at(square).piece_type] > PIECE_VALUES[forking_piece.piece_type]:
                        new_forked.append(square)
                    elif len(defenders) == 0:
                        new_forked.append(square)

                if len(new_forked) >= 1:
                    return forked_squares

        # Attacking less than two undefended pieces, not a fork
        if len(forked_squares) < 2:
            return []

        return forked_squares