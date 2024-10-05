# Modules
import numpy as np
import pygame
import chess

# Initialize Pygame
pygame.init()

class ChessGame:
    def __init__(self):
        self.width, self.height = 800, 800
        self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
        self.colours = [pygame.Color(184, 139, 74), pygame.Color(227, 193, 111)]
        self.piece_symbols = {
            'P': 'wp', 'p': 'bp', 'R': 'wr', 'r': 'br', 'N': 'wn', 'n': 'bn',
            'B': 'wb', 'b': 'bb', 'Q': 'wq', 'q': 'bq', 'K': 'wk', 'k': 'bk'}
        self.timer = pygame.time.Clock()
        self.fps = 60
        self.board = chess.Board()
        self.images = self.load_images()
        self.running = True

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

    # Draw the chess board and pieces
    def draw(self):
        min_dimension = min(self.width, self.height)
        offset_x = (self.width - min_dimension) // 2
        offset_y = (self.height - min_dimension) // 2
        square_size = min_dimension // 8

        for r in range(8):
            for c in range(8):
                colour = self.colours[(r + c) % 2]
                pygame.draw.rect(self.window, colour, pygame.Rect(offset_x + c * square_size, 
                                                                  offset_y + r * square_size, 
                                                                  square_size, square_size))
                piece = self.board.piece_at(chess.square(c, 7 - r))
                
                if piece:
                    piece_image = self.images[self.piece_symbols[piece.symbol()]]
                    if piece_image:
                        piece_image = pygame.transform.scale(piece_image, (square_size, square_size))
                        self.window.blit(piece_image, pygame.Rect(offset_x + c * square_size, 
                                                                  offset_y + r * square_size, 
                                                                  square_size, square_size))
                        
    def update_board(self):
        self.window.fill(pygame.Color(184, 139, 74))
        self.draw()

    # Main game loop
    def run(self):
        self.update_board()

        while self.running:
            self.timer.tick(self.fps)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                elif event.type == pygame.VIDEORESIZE:
                    self.width, self.height = event.w, event.h
                    self.window = pygame.display.set_mode((self.width, self.height), pygame.RESIZABLE)
                    self.update_board()

            pygame.display.flip()
        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.run()