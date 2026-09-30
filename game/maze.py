import random

CELL = 40  # cell size in pixels

def generate_maze(cols, rows):
    """Recursive backtracker maze generation. Returns 2D grid of walls."""
    visited = [[False]*cols for _ in range(rows)]
    # walls: each cell has [N, S, E, W]
    walls = [[[True,True,True,True] for _ in range(cols)] for _ in range(rows)]
    
    def neighbors(r, c):
        dirs = [(-1,0,0,1),(1,0,1,0),(0,1,2,3),(0,-1,3,2)]  # dr,dc,wall_dir,opp_dir
        result = []
        for dr,dc,wd,od in dirs:
            nr,nc = r+dr,c+dc
            if 0<=nr<rows and 0<=nc<cols and not visited[nr][nc]:
                result.append((nr,nc,wd,od))
        return result

    stack = [(0,0)]
    visited[0][0] = True
    while stack:
        r,c = stack[-1]
        nbrs = neighbors(r,c)
        if nbrs:
            nr,nc,wd,od = random.choice(nbrs)
            walls[r][c][wd] = False
            walls[nr][nc][od] = False
            visited[nr][nc] = True
            stack.append((nr,nc))
        else:
            stack.pop()
    return walls

def bfs_solve(walls, rows, cols, start, end):
    """BFS shortest path between two cells using wall connectivity.

    Args:
        walls: 2D grid where walls[r][c] = [N, S, E, W] booleans.
        rows, cols: maze dimensions.
        start: (row, col) of the start cell.
        end:   (row, col) of the destination cell.

    Returns:
        Ordered list of (row, col) tuples from start to end (inclusive),
        or an empty list if no path exists.
    """
    from collections import deque

    # Directions: (dr, dc, wall_index_in_current, wall_index_in_neighbor)
    # N=0, S=1, E=2, W=3
    DIRS = [(-1, 0, 0, 1), (1, 0, 1, 0), (0, 1, 2, 3), (0, -1, 3, 2)]

    visited = [[False] * cols for _ in range(rows)]
    parent  = {}
    queue   = deque([start])
    visited[start[0]][start[1]] = True

    while queue:
        r, c = queue.popleft()
        if (r, c) == end:
            # Reconstruct path
            path = []
            node = end
            while node != start:
                path.append(node)
                node = parent[node]
            path.append(start)
            path.reverse()
            return path

        for dr, dc, wall_cur, _ in DIRS:
            # Only traverse if there is NO wall on this side
            if not walls[r][c][wall_cur]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and not visited[nr][nc]:
                    visited[nr][nc] = True
                    parent[(nr, nc)] = (r, c)
                    queue.append((nr, nc))

    return []  # No path found


def cell_rect(r, c, import_pygame=None):
    import pygame
    return pygame.Rect(c*CELL, r*CELL, CELL, CELL)
