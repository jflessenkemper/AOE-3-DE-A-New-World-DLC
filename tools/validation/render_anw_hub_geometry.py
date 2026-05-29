#!/usr/bin/env python3
"""
ANW Hub Test Map Geometry Renderer

Renders a top-down 2D plot of the ANW Hub Test map geometry
derived from the deployed XS file. Used for sanity-checking
the geometry math after structural changes.

Date: 2026-05-15
"""

import matplotlib.pyplot as plt
import matplotlib.patches as patches
import numpy as np
from pathlib import Path


def render_anw_hub_geometry():
    """Render the ANW Hub Test map geometry to PNG."""

    # Create figure and axis
    fig, ax = plt.subplots(figsize=(10, 10), dpi=120)

    # Set up the coordinate system: [0,1] x [0,1], equal aspect, normal y-axis
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1)
    ax.set_aspect('equal')
    ax.invert_yaxis()  # XS uses bottom-left origin; invert y for top-left display

    # --- OUTER RIM CLIFF: dashed circle at r=0.48 ---
    outer_circle = patches.Circle((0.5, 0.5), 0.48, fill=False,
                                   edgecolor='darkgray', linestyle='--',
                                   linewidth=1.5, label='Outer Rim Cliff')
    ax.add_patch(outer_circle)

    # --- CENTRAL SEA: filled blue circle ---
    sea_radius = 0.159
    sea_circle = patches.Circle((0.5, 0.5), sea_radius, fill=True,
                                facecolor='#000080', edgecolor='navy',
                                linewidth=1, alpha=0.7, label='Central Sea')
    ax.add_patch(sea_circle)

    # --- CRATER RIM: closed heptagon ---
    crater_vertices = [
        (0.725, 0.608),
        (0.556, 0.744),
        (0.344, 0.695),
        (0.250, 0.500),
        (0.344, 0.305),
        (0.556, 0.256),
        (0.725, 0.392),
        (0.725, 0.608),  # Close the polygon
    ]
    crater_x = [v[0] for v in crater_vertices]
    crater_y = [v[1] for v in crater_vertices]
    ax.plot(crater_x, crater_y, color='darkgray', linewidth=2.5, label='Crater Rim')

    # --- 7 SPOKES (radial cliffs) ---
    spokes = [
        ((0.722, 0.608), (0.997, 0.734)),
        ((0.556, 0.744), (0.593, 0.999)),
        ((0.344, 0.695), (0.149, 0.911)),
        ((0.250, 0.500), (0.001, 0.500)),
        ((0.344, 0.305), (0.149, 0.089)),
        ((0.556, 0.256), (0.593, 0.001)),
        ((0.725, 0.392), (0.997, 0.266)),
    ]
    for i, (start, end) in enumerate(spokes):
        ax.plot([start[0], end[0]], [start[1], end[1]],
               color='darkgray', linewidth=1, alpha=0.6)

    # --- OBSERVER ISLAND (P1): small green circle ---
    p1_radius = 0.025
    p1_circle = patches.Circle((0.5, 0.5), p1_radius, fill=True,
                               facecolor='green', edgecolor='darkgreen',
                               linewidth=1, label='P1 Observer Island')
    ax.add_patch(p1_circle)
    ax.text(0.5, 0.5, 'P1', ha='center', va='center', fontsize=8,
           fontweight='bold', color='white')

    # --- 7 INNER BAYS: light-blue filled circles ---
    bays = [
        (0.820, 0.500),
        (0.700, 0.750),
        (0.430, 0.812),
        (0.211, 0.638),
        (0.211, 0.362),
        (0.430, 0.188),
        (0.700, 0.250),
    ]
    bay_radius = 0.026
    for i, (bx, by) in enumerate(bays):
        bay_circle = patches.Circle((bx, by), bay_radius, fill=True,
                                    facecolor='lightblue', edgecolor='steelblue',
                                    linewidth=0.5, alpha=0.7)
        ax.add_patch(bay_circle)

    # --- 7 PLAYER TCs (P2-P8): small colored squares ---
    player_tcs = [
        ((0.860, 0.500), 'red', 'P2'),
        ((0.725, 0.781), 'orange', 'P3'),
        ((0.421, 0.851), 'yellow', 'P4'),
        ((0.175, 0.655), 'green', 'P5'),
        ((0.175, 0.345), 'cyan', 'P6'),
        ((0.421, 0.149), 'blue', 'P7'),
        ((0.725, 0.219), 'magenta', 'P8'),
    ]
    tc_size = 0.018
    for (tcx, tcy), color, label in player_tcs:
        square = patches.Rectangle((tcx - tc_size/2, tcy - tc_size/2),
                                   tc_size, tc_size, fill=True,
                                   facecolor=color, edgecolor='black',
                                   linewidth=1, alpha=0.8)
        ax.add_patch(square)
        ax.text(tcx, tcy - 0.035, label, ha='center', va='top', fontsize=7)

    # --- 7 TRADE SOCKETS: small dark-yellow triangles ---
    trade_sockets = [
        (0.800, 0.500),
        (0.687, 0.735),
        (0.433, 0.793),
        (0.230, 0.630),
        (0.230, 0.369),
        (0.433, 0.208),
        (0.687, 0.265),
    ]
    trade_size = 0.015
    for (tsx, tsy) in trade_sockets:
        triangle = patches.Polygon([
            (tsx, tsy - trade_size),           # bottom
            (tsx - trade_size, tsy + trade_size),  # top-left
            (tsx + trade_size, tsy + trade_size),  # top-right
        ], fill=True, facecolor='goldenrod', edgecolor='darkgoldenrod',
           linewidth=0.5)
        ax.add_patch(triangle)

    # --- 7 NATIVE VILLAGES: small black stars ---
    native_villages = [
        (0.900, 0.500),
        (0.749, 0.813),
        (0.410, 0.890),
        (0.139, 0.673),
        (0.139, 0.327),
        (0.410, 0.110),
        (0.749, 0.187),
    ]
    star_size = 0.012
    for (nvx, nvy) in native_villages:
        # Create a 5-pointed star
        angles = np.array([0, 72, 144, 216, 288]) * np.pi / 180
        outer_x = nvx + star_size * np.cos(angles + np.pi/2)
        outer_y = nvy + star_size * np.sin(angles + np.pi/2)

        inner_angles = np.array([36, 108, 180, 252, 324]) * np.pi / 180
        inner_r = star_size * 0.4
        inner_x = nvx + inner_r * np.cos(inner_angles + np.pi/2)
        inner_y = nvy + inner_r * np.sin(inner_angles + np.pi/2)

        # Interleave outer and inner points
        star_x = []
        star_y = []
        for i in range(5):
            star_x.append(outer_x[i])
            star_y.append(outer_y[i])
            star_x.append(inner_x[i])
            star_y.append(inner_y[i])
        star_x.append(outer_x[0])
        star_y.append(outer_y[0])

        star = patches.Polygon(list(zip(star_x, star_y)), fill=True,
                              facecolor='black', edgecolor='black',
                              linewidth=0.5)
        ax.add_patch(star)

    # --- Labels and formatting ---
    ax.set_xlabel('X (normalized)', fontsize=10)
    ax.set_ylabel('Y (normalized)', fontsize=10)
    ax.set_title('ANW Hub Test — derived XS geometry (2026-05-15 crater-rim + water fix)',
                fontsize=12, fontweight='bold', pad=15)
    ax.grid(True, alpha=0.2, linestyle=':', linewidth=0.5)
    ax.legend(loc='upper left', fontsize=8)

    # Create output directory if it doesn't exist
    output_dir = Path('/var/home/jflessenkemper/AOE-3-DE-A-New-World/artifacts/validation/hub_test_layout')
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save the figure
    output_path = output_dir / 'whole_map_xs_render.png'
    plt.savefig(str(output_path), bbox_inches='tight', dpi=120)

    print(f"Geometry rendered successfully to: {output_path}")
    return output_path


if __name__ == '__main__':
    render_anw_hub_geometry()
