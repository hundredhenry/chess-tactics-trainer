# Modules
import numpy as np
import pygame
import chess

# Initialize Pygame
pygame.init()

class ChessGame:
    def __init__(self):
        self.width, self.height = 1000, 1000
        self.square_size, self.offset_x, self.offset_y = 125, 0, 0
        self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.colours = {'default': (pygame.Color(181, 136, 99), pygame.Color(240, 217, 181)),
                        'highlight': (pygame.Color(115, 130, 85, 255), pygame.Color(115, 130, 85, 128)),
                        'last_move': pygame.Color(189, 186, 83, 128),
                        'capture': pygame.Color(204, 0, 0, 128)}
        self.piece_symbols = {
            'P': 'wp', 'p': 'bp', 'R': 'wr', 'r': 'br', 'N': 'wn', 'n': 'bn',
            'B': 'wb', 'b': 'bb', 'Q': 'wq', 'q': 'bq', 'K': 'wk', 'k': 'bk'}
        self.timer = pygame.time.Clock()
        self.board = chess.Board()
        self.images = self.load_images()
        self.selected_piece = None

        pygame.display.set_caption('Chess Tactics Trainer')
        pygame.display.set_icon(self.images['bk'])

    # Load images for the chess pieces
    def load_images(self):
        images = {}
        for symbol in self.piece_symbols.values():
            try:
                image = pygame.image.load(f'images/{symbol}.png')
                images[symbol] = image
            except pygame.error as e:
                print(f"Error loading image for {symbol}: {e}")
                images[symbol] = None

        return images
    
    def update_square_size_offsets(self):
        min_dimension = min(self.width, self.height)
        self.offset_x = (self.width - min_dimension) // 2
        self.offset_y = (self.height - min_dimension) // 2
        self.square_size = min_dimension // 8

    # Draw the chess board and pieces
    def draw(self):
        for row in range(8):
            for col in range(8):
                square = chess.square(col, 7 - row)
                colour = self.colours['default'][(7 - row + col) % 2]
                move = None
                x, y = self.offset_x + col * self.square_size, self.offset_y + row * self.square_size
                piece = self.board.piece_at(square)
                pygame.draw.rect(self.window, colour, pygame.Rect(x, y, self.square_size, self.square_size))

                if self.selected_piece:
                    try:
                        move = self.board.find_move(self.selected_piece, square)
                    except chess.IllegalMoveError:
                        pass

                if square == self.selected_piece:
                    self.highlight_square(x, y, self.colours['highlight'][0])
                elif move:
                    if self.board.is_capture(move):
                        self.highlight_square(x, y, self.colours['capture'])
                    else:
                        self.highlight_square(x, y, self.colours['highlight'][1])
                elif self.board.is_check() and square == self.board.king(self.board.turn):
                    self.highlight_square(x, y, self.colours['capture'])
                elif self.board.move_stack:
                    last_move = self.board.peek()
                    if last_move and square in (last_move.from_square, last_move.to_square):
                        self.highlight_square(x, y, self.colours['last_move'])
                
                if piece:
                    piece_image = self.images[self.piece_symbols[piece.symbol()]]
                    if piece_image:
                        piece_image = pygame.transform.scale(piece_image, (self.square_size, self.square_size))
                        self.window.blit(piece_image, pygame.Rect(self.offset_x + col * self.square_size, 
                                                                  self.offset_y + row * self.square_size, 
                                                                  self.square_size, self.square_size))
                        
    def highlight_square(self, x, y, colour):
        board_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        board_surface.fill(colour)
        self.window.blit(board_surface, pygame.Rect(x, y, self.square_size, self.square_size))
                        
    def update_board(self):
        self.window.fill(self.colours['default'][0])
        self.draw()

    def handle_click(self, pos):
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
                move = self.board.find_move(self.selected_piece, square)
                self.board.push(move)
                self.selected_piece = None
            except chess.IllegalMoveError:
                self.selected_piece = square if piece and piece.color == self.board.turn else None
        # Select the clicked piece if it is a valid piece
        else:
            self.selected_piece = square if piece and piece.color == self.board.turn else None

        self.update_board()

    # Main game loop
    def run(self):
        running = True
        self.update_board()

        while running:
            # Limit the frame rate to 60 FPS
            self.timer.tick(60)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    self.update_square_size_offsets()
                    self.update_board()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_click(event.pos)
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.run()