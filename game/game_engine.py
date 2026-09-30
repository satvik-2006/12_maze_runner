import pygame
import time
from game.maze import generate_maze, bfs_solve, CELL
from game.player import Player
from game.leaderboard import load_times, save_time

# -- Colours -------------------------------------------------------------------
FPS            = 60
BG             = (240, 235, 220)
WALL_COLOR     = (40,  40,  60)
EXIT_COLOR     = (80, 200,  80)
PATH_COLOR     = (255, 200,  50, 160)   # semi-transparent amber — BFS hint
FOG_COLOR      = (18,  18,  30)         # solid dark fog fill
FOG_EDGE_COLOR = (38,  38,  55)         # lighter ring at the lit boundary
_FOG_KEY       = (0,   0,   0)          # colorkey sentinel ? transparent on blit
FOG_RADIUS     = CELL * 3              # reveal radius — exactly 3 cells

# -- Difficulty definitions ----------------------------------------------------
DIFFICULTIES = {
    "Easy":   (10,  8),
    "Medium": (15, 13),
    "Hard":   (20, 18),
}
DIFF_COLORS = {
    "Easy":   ( 50, 180,  80),   # green
    "Medium": (200, 150,  30),   # amber
    "Hard":   (200,  50,  50),   # red
}

# -- Select-screen layout ------------------------------------------------------
SELECT_W, SELECT_H = 540, 340   # fixed size of the difficulty-select window
HUD_H = 60                      # height of the HUD strip below the maze


class GameEngine:
    """Top-level game controller.

    State machine:
        "select"  ? difficulty picker screen
        "playing" ? active maze game
    Transitions:
        select  --[click difficulty]--> playing
        playing --[ESC]-------------> select
        playing --[R]---------------> reset (same difficulty)
    """

    # -- Initialisation ----------------------------------------------------

    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SELECT_W, SELECT_H))
        pygame.display.set_caption("Maze Runner")
        self.clock = pygame.time.Clock()

        self.font       = pygame.font.SysFont("monospace", 22)
        self.small_font = pygame.font.SysFont("monospace", 18)
        self.big_font   = pygame.font.SysFont("monospace", 36, bold=True)
        self.title_font = pygame.font.SysFont("monospace", 44, bold=True)

        # Game-state placeholders (populated by _start_game)
        self.state      = "select"
        self.difficulty = None
        self.cols = self.rows = self.width = self.height = None

    # -- Difficulty-select screen ------------------------------------------

    def _button_rects(self) -> dict:
        """Return {difficulty: pygame.Rect} for the three difficulty buttons."""
        btn_w, btn_h = 140, 90
        gap          = 18
        total_w      = len(DIFFICULTIES) * btn_w + (len(DIFFICULTIES) - 1) * gap
        x0           = (SELECT_W - total_w) // 2
        y0           = 185
        return {
            diff: pygame.Rect(x0 + i * (btn_w + gap), y0, btn_w, btn_h)
            for i, diff in enumerate(DIFFICULTIES)
        }

    def _handle_select_events(self) -> bool:
        btn_rects = self._button_rects()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                for diff, rect in btn_rects.items():
                    if rect.collidepoint(event.pos):
                        self._start_game(diff)
        return True

    def _draw_select(self):
        self.screen.fill((18, 18, 32))

        # Title
        title = self.title_font.render("MAZE  RUNNER", True, (80, 210, 255))
        self.screen.blit(title, (SELECT_W // 2 - title.get_width() // 2, 45))

        sub = self.font.render("Select a difficulty to begin", True, (150, 150, 185))
        self.screen.blit(sub, (SELECT_W // 2 - sub.get_width() // 2, 118))

        # Difficulty buttons
        mx, my    = pygame.mouse.get_pos()
        btn_rects = self._button_rects()
        for diff, rect in btn_rects.items():
            cols_d, rows_d = DIFFICULTIES[diff]
            base_clr = DIFF_COLORS[diff]
            hover    = rect.collidepoint(mx, my)

            # Brighten on hover, darken otherwise
            fill_clr = tuple(min(255, c + 45) for c in base_clr) if hover \
                       else tuple(max(0, c - 25) for c in base_clr)

            pygame.draw.rect(self.screen, fill_clr, rect, border_radius=12)
            pygame.draw.rect(self.screen, base_clr, rect, 2, border_radius=12)

            name_surf = self.font.render(diff.upper(), True, (255, 255, 255))
            dims_surf = self.small_font.render(f"{cols_d} x {rows_d}", True, (230, 230, 230))

            self.screen.blit(name_surf, (rect.centerx - name_surf.get_width() // 2, rect.y + 20))
            self.screen.blit(dims_surf, (rect.centerx - dims_surf.get_width() // 2, rect.y + 54))

        # Footer hint
        hint = self.small_font.render("ESC  to return here from the game", True, (90, 90, 110))
        self.screen.blit(hint, (SELECT_W // 2 - hint.get_width() // 2, SELECT_H - 34))

        pygame.display.flip()

    def _start_game(self, difficulty: str):
        """Resize the window and initialise a fresh maze for *difficulty*."""
        self.difficulty = difficulty
        self.cols, self.rows = DIFFICULTIES[difficulty]
        self.width  = self.cols * CELL
        self.height = self.rows * CELL + HUD_H
        self.screen = pygame.display.set_mode((self.width, self.height))
        self.state  = "playing"
        self.reset()

    # -- Game state --------------------------------------------------------

    def reset(self):
        """Regenerate the maze (same difficulty) and clear all per-run state."""
        self.walls      = generate_maze(self.cols, self.rows)
        self.player     = Player(0, 0)
        self.exit_rect  = pygame.Rect(
            (self.cols - 1) * CELL + 5,
            (self.rows - 1) * CELL + 5,
            CELL - 10, CELL - 10,
        )
        self.start_time = time.time()
        self.elapsed    = 0
        self.won        = False

        # BFS hint
        self.hint_active = False
        self.hint_path   = []

        # Leaderboard
        self.rank              = None
        self.leaderboard_times = load_times(self.difficulty)

        # Fog of war — regular surface with colorkey; no SRCALPHA needed
        self.fog_surf = pygame.Surface((self.width, self.rows * CELL))
        self.fog_surf.set_colorkey(_FOG_KEY)

    def handle_events(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_ESCAPE:
                    # Return to difficulty select
                    self.state  = "select"
                    self.screen = pygame.display.set_mode((SELECT_W, SELECT_H))
                elif event.key == pygame.K_h and not self.won:
                    self.hint_active = not self.hint_active
                    if self.hint_active:
                        cx = self.player.rect.centerx // CELL
                        cy = self.player.rect.centery // CELL
                        self.hint_path = bfs_solve(
                            self.walls, self.rows, self.cols,
                            (cy, cx),
                            (self.rows - 1, self.cols - 1),
                        )
        return True

    def update(self):
        if self.won:
            return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.walls, self.rows, self.cols)
        self.elapsed = time.time() - self.start_time
        if self.player.rect.colliderect(self.exit_rect):
            self.won = True
            # Save completion time and capture leaderboard state (fires once)
            self.rank, self.leaderboard_times = save_time(self.elapsed, self.difficulty)

    # -- Drawing helpers ---------------------------------------------------

    def draw_maze(self):
        wall_w = 3
        for r in range(self.rows):
            for c in range(self.cols):
                x, y = c * CELL, r * CELL
                w    = self.walls[r][c]
                if w[0]: pygame.draw.line(self.screen, WALL_COLOR, (x, y),        (x + CELL, y),        wall_w)
                if w[1]: pygame.draw.line(self.screen, WALL_COLOR, (x, y + CELL), (x + CELL, y + CELL), wall_w)
                if w[2]: pygame.draw.line(self.screen, WALL_COLOR, (x + CELL, y), (x + CELL, y + CELL), wall_w)
                if w[3]: pygame.draw.line(self.screen, WALL_COLOR, (x, y),        (x, y + CELL),        wall_w)

    def draw_hint_path(self):
        """Overlay semi-transparent amber squares on the BFS shortest path."""
        if not self.hint_active or not self.hint_path:
            return
        padding   = 6
        cell_surf = pygame.Surface((CELL - padding * 2, CELL - padding * 2), pygame.SRCALPHA)
        cell_surf.fill(PATH_COLOR)
        for r, c in self.hint_path:
            self.screen.blit(cell_surf, (c * CELL + padding, r * CELL + padding))

    def draw_fog(self):
        """Fog-of-war overlay using the colorkey punch-hole technique.

        Fills fog_surf with solid fog, then paints a soft edge ring and the
        reveal disc in _FOG_KEY (= surface colorkey).  Colorkey pixels are
        skipped entirely on blit ? clean transparent hole in all pygame versions.
        """
        cx, cy = self.player.rect.centerx, self.player.rect.centery
        self.fog_surf.fill(FOG_COLOR)
        # Soft boundary ring just outside the lit area
        pygame.draw.circle(self.fog_surf, FOG_EDGE_COLOR, (cx, cy), FOG_RADIUS + CELL // 2)
        # Hard reveal hole — colorkey colour ? not blitted
        pygame.draw.circle(self.fog_surf, _FOG_KEY, (cx, cy), FOG_RADIUS)
        self.screen.blit(self.fog_surf, (0, 0))

    def _draw_win_screen(self):
        """Leaderboard overlay shown after the player reaches the exit."""
        # Semi-opaque dark backdrop
        overlay = pygame.Surface((self.width, self.rows * CELL), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 160))
        self.screen.blit(overlay, (0, 0))

        MEDAL  = {1: (255, 215, 0), 2: (192, 192, 192), 3: (205, 127, 50)}
        MY_CLR = (80, 240, 80)     # highlight colour for the player's entry
        DIM    = (170, 170, 170)   # colour for other entries
        cx     = self.width // 2
        y      = 35

        # "Solved in X.Xs!"
        msg = self.big_font.render(f"Solved in {self.elapsed:.1f}s!", True, MY_CLR)
        self.screen.blit(msg, (cx - msg.get_width() // 2, y))
        y += msg.get_height() + 8

        # Rank badge
        if self.rank == 1:
            badge_txt, badge_clr = "NEW BEST!", MEDAL[1]
        elif self.rank in MEDAL:
            badge_txt, badge_clr = f"Rank #{self.rank}  {'*' * (4 - self.rank)}", MEDAL[self.rank]
        elif self.rank:
            badge_txt, badge_clr = f"Rank #{self.rank}", (200, 200, 200)
        else:
            badge_txt, badge_clr = "Not in top 5", (150, 150, 150)
        badge = self.font.render(badge_txt, True, badge_clr)
        self.screen.blit(badge, (cx - badge.get_width() // 2, y))
        y += badge.get_height() + 12

        # Leaderboard header
        sep = "-" * 22
        hdr = self.small_font.render(
            f"{sep} TOP 5 [{self.difficulty.upper()}] {sep}", True, (120, 120, 150)
        )
        self.screen.blit(hdr, (cx - hdr.get_width() // 2, y))
        y += hdr.get_height() + 6

        # Entries
        for i, t in enumerate(self.leaderboard_times):
            pos       = i + 1
            is_me     = (pos == self.rank)
            medal_clr = MEDAL.get(pos, DIM)
            clr       = MY_CLR if is_me else medal_clr
            marker    = " <--" if is_me else "    "
            line      = f"{pos}.  {t:.2f}s{marker}"
            surf      = self.small_font.render(line, True, clr)
            self.screen.blit(surf, (cx - surf.get_width() // 2, y))
            y += surf.get_height() + 4

        # Footer
        y += 8
        sub = self.font.render("R = new maze   ESC = menu", True, (200, 200, 200))
        self.screen.blit(sub, (cx - sub.get_width() // 2, y))

    def draw(self):
        self.screen.fill(BG)
        self.draw_maze()
        self.draw_hint_path()                          # amber BFS trail (under fog)

        # Exit marker
        pygame.draw.rect(self.screen, EXIT_COLOR, self.exit_rect, border_radius=4)
        ex_label = self.font.render("EXIT", True, (20, 80, 20))
        self.screen.blit(ex_label, (self.exit_rect.x + 2, self.exit_rect.y + 4))

        self.player.draw(self.screen)
        self.draw_fog()                                # fog sits on top; hole reveals player

        # HUD strip
        hud = pygame.Rect(0, self.rows * CELL, self.width, HUD_H)
        pygame.draw.rect(self.screen, (30, 30, 50), hud)

        diff_clr  = DIFF_COLORS[self.difficulty]
        diff_tag  = self.small_font.render(f"[{self.difficulty}]", True, diff_clr)
        hud_info  = self.small_font.render(
            f"  {self.elapsed:.1f}s   R=New  H=Hint  ESC=Menu", True, (200, 200, 200)
        )
        self.screen.blit(diff_tag, (10, self.rows * CELL + 20))
        self.screen.blit(hud_info, (10 + diff_tag.get_width(), self.rows * CELL + 20))

        if self.won:
            self._draw_win_screen()

        pygame.display.flip()

    # -- Main loop ---------------------------------------------------------

    def run(self):
        running = True
        while running:
            if self.state == "select":
                running = self._handle_select_events()
                self._draw_select()
            else:  # "playing"
                running = self.handle_events()
                self.update()
                self.draw()
            self.clock.tick(FPS)
        pygame.quit()
