# Modules
import os
import pygame
import chess
from engine import TacticsEngine

class ChessGame:
    def __init__(self) -> None:
        self.init_display()
        self.init_board()
        self.init_engine(use_engine = True, engine_path = r"./stockfish-windows-x86-64-avx2.exe", multipv = 10)

    def init_display(self) -> None:
        pygame.init()
        self.width, self.height = 800, 800
        self.square_size, self.offset_x, self.offset_y = 100, 0, 0
        self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.timer = pygame.time.Clock()
        self.colours = {'default': (pygame.Color(240, 217, 181), pygame.Color(181, 136, 99)),
                        'highlight': (pygame.Color(115, 130, 85, 128), pygame.Color(115, 130, 85, 255)),
                        'last_move': pygame.Color(189, 186, 83, 128),
                        'capture': pygame.Color(204, 0, 0, 128)}
        self.piece_symbols = {
            'P': 'wp', 'p': 'bp', 'R': 'wr', 'r': 'br', 'N': 'wn', 'n': 'bn',
            'B': 'wb', 'b': 'bb', 'Q': 'wq', 'q': 'bq', 'K': 'wk', 'k': 'bk'}
        self.images = self.scale_images(self.load_images())

        pygame.display.set_caption('Chess Tactics Trainer')
        pygame.display.set_icon(self.images['bk'])

    def init_board(self, fen: str = chess.STARTING_FEN) -> None:
        self.board = chess.Board(fen)
        self.selected_piece = None
    
    def init_engine(self, use_engine: bool, engine_path: str, multipv: int) -> None:
        self.use_engine = use_engine
        self.engine = TacticsEngine(engine_path, self.board, multipv) if use_engine else None

    def load_images(self) -> dict:
        """
            Load the images for the chess pieces.
        """
        images = {}
        for symbol in self.piece_symbols.values():
            try:
                image = pygame.image.load(os.path.join('images', f'{symbol}.png'))
                images[symbol] = image
            except pygame.error as e:
                print(f"Error loading image for {symbol}: {e}")
                images[symbol] = None

        return images
    
    def scale_images(self, images: dict) -> dict:
        """
            Scale the images based on the square size.
        """
        for symbol, image in images.items():
            if image:
                image = pygame.transform.smoothscale(image, (self.square_size, self.square_size))
                images[symbol] = image

        return images
    
    def handle_resize(self, event: pygame.event.Event) -> None:
        """
            Handle the window resize event.
        """
        self.width, self.height = event.w, event.h
        self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)

        min_dimension = min(self.width, self.height)
        self.offset_x = (self.width - min_dimension) // 2
        self.offset_y = (self.height - min_dimension) // 2
        self.square_size = min_dimension // 8
        self.images = self.scale_images(self.images)

    def draw_piece(self, piece: chess.Piece, x: int, y: int) -> None:
        """
            Draw the chess piece on the board.
        """
        piece_image = self.images[self.piece_symbols[piece.symbol()]]
        if piece_image:
            self.window.blit(piece_image, pygame.Rect(x, y, self.square_size, self.square_size))

    def highlight_square(self, x: int, y: int, colour: pygame.Color) -> None:
        """
            Highlight a given square with the given colour.
        """
        board_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        board_surface.fill(colour)
        self.window.blit(board_surface, pygame.Rect(x, y, self.square_size, self.square_size))
            
    def highlight_logic(self, square: chess.Square, move: chess.Move, x: int, y: int) -> None:
        """
            Handles the logic for highlighting squares based on the selected piece and legal moves.
        """
        if square == self.selected_piece:
            self.highlight_square(x, y, self.colours['highlight'][1])
            return
        
        if move:
            if self.board.is_capture(move):
                self.highlight_square(x, y, self.colours['capture'])
            else:
                self.highlight_square(x, y, self.colours['highlight'][0])
            return
        
        if self.board.is_check() and square == self.board.king(self.board.turn):
            self.highlight_square(x, y, self.colours['capture'])
            return

        if self.board.move_stack:
            last_move = self.board.peek()
            if last_move and square in (last_move.from_square, last_move.to_square):
                self.highlight_square(x, y, self.colours['last_move'])
            return

    def draw(self) -> None:
        """
            Draw the chess board, pieces, and highlights.
        """
        for row in range(8):
            for col in range(8):
                # Get the square, colour, and position of the square
                square = chess.square(col, 7 - row)
                colour = self.colours['default'][(row + col) % 2]
                x, y = self.offset_x + col * self.square_size, self.offset_y + row * self.square_size
                piece = self.board.piece_at(square)
                pygame.draw.rect(self.window, colour, pygame.Rect(x, y, self.square_size, self.square_size))

                move = None
                if self.selected_piece:
                    try:
                        move = self.board.find_move(self.selected_piece, square)
                    except chess.IllegalMoveError:
                        pass
                self.highlight_logic(square, move, x, y)

                if piece:
                    self.draw_piece(piece, x, y)
                        
    def update_board(self) -> None:
        """
            Update the board state.
        """
        self.window.fill(self.colours['default'][1])
        self.draw()

    def handle_click(self, pos: tuple[int, int]) -> None:
        """
            Handle the mouse click event.
        """
        x, y = pos

        if x < self.offset_x or x > self.offset_x + 8 * self.square_size or \
        y < self.offset_y or y > self.offset_y + 8 * self.square_size:
            return
        
        col = (x - self.offset_x) // self.square_size
        row = 7 - (y - self.offset_y) // self.square_size
        square = chess.square(col, row)
        piece = self.board.piece_at(square)

        # Deselect the piece if it is clicked again
        if self.selected_piece == square:
            self.selected_piece = None
        # Move the selected piece to the clicked square if it is a legal move
        elif self.selected_piece:
            try:
                self.board.push(self.board.find_move(self.selected_piece, square))
                self.selected_piece = None
            except chess.IllegalMoveError:
                if piece and piece.color == self.board.turn:
                    self.selected_piece = square
        # Select the clicked piece if it is a valid piece
        elif piece and piece.color == self.board.turn:
            self.selected_piece = square
        else:
            self.selected_piece = None

        self.update_board()

    def make_engine_move(self) -> None:
        """
            Make a move using the engine.
        """
        move = self.engine.find_move(0.5)
        self.board.push(move)

    def run(self) -> None:
        """
            Main game loop.
        """
        running = True
        self.update_board()

        while running:
            # Limit the frame rate to 60 FPS
            self.timer.tick(60)

            if self.use_engine and self.board.turn == chess.BLACK:
                self.make_engine_move()
                self.update_board()
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.handle_resize(event)
                    self.update_board()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)

            if self.board.is_game_over():
                print(f"Game Over: {self.board.result()}")
                running = False

            pygame.display.flip()

        if self.use_engine:
            self.engine.close()
        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.run()