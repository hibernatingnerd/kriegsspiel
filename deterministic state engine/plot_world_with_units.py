import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap, BoundaryNorm
from matplotlib.patches import Patch
from matplotlib.lines import Line2D

from kriegsspiel.engine.enums import Side, TerrainBase, TerrainFeature
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world


def plot_world_with_units(save_path: str | None = None) -> None:
    world = build_latgale_world()
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

    # OPEN, FOREST, URBAN, WATER, MOUNTAIN, SWAMP, IMPASSABLE
    colors = ["#d9c9a3", "#2e7d32", "#8e8e8e", "#1e88e5", "#8d6e63", "#6b8e23", "#000000"]
    cmap = ListedColormap(colors)
    norm = BoundaryNorm(np.arange(len(base_order) + 1) - 0.5, cmap.N)

    plt.figure(figsize=(10, 10))
    plt.imshow(base_mat, cmap=cmap, norm=norm, interpolation="nearest")

    ys, xs = np.where(road_mask == 1)
    plt.scatter(xs, ys, s=10, c="#fff176", alpha=0.95, marker="s", linewidths=0)
    d_ys, d_xs = np.where(deep_water_mask == 1)
    plt.scatter(d_xs, d_ys, s=14, c="#0d47a1", alpha=0.7, marker="s", linewidths=0)

    # Overlay units by side.
    for unit in world.alive_units_of_side(Side.BLUE):
        r, c = unit.position
        plt.scatter(c, r, s=90, c="#0d47a1", marker="o", edgecolors="white", linewidths=0.8, zorder=5)
        plt.text(c + 0.15, r - 0.15, unit.unit_id.split("-")[1], color="white", fontsize=7, zorder=6)

    for unit in world.alive_units_of_side(Side.RED):
        r, c = unit.position
        plt.scatter(c, r, s=100, c="#b71c1c", marker="X", edgecolors="white", linewidths=0.7, zorder=5)
        plt.text(c + 0.15, r - 0.15, unit.unit_id.split("-")[1], color="white", fontsize=7, zorder=6)

    terrain_legend = [
        Patch(facecolor=colors[i], edgecolor="none", label=base_order[i].value)
        for i in range(len(base_order))
    ]
    terrain_legend.append(Patch(facecolor="#fff176", edgecolor="none", label="ROAD feature"))
    terrain_legend.append(Patch(facecolor="#0d47a1", edgecolor="none", label="WATER_DEEP"))
    unit_legend = [
        Line2D([0], [0], marker="o", color="none", markerfacecolor="#0d47a1", markeredgecolor="white", markersize=8, label="BLUE unit"),
        Line2D([0], [0], marker="X", color="none", markerfacecolor="#b71c1c", markeredgecolor="white", markersize=8, label="RED unit"),
    ]

    plt.legend(
        handles=terrain_legend + unit_legend,
        bbox_to_anchor=(1.02, 1),
        loc="upper left",
        borderaxespad=0.0,
        fontsize=8,
    )
    plt.title("Latgale 2027: Terrain + Units")
    plt.axis("off")
    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, dpi=160)
        print(f"Saved image to: {save_path}")
    else:
        plt.show()


if __name__ == "__main__":
    plot_world_with_units(save_path=r"D:\hackathon\Hacky Stack\world_with_units.png")
