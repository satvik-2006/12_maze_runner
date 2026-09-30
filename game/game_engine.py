import pygame
import time
from game.maze import generate_maze, bfs_solve, CELL
from game.player import Player

FPS = 60
BG = (240, 235, 220)
WALL_COLOR = (40, 40, 60)
EXIT_COLOR = (80, 200, 80)
PATH_COLOR = (255, 200, 50, 160)   # semi-transparent amber for the hint path
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

    def draw(self):
        self.screen.fill(BG)
        self.draw_maze()
        self.draw_hint_path()                                  # drawn before player
        pygame.draw.rect(self.screen, EXIT_COLOR, self.exit_rect, border_radius=4)
        ex_label = self.font.render("EXIT", True, (20,80,20))
        self.screen.blit(ex_label, (self.exit_rect.x+2, self.exit_rect.y+4))
        self.player.draw(self.screen)

        hud = pygame.Rect(0, ROWS*CELL, WIDTH, 60)
        pygame.draw.rect(self.screen, (30,30,50), hud)
        hud_text = f"Time: {self.elapsed:.1f}s   R=New Maze   H=Hint"
        time_surf = self.font.render(hud_text, True, (200,200,200))
        self.screen.blit(time_surf, (10, ROWS*CELL+18))

        if self.won:
            overlay = pygame.Surface((WIDTH, ROWS*CELL), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            self.screen.blit(overlay, (0,0))
            msg = self.big_font.render(f"Solved in {self.elapsed:.1f}s!", True, (80,240,80))
            sub = self.font.render("Press R for a new maze", True, (200,200,200))
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, ROWS*CELL//2 - 30))
            self.screen.blit(sub, (WIDTH//2 - sub.get_width()//2, ROWS*CELL//2 + 20))
        pygame.display.flip()

    def run(self):
        running = True
        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        pygame.quit()
