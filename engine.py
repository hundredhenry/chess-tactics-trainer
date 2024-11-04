import chess
import chess.engine
from collections import namedtuple

Pin = namedtuple('Pin', ['pinned', 'move', 'score', 'rank'])
Fork = namedtuple('Fork', ['forked', 'move', 'score', 'rank'])

class TacticsEngine:
    def __init__(self, engine_path: str, board: chess.Board, multipv: int):
        self.board = board
        self.engine = chess.engine.SimpleEngine.popen_uci(engine_path)
        self.multipv = multipv

    def find_move(self, time_limit: float):
        result = self.engine.play(self.board, chess.engine.Limit(time=time_limit))

        return result.move
    
    def check_tactics(self) -> dict:
        info = self.engine.analyse(self.board, chess.engine.Limit(depth=10), multipv=self.multipv)
        tactics = {}

        pins = []
        forks = []

        for i in range(min(self.multipv, sum(1 for _ in self.board.legal_moves))):
            score = info[i]["score"].relative.score()
            pv = info[i]["pv"]
            move = pv[0]

            tmp_board = self.board.copy()
            tmp_board.push(move)

            pins.extend(self.absolute_pins(tmp_board, move, score, i+1))
            forks.extend(self.forks(tmp_board, move, score, i+1))
        
        tactics["pins"] = pins
        tactics["forks"] = forks

        return tactics
    
    def pin_mask_queen(self, color: bool, square: int) -> chess.Bitboard:
        queens = self.board.queens & self.board.occupied_co[color]
        if not queens:
            return chess.BB_ALL

        square_mask = chess.BB_SQUARES[square]

        for attacks, sliders in [(chess.BB_FILE_ATTACKS, self.board.rooks | self.board.queens),
                                 (chess.BB_RANK_ATTACKS, self.board.rooks | self.board.queens),
                                 (chess.BB_DIAG_ATTACKS, self.board.bishops | self.board.queens)]:
            for q in chess.scan_reversed(queens):
                rays = attacks[q][0]
                if rays & square_mask:
                    snipers = rays & sliders & self.board.occupied_co[not color]
                    for sniper in chess.scan_reversed(snipers):
                        if chess.between(sniper, q) & (self.board.occupied | square_mask) == square_mask:
                            return chess.ray(q, sniper)

        return chess.BB_ALL

    def absolute_pins(self, board: chess.Board, pinning_move: chess.Move, score: int, rank: int) -> list:
        pins = []
        pieces = board.occupied_co[board.turn]

        # Create a copy of the board and pop the last move once (to check for exisiting pins before the move)
        tmp_board = board.copy()
        tmp_board.pop()

        for square in chess.scan_reversed(pieces):
            piece = board.piece_at(square)

            # Skip pawns and kings
            if piece.piece_type == chess.PAWN or piece.piece_type == chess.KING:
                continue

            # Check if the piece is pinned because of the given move
            if board.is_pinned(board.turn, square) and not tmp_board.is_pinned(board.turn, square):
                # Make sure the pinned piece has no legal moves (like capturing the pinning piece)
                if all(move.from_square != square for move in board.legal_moves):
                    attackers = tmp_board.attackers(not board.turn, square)
                    defenders = tmp_board.attackers(board.turn, square)
                    if len(attackers) >= len(defenders):
                        piece_type = chess.piece_name(piece.piece_type)
                        piece_square = chess.square_name(square)
                        pins.append(Pin(square, pinning_move, score, rank))
                        print(f"Absolute Pin: {piece_type} on {piece_square}")

        return pins
    
    def forks(self, board: chess.Board, move: chess.Move, score: int, rank: int) -> list:
        forks = []

        # Check if the square the forking piece has moved to is defended
        if len(board.attackers(board.turn, move.to_square)):
            return forks

        # Check the pieces that the forking piece is attacking
        attacked_squares = board.attacks(move.to_square) & board.occupied_co[board.turn]
        forked_squares = []
        
        if len(attacked_squares) >= 2:
            # Check if the attacked squares are defended
            for square in attacked_squares:
                defenders = board.attackers(board.turn, square)
                if len(defenders):
                    continue
                
                forked_squares.append(square)
        
        if len(forked_squares) >= 2:
            forks.append(Fork(forked_squares, move, score, rank))
            for square in forked_squares:
                piece_type = chess.piece_name(board.piece_type_at(square))
                piece_square = chess.square_name(square)
                print(f"Fork: {piece_type} on {piece_square}")

        return forks
                
    
    def close(self):
        self.engine.quit()

if __name__ == "__main__":
    board = chess.Board("1k1r3r/ppqb1pQp/2n5/1B6/8/B3PN2/P4PPP/2R3K1 b - - 0 1")
    engine = TacticsEngine(r"./stockfish-windows-x86-64-avx2.exe", board, 10)
    pins = engine.check_tactics()
    engine.close()
    print(pins)