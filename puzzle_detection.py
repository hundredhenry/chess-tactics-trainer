import chess
from engine import TacticSearch

board = chess.Board(fen="1r1rkq2/1p3p2/1b2nQ2/p2Bp3/4P2P/1NP3R1/PP4P1/3R3K w - - 1 29")
sequence = "f6e5 b6c7 e5f5 c7g3"
moves = [chess.Move.from_uci(move) for move in sequence.split()]

for index, move in enumerate(moves):
    skewered = []
    board.push(move)
    if index + 1 < len(moves):
        skewered = TacticSearch.skewer(board, moves[index + 1])
    else:
        skewered = TacticSearch.skewer(board, None)

    if skewered:
        print(board.fen())
        print("Skewered:", chess.square_name(skewered[0]))