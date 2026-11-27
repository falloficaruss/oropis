from pathlib import Path

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import PercentFormatter

TEXT = "#888780"
CORAL = "#D85A30"
GRAYS = {
    1: "#C4C1B9",
    2: "#B0ADA5",
    4: "#9C9991",
    16: "#78756F",
}
ENGINE_COUNTS = [1, 2, 4, 8, 16]
HIGHLIGHT = [0.99, 0.98, 0.95, 0.90]
OUT_DIR = Path(__file__).resolve().parent

plt.rcParams.update(
    {
        "font.family": "sans-serif",
        "font.sans-serif": ["DejaVu Sans", "Arial", "Helvetica"],
        "font.size": 11,
        "svg.fonttype": "none",
        "axes.edgecolor": TEXT,
        "axes.labelcolor": TEXT,
        "xtick.color": TEXT,
        "ytick.color": TEXT,
        "text.color": TEXT,
        "figure.facecolor": "none",
        "axes.facecolor": "none",
    }
)

p = np.linspace(0.85, 1.0, 400)

fig = plt.figure(figsize=(8, 5))
ax = fig.add_axes([0.10, 0.16, 0.66, 0.63])

fig.text(
    0.10,
    0.95,
    "Package yield collapses as engine count grows",
    ha="left",
    va="top",
    fontsize=15.5,
    fontweight="bold",
    color=TEXT,
)
fig.text(
    0.10,
    0.905,
    "Illustrative: package yield = per-engine yield ^ engine count.\n"
    "Author's arithmetic, not vendor data.",
    ha="left",
    va="top",
    fontsize=11,
    color=TEXT,
    linespacing=1.35,
)

for n in ENGINE_COUNTS:
    if n == 8:
        continue
    ax.plot(p, p**n, color=GRAYS[n], linewidth=1.15, solid_capstyle="round", zorder=2)

ax.plot(p, p**8, color=CORAL, linewidth=3.2, solid_capstyle="round", zorder=3)

ax.set_xlim(0.85, 1.0)
ax.set_ylim(0.0, 1.0)
ax.set_xticks([0.85, 0.90, 0.95, 1.0])
ax.set_yticks([0.0, 0.25, 0.50, 0.75, 1.0])
ax.xaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
ax.yaxis.set_major_formatter(PercentFormatter(1.0, decimals=0))
ax.set_xlabel("Per-engine integration yield", fontsize=11.5, labelpad=8)
ax.set_ylabel("Package yield", fontsize=11.5, labelpad=8)
ax.tick_params(axis="both", which="major", labelsize=11, length=3, width=0.8, pad=4)
ax.grid(True, color=TEXT, alpha=0.14, linewidth=0.6)
ax.set_axisbelow(True)

for side in ("top", "right"):
    ax.spines[side].set_visible(False)
for side in ("left", "bottom"):
    ax.spines[side].set_color(TEXT)
    ax.spines[side].set_linewidth(0.8)

line_labels = {
    1: (0.995, 0.985),
    2: (0.990, 0.925),
    4: (0.985, 0.865),
    8: (0.980, 0.805),
    16: (0.975, 0.745),
}

for n in ENGINE_COUNTS:
    anchor_x, label_y = line_labels[n]
    anchor_y = anchor_x**n
    color = CORAL if n == 8 else TEXT
    ax.annotate(
        f"{n} engine" if n == 1 else f"{n} engines",
        xy=(anchor_x, anchor_y),
        xytext=(1.008, label_y),
        textcoords="data",
        ha="left",
        va="center",
        fontsize=11,
        color=color,
        annotation_clip=False,
        arrowprops=dict(arrowstyle="-", color=color, linewidth=0.8, shrinkA=2, shrinkB=4),
    )

point_labels = [
    (0.99, "99% → 92.3%", (0.940, 0.980)),
    (0.98, "98% → 85.1%", (0.880, 0.850)),
    (0.95, "95% → 66.3%", (0.900, 0.730)),
    (0.90, "90% → 43.0%", (0.875, 0.430)),
]

for p0, label, (label_x, label_y) in point_labels:
    y0 = p0**8
    ax.plot(
        [p0],
        [y0],
        marker="o",
        markersize=5.5,
        markerfacecolor=CORAL,
        markeredgecolor=CORAL,
        zorder=5,
    )
    ax.annotate(
        label,
        xy=(p0, y0),
        xytext=(label_x, label_y),
        textcoords="data",
        ha="center",
        va="center",
        fontsize=11,
        color=TEXT,
        zorder=6,
        arrowprops=dict(arrowstyle="-", color=CORAL, linewidth=0.8, shrinkA=2, shrinkB=4),
    )

ax.annotate(
    "8 engines =\nAyar Labs' demo\nconfiguration per\naccelerator",
    xy=(0.940, 0.940**8),
    xytext=(1.012, 0.700),
    textcoords="data",
    ha="left",
    va="top",
    fontsize=11,
    color=CORAL,
    linespacing=1.25,
    annotation_clip=False,
    arrowprops=dict(arrowstyle="-", color=CORAL, linewidth=0.8, shrinkA=3, shrinkB=4),
)

fig.savefig(OUT_DIR / "yield_cliff.svg", transparent=True, facecolor="none", edgecolor="none")
fig.savefig(
    OUT_DIR / "yield_cliff.png",
    dpi=200,
    transparent=True,
    facecolor="none",
    edgecolor="none",
)
plt.close(fig)

print("Package yield at highlighted per-engine yields")
print("   p     n=1     n=2     n=4     n=8    n=16")
for p0 in HIGHLIGHT:
    row = [p0**n for n in ENGINE_COUNTS]
    print(f"{p0:>4.0%}  " + "  ".join(f"{v:>6.2%}" for v in row))

print("\nHighlighted n=8 points")
for p0 in HIGHLIGHT:
    print(f"{p0:.0%} -> {p0**8:.6f}  ({p0**8:.1%})")

print(f"\nSaved: {OUT_DIR / 'yield_cliff.svg'}")
print(f"Saved: {OUT_DIR / 'yield_cliff.png'}")
