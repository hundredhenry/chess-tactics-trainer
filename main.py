# Modules
import os
import random
import pygame
import pygame_gui
import pygame_menu
import chess
from dataclasses import dataclass
from engine import TacticsEngine,  TACTIC_TYPES

# Colors for board and highlights
COLOURS = {
    "LIGHT_SQUARE": pygame.Color(240, 217, 181),
    "DARK_SQUARE": pygame.Color(181, 136, 99),
    "HIGHLIGHT_MOVE": pygame.Color(115, 130, 85, 128),
    "HIGHLIGHT_PIECE": pygame.Color(115, 130, 85, 255),
    "LAST_MOVE": pygame.Color(189, 186, 83, 128),
    "CAPTURE": pygame.Color(204, 0, 0, 128),
    "HINT": pygame.Color(49, 120, 115, 128),
    "BACKGROUND": pygame.Color(66, 69, 73),
    "TEXT": pygame.Color(255, 255, 255),
    "NOTATION_TEXT": pygame.Color(0, 0, 0),
    "GAME_OVER_TEXT": pygame.Color(0, 0, 0)
}

ENGINE_PATH = "./stockfish-windows-x86-64-bmi2.exe"

@dataclass
class Puzzle:
    """Represents a chess puzzle with a position and solution moves."""
    tactic_type: int
    fen: str
    moves: list[chess.Move]

class ChessGame:
    """Class to represent the chess game and handle the game logic."""

    def __init__(self) -> None:
        """Initialize the game display and default settings."""
        pygame.init()
        info = pygame.display.Info()
        self.width = info.current_h - 150
        self.height = info.current_h - 100
        self.square_size = self.width // 8

        self._load_assets()
        self._setup_display()
        self._init_game_settings()

    def _setup_display(self):
        """Configure the game window and display properties."""
        # Set window icon
        pygame.display.set_caption("Chess Tactics Trainer")
        icon = pygame.transform.smoothscale(self.images['bk'], (32, 32))
        pygame.display.set_icon(icon)
        # Set window size and display
        self.window = pygame.display.set_mode((self.width, self.height))

    def _load_assets(self):
        """Load game assets like pieces, images, and sounds."""
        # Piece symbol mapping for image loading
        self.piece_symbols = {
            'P': 'wp', 'p': 'bp', 'R': 'wr', 'r': 'br',
            'N': 'wn', 'n': 'bn', 'B': 'wb', 'b': 'bb',
            'Q': 'wq', 'q': 'bq', 'K': 'wk', 'k': 'bk'
        }
        
        # Load piece images and sounds
        self.images = self._load_images()
        self.sounds = self._load_sounds()
        
    def _init_game_settings(self):
        """Initialize default game settings."""
        self.player_colour = chess.WHITE
        self.difficulty = None
        self.tactic_types = list(TACTIC_TYPES.values())  # All tactic types enabled by default
        self.board = None
        self.engine = None
        self.puzzle_mode = False
        self.puzzles = []

    def _load_images(self) -> dict:
        """Load chess piece images from file."""
        images = {}
        for symbol in self.piece_symbols.values():
            try:
                image_path = os.path.join("images", f'{symbol}.png')
                image = pygame.image.load(image_path)
                scaled_image = pygame.transform.smoothscale(image, (self.square_size, self.square_size))
                images[symbol] = scaled_image
            except pygame.error as e:
                print(f"Error loading image for {symbol} from 'images/{symbol}.png': {e}")
                images[symbol] = None

        return images
    
    def _load_sounds(self) -> dict:
        """Load chess move sound effects."""
        return {
            "capture": pygame.mixer.Sound("sounds/capture.mp3"),
            "move": pygame.mixer.Sound("sounds/move.mp3"),
            "complete": pygame.mixer.Sound("sounds/complete.mp3"),
            "notify": pygame.mixer.Sound("sounds/notify.mp3"),
            "correct": pygame.mixer.Sound("sounds/correct.mp3"),
            "incorrect": pygame.mixer.Sound("sounds/incorrect.mp3")
        }

    def _init_board(self, fen: str = chess.STARTING_FEN) -> None:
        """Initialize the chess board with the given FEN position."""
        self.board = chess.Board(fen)
        self.selected_piece = None
        self.highlight_hint = False
        self.hint_move = None
    
    def _init_engine(self, difficulty: int, tactic_types: list[int]) -> None:
        """Initialize the chess engine with specified difficulty and tactic types."""
        self.engine = TacticsEngine(ENGINE_PATH, self.board, not self.player_colour)
        self.engine.set_difficulty(difficulty)
        self.engine.set_tactic_types(tactic_types)
    
    def _set_player_colour(self, selection: tuple, value: int) -> None:
        """Set the player's color (white, black, or random)."""
        if selection[0][0] == "Random":
            self.player_colour = random.choice([chess.WHITE, chess.BLACK])
        else:
            self.player_colour = value

    def _set_difficulty(self, _, value: int) -> None:
        """Set the game difficulty."""
        self.difficulty = value

    def _set_tactic_types(self, value: list[int]) -> None:
        """Set the types of tactics to practice."""
        self.tactic_types = value[-1]

    def _draw_piece(self, piece: chess.Piece, x: int, y: int) -> None:
        """Draw a chess piece on the board."""
        piece_image = self.images.get(self.piece_symbols[piece.symbol()])
        if piece_image:
            self.window.blit(piece_image, pygame.Rect(x, y, self.square_size, self.square_size))

    def _highlight_square(self, x: int, y: int, colour: pygame.Color) -> None:
        """Highlight a square with the specified color."""
        board_surface = pygame.Surface((self.square_size, self.square_size), pygame.SRCALPHA)
        board_surface.fill(colour)
        self.window.blit(board_surface, pygame.Rect(x, y, self.square_size, self.square_size))
            
    def _apply_highlighting(self, square: chess.Square, move: chess.Move, x: int, y: int) -> None:
        """Apply appropriate highlighting to squares based on game state."""    
        # Hint highlighting has top priority
        if self.hint_move != None and square == self.hint_move.to_square:
            self._highlight_square(x, y, COLOURS["HINT"])
            return

        # Selected piece highlighting
        if square == self.selected_piece:
            self._highlight_square(x, y, COLOURS["HIGHLIGHT_PIECE"])
            return
        
        # Move highlighting
        if move:
            highlight_color = COLOURS["CAPTURE"] if self.board.is_capture(move) else COLOURS["HIGHLIGHT_MOVE"]
            self._highlight_square(x, y, highlight_color)
            return
        
        # Check highlighting
        if self.board.is_check() and square == self.board.king(self.board.turn):
            self._highlight_square(x, y, COLOURS["CAPTURE"])
            return

        # Last move highlighting
        if self.board.move_stack:
            last_move = self.board.peek()
            if last_move and square in (last_move.from_square, last_move.to_square):
                self._highlight_square(x, y, COLOURS["LAST_MOVE"])

    def _draw_board(self) -> None:
        """Draw the complete chess board with pieces and highlights."""
        # Update hint move if available
        if self.highlight_hint and self.engine.current_tactic.moves_left() > 0:
            self.hint_move = self.engine.current_tactic.hint_move()
            self.selected_piece = self.hint_move.from_square
        else:
            self.hint_move = None

        # Get legal moves for selected piece
        legal_moves = {}
        if self.selected_piece is not None:
            legal_moves = {
                move.to_square: move for move in self.board.legal_moves 
                if move.from_square == self.selected_piece
            }

        # Draw the board and pieces
        for row in range(8):
            for col in range(8):
                # Get square information
                square = chess.square(col, row)
                if (row + col) % 2 == 0:
                    square_color = COLOURS["DARK_SQUARE"]
                else:
                    square_color = COLOURS["LIGHT_SQUARE"]

                # Pygame coordinates start at (0, 0) in the top left corner
                if self.player_colour == chess.WHITE:
                    square_x = col * self.square_size
                    square_y = (7 - row) * self.square_size
                else:
                    square_x = (7 - col) * self.square_size
                    square_y = row * self.square_size

                # Draw square
                pygame.draw.rect(
                    self.window, 
                    square_color, 
                    pygame.Rect(square_x, square_y, self.square_size, self.square_size)
                )

                # Apply highlighting
                move = legal_moves.get(square)
                self._apply_highlighting(square, move, square_x, square_y)

                # Draw piece if present
                piece = self.board.piece_at(square)
                if piece:
                    self._draw_piece(piece, square_x, square_y)

        # Draw coordinate notations
        font = pygame.font.Font("freesansbold.ttf", 14)
        offset = 15  # Offset from the edge of the square
        
        # Draw file coordinates (a-h) along the bottom
        for col in range(8):
            file_idx = col if self.player_colour == chess.WHITE else 7 - col
            file_letter = chr(ord('a') + file_idx)
            file_text = font.render(file_letter, True, COLOURS["NOTATION_TEXT"])
            self.window.blit(file_text, (
                col * self.square_size + self.square_size - offset,
                8 * self.square_size - offset
            ))

        offset = 5  # Offset from the edge of the square
        # Draw rank coordinates (1-8) along the left side
        for row in range(8):
            rank_idx = 7 - row if self.player_colour == chess.WHITE else row
            rank_number = str(rank_idx + 1)
            rank_text = font.render(rank_number, True, COLOURS["NOTATION_TEXT"])
            self.window.blit(rank_text, (
                offset, 
                row * self.square_size + offset
            ))
                    
    def _update_board(self) -> None:
        # Clear window and redraw the board
        self.window.fill(COLOURS["BACKGROUND"])
        self._draw_board()

    def _display_tactic_text(self) -> None:
        """Display the current tactic message on the screen."""
        font = pygame.font.Font("freesansbold.ttf", 14)
        num_moves = self.engine.current_tactic.moves_left()
        tactic_messages = {
            TACTIC_TYPES["Checkmate"]: f'Mate in {num_moves} moves',
            TACTIC_TYPES["Fork"]: f'Fork in {num_moves} moves',
            TACTIC_TYPES["Absolute Pin"]: f'Absolute Pin in {num_moves} moves',
            TACTIC_TYPES["Relative Pin"]: f'Relative Pin in {num_moves} moves'
        }
        message = tactic_messages.get(self.engine.current_tactic.type, '')
        text = font.render(message, True, COLOURS["TEXT"])
        text_rect = text.get_rect(center=(self.square_size, self.height - 25))
        self.window.blit(text, text_rect)

    def _display_game_over(self, outcome: chess.Outcome) -> None:
        """Display game over message with the outcome."""
        font = pygame.font.Font("freesansbold.ttf", 42)
        
        if outcome.winner == self.player_colour:
            message = "You Won"
        elif outcome.winner == (not self.player_colour):
            message = "You Lost"
        else:
            # Draw message based on termination type
            draw_messages = {
                chess.Termination.STALEMATE: "Draw: Stalemate",
                chess.Termination.FIFTY_MOVES: "Draw: Fifty Move Rule",
                chess.Termination.THREEFOLD_REPETITION: "Draw: Threefold Repetition",
                chess.Termination.INSUFFICIENT_MATERIAL: "Draw: Insufficient Material"
            }
            message = draw_messages.get(outcome.termination, "Draw")

        text = font.render(message, True, COLOURS["GAME_OVER_TEXT"])
        text_rect = text.get_rect(center=(self.width // 2, self.height // 2))
        self.window.blit(text, text_rect)

    def _play_move_sound(self, move: chess.Move) -> None:
        """Play sound effect based on the move type."""
        if self.board.is_capture(move):
            self.sounds["capture"].play()
        else:
            self.sounds["move"].play()

    def _handle_click(self, pos: tuple[int, int]) -> None:
        """Handle mouse click on the chess board."""
        x, y = pos

        # Check if the click is within the board bounds
        if not (0 <= x < 8 * self.square_size and 0 <= y < 8 * self.square_size):
            return
        
        # Convert screen coordinates to chess square
        col = x // self.square_size
        row = y // self.square_size

        # Adjust for player perspective
        if self.player_colour == chess.WHITE:
            col_adjusted = col
            row_adjusted = 7 - row
        else:
            col_adjusted = 7 - col
            row_adjusted = row
        
        square = chess.square(col_adjusted, row_adjusted)
        piece = self.board.piece_at(square)

        # Handle piece selection and move
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
                    self._play_move_sound(move)
                    self.board.push(move)
                    self.selected_piece = None
                    self.hint_move = None
                    self.highlight_hint = False

                    # Update tactic state
                    if self.engine.current_tactic:
                        if self.engine.current_tactic.next_move() != move:
                            self.sounds["incorrect"].play()
                            self.engine.end_tactic()
                        elif self.engine.current_tactic.index > self.engine.current_tactic.max_index:
                            self.sounds["complete"].play()
                            self.engine.end_tactic()
                        else:
                            self.sounds["correct"].play()

                except chess.IllegalMoveError:
                    # Select a different piece if clicked on another valid piece
                    if piece and piece.color == self.board.turn:
                        self.selected_piece = square

    def _make_engine_move(self) -> None:
        """Make the engine's move and update the board state."""
        move = self.engine.play_move()
        self._play_move_sound(move)
        self.board.push(move)

    def _handle_undo(self):
        """Handle undo button press."""
        if len(self.board.move_stack) >= 2:
            # Pop the engine move and the player move before it
            self.board.pop()
            self.board.pop()
            self.selected_piece = None
            self.highlight_hint = False
            
            # Update tactic state
            if self.engine.current_tactic:
                self.engine.undo_tactic_move()
            else:
                self.engine.tactic_search()

            self._update_board()

    def _goto_puzzle(self, index):
        """Go to the specified puzzle."""
        if 0 <= index < len(self.puzzles):
            self.puzzle_index = index
            self._init_board(self.puzzles[index].fen)
            self.board.push(self.puzzles[index].moves[0])
            self.player_colour = self.board.turn
            
            # Reset engine for new puzzle
            self.engine.reset_engine(self.board, not self.player_colour)
            self.engine.tactic_search()
            self._update_board()

    def _setup_ui(self) -> tuple:
        """Set up UI elements for the game."""
        manager = pygame_gui.UIManager((self.width, self.height), "theme.json")
        ui_elements = {}
        
        # Common UI elements
        ui_elements["tactic_status"] = pygame_gui.elements.UIStatusBar(
            relative_rect=pygame.Rect((0, self.height - 50, 2 * self.square_size, 50)),
            manager=manager
        )
        
        ui_elements["hint_button"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((2 * self.square_size, self.height - 50, self.square_size, 50)), 
            text='Hint', manager=manager
        )
        
        ui_elements["undo_button"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((3 * self.square_size, self.height - 50, self.square_size, 50)), 
            text='Undo', manager=manager
        )
        
        ui_elements["reset_button"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((4 * self.square_size, self.height - 50, self.square_size, 50)), 
            text='Reset', manager=manager
        )
        
        ui_elements["menu_button"] = pygame_gui.elements.UIButton(
            relative_rect=pygame.Rect((7 * self.square_size, self.height - 50, self.square_size, 50)), 
            text='Menu', manager=manager
        )
        
        # Puzzle mode specific buttons
        if self.puzzle_mode:
            ui_elements["prev_button"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((5 * self.square_size, self.height - 50, self.square_size, 50)),
                text='Previous', manager=manager
            )
            
            ui_elements["next_button"] = pygame_gui.elements.UIButton(
                relative_rect=pygame.Rect((6 * self.square_size, self.height - 50, self.square_size, 50)),
                text='Next', manager=manager
            )
            
        pygame.display.update()
        return manager, ui_elements
    
    def _handle_button_click(self, event: pygame.event.Event, ui_elements: dict) -> bool:
        """Handle UI button click events."""
        # Handle hint
        if event.ui_element == ui_elements["hint_button"]:
            if self.engine.current_tactic:
                self.highlight_hint = True
                self._update_board()
        # Handle undo
        elif event.ui_element == ui_elements["undo_button"]:
            self._handle_undo()
        # Handle reset
        elif event.ui_element == ui_elements["reset_button"]:
            if self.puzzle_mode:
                self._init_board(self.puzzles[self.puzzle_index].fen)
                self.board.push(self.puzzles[self.puzzle_index].moves[0])
                self.player_colour = self.board.turn
            else:
                self._init_board()

            self.engine.reset_engine(self.board, not self.player_colour)
            if self.puzzle_mode:
                self.engine.tactic_search()
            
            self._update_board()
        # Handle previous puzzle
        elif self.puzzle_mode and event.ui_element == ui_elements["prev_button"]:
            self._goto_puzzle(self.puzzle_index - 1)
        # Handle next puzzle
        elif self.puzzle_mode and event.ui_element == ui_elements["next_button"]:
            self._goto_puzzle(self.puzzle_index + 1)
        # Handle menu
        elif event.ui_element == ui_elements["menu_button"]:
            self.engine.close()
            self._init_game_settings()
            # Exit game loop
            return False
        
        # Continue game loop
        return True
            
    def _run(self) -> None:
        """Run the main game loop."""
        running = True
        timer = pygame.time.Clock()

        # Initialize the board and engine based on game mode
        if self.puzzle_mode:
            self._init_board(self.puzzles[0].fen)
            self.board.push(self.puzzles[0].moves[0])
            self.player_colour = self.board.turn
            self.puzzle_index = 0
            self.difficulty = 2
        else:
            self._init_board()

        self._init_engine(self.difficulty, self.tactic_types)
        self._update_board()

        manager, ui_elements = self._setup_ui()

        if self.puzzle_mode:
            self.engine.tactic_search()

        while running:
            # Limit the frame rate to 60 FPS
            time_delta = timer.tick(60)
            manager.update(time_delta)
            # Update tactic status display
            if self.engine.current_tactic:
                ui_elements["tactic_status"].percent_full = 100
            else:
                ui_elements["tactic_status"].percent_full = 0

            # Make the engine move if it is the engine's turn
            if self.board.turn != self.player_colour and not self.board.is_game_over():
                self._make_engine_move()
                self._update_board()

            # Check for game over conditions
            outcome = self.board.outcome()
            if outcome:
                self._display_game_over(outcome)
            
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.engine.close()
                    pygame.quit()
                    exit()
                    
                if event.type == pygame_gui.UI_BUTTON_PRESSED:
                    running = self._handle_button_click(event, ui_elements)
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    self._handle_click(event.pos)
                    self._update_board()
                
                manager.process_events(event)
            
            # Exit game loop if menu button is clicked
            if not running:
                break

            manager.draw_ui(self.window)
            # Display tactic text after UI is drawn so it appears on top
            if self.engine.current_tactic:
                self._display_tactic_text()
                
            pygame.display.flip()
            
    def _puzzle_demo(self) -> None:
        """Run the puzzle demo mode."""
        self.puzzle_mode = True
        # Load the FENs and moves from the puzzles.csv file
        with open("puzzles.csv", 'r') as file:
            lines = file.readlines()
            for line in lines:
                tactic_type, fen, moves = line.strip().split(',')
                moves = [chess.Move.from_uci(move) for move in moves.split()]
                self.puzzles.append(Puzzle(int(tactic_type), fen, moves))

        self._run()

    def _create_menus(self) -> None:
        """Create the game menus."""
        menus = {}
        
        # Create menu instances
        menus["main"] = pygame_menu.Menu(
            "Chess Tactics Trainer", 
            self.width, self.height, 
            theme=pygame_menu.themes.THEME_DEFAULT
        )
        
        menus["game"] = pygame_menu.Menu(
            "Game Configuration", 
            self.width, self.height, 
            theme=pygame_menu.themes.THEME_DEFAULT
        )
        
        menus["settings"] = pygame_menu.Menu(
            "Settings", 
            self.width, self.height, 
            theme=pygame_menu.themes.THEME_DEFAULT
        )

        # Main menu options
        button_style = {
            "align": pygame_menu.locals.ALIGN_LEFT,
            "font_size": 64,
            "margin": (50, 50),
            "selection_effect": None
        }
        
        menus["main"].add.button("Start", menus["game"], **button_style)
        menus["main"].add.button("Puzzle Demo", self._puzzle_demo, **button_style)
        menus["main"].add.button("Settings", menus["settings"], **button_style)
        menus["main"].add.button("Quit", pygame_menu.events.EXIT, **button_style)

        # Game settings menu
        game_style = {
            "align": pygame_menu.locals.ALIGN_RIGHT,
            "font_size": 40,
            "margin": (-75, 25),
            "selection_effect": None
        }
        
        menus["game"].add.selector(
            "Player Colour:", 
            [("White", chess.WHITE), ("Black", chess.BLACK), ("Random", -1)],
            default=0,
            onchange=self._set_player_colour,
            style=pygame_menu.widgets.SELECTOR_STYLE_FANCY,
            **game_style
        )
        
        menus['game'].add.dropselect_multiple(
            'Tactic Types:', 
            [
                ("Checkmate", TACTIC_TYPES["Checkmate"]), 
                ("Fork", TACTIC_TYPES["Fork"]), 
                ("Absolute Pin", TACTIC_TYPES["Absolute Pin"]), 
                ("Relative Pin", TACTIC_TYPES["Relative Pin"])
            ],
            default=list(TACTIC_TYPES.values()),
            onchange=self._set_tactic_types,
            **game_style
        )
        
        menus["game"].add.selector(
            "Difficulty:",
            [("Easy", 0), ("Medium", 1), ("Hard", 2)],
            default=1,
            onchange=self._set_difficulty,
            style=pygame_menu.widgets.SELECTOR_STYLE_FANCY,
            **game_style
        )
        
        menus["game"].add.button(
            "Start Game", 
            self._run, 
            font_size=64, 
            margin=(0, 50), 
            selection_effect=None
        )
        
        return menus

    def menu(self) -> None:
        """Display and handle the main menu."""
        running = True
        
        # Create menus
        menus = self._create_menus()
        
        # Main menu loop
        while running:
            events = pygame.event.get()
            for event in events:
                if event.type == pygame.QUIT:
                    running = False
                    break

            # Update and draw the main menu
            menus["main"].update(events)
            menus["main"].draw(self.window)
            pygame.display.flip()

        pygame.quit()

if __name__ == "__main__":
    game = ChessGame()
    game.menu()