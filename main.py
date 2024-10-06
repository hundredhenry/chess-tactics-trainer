# Modules
import numpy as np
import pygame
import chess

# Initialize Pygame
pygame.init()

class ChessGame:
    def __init__(self):
        self.width, self.height = 800, 800
        self.square_size, self.offset_x, self.offset_y = 100, 0, 0
        self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.colours = [pygame.Color(184, 139, 74), pygame.Color(227, 193, 111)]
        self.highlight_colours = [pygame.Color(129, 150, 105), pygame.Color(129, 150, 105)]
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

                if square == self.selected_piece:
                    colour = self.highlight_colours[(row + col) % 2]
                else:
                    colour = self.colours[(row + col) % 2]

                pygame.draw.rect(self.window, colour, pygame.Rect(self.offset_x + col * self.square_size, 
                                                                  self.offset_y + row * self.square_size, 
                                                                  self.square_size, self.square_size))
                piece = self.board.piece_at(square)
                
                if piece:
                    piece_image = self.images[self.piece_symbols[piece.symbol()]]
                    if piece_image:
                        piece_image = pygame.transform.scale(piece_image, (self.square_size, self.square_size))
                        self.window.blit(piece_image, pygame.Rect(self.offset_x + col * self.square_size, 
                                                                  self.offset_y + row * self.square_size, 
                                                                  self.square_size, self.square_size))
                        
    def update_board(self):
        self.window.fill(pygame.Color(184, 139, 74))
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
        
        if self.selected_piece:
            move = chess.Move(self.selected_piece, square)
            if move in self.board.legal_moves:
                self.board.push(move)
                self.selected_piece = None
        
        self.selected_piece = square if piece else None
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