# Modules
import os
import pygame
import pygame_gui
import pygame_menu
import chess
import random
from engine import TacticsEngine, Tactic, TACTIC_TYPES

SQUARE = [pygame.Color(240, 217, 181), pygame.Color(181, 136, 99)]
HIGHLIGHT_MOVE = pygame.Color(115, 130, 85, 128)
HIGHLIGHT_PIECE = pygame.Color(115, 130, 85, 255)
LAST_MOVE = pygame.Color(189, 186, 83, 128)
CAPTURE = pygame.Color(204, 0, 0, 128)
HINT = pygame.Color(49, 120, 115, 128)

class ChessGame:
    def __init__(self) -> None:
        self.init_display()

    def init_display(self) -> None:
        pygame.init()
        info = pygame.display.Info()

        self.width, self.height = info.current_h - 150, info.current_h - 100
        self.square_size = self.width // 8
        self.window = pygame.display.set_mode((self.width, self.height))
        self.timer = pygame.time.Clock()
        self.piece_symbols = {
            'P': 'wp', 'p': 'bp', 'R': 'wr', 'r': 'br', 'N': 'wn', 'n': 'bn',
            'B': 'wb', 'b': 'bb', 'Q': 'wq', 'q': 'bq', 'K': 'wk', 'k': 'bk'}
        self.images = self.load_images()
        self.player_colour = chess.WHITE

        pygame.display.set_caption('Chess Tactics Trainer')
        pygame.display.set_icon(self.images['bk'])

    def init_board(self, fen: str = chess.STARTING_FEN) -> None:
        self.board = chess.Board(fen)
        self.selected_piece = None
        self.highlight_hint = False
        self.engine_stack = []
        self.hint_move = None
    
    def init_engine(self) -> None:
        self.engine_path = r"./stockfish-windows-x86-64-avx2.exe"
        self.engine = TacticsEngine(self.engine_path, self.board, not self.player_colour)

    def load_images(self) -> dict:
        images = {}
        for symbol in self.piece_symbols.values():
            try:
                image = pygame.image.load(os.path.join('images', f'{symbol}.png'))
                scaled_image = pygame.transform.smoothscale(image, (self.square_size, self.square_size))
                images[symbol] = scaled_image
            except pygame.error as e:
                print(f"Error loading image for {symbol} from 'images/{symbol}.png': {e}")
                images[symbol] = None

        return images
    
    def set_player_colour(self, tuple: tuple, value: int) -> None:
        # Set the player colour to the selected value, or randomly if 'Random' is selected
        if tuple[0][0] == 'Random':
            self.player_colour = random.choice([chess.WHITE, chess.BLACK])
        else:
            self.player_colour = value

    def draw_piece(self, piece: chess.Piece, x: int, y: int) -> None:
        # Get the image for the piece
        piece_image = self.images[self.piece_symbols[piece.symbol()]]
        # Draw the piece on the board
        if piece_image:
            self.window.blit(piece_image, pygame.Rect(x, y, self.square_size, self.square_size))

    def highlight_square(self, x: int, y: int, colour: pygame.Color) -> None:
        # Highlight the square with the specified colour
        board_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        board_surface.fill(colour)
        self.window.blit(board_surface, pygame.Rect(x, y, self.square_size, self.square_size))
            
    def highlight_logic(self, square: chess.Square, move: chess.Move, x: int, y: int) -> None:
        if self.hint_move != None and square == self.hint_move.to_square:
            self.highlight_square(x, y, HINT)
            return

        if square == self.selected_piece:
            self.highlight_square(x, y, HIGHLIGHT_PIECE)
            return
        
        if move:
            if self.board.is_capture(move):
                self.highlight_square(x, y, CAPTURE)
            else:
                self.highlight_square(x, y, HIGHLIGHT_MOVE)
            return
        
        if self.board.is_check() and square == self.board.king(self.board.turn):
            self.highlight_square(x, y, CAPTURE)
            return

        if self.board.move_stack:
            last_move = self.board.peek()
            if last_move and square in (last_move.from_square, last_move.to_square):
                self.highlight_square(x, y, LAST_MOVE)

    def draw(self) -> None:
        if self.highlight_hint and len(self.engine_stack) > 0:
            self.hint_move = self.engine_stack[-1]
            self.selected_piece = self.hint_move.from_square

        for row in range(8):
            for col in range(8):
                # Flip row if playing as black
                visual_row = 7 - row if self.player_colour == chess.WHITE else row
                visual_col = col if self.player_colour == chess.WHITE else 7 - col
                square = chess.square(visual_col, visual_row)
                colour = SQUARE[(visual_row + visual_col) % 2]
                x, y = col * self.square_size, row * self.square_size
                piece = self.board.piece_at(square)
                pygame.draw.rect(self.window, colour, pygame.Rect(x, y, self.square_size, self.square_size))

                move = None
                if self.selected_piece != None:
                    try:
                        move = self.board.find_move(self.selected_piece, square)
                    except chess.IllegalMoveError:
                        pass

                self.highlight_logic(square, move, x, y)

                if piece:
                    self.draw_piece(piece, x, y)
                        
    def update_board(self) -> None:
        # Clear window and redraw the board
        self.window.fill((66,69,73))
        self.draw()

    def display_tactic_text(self) -> None:
        font = pygame.font.Font('freesansbold.ttf', 16)
        num_moves = (len(self.engine_stack) + 1) // 2
        
        if self.engine.current_tactic.type == TACTIC_TYPES['Checkmate']:
            text = font.render(f'Mate in {num_moves} moves', True, (255, 255, 255))
        elif self.engine.current_tactic.type == TACTIC_TYPES['Fork']:
            text = font.render(f'Fork in {num_moves} moves', True, (255, 255, 255))
        elif self.engine.current_tactic.type == TACTIC_TYPES['Absolute Pin']:
            text = font.render(f'Absolute Pin in {num_moves} moves', True, (255, 255, 255))
        elif self.engine.current_tactic.type == TACTIC_TYPES['Relative Pin']:
            text = font.render(f'Relative Pin in {num_moves} moves', True, (255, 255, 255))
        
        text_rect = text.get_rect()
        text_rect.center = (self.square_size, self.height - 25)
        self.window.blit(text, text_rect)

    def display_game_over(self, outcome: chess.Outcome) -> None:
        font = pygame.font.Font('freesansbold.ttf', 32)
        
        
        if outcome.winner == self.player_colour:
            text = font.render('You Won', True, (255, 255, 255))
        elif outcome.winner == (not self.player_colour):
            text = font.render('You Lost', True, (255, 255, 255))
        else:
            if outcome.termination == chess.Termination.STALEMATE:
                text = font.render('Draw: Stalemate', True, (255, 255, 255))
            elif outcome.termination == chess.Termination.FIFTY_MOVES:
                text = font.render('Draw: Fifty Move Rule', True, (255, 255, 255))
            elif outcome.termination == chess.Termination.THREEFOLD_REPETITION:
                text = font.render('Draw: Threefold Repetition', True, (255, 255, 255))
            elif outcome.termination == chess.Termination.INSUFFICIENT_MATERIAL:
                text = font.render('Draw: Insufficient Material', True, (255, 255, 255))

        text_rect = text.get_rect()
        text_rect.center = (self.width // 2, self.height // 2)
        self.window.blit(text, text_rect)

    def play_move_sound(self, move: chess.Move) -> None:
        if self.board.gives_check(move):
            pygame.mixer.Sound('sounds/move-check.mp3').play()
        elif self.board.is_capture(move):
            pygame.mixer.Sound('sounds/capture.mp3').play()
        elif move.promotion:
            pygame.mixer.Sound('sounds/promote.mp3').play()
        else:
            pygame.mixer.Sound('sounds/move-self.mp3').play()

    def handle_click(self, pos: tuple[int, int]) -> None:
        x, y = pos

        # Check if the click is within the board bounds
        if x < 0 or x > 8 * self.square_size or y < 0 or y > 8 * self.square_size:
            return
        
        # Get the row and column of the clicked square
        col = x // self.square_size if self.player_colour == chess.WHITE else 7 - (x // self.square_size)
        row = 7 - (y // self.square_size) if self.player_colour == chess.WHITE else y // self.square_size
        square = chess.square(col, row)
        piece = self.board.piece_at(square)

        if self.selected_piece == None:
            # Select the clicked piece if it is a valid piece
            if piece and piece.color == self.board.turn:
                self.selected_piece = square
        else:
            # Deselect the piece if it is clicked again
            if self.selected_piece == square:
                self.selected_piece = None  
            # Move the selected piece to the clicked square if it is a legal move
            else:
                try:
                    move = self.board.find_move(self.selected_piece, square)
                    self.play_move_sound(move)
                    self.board.push(move)
                    self.selected_piece = None
                    self.hint_move = None
                    self.highlight_hint = False
                except chess.IllegalMoveError:
                    if piece and piece.color == self.board.turn:
                        self.selected_piece = square

    def make_engine_move(self) -> None:
        # Pop the player move before the engine move
        if len(self.engine_stack) >= 2:
            expected_move = self.engine_stack.pop()
            # Check if the player has made the expected move
            if self.board.peek() != expected_move:
                self.engine_stack = self.engine.play_move()
        else:
            self.engine_stack = self.engine.play_move()
            
        move = self.engine_stack.pop()
        self.play_move_sound(move)
        self.board.push(move)

    def run(self) -> None:
        running = True
        self.init_board()
        self.init_engine()
        self.update_board()

        # UI elements
        manager = pygame_gui.UIManager((self.width, self.height), 'theme.json')
        tactic_status = pygame_gui.elements.UIStatusBar(relative_rect=pygame.Rect((0, self.height - 50, 2 * self.square_size, 50)),
                                                        manager=manager)
        hint_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((3 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Hint', manager=manager)
        undo_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((4 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Undo', manager=manager)
        reset_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((5 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                    text='Reset', manager=manager)
        menu_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((7 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Menu', manager=manager)
        pygame.display.update()

        while running:
            # Limit the frame rate to 60 FPS
            time_delta = self.timer.tick(60)
            manager.update(time_delta)
            manager.draw_ui(self.window)
            if self.engine.current_tactic:
                self.display_tactic_text()

            # Make the engine move if it is the engine's turn
            if not self.board.turn == self.player_colour and not self.board.is_game_over():
                self.make_engine_move()
                if self.engine.current_tactic:
                    tactic_status.percent_full = 100
                else:
                    tactic_status.percent_full = 0

                self.update_board()

            outcome = self.board.outcome()
            if outcome:
                self.display_game_over(outcome)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                    self.engine.close()
                    exit()
                    
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    # Get hint
                    if event.ui_element == hint_button:
                        if self.engine.current_tactic:
                            self.highlight_hint = True
                            self.update_board()
                    # Undo move
                    elif event.ui_element == undo_button:
                        if len(self.board.move_stack) >= 2:
                            # Pop the engine move and the player move before it
                            self.board.pop()
                            self.board.pop()
                            self.selected_piece = None
                            self.engine_stack = []
                            self.engine.current_tactic = None
                            self.update_board()
                    # Reset board
                    elif event.ui_element == reset_button:
                        self.init_board()
                        # Reinitialize the engine
                        self.engine.close()
                        self.init_engine()
                        self.engine.current_tactic = None
                        self.update_board()
                    # Return to the main menu
                    elif event.ui_element == menu_button:
                        running = False
                        self.engine.close()
                        break
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self.handle_click(event.pos)
                    self.update_board()
                
                manager.process_events(event)

            pygame.display.flip()

    def menu(self) -> None:
        running = True
        # Create the menus
        main_menu = pygame_menu.Menu('Chess Tactics Trainer', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)
        game_menu = pygame_menu.Menu('Start Game', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)
        settings_menu = pygame_menu.Menu('Settings', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)

        # Main menu buttons
        main_menu.add.button('Start', game_menu)
        main_menu.add.button('Settings', settings_menu)
        main_menu.add.button('Quit', pygame_menu.events.EXIT)

        # Game settings menu buttons
        game_menu.add.selector('Player Colour:', [('White', chess.WHITE), ('Black', chess.BLACK), ('Random', -1)], default=0,
                               onchange=self.set_player_colour, style=pygame_menu.widgets.SELECTOR_STYLE_FANCY)
        game_menu.add.button('Start Game', self.run)
        
        while running:
            events = pygame.event.get()

            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

            main_menu.update(events)
            main_menu.draw(self.window)
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.menu()