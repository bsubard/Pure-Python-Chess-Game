import asyncio
import pygame as pg
import sys

# --- CONSTANTS AND GLOBALS ---
w = 1120 
h = 490
BOARD_WIDTH = 400
INFO_PANEL_WIDTH = 200
GAP = 40

BOARD_1_OFFSET_X = GAP
INFO_PANEL_OFFSET_X = BOARD_1_OFFSET_X + BOARD_WIDTH + GAP
BOARD_2_OFFSET_X = INFO_PANEL_OFFSET_X + INFO_PANEL_WIDTH + GAP


BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (142, 142, 142)
SILVER = (120, 120, 120)
LIGHT = (252, 204, 116)
DARK = (87, 58, 46)
GREEN = (0, 255, 0)
RED = (215, 0, 0)
ORANGE = (255, 165, 0)
transcript, turn_number = '', 0

# --- FONT FINDER HELPER FUNCTION ---
def find_system_font():
    """Searches for a system font that supports chess characters."""
    font_preferences = ["dejavusans", "segoeuisymbol", "freeserif", "arialunicode", "symbola"]
    available_fonts = pg.font.get_fonts()
    for pref_font in font_preferences:
        if pref_font in available_fonts:
            print(f"Using system font: {pref_font}")
            return pg.font.match_font(pref_font)
    print("Warning: No suitable system font found for chess symbols. Falling back to default.")
    return None

# --- PIECE CLASS DEFINITIONS ---
class Piece:
    piece_names = ['king', 'queen', 'rook', 'bishop', 'knight', 'pawn']

    def __init__(self, colour, name, unbounded=True):
        self.colour = colour
        self.name = name
        self.unbounded = unbounded
        base_unicode = 9818 
        piece_index = self.piece_names.index(name)
        self.image = chr(base_unicode + piece_index)

    def find_moves(self, board, location, kings, check):
        x, y = location[0], location[1]
        legal_moves = []
        additional = set()
        if self.name == 'pawn':
            additional.update(self.additional_moves(board, x, y))
        for x2, y2 in self.moveset.union(additional):
            if any(i < 0 for i in (x + x2, y + y2)): continue
            try:
                coords = x + x2, y + y2
                square = board[coords[1]][coords[0]]
                if self.name != 'pawn' and (square is None or square and square.colour != self.colour) or \
                        self.name == 'pawn' and ((x2 == 0 and square is None) or (x2, y2) in additional):
                    king = kings[int(self.colour == "black")]
                    king_pos = coords if king == (x, y) else king
                    if not board[king[1]][king[0]].in_check(board, king_pos, moved_from=location, moved_to=coords):
                        legal_moves.append(coords)
                    if square and square.colour != self.colour or coords not in legal_moves and not check: continue
                    while self.unbounded or self.name == 'pawn' and self.double_move:
                        coords = coords[0] + x2, coords[1] + y2
                        square = board[coords[1]][coords[0]]
                        if check and board[king[1]][king[0]].in_check(board, king_pos, moved_from=location, moved_to=coords): continue
                        if all(i >= 0 for i in coords) and self.name != 'pawn' and (square is None or square and square.colour != self.colour) or self.name == 'pawn' and (x2 == 0 and square is None):
                            legal_moves.append(coords)
                        elif not check: break
                        if self.name == 'pawn' or square and square.colour != self.colour: break
            except IndexError: continue
        if self.name == 'king' and not check and self.castle_rights and self.castle(board, x, y):
            legal_moves.extend(self.castle(board, x, y))
        return legal_moves

class King(Piece):
    def __init__(self, colour):
        self.back_rank = 7 if colour == 'white' else 0
        self.moveset = {(x, y) for x in range(-1, 2) for y in range(-1, 2) if x != 0 or y != 0}
        self.castle_rights = True
        super().__init__(colour, 'king', unbounded=False)
    def in_check(self, board, location, moved_from=None, moved_to=None):
        for move in self.moveset:
            coords = location
            square = board[coords[1]][coords[0]]
            while (coords != moved_to or location == moved_to) and (coords == location or coords == moved_from or square is None):
                try:
                    if any(i < 0 or i > 7 for i in (coords[0] + move[0], coords[1] + move[1])): break
                    coords = coords[0] + move[0], coords[1] + move[1]
                    square = board[coords[1]][coords[0]]
                except IndexError: break
            if square is None or square.colour == self.colour or coords == moved_to: continue
            if 0 in move and (square.name == 'rook' or square.name == 'queen') or 0 not in move and (square.name == 'bishop' or square.name == 'queen' or (square.name == 'pawn' and location[1] - coords[1] == square.direction)): return True
        for x, y in {(x, y) for x in range(-2, 3) for y in range(-2, 3) if x != 0 and y != 0 and abs(x) != abs(y)}:
            try:
                coords = location[0] + x, location[1] + y
                square = board[coords[1]][coords[0]]
                if any(i < 0 for i in (coords[0], coords[1])): continue
                if square and square.colour != self.colour and square.name == 'knight' and coords != moved_to: return True
            except IndexError: continue
        return False
    def castle(self, board, x, y):
        moves = []
        if board[self.back_rank][0] and board[self.back_rank][0].name == 'rook' and board[self.back_rank][0].castle_rights:
            squares = [(i, self.back_rank) for i in range(1, 4)]
            if all(not piece for piece in board[self.back_rank][1:4]) and all(not self.in_check(board, square) for square in squares):
                moves.append((2, self.back_rank))
        if board[self.back_rank][7] and board[self.back_rank][7].name == 'rook' and board[self.back_rank][7].castle_rights:
            squares = [(i, self.back_rank) for i in range(5, 7)]
            if all(not piece for piece in board[self.back_rank][5:7]) and all(not self.in_check(board, square) for square in squares):
                moves.append((6, self.back_rank))
        return moves

class Queen(Piece):
    def __init__(self, colour):
        self.moveset = {(x, y) for x in range(-1, 2) for y in range(-1, 2) if x != 0 or y != 0}
        super().__init__(colour, 'queen')

class Rook(Piece):
    def __init__(self, colour):
        self.moveset = {(x, y) for x in range(-1, 2) for y in range(-1, 2) if (x == 0 or y == 0) and (x != 0 or y != 0)}
        self.castle_rights = True
        super().__init__(colour, 'rook')

class Bishop(Piece):
    def __init__(self, colour):
        self.moveset = {(x, y) for x in range(-1, 2) for y in range(-1, 2) if x != 0 and y != 0}
        super().__init__(colour, 'bishop')

class Knight(Piece):
    def __init__(self, colour):
        self.moveset = {(x, y) for x in range(-2, 3) for y in range(-2, 3) if x != 0 and y != 0 and abs(x) != abs(y)}
        super().__init__(colour, 'knight', unbounded=False)

class Pawn(Piece):
    def __init__(self, colour):
        self.direction = -1 if colour == 'white' else 1
        self.moveset = {(0, y * self.direction) for y in range(1, 2)}
        self.en_passant = False
        self.double_move = True
        super().__init__(colour, 'pawn', unbounded=False)
    def additional_moves(self, board, x, y):
        valid_attacks = set()
        for n in range(-1, 2, 2):
            try:
                square = board[y + self.direction][x + n]
                if square and square.colour != self.colour:
                    valid_attacks.add((n, self.direction))
                else:
                    square = board[y][x + n]
                    if square and square.name == 'pawn' and square.en_passant:
                        valid_attacks.add((n, self.direction))
            except IndexError: pass
        return valid_attacks

# --- GAME LOGIC FUNCTIONS ---
def reset_board(with_pieces=True):
    def generate_pieces(colour):
        return [Rook(colour), Knight(colour), Bishop(colour), Queen(colour), King(colour), Bishop(colour), Knight(colour), Rook(colour)]
    board = [[None for _ in range(8)] for _ in range(8)]
    if with_pieces:
        board[0] = generate_pieces("black")
        board[7] = generate_pieces("white")
        board[1] = [Pawn("black") for _ in board[1]]
        board[6] = [Pawn("white") for _ in board[6]]
    return board

def move_piece(board, target, kings, origin, destination, captures, promotion):
    if board[destination[1]][destination[0]]:
        captures.append(board[destination[1]][destination[0]])

    promoting = False
    if target.name == 'pawn':
        if target.double_move: target.double_move = False
        if abs(origin[1] - destination[1]) == 2: target.en_passant = True
        if origin[0] != destination[0] and not board[destination[1]][destination[0]]:
            captured_pawn = board[destination[1] - target.direction][destination[0]]
            captures.append(captured_pawn)
            board[destination[1] - target.direction][destination[0]] = None
        if destination[1] == (0 if target.colour == 'white' else 7):
            promoting = True
            piece_dict = {'queen': Queen(target.colour), 'knight': Knight(target.colour), 'rook': Rook(target.colour), 'bishop': Bishop(target.colour)}
            board[destination[1]][destination[0]] = piece_dict[promotion]
    
    if not promoting:
        board[destination[1]][destination[0]] = target

    if target.name == 'king':
        kings[int(target.colour == "black")] = destination
        if target.castle_rights: target.castle_rights = False
        if destination[0] - origin[0] == 2:
            board[target.back_rank][5], board[target.back_rank][7] = board[target.back_rank][7], None
        if origin[0] - destination[0] == 2:
            board[target.back_rank][3], board[target.back_rank][0] = board[target.back_rank][0], None

    if target.name == 'rook' and target.castle_rights: target.castle_rights = False
    
    board[origin[1]][origin[0]] = None
    
    for row in board:
        for piece in row:
            if piece and piece.name == 'pawn' and piece.en_passant and piece.colour != target.colour:
                piece.en_passant = False
    
    enemy_king_idx = int(target.colour == "white")
    enemy_king_pos = kings[enemy_king_idx]
    check = board[enemy_king_pos[1]][enemy_king_pos[0]].in_check(board, enemy_king_pos)
    return board, captures, kings, check

def checkmate(board, turn, kings):
    for y, row in enumerate(board):
        for x, square in enumerate(row):
            if square and square.colour != turn:
                if square.find_moves(board, (x, y), kings, True):
                    return False
    return True

# --- DRAWING & INPUT FUNCTIONS ---
def draw_squares(screen, offset_x):
    colour_dict = {True: LIGHT, False: DARK}
    for row in range(8):
        current_colour = not (row % 2 == 0)
        for square in range(8):
            pg.draw.rect(screen, colour_dict[current_colour], (offset_x + (square * 50), 40 + (row * 50), 50, 50))
            current_colour = not current_colour

def draw_coords(screen, font, flipped, offset_x):
    for row in range(8):
        char = chr(49 + row) if flipped else chr(56 - row)
        text_surf = font.render(char, True, BLACK)
        screen.blit(text_surf, (offset_x - 30, 45 + (row * 50)))
    for col in range(8):
        char = chr(72 - col) if flipped else chr(65 + col)
        text_surf = font.render(char, True, BLACK)
        screen.blit(text_surf, (offset_x + 5 + (col * 50), 450))

def draw_pieces(screen, font, board, flipped, offset_x):
    for row_idx, pieces_row in enumerate(board[::(-1 if flipped else 1)]):
        for col_idx, piece in enumerate(pieces_row[::(-1 if flipped else 1)]):
            if piece:
                center_pos = (offset_x + col_idx * 50 + 25, 40 + row_idx * 50 + 25)
                piece_color = (240, 240, 240) if piece.colour == 'white' else BLACK
                if piece.colour == 'white':
                    offsets = [(-1, -1), (0, -1), (1, -1), (-1, 0), (1, 0), (-1, 1), (0, 1), (1, 1)]
                    for dx, dy in offsets:
                        border_surf = font.render(piece.image, True, BLACK)
                        screen.blit(border_surf, border_surf.get_rect(center=(center_pos[0] + dx, center_pos[1] + dy)))
                main_surf = font.render(piece.image, True, piece_color)
                screen.blit(main_surf, main_surf.get_rect(center=center_pos))

def find_square(x, y, offset_x):
    grid_x = int((x - offset_x) / 50)
    grid_y = int((y - 40) / 50)
    return grid_x, grid_y

def draw_center_divider(screen):
    pg.draw.rect(screen, SILVER, (INFO_PANEL_OFFSET_X - GAP, 0, INFO_PANEL_WIDTH + 2 * GAP, h))

def draw_captures_above_board(screen, font, captures, color_to_draw, offset_x):
    captured_pieces = [p for p in captures if p.colour == color_to_draw]
    for i, piece in enumerate(captured_pieces):
        pos = (offset_x + 5 + i * 25, 5)
        piece_color = (240, 240, 240) if piece.colour == 'white' else BLACK
        if piece.colour == 'white':
            border_surf = font.render(piece.image, True, BLACK)
            screen.blit(border_surf, (pos[0] + 1, pos[1] + 1))
        main_surf = font.render(piece.image, True, piece_color)
        screen.blit(main_surf, pos)

def draw_turn_indicator_dot(screen, turn):
    y_pos = h - 25
    radius = 6
    x_pos = (w // 2) - 90 if turn == 'white' else (w // 2) + 90
    pg.draw.circle(screen, BLACK, (x_pos, y_pos), radius)

def draw_check_highlight(screen, kings, flipped, turn, checkmate, offset_x):
    king = kings[1 if turn == 'white' else 0] if checkmate else kings[0 if turn == 'white' else 1]
    color = RED if checkmate else ORANGE
    x, y = king
    center_pos = (offset_x + (7-x if flipped else x) * 50 + 25, 40 + (7-y if flipped else y) * 50 + 25)
    pg.draw.circle(screen, color, center_pos, 25, width=3)

# --- MAIN GAME LOOP ---
def main():
    pg.init()
    pg.font.init()
    clock = pg.time.Clock()
    pg.display.set_caption('Chess - Dual View')
    screen = pg.display.set_mode((w, h))
    font_path = find_system_font() 
    piece_font = pg.font.Font(font_path, 50)
    info_font = pg.font.Font(font_path, 25)

    # --- Initial instructions ---
    print("\n--- Welcome to Chess ---")
    print("Press the number keys to select your pawn promotion piece:")
    print("1: Queen (Default)")
    print("2: Knight")
    print("3: Rook")
    print("4: Bishop")
    print("Press 'R' to reset the game at any time.")
    print("------------------------\n")

    board = reset_board()
    playing, turn, check = True, 'white', False
    kings = [(4, 7), (4, 0)]
    promotion = 'queen'
    selected_square_coords, selected_piece, captures, legal_moves = None, None, [], []

    board1_rect = pg.Rect(BOARD_1_OFFSET_X, 40, BOARD_WIDTH, BOARD_WIDTH)
    board2_rect = pg.Rect(BOARD_2_OFFSET_X, 40, BOARD_WIDTH, BOARD_WIDTH)
    
    while True:
        screen.fill(GREY)
        draw_center_divider(screen)
        draw_squares(screen, BOARD_1_OFFSET_X)
        draw_coords(screen, info_font, False, BOARD_1_OFFSET_X)
        draw_pieces(screen, piece_font, board, False, BOARD_1_OFFSET_X)
        draw_squares(screen, BOARD_2_OFFSET_X)
        draw_coords(screen, info_font, True, BOARD_2_OFFSET_X)
        draw_pieces(screen, piece_font, board, True, BOARD_2_OFFSET_X)
        draw_captures_above_board(screen, info_font, captures, "black", BOARD_1_OFFSET_X)
        draw_captures_above_board(screen, info_font, captures, "white", BOARD_2_OFFSET_X)

        for event in pg.event.get():
            if event.type == pg.MOUSEBUTTONDOWN and event.button == 1 and playing:
                pos = event.pos
                offset_x, flipped = (BOARD_1_OFFSET_X, False) if turn == 'white' and board1_rect.collidepoint(pos) else \
                                    (BOARD_2_OFFSET_X, True) if turn == 'black' and board2_rect.collidepoint(pos) else (None, None)
                if offset_x is not None:
                    grid_coords = find_square(pos[0], pos[1], offset_x)
                    board_coords = (7-grid_coords[0], 7-grid_coords[1]) if flipped else grid_coords
                    if selected_piece and board_coords in legal_moves:
                        board, captures, kings, check = move_piece(board, selected_piece, kings, selected_board_coords, board_coords, captures, promotion)
                        if check and checkmate(board, turn, kings):
                            playing = False
                        else:
                            turn = 'black' if turn == 'white' else 'white'
                        selected_piece, selected_square_coords, legal_moves = None, None, []
                    else:
                        clicked_piece = board[board_coords[1]][board_coords[0]]
                        if clicked_piece and clicked_piece.colour == turn:
                            selected_piece, selected_square_coords, selected_board_coords, legal_moves = \
                                clicked_piece, grid_coords, board_coords, clicked_piece.find_moves(board, board_coords, kings, check)
                        else:
                            selected_piece, selected_square_coords, legal_moves = None, None, []
                else: 
                    selected_piece, selected_square_coords, legal_moves = None, None, []

            if event.type == pg.KEYDOWN:
                if event.key == pg.K_r:
                    board, kings, turn, check, captures, playing = reset_board(), [(4, 7), (4, 0)], 'white', False, [], True
                    selected_piece, selected_square_coords, legal_moves = None, None, []
                    print("\n--- Game Reset ---")
                
                # --- Promotion choice confirmations ---
                if event.key == pg.K_1: 
                    promotion = 'queen'
                    print("Pawn promotion chosen: Queen")
                if event.key == pg.K_2: 
                    promotion = 'knight'
                    print("Pawn promotion chosen: Knight")
                if event.key == pg.K_3: 
                    promotion = 'rook'
                    print("Pawn promotion chosen: Rook")
                if event.key == pg.K_4: 
                    promotion = 'bishop'
                    print("Pawn promotion chosen: Bishop")

            if event.type == pg.QUIT:
                pg.quit()
                sys.exit()

        if selected_piece:
            offset_x = BOARD_2_OFFSET_X if turn == 'black' else BOARD_1_OFFSET_X
            x, y = selected_square_coords
            pg.draw.rect(screen, GREEN, (offset_x + x * 50, 40 + y * 50, 50, 50), width=3)
        
        if check:
            draw_check_highlight(screen, kings, False, turn, not playing, BOARD_1_OFFSET_X)
            draw_check_highlight(screen, kings, True, turn, not playing, BOARD_2_OFFSET_X)
            
        draw_turn_indicator_dot(screen, turn)
        pg.display.update()
        clock.tick(60)

if __name__ == '__main__':
    main()
