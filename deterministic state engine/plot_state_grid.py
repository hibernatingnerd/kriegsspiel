import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from kriegsspiel.engine.enums import Side, TerrainBase, TerrainFeature
from kriegsspiel.scenarios.generated_world import build_world_from_npz


def plot_state_grid(world, save_path: str | None = None, show_units: bool = True):
    grid = world.terrain

    base_order = [
        TerrainBase.OPEN,
        TerrainBase.FOREST,
        TerrainBase.URBAN,
        TerrainBase.WATER,
        TerrainBase.MOUNTAIN,
        TerrainBase.SWAMP,
        TerrainBase.IMPASSABLE,
    ]
    base_to_idx = {b: i for i, b in enumerate(base_order)}

    base_mat = np.zeros((grid.height, grid.width), dtype=np.int32)
    road_mask = np.zeros((grid.height, grid.width), dtype=np.uint8)
    deep_water_mask = np.zeros((grid.height, grid.width), dtype=np.uint8)

    for r in range(grid.height):
        for c in range(grid.width):
            cell = grid.cell_at((r, c))
            base_mat[r, c] = base_to_idx[cell.base]
            if TerrainFeature.ROAD in cell.features:
                road_mask[r, c] = 1
            if TerrainFeature.WATER_DEEP in cell.features:
                deep_water_mask[r, c] = 1

    # Fixed demo-friendly colors:
    # OPEN=tan, FOREST=green, URBAN=gray, WATER=blue, MOUNTAIN=brown,
    # SWAMP=olive, IMPASSABLE=black.
    colors = ["#d9c9a3", "#2e7d32", "#8e8e8e", "#1e88e5", "#8d6e63", "#6b8e23", "#000000"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(len(base_order) + 1) - 0.5, cmap.N)

    plt.figure(figsize=(10, 10))
    plt.imshow(base_mat, cmap=cmap, norm=norm, interpolation="nearest")

    ys, xs = np.where(road_mask == 1)
    plt.scatter(xs, ys, s=2, c="#fff176", alpha=0.95, label="ROAD feature")
    d_ys, d_xs = np.where(deep_water_mask == 1)
    plt.scatter(d_xs, d_ys, s=8, c="#0d47a1", alpha=0.7, marker="s", linewidths=0, label="WATER_DEEP")

    if show_units:
        for i, unit in enumerate(world.alive_units_of_side(Side.BLUE), start=1):
            r, c = unit.position
            plt.scatter(c, r, s=110, c="#0d47a1", marker="o", edgecolors="white", linewidths=1.0, zorder=5)
            plt.text(c + 0.4, r - 0.3, f"B{i}", color="white", fontsize=8, zorder=6)

        for i, unit in enumerate(world.alive_units_of_side(Side.RED), start=1):
            r, c = unit.position
            plt.scatter(c, r, s=120, c="#b71c1c", marker="X", edgecolors="white", linewidths=0.8, zorder=5)
            plt.text(c + 0.4, r - 0.3, f"R{i}", color="white", fontsize=8, zorder=6)

    legend = [
        Patch(facecolor=colors[i], edgecolor="none", label=base_order[i].value)
        for i in range(len(base_order))
    ]
    legend.append(Patch(facecolor="#fff176", edgecolor="none", label="ROAD feature"))
    legend.append(Patch(facecolor="#0d47a1", edgecolor="none", label="WATER_DEEP"))
    if show_units:
        legend.extend(
            [
                Line2D([0], [0], marker="o", color="none", markerfacecolor="#0d47a1", markeredgecolor="white", markersize=8, label="BLUE unit"),
                Line2D([0], [0], marker="X", color="none", markerfacecolor="#b71c1c", markeredgecolor="white", markersize=8, label="RED unit"),
            ]
        )
    plt.legend(handles=legend, bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0.0, fontsize=9)
    plt.title("Deterministic TerrainGrid View")
    plt.axis("off")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=150)
        print(f"Saved image to: {save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    plot_state_grid(
        npz_path=r"D:\hackathon\kriegsspiel\backend\test_grid.npz",
        save_path=r"D:\hackathon\Hacky Stack\state_grid.png",
        show_units=True,
    )
