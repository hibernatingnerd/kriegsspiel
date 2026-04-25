import numpy as np
from collections import deque
import matplotlib.pyplot as plt
import random
import heapq
from scipy.ndimage import distance_transform_edt, label
import os

def render_grid(grid_layer):
    plt.figure(figsize=(8, 8))
    plt.imshow(grid_layer, cmap='tab10', interpolation='nearest')
    plt.colorbar(label='region')
    plt.title('Flood Fill Regions')
    plt.show()

def draw_line(grid, start, end, fill_value=1):
    x0, y0 = start
    x1, y1 = end
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy

    while True:
        if 0 <= x0 < grid.shape[0] and 0 <= y0 < grid.shape[1]:
            grid[x0, y0] = fill_value
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy

def flood_fill(grid, start, target, fill_value=1, max_size=50):
    rows, cols = grid.shape[0], grid.shape[1]
    queue = deque([tuple(start)])
    visited = set([tuple(start)])
    while queue and len(visited) < max_size:
        x, y = queue.popleft()
        grid[x, y] = fill_value
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if (0 <= nx < rows and 0 <= ny < cols):
                if (nx, ny) not in visited and grid[nx][ny] == target:
                    visited.add((nx, ny))
                    queue.append((nx, ny))

def assign_heights(grid, num_peaks=5, x_max=50, y_max=50):
    x_size, y_size = grid.shape
    height_map = np.zeros((x_size, y_size), dtype=np.float32)
    
    # place random peaks
    peaks = [(random.randint(0, x_size), random.randint(0, y_size)) for _ in range(num_peaks)]
    
    # build coordinate grids
    xs, ys = np.meshgrid(np.arange(x_size), np.arange(y_size), indexing='ij')
    
    for px, py in peaks:
        spread = random.uniform(x_max/8 , y_max/8)  # controls how wide the peak is
        height = random.uniform(0, 1.0)  # peak amplitude
        gaussian = height * np.exp(-((xs - px)**2 + (ys - py)**2) / (2 * spread**2))
        height_map += gaussian
    
    # normalize to [0, 1]
    height_map -= height_map.min()
    height_map /= height_map.max()
    
    return height_map

def flood_fill_splotch(grid, start, target, fill_value=1, max_size=50):
    rows, cols = grid.shape
    frontier = [tuple(start)]
    visited = set(frontier)
    grid[start[0], start[1]] = fill_value
    bias = max(0.0, min(1.0, random.gauss(mu=0.5, sigma=0.2)))

    while frontier and len(visited) < max_size:
        min_idx = int(bias * (len(frontier) - 1))
        idx = random.randint(min_idx, len(frontier) - 1)
        x, y = frontier[idx]

        neighbors = [
            (x+dx, y+dy) for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]
            if 0 <= x+dx < rows and 0 <= y+dy < cols
        ]
        neighbors = [(nx, ny) for nx, ny in neighbors
                     if (nx, ny) not in visited and grid[nx][ny] == target]

        if neighbors:
            nx, ny = random.choice(neighbors)
            visited.add((nx, ny))
            frontier.append((nx, ny))
            grid[nx, ny] = fill_value
        else:
            frontier.pop(idx)

    return frontier  # return frontier for chaining

def sample_lowland_points(height_map, forest_layer, water_layer, n=5, forest_penalty=0.1, altitude_threshold=0.5):
    inverted = 1.0 - height_map
    inverted = np.where(height_map > altitude_threshold, 0.0, inverted)  # mask high altitude
    inverted = np.where(water_layer > 0, 0.0, inverted)                  # hard mask water
    inverted = np.where(forest_layer > 0, inverted * forest_penalty, inverted)  # penalize forest

    weights = inverted.flatten()
    weights /= weights.sum()

    indices = np.random.choice(len(weights), size=n, replace=False, p=weights)
    points = np.array(np.unravel_index(indices, height_map.shape)).T
    return points

def flood_fill_round(grid, start, target, fill_value=1, max_size=50, roundness=0.8):
    rows, cols = grid.shape
    frontier = [tuple(start)]
    visited = set(frontier)
    grid[start[0], start[1]] = fill_value

    while frontier and len(visited) < max_size:
        # roundness=1.0 -> pure BFS (perfect circle)
        # roundness=0.0 -> fully random (splotch)
        max_idx = int((1.0 - roundness) * (len(frontier) - 1))
        idx = random.randint(0, max(0, max_idx))  # biased toward oldest
        x, y = frontier[idx]

        neighbors = [
            (x+dx, y+dy) for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]
            if 0 <= x+dx < rows and 0 <= y+dy < cols
        ]
        neighbors = [(nx, ny) for nx, ny in neighbors
                     if (nx, ny) not in visited and grid[nx][ny] == target]

        if neighbors:
            nx, ny = random.choice(neighbors)
            visited.add((nx, ny))
            frontier.append((nx, ny))
            grid[nx, ny] = fill_value
        else:
            frontier.pop(idx)

    return frontier

def generate_lowland_splotches(matrices, height_map, layer=2, n=5, iter=10, max_size=100):
    points = sample_lowland_points(height_map, n=n)
    
    last_frontier = flood_fill_splotch(matrices[:, :, layer], tuple(points[0]), target=0, fill_value=1, max_size=random.randint(50, max_size))
    for i, point in enumerate(points[1:], start=1):
        if len(last_frontier) == 0:
            break
        next_start = random.choice(list(last_frontier))
        last_frontier = flood_fill_splotch(matrices[:, :, layer], next_start, target=0, fill_value=i+1, max_size=random.randint(50, max_size))

def draw_hatch(urban_grid, road_grid, spacing=5, angle='cross', road_value=1, jitter=2):
    rows, cols = urban_grid.shape
    mask = urban_grid > 0  # mask from urban layer

    if angle in ('horizontal', 'cross'):
        y = 0
        while y < rows:
            jittered_y = int(np.clip(y + random.randint(-jitter, jitter), 0, rows - 1))
            road_grid[jittered_y, :] = np.where(mask[jittered_y, :], road_value, road_grid[jittered_y, :])
            y += spacing + random.randint(-jitter, jitter)

    if angle in ('vertical', 'cross'):
        x = 0
        while x < cols:
            jittered_x = int(np.clip(x + random.randint(-jitter, jitter), 0, cols - 1))
            road_grid[:, jittered_x] = np.where(mask[:, jittered_x], road_value, road_grid[:, jittered_x])
            x += spacing + random.randint(-jitter, jitter)


def render_layers(matrices):
    titles = ('Trees', 'Altitude', 'Urban', 'Roads')
    cmaps = ['Greens', 'terrain', 'tab10', 'Reds']
    fig, axes = plt.subplots(1, 4, figsize=(24, 6))
    for ax, l, title, cmap in zip(axes, range(4), titles, cmaps):
        ax.imshow(matrices[:, :, l], cmap=cmap, interpolation='nearest', vmin=0)
        ax.set_title(title)
        ax.axis('off')
    plt.tight_layout()
    plt.show()

def render_merged(flat, altitude):
    rows, cols = altitude.shape
    image = np.zeros((rows, cols, 4), dtype=np.float32)

    # background
    image[:, :] = [0.10, 0.10, 0.10, 1.0]

    # forest — density shading
    forest_norm = flat[:, :, 0] / (flat[:, :, 0].max() + 1e-6)
    forest_mask = flat[:, :, 0] > 0
    image[forest_mask, 0] = 0.05 + forest_norm[forest_mask] * 0.2
    image[forest_mask, 1] = 0.25 + forest_norm[forest_mask] * 0.4
    image[forest_mask, 2] = 0.05
    image[forest_mask, 3] = 1.0

    # shallow water
    image[flat[:, :, 3] == 1.0] = [0.29, 0.62, 0.83, 1.0]

    # deep water
    image[flat[:, :, 3] == 2.0] = [0.10, 0.29, 0.48, 1.0]

    # urban
    image[flat[:, :, 1] > 0] = [0.71, 0.40, 0.11, 1.0]

    # roads
    image[flat[:, :, 2] > 0] = [0.88, 0.88, 0.88, 1.0]

    plt.figure(figsize=(8, 8))
    plt.imshow(image, interpolation='nearest')
    plt.axis('off')
    plt.title('Merged Map')
    plt.show()


def render_merged_3d_scatter(flat, altitude, point_size=10):
    rows, cols = altitude.shape

    color_lookup = {
        'bg':           [0.10, 0.10, 0.10],
        'shallow':      [0.29, 0.62, 0.83],
        'deep':         [0.10, 0.29, 0.48],
        'urban':        [0.71, 0.40, 0.11],
        'roads':        [0.88, 0.88, 0.88],
    }

    xs, ys = np.meshgrid(np.arange(cols), np.arange(rows))
    xs = xs.flatten()
    ys = ys.flatten()
    zs = altitude[ys, xs] * (rows * 0.2)

    forest_norm = flat[:, :, 0] / (flat[:, :, 0].max() + 1e-6)

    colors = []
    for x, y in zip(xs, ys):
        if flat[y, x, 3] == 2.0:
            colors.append(color_lookup['deep'])
        elif flat[y, x, 3] == 1.0:
            colors.append(color_lookup['shallow'])
        elif flat[y, x, 2] > 0:
            colors.append(color_lookup['roads'])
        elif flat[y, x, 1] > 0:
            colors.append(color_lookup['urban'])
        elif flat[y, x, 0] > 0:
            d = forest_norm[y, x]
            colors.append([0.05 + d * 0.2, 0.25 + d * 0.4, 0.05])
        else:
            colors.append(color_lookup['bg'])

    fig = plt.figure(figsize=(12, 8))
    ax = fig.add_subplot(111, projection='3d')
    ax.scatter(xs, ys, zs, c=colors, s=point_size, alpha=1.0)
    ax.set_box_aspect([1, 1, 0.1])
    ax.set_title('Merged Map with Altitude')
    ax.set_axis_off()
    plt.tight_layout()
    plt.show()

def altitude_cost(height_map, x, y):
    return height_map[x, y] + random.uniform(0, 0.05)

def random_edge_point(rows, cols):
    edge = random.randint(0, 3)
    if edge == 0: return (0, random.randint(0, cols-1))           # top
    elif edge == 1: return (rows-1, random.randint(0, cols-1))    # bottom
    elif edge == 2: return (random.randint(0, rows-1), 0)         # left
    else: return (random.randint(0, rows-1), cols-1)              # right

def astar_road(height_map, urban_layer, start, road_layer, road_value=1):
    rows, cols = height_map.shape
    end = random_edge_point(rows, cols)

    open_set = [(0, start)]
    came_from = {}
    g_score = {start: 0}
    escaped_urban = False

    while open_set:
        _, current = heapq.heappop(open_set)
        x, y = current

        if not escaped_urban and urban_layer[x, y] == 0:
            escaped_urban = True

        at_edge = current == end
        at_urban = escaped_urban and urban_layer[x, y] > 0

        if at_edge or at_urban:
            while current in came_from:
                rx, ry = current
                road_layer[rx, ry] = road_value
                current = came_from[current]
            return

        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if not (0 <= nx < rows and 0 <= ny < cols):
                continue
            tentative_g = g_score[current] + height_map[nx, ny] + random.uniform(0, 0.05)
            neighbor = (nx, ny)
            if tentative_g < g_score.get(neighbor, float('inf')):
                came_from[neighbor] = current
                g_score[neighbor] = tentative_g
                h = abs(nx - end[0]) + abs(ny - end[1])
                heapq.heappush(open_set, (tentative_g + h, neighbor))

def generate_roads(flat, altitude, road_layer=2, num_roads=5):
    from scipy.ndimage import label
    labeled, num_features = label(flat[:, :, 1] > 0)  # urban is layer 1

    if num_features == 0:
        return

    centroids = []
    for i in range(1, num_features + 1):
        cells = list(zip(*np.where(labeled == i)))
        centroids.append(cells[len(cells) // 2])

    # guaranteed connection per city
    for i in range(len(centroids) - 1):
        astar_road(altitude, flat[:, :, 1], centroids[i], flat[:, :, road_layer])

    # extra roads from random urban cells
    urban_cells = list(zip(*np.where(flat[:, :, 1] > 0)))
    if urban_cells:
        extra = random.sample(urban_cells, min(num_roads, len(urban_cells)))
        for start in extra:
            astar_road(altitude, flat[:, :, 1], start, flat[:, :, road_layer])


def add_deep_water(water_layer, depth_threshold=0.3):
    # distance from non-water cells
    distance = distance_transform_edt(water_layer > 0)
    
    # normalize distance
    if distance.max() > 0:
        distance = distance / distance.max()
    
    # deep water where distance from shore exceeds threshold
    deep_water = np.where((water_layer > 0) & (distance > depth_threshold), 2.0, water_layer)
    return deep_water


def generate_water(height_map, water_coverage=0.3):
    rows, cols = height_map.shape
    water = np.zeros((rows, cols), dtype=np.float32)
    sorted_altitudes = np.sort(height_map.flatten())
    water_threshold = sorted_altitudes[int(len(sorted_altitudes) * water_coverage)]

    if water_coverage > 0.3:
        # ocean — flood inward from edges
        queue = deque()
        visited = set()
        for i in range(rows):
            for j in [0, cols - 1]:
                if height_map[i, j] < water_threshold:
                    queue.append((i, j))
                    visited.add((i, j))
        for j in range(cols):
            for i in [0, rows - 1]:
                if height_map[i, j] < water_threshold:
                    queue.append((i, j))
                    visited.add((i, j))
    else:
        # lake — flood outward from lowest interior point
        min_point = np.unravel_index(np.argmin(height_map), height_map.shape)
        queue = deque([min_point])
        visited = set([min_point])

    # shared flood fill for both cases
    while queue:
        x, y = queue.popleft()
        water[x, y] = 1.0
        for dx, dy in [(0,1),(0,-1),(1,0),(-1,0)]:
            nx, ny = x+dx, y+dy
            if (0 <= nx < rows and 0 <= ny < cols
                    and (nx, ny) not in visited
                    and height_map[nx, ny] < water_threshold):
                visited.add((nx, ny))
                queue.append((nx, ny))

    return water


def initialize_grid(
    x=100,
    y=100,
    urban_centers=1,
    iter=10,
    max_size=50,
    forest_density=10,
    restarts=10,
    water_coverage=0.1,
    urban_size=20,
    seed=None,
    render=True,
):
    # categorical layers: 0=forest, 1=urban, 2=roads, 3=water
    flat = np.zeros((x, y, 4), dtype=np.float32)
    altitude = np.zeros((x, y), dtype=np.float32)
    # Deterministic mode: lock both Python and NumPy RNG streams.
    if seed is not None:
        random.seed(seed)
        np.random.seed(seed)
    rng = np.random.default_rng(seed)

    """altitude"""
    altitude = assign_heights(flat[:, :, 0], num_peaks=5, x_max=x, y_max=y)

    """water"""
    flat[:, :, 3] = generate_water(altitude, water_coverage=water_coverage)
    flat[:, :, 3] = add_deep_water(flat[:, :, 3], depth_threshold=0.3)

    """forest"""
    for j in range(forest_density):
        point = tuple(rng.integers([0, 0], [x, y]))
        if flat[point[0], point[1], 3] > 0:
            continue
        last_frontier = flood_fill_splotch(flat[:, :, 0], point, target=0, fill_value=1, max_size=random.randint(10, max_size))
        for i in range(1, iter):
            if len(last_frontier) == 0:
                break
            next_start = random.choice(list(last_frontier))
            last_frontier = flood_fill_splotch(flat[:, :, 0], next_start, target=0, fill_value=1, max_size=random.randint(10, max_size))
    flat[:, :, 0] = np.where(flat[:, :, 3] > 0, 0.0, flat[:, :, 0])

    """urban"""
    for _ in range(urban_centers):
        urban_points = sample_lowland_points(altitude, flat[:, :, 0], flat[:, :, 3], n=restarts, forest_penalty=0.1)
        last_frontier = flood_fill_round(flat[:, :, 1], tuple(urban_points[0]), target=0, fill_value=1, max_size=random.randint(urban_size // 2, urban_size), roundness=0.75)
        for i, point in enumerate(urban_points[1:], start=1):
            if len(last_frontier) == 0:
                break
            next_start = random.choice(list(last_frontier))
            last_frontier = flood_fill_round(flat[:, :, 1], next_start, target=0, fill_value=i+1, max_size=random.randint(urban_size // 2, urban_size), roundness=0.75)
    flat[:, :, 1] = np.where(flat[:, :, 3] > 0, 0.0, flat[:, :, 1])

    """roads"""
    generate_roads(flat, altitude, road_layer=2, num_roads=5)
    flat[:, :, 2] = np.where(flat[:, :, 3] > 0, 0.0, flat[:, :, 2])

    """hatching"""
    draw_hatch(flat[:, :, 1], flat[:, :, 2], spacing=8, angle='cross')

    if render:
        render_merged(flat, altitude)
        render_merged_3d_scatter(flat, altitude)

    return flat, altitude
    


if __name__ == "__main__":
    terrain, altitude = initialize_grid(
        x=100,
        y=100,
        iter=200,
        max_size=200,
        restarts=20,
        forest_density=20,
        urban_centers=2,
        water_coverage=.2,
        urban_size=50,
        seed=1729,
        render=True,
    )
    np.savez("test_grid.npz", terrain = terrain, altitude=altitude)
    print(os.path.abspath("test_grid.npz"))  # exact path it saved to
    print(os.path.exists("test_grid.npz"))   # did it actually save

    data = np.load("test_grid.npz")
    print(data.files)
    print("terrain sum:", data['terrain'].sum())
    print("altitude sum:", data['altitude'].sum())

    