import numpy as np
from pathlib import Path
import sys

home = Path(__file__).parent.parent.parent
sys.path.insert(0, str(home))

from kriegsspiel.engine import state
from kriegsspiel.scenarios.latgale_2027 import build_latgale_world
from kriegsspiel.engine.enums import Side

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyArrowPatch
import numpy as np
from kriegsspiel.engine.enums import TerrainBase, Side

def visualize_combat(world_before: dict, world_after, attack_map: dict, terrain):
    fig, axes = plt.subplots(1, 2, figsize=(20, 10))

    terrain_colors = {
        TerrainBase.OPEN:       "#d4e6b5",
        TerrainBase.FOREST:     "#4a7c59",
        TerrainBase.WATER:      "#4a90d9",
        TerrainBase.URBAN:      "#c2b280",
        TerrainBase.IMPASSABLE: "#555555",
    }

    readiness_colors = {
        "FULLY_OPERATIONAL": "#00ff00",
        "DEGRADED":          "#ffaa00",
        "SUPPRESSED":        "#ff4400",
        "DESTROYED":         "#444444",
    }

    for ax, (title, states) in zip(axes, [
        ("BEFORE", world_before),
        ("AFTER",  world_after.units),
    ]):
        ax.set_title(title, fontsize=16, fontweight="bold")
        ax.set_xlim(-0.5, terrain.width - 0.5)
        ax.set_ylim(-0.5, terrain.height - 0.5)
        ax.invert_yaxis()
        ax.set_aspect("equal")

        # terrain
        for r in range(terrain.height):
            for c in range(terrain.width):
                cell = terrain.cell_at((r, c))
                color = terrain_colors.get(cell.base, "#ffffff")
                ax.add_patch(mpatches.Rectangle(
                    (c - 0.5, r - 0.5), 1, 1, color=color, zorder=0
                ))

        # attack arrows — shrink endpoints so arrows aren't hidden under markers
        for target_id, attacker_ids in attack_map.items():
            t_pos = states[target_id].position
            for attacker_id in attacker_ids:
                a_pos = states[attacker_id].position
                ax.annotate("",
                    xy=(t_pos[1], t_pos[0]),
                    xytext=(a_pos[1], a_pos[0]),
                    arrowprops=dict(
                        arrowstyle="-|>",
                        color="#ff0000",
                        lw=2.5,
                        mutation_scale=20,
                        connectionstyle="arc3,rad=0.25",
                        shrinkA=12,   # pull tail away from attacker circle
                        shrinkB=12,   # pull head away from target circle
                    ),
                    zorder=6        # above units
                )

        # units
        for uid, u in states.items():
            pos = u.position
            side_color = "#1f77b4" if u.side == Side.BLUE else "#d62728"
            alpha = 1.0 if u.is_alive else 0.25
            r_color = readiness_colors.get(u.readiness.value, "#ffffff")

            ax.plot(pos[1], pos[0], "o",
                    color=side_color, markersize=16,
                    alpha=alpha, zorder=4,
                    markeredgecolor=r_color, markeredgewidth=2.5)

            # unit type (MNV, FRS, ENB) inside the circle
            unit_type = uid.split("-")[1]
            ax.text(pos[1], pos[0], unit_type,
                    ha="center", va="center",
                    fontsize=12, color="white", fontweight="bold", zorder=5)

            # full id beside the vertex
            ax.text(pos[1] + 0.55, pos[0], uid,
                    ha="left", va="center",
                    fontsize=10, color="white", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.5, ec="none"))

            # readiness + strength above
            label = f"{u.readiness.value}  {u.strength:.2f}"
            ax.text(pos[1], pos[0] - 0.7, label,
                    ha="center", va="bottom",
                    fontsize=11, color=r_color, fontweight="bold", zorder=5,
                    bbox=dict(boxstyle="round,pad=0.15", fc="black", alpha=0.5, ec="none"))

    # legend
    legend_elements = [
        mpatches.Patch(color="#1f77b4", label="BLUE"),
        mpatches.Patch(color="#d62728", label="RED"),
        mpatches.Patch(color="#00ff00", label="FULLY_OPERATIONAL"),
        mpatches.Patch(color="#ffaa00", label="DEGRADED"),
        mpatches.Patch(color="#ff4400", label="SUPPRESSED"),
        mpatches.Patch(color="#444444", label="DESTROYED"),
    ]
    axes[1].legend(handles=legend_elements, loc="lower right", fontsize=8)

    plt.tight_layout()
    plt.savefig("combat_map.png", dpi=150)
    plt.show()

# --- run ---
w = build_latgale_world()
w.compute_visibilities()
unit_decision_list = [
    # RED attacking BLUE
    {"unit_id": "RED-MNV-006-A", "action": "ATTACK", "target_id": "BLUE-MNV-001-A", "target_position": None},
    {"unit_id": "RED-MNV-005-A", "action": "ATTACK", "target_id": "BLUE-MNV-002-A", "target_position": None},
    {"unit_id": "RED-FRS-007-A", "action": "ATTACK", "target_id": "BLUE-MNV-001-A", "target_position": None},
    # BLUE attacking RED
    {"unit_id": "BLUE-MNV-001-A", "action": "ATTACK", "target_id": "RED-MNV-006-A", "target_position": None},
    {"unit_id": "BLUE-MNV-002-A", "action": "ATTACK", "target_id": "RED-MNV-005-A", "target_position": None},
    # some units waiting
    {"unit_id": "BLUE-FRS-001-A", "action": "WAIT", "target_id": None, "target_position": None},
    {"unit_id": "BLUE-ENB-001-A", "action": "WAIT", "target_id": None, "target_position": None},
    {"unit_id": "RED-ENB-009-A",  "action": "WAIT", "target_id": None, "target_position": None},
]

before_snapshot = {uid: u.model_copy() for uid, u in w.units.items()}
attack_map = w._build_attack_map(unit_decision_list)
w._resolve_attacks(attack_map)

visualize_combat(before_snapshot, w, attack_map, w.terrain)

# w = build_latgale_world()
# w.compute_visibilities()

# # --- mock decisions ---
# unit_decision_list = [
#     # RED attacking BLUE
#     {"unit_id": "RED-MNV-006-A", "action": "ATTACK", "target_id": "BLUE-MNV-001-A", "target_position": None},
#     {"unit_id": "RED-MNV-005-A", "action": "ATTACK", "target_id": "BLUE-MNV-002-A", "target_position": None},
#     {"unit_id": "RED-FRS-007-A", "action": "ATTACK", "target_id": "BLUE-MNV-001-A", "target_position": None},
#     # BLUE attacking RED
#     {"unit_id": "BLUE-MNV-001-A", "action": "ATTACK", "target_id": "RED-MNV-006-A", "target_position": None},
#     {"unit_id": "BLUE-MNV-002-A", "action": "ATTACK", "target_id": "RED-MNV-005-A", "target_position": None},
#     # some units waiting
#     {"unit_id": "BLUE-FRS-001-A", "action": "WAIT", "target_id": None, "target_position": None},
#     {"unit_id": "BLUE-ENB-001-A", "action": "WAIT", "target_id": None, "target_position": None},
#     {"unit_id": "RED-ENB-009-A",  "action": "WAIT", "target_id": None, "target_position": None},
# ]

# w.unit_decision_list=unit_decision_list

# # --- before ---
# print("=== BEFORE ===")
# print("BLUE:")
# for u in w.units_of_side(Side.BLUE):
#     print(f"  {u.unit_id}: strength={u.strength:.2f} readiness={u.readiness}")
# print("RED:")
# for u in w.units_of_side(Side.RED):
#     print(f"  {u.unit_id}: strength={u.strength:.2f} readiness={u.readiness}")

# # --- resolve ---
# w.map_solve_attacks()

# # --- after ---
# print("\n=== AFTER ===")
# print("BLUE:")
# for u in w.units_of_side(Side.BLUE):
#     print(f"  {u.unit_id}: strength={u.strength:.2f} readiness={u.readiness}")
# print("RED:")
# for u in w.units_of_side(Side.RED):
#     print(f"  {u.unit_id}: strength={u.strength:.2f} readiness={u.readiness}")

