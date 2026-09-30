import pygame
import time
from game.maze import generate_maze, bfs_solve, CELL
from game.player import Player
from game.leaderboard import load_times, save_time

FPS = 60
BG = (240, 235, 220)
WALL_COLOR = (40, 40, 60)
EXIT_COLOR = (80, 200, 80)
PATH_COLOR = (255, 200, 50, 160)   # semi-transparent amber for the hint path
FOG_COLOR      = (18, 18, 30)          # solid dark fog fill
FOG_EDGE_COLOR = (38, 38, 55)          # slightly lighter ring at the lit boundary
_FOG_KEY       = (0, 0, 0)             # colorkey sentinel → transparent on blit
                                        # (pure black is safe: no maze element uses it)
FOG_RADIUS     = CELL * 3              # reveal radius in pixels — exactly 3 cells
COLS, ROWS = 15, 13

WIDTH = COLS * CELL
HEIGHT = ROWS * CELL + 60

class GameEngine:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Maze Runner")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 22)
        self.small_font = pygame.font.SysFont("monospace", 19)
        self.big_font = pygame.font.SysFont("monospace", 36, bold=True)
        self.reset()

    def reset(self):
        self.walls = generate_maze(COLS, ROWS)
        self.player = Player(0, 0)
        self.exit_rect = pygame.Rect((COLS-1)*CELL+5, (ROWS-1)*CELL+5, CELL-10, CELL-10)
        self.start_time = time.time()
        self.elapsed = 0
        self.won = False
        self.hint_active = False   # True while the BFS path overlay is visible
        self.hint_path   = []      # List of (row, col) cells on the shortest path
        self.rank            = None   # 1-based leaderboard rank for the last run
        self.leaderboard_times = load_times()   # top-5 times loaded from disk
        # Pre-allocate fog surface — regular (non-SRCALPHA) surface with a colorkey.
        # Any pixel painted _FOG_KEY is skipped on blit → transparent reveal hole.
        self.fog_surf = pygame.Surface((WIDTH, ROWS * CELL))
        self.fog_surf.set_colorkey(_FOG_KEY)

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()
                elif event.key == pygame.K_h and not self.won:
                    self.hint_active = not self.hint_active
                    if self.hint_active:
                        # Derive current cell from the player rect's centre
                        cx = (self.player.rect.centerx) // CELL
                        cy = (self.player.rect.centery) // CELL
                        start = (cy, cx)                     # (row, col)
                        end   = (ROWS - 1, COLS - 1)
                        self.hint_path = bfs_solve(
                            self.walls, ROWS, COLS, start, end
                        )
        return True

    def update(self):
        if self.won:
            return
        keys = pygame.key.get_pressed()
        self.player.move(keys, self.walls, ROWS, COLS)
        self.elapsed = time.time() - self.start_time
        if self.player.rect.colliderect(self.exit_rect):
            self.won = True
            # Save completion time and capture leaderboard state for the win screen
            self.rank, self.leaderboard_times = save_time(self.elapsed)

    def draw_maze(self):
        wall_w = 3
        for r in range(ROWS):
            for c in range(COLS):
                x, y = c*CELL, r*CELL
                w = self.walls[r][c]
                if w[0]: pygame.draw.line(self.screen, WALL_COLOR, (x,y), (x+CELL,y), wall_w)
                if w[1]: pygame.draw.line(self.screen, WALL_COLOR, (x,y+CELL), (x+CELL,y+CELL), wall_w)
                if w[2]: pygame.draw.line(self.screen, WALL_COLOR, (x+CELL,y), (x+CELL,y+CELL), wall_w)
                if w[3]: pygame.draw.line(self.screen, WALL_COLOR, (x,y), (x,y+CELL), wall_w)

    def draw_hint_path(self):
        """Overlay semi-transparent squares on each cell of the BFS hint path."""
        if not self.hint_active or not self.hint_path:
            return
        padding = 6
        cell_surf = pygame.Surface((CELL - padding * 2, CELL - padding * 2), pygame.SRCALPHA)
        cell_surf.fill(PATH_COLOR)
        for r, c in self.hint_path:
            self.screen.blit(cell_surf, (c * CELL + padding, r * CELL + padding))

    def draw_fog(self):
        """Fog-of-war overlay using the colorkey punch-hole technique.

        Works in all pygame versions (pygame.draw alpha=0 is a no-op on SRCALPHA
        surfaces in pygame 2; colorkey is reliable across all versions).

        Steps each frame:
          1. Flood-fill fog_surf with solid dark fog.
          2. Paint a slightly lighter ring just outside the reveal radius (soft edge).
          3. Paint the reveal disc in _FOG_KEY (= the surface's colorkey).
             Colorkey pixels are skipped entirely on blit → clean transparent hole.
        """
        cx, cy = self.player.rect.centerx, self.player.rect.centery

        self.fog_surf.fill(FOG_COLOR)                          # solid dark fog everywhere

        # Soft boundary: lighter fog ring just outside the lit area
        pygame.draw.circle(
            self.fog_surf, FOG_EDGE_COLOR,
            (cx, cy), FOG_RADIUS + CELL // 2
        )

        # Reveal hole: colorkey colour → these pixels are not blitted at all
        pygame.draw.circle(self.fog_surf, _FOG_KEY, (cx, cy), FOG_RADIUS)

        self.screen.blit(self.fog_surf, (0, 0))

    def draw(self):
        self.screen.fill(BG)
        self.draw_maze()
        self.draw_hint_path()                                  # drawn before player
        pygame.draw.rect(self.screen, EXIT_COLOR, self.exit_rect, border_radius=4)
        ex_label = self.font.render("EXIT", True, (20,80,20))
        self.screen.blit(ex_label, (self.exit_rect.x+2, self.exit_rect.y+4))
        self.player.draw(self.screen)
        self.draw_fog()                                        # fog sits on top; hole reveals player

        hud = pygame.Rect(0, ROWS*CELL, WIDTH, 60)
        pygame.draw.rect(self.screen, (30,30,50), hud)
        hud_text = f"Time: {self.elapsed:.1f}s   R=New Maze   H=Hint"
        time_surf = self.font.render(hud_text, True, (200,200,200))
        self.screen.blit(time_surf, (10, ROWS*CELL+18))

        if self.won:
            # --- dark overlay behind all win-screen text ---
            overlay = pygame.Surface((WIDTH, ROWS * CELL), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 160))
            self.screen.blit(overlay, (0, 0))

            MEDAL  = {1: (255, 215,  0), 2: (192, 192, 192), 3: (205, 127, 50)}
            MY_CLR = (80,  240,  80)    # highlight colour for the player's entry
            DIM    = (170, 170, 170)    # colour for other entries
            cx     = WIDTH // 2
            y      = 35                 # current draw cursor

            # ── "Solved in X.Xs!" ──────────────────────────────────────────
            msg = self.big_font.render(f"Solved in {self.elapsed:.1f}s!", True, MY_CLR)
            self.screen.blit(msg, (cx - msg.get_width() // 2, y))
            y += msg.get_height() + 8

            # ── rank badge ─────────────────────────────────────────────────
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

            # ── leaderboard header ─────────────────────────────────────────
            sep   = "-" * 26
            hdr   = self.small_font.render(f"{sep} TOP 5 {sep}", True, (120, 120, 150))
            self.screen.blit(hdr, (cx - hdr.get_width() // 2, y))
            y += hdr.get_height() + 6

            # ── entries ────────────────────────────────────────────────────
            for i, t in enumerate(self.leaderboard_times):
                pos    = i + 1
                is_me  = (pos == self.rank)
                medal_clr = MEDAL.get(pos, DIM)
                clr    = MY_CLR if is_me else medal_clr
                marker = " <--" if is_me else "    "
                line   = f"{pos}.  {t:.2f}s{marker}"
                surf   = self.small_font.render(line, True, clr)
                self.screen.blit(surf, (cx - surf.get_width() // 2, y))
                y += surf.get_height() + 4

            # ── "press R" footer ───────────────────────────────────────────
            y += 8
            sub = self.font.render("Press R for a new maze", True, (200, 200, 200))
            self.screen.blit(sub, (cx - sub.get_width() // 2, y))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
