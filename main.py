# Modules
import os
import pygame
import pygame_gui
import pygame_menu
import chess
import random
from engine import TacticsEngine,  TACTIC_TYPES

SQUARE = [pygame.Color(240, 217, 181), pygame.Color(181, 136, 99)]
HIGHLIGHT_MOVE = pygame.Color(115, 130, 85, 128)
HIGHLIGHT_PIECE = pygame.Color(115, 130, 85, 255)
LAST_MOVE = pygame.Color(189, 186, 83, 128)
CAPTURE = pygame.Color(204, 0, 0, 128)
HINT = pygame.Color(49, 120, 115, 128)

class Puzzle:
    def __init__(self, tactic_type: int, fen: str, moves: list[chess.Move]) -> None:
        self.tactic_type = tactic_type
        self.fen = fen
        self.moves = moves

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
        self.sounds = self.load_sounds()
        self.player_colour = chess.WHITE
        self.difficulty = 2
        self.tactic_types = [0, 1, 2, 3]

        pygame.display.set_caption('Chess Tactics Trainer')
        pygame.display.set_icon(self.images['bk'])

    def init_board(self, fen: str = chess.STARTING_FEN) -> None:
        self.board = chess.Board(fen)
        self.selected_piece = None
        self.highlight_hint = False
        self.hint_move = None
    
    def init_engine(self, difficulty: int, tactic_types: list[int]) -> None:
        self.engine_path = r"./stockfish-windows-x86-64-avx2.exe"
        self.engine = TacticsEngine(self.engine_path, self.board, not self.player_colour)
        self.engine.set_difficulty(difficulty)
        self.engine.set_tactic_types(tactic_types)

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
    
    def load_sounds(self) -> None:
        sounds = {
            'move_check': pygame.mixer.Sound('sounds/move-check.mp3'),
            'capture': pygame.mixer.Sound('sounds/capture.mp3'),
            'promote': pygame.mixer.Sound('sounds/promote.mp3'),
            'move_self': pygame.mixer.Sound('sounds/move-self.mp3')
        }
        return sounds
    
    def set_player_colour(self, selection: tuple, value: int) -> None:
        # Set the player colour to the selected value, or randomly if 'Random' is selected
        if selection[0][0] == 'Random':
            self.player_colour = random.choice([chess.WHITE, chess.BLACK])
        else:
            self.player_colour = value

    def set_difficulty(self, selection: tuple, value: int) -> None:
        # Set the difficulty to the selected value
        self.difficulty = value

    def set_tactic_types(self, value: list[int]) -> None:
        # Set the tactic types to the selected values
        self.tactic_types = value[-1]

    def draw_piece(self, piece: chess.Piece, x: int, y: int) -> None:
        # Draw the piece on the board
        piece_image = self.images.get(self.piece_symbols[piece.symbol()])
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
        if self.highlight_hint and self.engine.current_tactic.moves_left() > 0:
            self.hint_move = self.engine.current_tactic.hint_move()
            self.selected_piece = self.hint_move.from_square
        else:
            self.hint_move = None

        legal_moves = {}
        if self.selected_piece is not None:
            legal_moves = {move.to_square: move for move in self.board.legal_moves if move.from_square == self.selected_piece}

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

                move = legal_moves.get(square, None)
                self.highlight_logic(square, move, x, y)
                if piece:
                    self.draw_piece(piece, x, y)
                    
    def update_board(self) -> None:
        # Clear window and redraw the board
        self.window.fill((66,69,73))
        self.draw()

    def display_tactic_text(self) -> None:
        font = pygame.font.Font('freesansbold.ttf', 16)
        num_moves = self.engine.current_tactic.moves_left()
        tactic_messages = {
            TACTIC_TYPES['Checkmate']: 'Mate in {num_moves} moves',
            TACTIC_TYPES['Fork']: 'Fork in {num_moves} moves',
            TACTIC_TYPES['Absolute Pin']: 'Absolute Pin in {num_moves} moves',
            TACTIC_TYPES['Relative Pin']: 'Relative Pin in {num_moves} moves'
        }
        message = tactic_messages.get(self.engine.current_tactic.type, '').format(num_moves=num_moves)
        text = font.render(message, True, (255, 255, 255))
        text_rect = text.get_rect()
        text_rect.center = (self.square_size, self.height - 25)
        self.window.blit(text, text_rect)

    def display_game_over(self, outcome: chess.Outcome) -> None:
        font = pygame.font.Font('freesansbold.ttf', 42)
        
        if outcome.winner == self.player_colour:
            text = font.render('You Won', True, (0, 0, 0))
        elif outcome.winner == (not self.player_colour):
            text = font.render('You Lost', True, (0, 0, 0))
        else:
            draw_messages = {
                chess.Termination.STALEMATE: 'Draw: Stalemate',
                chess.Termination.FIFTY_MOVES: 'Draw: Fifty Move Rule',
                chess.Termination.THREEFOLD_REPETITION: 'Draw: Threefold Repetition',
                chess.Termination.INSUFFICIENT_MATERIAL: 'Draw: Insufficient Material'
            }
            text = font.render(draw_messages.get(outcome.termination, 'Draw'), True, (0, 0, 0))

        text_rect = text.get_rect()
        text_rect.center = (self.width // 2, self.height // 2)
        self.window.blit(text, text_rect)

    def play_move_sound(self, move: chess.Move) -> None:
        if self.board.gives_check(move):
            self.sounds['move_check'].play()
        elif self.board.is_capture(move):
            self.sounds['capture'].play()
        elif move.promotion:
            self.sounds['promote'].play()
        else:
            self.sounds['move_self'].play()

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
        move = self.engine.play_move()
        self.play_move_sound(move)
        self.board.push(move)
        if not self.engine.current_tactic:
            self.engine.tactic_search()

    def run(self, puzzles: list[Puzzle] = None) -> None:
        running = True
        # Initialize the board and engine
        if puzzles:
            self.init_board(puzzles[0].fen)
            self.board.push(puzzles[0].moves[0])
            self.player_colour = self.board.turn
            self.puzzle_index = 0
        else:
            self.init_board()

        self.init_engine(self.difficulty, self.tactic_types)
        self.update_board()

        # UI elements
        manager = pygame_gui.UIManager((self.width, self.height), 'theme.json')
        tactic_status = pygame_gui.elements.UIStatusBar(relative_rect=pygame.Rect((0, self.height - 50, 2 * self.square_size, 50)),
                                                        manager=manager)
        hint_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((2 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Hint', manager=manager)
        undo_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((3 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Undo', manager=manager)
        reset_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((4 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                    text='Reset', manager=manager)
        menu_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((7 * self.square_size, self.height - 50, self.square_size, 50)), 
                                                   text='Menu', manager=manager)
        if puzzles:
            prev_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((5 * self.square_size, self.height - 50, self.square_size, 50)),
                                                        text='Previous', manager=manager)
            next_button = pygame_gui.elements.UIButton(relative_rect=pygame.Rect((6 * self.square_size, self.height - 50, self.square_size, 50)),
                                                        text='Next', manager=manager)
        pygame.display.update()

        if puzzles:
            self.engine.tactic_search(True)

        while running:
            # Limit the frame rate to 60 FPS
            time_delta = self.timer.tick(60)
            manager.update(time_delta)
            manager.draw_ui(self.window)
            if self.engine.current_tactic:
                self.display_tactic_text()
                tactic_status.percent_full = 100
            else:
                tactic_status.percent_full = 0

            # Make the engine move if it is the engine's turn
            if not self.board.turn == self.player_colour and not self.board.is_game_over():
                self.make_engine_move()
                self.update_board()

            outcome = self.board.outcome()
            if outcome:
                self.engine.current_tactic = None
                self.display_game_over(outcome)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.engine.close()
                    pygame.quit()
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
                            self.highlight_hint = False
                            if self.engine.current_tactic:
                                self.engine.undo_tactic_move()
                            else:
                                if self.board.fullmove_number in self.engine.tactic_cache:
                                    self.engine.current_tactic = self.engine.tactic_cache[self.board.fullmove_number]
                                    tactic_status.percent_full = 100
                                else:
                                    self.engine.tactic_search()

                            self.update_board()
                    # Reset board
                    elif event.ui_element == reset_button:
                        self.init_board()
                        # Reinitialize the engine
                        self.engine.reset_engine(self.board, not self.player_colour)
                        self.update_board()
                    # Go to the previous puzzle
                    elif event.ui_element == prev_button:
                        if self.puzzle_index > 0:
                            self.puzzle_index -= 1
                            self.init_board(puzzles[self.puzzle_index].fen)
                            self.board.push(puzzles[self.puzzle_index].moves[0])
                            self.player_colour = self.board.turn
                            # Reinitialize the engine
                            self.engine.reset_engine(self.board, not self.player_colour)
                            self.engine.tactic_search(True)
                            self.update_board()
                    # Go to the next puzzle
                    elif event.ui_element == next_button:
                        if self.puzzle_index < len(puzzles) - 1:
                            self.puzzle_index += 1
                            self.init_board(puzzles[self.puzzle_index].fen)
                            self.board.push(puzzles[self.puzzle_index].moves[0])
                            self.player_colour = self.board.turn
                            # Reinitialize the engine
                            self.engine.reset_engine(self.board, not self.player_colour)
                            self.engine.tactic_search(True)
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

    def puzzle_demo(self) -> None:
        puzzles = []
        # Load the FENs and moves from the puzzles.csv file
        with open('puzzles.csv', 'r') as file:
            lines = file.readlines()
            for line in lines:
                tactic_type, fen, moves = line.strip().split(',')
                moves = [chess.Move.from_uci(move) for move in moves.split()]
                puzzles.append(Puzzle(int(tactic_type), fen, moves))

        self.run(puzzles)
        
    def menu(self) -> None:
        running = True
        # Create the menus
        main_menu = pygame_menu.Menu('Chess Tactics Trainer', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)
        game_menu = pygame_menu.Menu('Game Configuration', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)
        settings_menu = pygame_menu.Menu('Settings', self.width, self.height, theme=pygame_menu.themes.THEME_DEFAULT)

        # Main menu buttons
        main_menu.add.button('Start', game_menu, align=pygame_menu.locals.ALIGN_LEFT, font_size=64, margin=(50, 50), 
                             selection_effect=None)
        main_menu.add.button('Puzzle Demo', self.puzzle_demo, align=pygame_menu.locals.ALIGN_LEFT, font_size=64, margin=(50, 50),
                             selection_effect=None)
        main_menu.add.button('Settings', settings_menu, align=pygame_menu.locals.ALIGN_LEFT, font_size=64, margin=(50, 50), 
                             selection_effect=None)
        main_menu.add.button('Quit', pygame_menu.events.EXIT, align=pygame_menu.locals.ALIGN_LEFT, font_size=64, margin=(50, 50),
                             selection_effect=None)

        # Game settings menu buttons
        game_menu.add.selector('Player Colour:', [('White', chess.WHITE), ('Black', chess.BLACK), ('Random', -1)], default=0,
                               onchange=self.set_player_colour, style=pygame_menu.widgets.SELECTOR_STYLE_FANCY, 
                               align=pygame_menu.locals.ALIGN_RIGHT, font_size=52, margin=(-75, 25), selection_effect=None)
        game_menu.add.dropselect_multiple('Tactic Types:', [('Checkmate', TACTIC_TYPES['Checkmate']), ('Fork', TACTIC_TYPES['Fork']), 
                                                           ('Absolute Pin', TACTIC_TYPES['Absolute Pin']), ('Relative Pin', TACTIC_TYPES['Relative Pin'])],
                                        default=[TACTIC_TYPES['Checkmate'], TACTIC_TYPES['Fork'], TACTIC_TYPES['Absolute Pin'], TACTIC_TYPES['Relative Pin']],
                                        onchange=self.set_tactic_types, align=pygame_menu.locals.ALIGN_RIGHT, font_size=52, margin=(-75, 25), selection_effect=None)
        game_menu.add.selector('Difficulty:', [('Easy', 1), ('Medium', 2), ('Hard', 3)], default=1, 
                               onchange=self.set_difficulty, style=pygame_menu.widgets.SELECTOR_STYLE_FANCY,
                               align=pygame_menu.locals.ALIGN_RIGHT, font_size=52, margin=(-75, 25), selection_effect=None)
        game_menu.add.button('Start Game', self.run, font_size=64, margin=(0, 50), selection_effect=None)
        
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