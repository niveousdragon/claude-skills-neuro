---
name: figure-alignment
description: Use when creating, modifying, or debugging multi-panel matplotlib figures for publication. Use when panels misalign, axes don't share baselines, squares aren't square, or layout changes break other panels. Use when user says "fix alignment", "make square", "move panel", "adjust spacing", or any figure layout work.
---

# Publication Figure Alignment

## Overview

Build multi-panel figures on a **single master GridSpec** — never subfigures. Verify alignment **programmatically** — never visually. Route all styling through **StylePreset** — no free parameters.

## Core Rules

1. **One figure, one GridSpec.** All panels live in cells of the same grid. Use cell spanning for different panel sizes. Use LCM row/column counts for columns with different subdivision.
2. **Axes alignment is automatic.** Same GridSpec row = same y baseline. Same GridSpec column = same x left edge. This is guaranteed by matplotlib — do not fight it.
3. **Subfigures are banned.** `fig.subfigures()` creates independent layout units whose axes do NOT align across boundaries. Never use them. The matplotlib docs explicitly state: "subfigure layouts are independent, so the Axes spines are not necessarily aligned."
4. **StylePreset is mandatory.** Every font size, line width, tick param goes through StylePreset. No raw `fontsize=11` or `linewidth=1.5` anywhere unless the user explicitly overrides a specific element.
5. **Programmatic verification after every generation.** Run `verify_figure()` — check axis alignment, squareness, overlap. Never claim "looks good" or "looks square" from visual inspection alone.
6. **Panel labels are positioned last, from grid geometry.** Compute x/y from axes positions. Labels in the same grid row share y. Labels in the same grid column share x. Place on main figure with `fig.text()`.

## Grid Design

### Step 1: Plan the grid on paper

Before writing code, determine:
- How many distinct rows and columns of panels
- Which panels span multiple cells
- Where gaps go (explicit gap rows/columns)

### Step 2: Compute LCM for unequal subdivisions

If left column needs 2 panels and right needs 3, use LCM(2,3) = 6 content rows:

```python
# 6 content rows + gap rows between panels
gs = GridSpec(11, 3, figure=fig,
    height_ratios=[
        3,    # L0 / R0 (shared top)
        3,    # L0 continued
        3,    # L0 continued
        0.3,  # gap
        2,    # L1 / R1
        2,    # L1 / R1 continued
        0.3,  # gap
        2,    # L1 continued / R2
        2,    # L1 continued / R2 continued
        0.3,  # bottom gap
        0.3,  # bottom pad
    ],
    width_ratios=[10, 0.5, 6],  # col_A | gap | col_B
    left=0.08, right=0.95, top=0.95, bottom=0.05,
    wspace=0, hspace=0,
)

ax_L0 = fig.add_subplot(gs[0:3, 0], label="A")   # rows 0-2, left col
ax_L1 = fig.add_subplot(gs[4:9, 0], label="C")   # rows 4-8, left col
ax_R0 = fig.add_subplot(gs[0:3, 2], label="B")   # rows 0-2, right col (aligned with L0)
ax_R1 = fig.add_subplot(gs[4:6, 2], label="D")   # rows 4-5, right col
ax_R2 = fig.add_subplot(gs[7:9, 2], label="E")   # rows 7-8, right col
# Column 1 is always the gap — never assign axes to it
```

### Step 3: Use explicit gap rows/columns

Never rely on `wspace`/`hspace` for spacing between panels. Add dedicated rows/columns:

```python
width_ratios = [10, 0.5, 6]      # col_A | gap | col_B
height_ratios = [6, 0.3, 4, 0.5, 5]  # row1 | gap | row2 | gap | row3
```

Gap cells stay empty — never assign axes to them.

### Step 4: GridSpec boundaries

```python
gs = GridSpec(nrows, ncols, figure=fig,
    width_ratios=width_ratios,
    height_ratios=height_ratios,
    left=0.08, right=0.95, top=0.95, bottom=0.06,
    wspace=0, hspace=0,  # ALWAYS zero — gaps are explicit grid cells
)
```

### Step 5: Compute row ratios for square cells

When panels must be physically square, solve for the row ratio algebraically — don't guess and iterate:

```python
# Given: figure dimensions, column ratios, and margins
W_content = W_CM * (RIGHT - LEFT)
H_content = H_CM * (TOP - BOTTOM)
col_w_cm = W_content * content_col_ratio / sum(col_ratios)

# For a square cell: row_height_cm = col_w_cm
# row_ratio / sum_row * H_content = col_w_cm
# Solve: R = col_w_cm * non_R_sum / (H_content - N_square_rows * col_w_cm)
non_R_sum = sum(all non-square row ratios)
R = col_w_cm * non_R_sum / (H_content - 2 * col_w_cm)  # for 2 square rows
```

This gives exact squareness. Verify: `R / sum_row * H_content` should equal `col_w_cm`.

## Iterative Grid Refinement

**Design the grid structure with the user BEFORE populating with data.** Data-heavy panels take minutes to render. Grid structure issues (wrong column ratios, missing gaps, broken symmetry) are visible instantly from an empty grid diagram.

### Workflow

1. **Write a debug grid script** that renders all cells with colored overlays showing axes assignments, row/column ratios, physical dimensions, and gap labels. No data — just the skeleton.

```python
# For each grid cell: draw border, label gap rows/cols in gray
# For each axes assignment: colored overlay with label and grid coords
# Annotate margins: row heights in cm, column widths in cm
fig.text(x, y, f"c{c}\n{ratio}\n{w:.1f}cm", ...)  # column labels at top
fig.text(x, y, f"r{r} ({ratio:.2f}) {h:.1f}cm", ...)  # row labels on left
```

2. **Show to user.** Fix structural issues (asymmetric halves, wrong aspect ratios, missing gaps, overcrowded regions) before any data touches the figure.

3. **Only after grid approval**, populate with data by wiring panel functions to the approved grid cells.

### Why this matters

Common failure mode: spend 2 minutes rendering a data-heavy figure, discover the column ratios are wrong, re-render, discover the gaps are too small, re-render. Each iteration costs a full data load + plot cycle. The debug grid renders in <1 second and catches:

- Asymmetric halves when symmetry is required
- Non-square cells when panels need square aspect
- Missing or undersized gap rows/columns
- Wrong column spans for multi-column panels
- SubplotSpec regions that don't cover the right cells

### Symmetric halves pattern

When left and right halves must mirror each other, enforce it in column ratios:

```python
# WRONG: asymmetric (different content widths per half)
col_ratios = [1, 0.06, 1, 0.25, 1.2, 0.06, 0.5]

# RIGHT: symmetric (both halves identical)
col_ratios = [1, g, 1, G, 1, g, 1]  # mirrors around G
```

If one half needs a different internal split (e.g., 70:30 for B bottom vs 50:50 for B top), use SubplotSpec within that row's cell — don't break column symmetry.

### SubplotSpec for local splits within a symmetric grid

When a panel pair in one row needs different width ratios than the same columns in another row, use SubplotSpec to subdivide within the master grid cell. Row alignment is preserved because the SubplotSpec region is bounded by the master grid row.

```python
# B bottom needs 70:30 but B top needs 50:50 (both square)
# Solution: B top panels in individual grid cells, B bottom via SubplotSpec
ax_B_place = fig.add_subplot(gs[0, 4], label="B_place")  # square cell
ax_B_hd    = fig.add_subplot(gs[0, 6], label="B_hd")     # square cell

inner = GridSpecFromSubplotSpec(1, 2, subplot_spec=gs[2, 4:7],
                                 width_ratios=[0.70, 0.30], wspace=0.15)
ax_loco    = fig.add_subplot(inner[0, 0], label="B_loco")
ax_density = fig.add_subplot(inner[0, 1], label="B_density")
# Row alignment with A_umap in gs[2, 0] is guaranteed by master grid row 2
```

### Centered sub-panels via padding SubplotSpec

To center a panel at partial width within a wider grid region (e.g., spectra at half-width under full-width networks):

```python
inner = GridSpecFromSubplotSpec(1, 3, subplot_spec=gs[7, 0:3],
                                 width_ratios=[1, 2, 1], wspace=0)
ax_spec = fig.add_subplot(inner[0, 1], label="C_spec")
# Spectrum occupies middle 50%, padding 25% on each side
```

## Delegation Pattern

Two calling conventions, chosen per panel based on complexity:

| Panel type | Receives | Orchestrator creates | Use when |
|---|---|---|---|
| Simple | `ax` | The axes | Single plot area (line, scatter, heatmap, bar) |
| Complex | `fig` + `SubplotSpec` | Nothing | Panel needs internal substructure (subplot grid, heatmap+colorbar) |

### Simple panels: receive a pre-created Axes

```python
# Orchestrator
ax_A = fig.add_subplot(gs[0:3, 0], label="A")
create_panel_A(ax_A, style, panel_size_A)

# Panel script
def create_panel_A(ax, style, panel_size_cm):
    style.apply_to_axes(ax, panel_size_cm, 'cm')
    ax.plot(x, y)
    ax.set_xlabel("Time (s)")
    ax.set_ylabel("Amplitude")
```

**Colorbars must not resize the parent axes.** Three approaches, from safest to most intrusive:

```python
# BEST: inset_axes — colorbar floats inside the axes, zero effect on parent size
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
cax = inset_axes(ax, width="4%", height="60%", loc="right",
                 bbox_to_anchor=(1.05, 0, 1, 1), bbox_transform=ax.transAxes,
                 borderpad=0)
fig.colorbar(im, cax=cax)

# OK: make_axes_locatable — steals space from parent, shrinks it slightly.
# Breaks row alignment if other axes in the same row don't also have colorbars.
from mpl_toolkits.axes_grid1 import make_axes_locatable
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.05)
fig.colorbar(im, cax=cax)

# BANNED in composite figures: fig.colorbar(im, ax=ax) — steals space AND
# repositions the parent axes unpredictably. Only acceptable in standalone plots.
```

### Complex panels: receive a SubplotSpec region

```python
# Orchestrator
create_panel_D(fig, gs[4:7, 2:5], style, panel_size_D)

# Panel script
def create_panel_D(fig, subplot_spec, style, panel_size_cm):
    from matplotlib.gridspec import GridSpecFromSubplotSpec
    inner = GridSpecFromSubplotSpec(2, 3, subplot_spec=subplot_spec,
                                    wspace=0.3, hspace=0.3)
    for i in range(2):
        for j in range(3):
            ax = fig.add_subplot(inner[i, j], label=f"D_{i}{j}")
            style.apply_to_axes(ax, ...)
            ax.imshow(data[i, j])
```

The outer boundaries of the SubplotSpec are locked to the master grid. Internal axes are the panel's own business.

**Rule of thumb:** If a panel's internal axes need to align with axes in another panel, those axes belong in the master grid, not inside a delegated SubplotSpec.

### Per-panel padding via inner grid

`GridSpecFromSubplotSpec` does not accept `left`/`right`/`top`/`bottom`. Use padding cells instead:

```python
def create_panel_with_padding(fig, subplot_spec, style, panel_size_cm,
                               pad_l=0.12, pad_r=0.05, pad_t=0.05, pad_b=0.15):
    inner = GridSpecFromSubplotSpec(3, 3, subplot_spec=subplot_spec,
                                    width_ratios=[pad_l, 1, pad_r],
                                    height_ratios=[pad_t, 1, pad_b],
                                    wspace=0, hspace=0)
    ax = fig.add_subplot(inner[1, 1], label="X")
    style.apply_to_axes(ax, panel_size_cm, 'cm')
    return ax
```

### Standalone mode

Both panel types run independently for testing:

```python
# Simple panel
if __name__ == '__main__':
    fig, ax = plt.subplots(figsize=(10/2.54, 8/2.54))
    create_panel_A(ax, StylePreset.publication_default(), (10, 8))
    plt.savefig("panel_A_standalone.png")

# Complex panel
if __name__ == '__main__':
    fig = plt.figure(figsize=(16/2.54, 6/2.54))
    gs = fig.add_gridspec(1, 1)
    create_panel_D(fig, gs[0], StylePreset.publication_default(), (16, 6))
    plt.savefig("panel_D_standalone.png")
```

## Panel Labels

Labels are placed AFTER all content is finalized. Positions are derived from axes positions with row/column alignment enforced:

```python
def add_panel_labels(fig, label_map, fontsize=12, x_offset=-0.03, y_offset=0.01):
    """Add panel labels aligned by grid row and column.

    Parameters
    ----------
    label_map : dict
        {label_str: axes_name_or_axes} mapping labels to their axes.
        Use the axes label string or the axes object directly.
    """
    fig.canvas.draw()

    # Collect positions from axes
    info = {}
    for label, ax_ref in label_map.items():
        if isinstance(ax_ref, str):
            ax = next(a for a in fig.axes if a.get_label() == ax_ref)
        else:
            ax = ax_ref
        pos = ax.get_position()
        info[label] = {
            'x': pos.x0 + x_offset,
            'y': pos.y0 + pos.height + y_offset,
            'row_top': round(pos.y0 + pos.height, 2),  # for row grouping
            'col_left': round(pos.x0, 2),                # for column grouping
        }

    # Enforce row alignment: labels at same row_top get same y
    from collections import defaultdict
    row_groups = defaultdict(list)
    for label, d in info.items():
        row_groups[d['row_top']].append(label)
    for members in row_groups.values():
        if len(members) > 1:
            shared_y = max(info[l]['y'] for l in members)
            for l in members:
                info[l]['y'] = shared_y

    # Enforce column alignment: labels at same col_left get same x
    col_groups = defaultdict(list)
    for label, d in info.items():
        col_groups[d['col_left']].append(label)
    for members in col_groups.values():
        if len(members) > 1:
            shared_x = min(info[l]['x'] for l in members)
            for l in members:
                info[l]['x'] = shared_x

    # Place labels on main figure
    for label, d in info.items():
        fig.text(d['x'], d['y'], label,
                 fontsize=fontsize, fontweight='bold',
                 va='bottom', ha='left', transform=fig.transFigure)
```

## Programmatic Verification

Run after every figure generation. **Do not skip.**

```python
def verify_figure(fig, expected=None, tolerance=0.005):
    """Verify axis alignment, squareness, and overlap.

    Parameters
    ----------
    expected : dict, optional
        {
            'square': ['B'],                          # axes that must be square
            'rows': [['A', 'B'], ['C', 'D']],        # axes sharing row baseline
            'cols': [['A', 'C'], ['B', 'D']],         # axes sharing column left edge
        }
    tolerance : float
        Max acceptable misalignment in figure-fraction units (~0.005 = 0.5%).

    Returns
    -------
    dict : axes_name -> position info
    """
    fig.canvas.draw()
    fig_w, fig_h = fig.get_size_inches()
    issues = []

    axes_info = {}
    for ax in fig.axes:
        name = ax.get_label()
        if not name or name.startswith('_'):
            continue
        pos = ax.get_position()
        w_inch = pos.width * fig_w
        h_inch = pos.height * fig_h
        axes_info[name] = {
            'x0': pos.x0, 'y0': pos.y0,
            'x1': pos.x0 + pos.width, 'y1': pos.y0 + pos.height,
            'w_cm': w_inch * 2.54, 'h_cm': h_inch * 2.54,
            'aspect': h_inch / w_inch if w_inch > 0 else 0,
        }

    # Print all positions
    for name, info in sorted(axes_info.items()):
        sq = ' [SQUARE]' if abs(info['aspect'] - 1.0) < 0.02 else ''
        print(f"  {name:12s}: ({info['w_cm']:.1f} x {info['h_cm']:.1f} cm) "
              f"aspect={info['aspect']:.3f}{sq}")

    if expected is None:
        return axes_info

    # Check squareness
    for name in expected.get('square', []):
        if name in axes_info:
            a = axes_info[name]['aspect']
            if abs(a - 1.0) > 0.02:
                issues.append(f"SQUARE FAIL: {name} aspect={a:.3f} (need 1.0)")

    # Check row alignment (same y0 and y1)
    for row in expected.get('rows', []):
        present = [n for n in row if n in axes_info]
        if len(present) < 2:
            continue
        bottoms = [axes_info[n]['y0'] for n in present]
        tops = [axes_info[n]['y1'] for n in present]
        spread_b = max(bottoms) - min(bottoms)
        spread_t = max(tops) - min(tops)
        if spread_b > tolerance:
            issues.append(f"ROW BASELINE MISALIGNED: {present} spread={spread_b:.4f}")
        if spread_t > tolerance:
            issues.append(f"ROW TOP MISALIGNED: {present} spread={spread_t:.4f}")

    # Check column alignment (same x0)
    for col in expected.get('cols', []):
        present = [n for n in col if n in axes_info]
        if len(present) < 2:
            continue
        lefts = [axes_info[n]['x0'] for n in present]
        spread = max(lefts) - min(lefts)
        if spread > tolerance:
            issues.append(f"COL LEFT MISALIGNED: {present} spread={spread:.4f}")

    # Check overlap between non-internal axes
    names = [n for n in axes_info if '_' not in n]  # skip internal axes like D_01
    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            a, b = axes_info[names[i]], axes_info[names[j]]
            overlap_x = min(a['x1'], b['x1']) - max(a['x0'], b['x0'])
            overlap_y = min(a['y1'], b['y1']) - max(a['y0'], b['y0'])
            if overlap_x > tolerance and overlap_y > tolerance:
                issues.append(f"OVERLAP: {names[i]} and {names[j]}")

    if issues:
        print("VERIFICATION FAILED:")
        for issue in issues:
            print(f"  ! {issue}")
    else:
        print("VERIFICATION PASSED")

    return axes_info
```

## Square Axes

To make an axes physically square:

```python
# Preferred: make the grid cell square by matching width/height ratios
# to figure dimensions. If figure is 18cm × 22cm and panel spans
# 1 col (6cm wide), set that row to 6 * (22/18) = 7.33 height units.

# Fallback: force aspect after creation
ax.set_aspect('equal', adjustable='box')

# ALWAYS verify:
fig.canvas.draw()
pos = ax.get_position()
w_inch = pos.width * fig.get_size_inches()[0]
h_inch = pos.height * fig.get_size_inches()[1]
ratio = h_inch / w_inch
assert abs(ratio - 1.0) < 0.02, f"Not square: {w_inch:.3f} x {h_inch:.3f} in, ratio={ratio:.3f}"
```

## Improvement Workflow

When the user requests visual changes to an existing figure:

1. **Rename** current output to `_old`.
2. **Parse** request into numbered checklist.
3. **Direction check**: for each change, state what parameter changes and what visual effect to expect. If the direction contradicts the goal, revise before coding.
4. **Apply**, regenerate, run `verify_figure()`.
5. **Compare** old vs new. For each checklist item: describe old state, describe new state, then judge.
6. If verification reports issues, **compute** the exact correction from the reported numbers. Do not guess or trial-and-error.
7. If fixing X breaks Y, **stop and ask** the user.

## Quick Reference

| Problem | Solution |
|---------|----------|
| Panels in same row don't share baseline | They must be in same master GridSpec row |
| Panels in same column don't share left edge | They must be in same master GridSpec column |
| Need different row counts per column | Use LCM rows with cell spanning |
| Panel needs internal substructure | Delegate with SubplotSpec + GridSpecFromSubplotSpec |
| Panel needs colorbar | Use `inset_axes` (best) or `make_axes_locatable`; never `fig.colorbar(ax=)` |
| Need symmetric left/right halves | Mirror column ratios around central gap: `[1, g, 1, G, 1, g, 1]` |
| Need different width splits per row | SubplotSpec within the row's cell; keeps master row alignment |
| Sub-panel centered at partial width | SubplotSpec with padding: `width_ratios=[1, 2, 1]`, use middle cell |
| Need physically square cells | Compute row ratio algebraically from column width and figure dimensions |
| Grid looks wrong before adding data | Use debug grid script — fix structure before populating |
| Spacing between panels | Explicit gap rows/cols (never wspace/hspace) |
| Per-panel margin tuning | Padding cells in inner GridSpecFromSubplotSpec |
| Square claim without proof | Run aspect ratio assertion from `get_position()` |
| Visual "looks aligned" claim | Run `verify_figure()` with expected alignment spec |
| `bbox_inches='tight'` on composite | Banned — crops intentional margins |
| `fig.subfigures()` | Banned — breaks cross-panel alignment |
| Raw fontsize/linewidth in code | Banned — route through StylePreset |
| Constrained layout | Don't use — it overrides manual margins |
| Labels misaligned across panels | Compute from axes positions, enforce row/col grouping |

## Gotchas

### Image anchoring with `set_anchor()`

When using `imshow` with `aspect='equal'`, matplotlib centers the image and splits whitespace equally above and below. Use `set_anchor()` to control where the empty space goes:

```python
ax.imshow(img, aspect='equal')
ax.set_anchor('N')  # pin to top, empty space goes to bottom
# Options: 'N', 'S', 'E', 'W', 'NE', 'NW', 'SE', 'SW', 'C'
```

### cm to inches conversion

All matplotlib sizes are in inches. Convert once at figure creation:

```python
W_CM, H_CM = 18.0, 22.0
fig = plt.figure(figsize=(W_CM / 2.54, H_CM / 2.54), dpi=600)
```

### Correct save pattern

```python
# WRONG — crops intentional margins:
fig.savefig(path, bbox_inches='tight')

# CORRECT:
fig.savefig(path, dpi=DPI, facecolor='white', edgecolor='none')
```

### Height ratios are relative, not absolute

Increasing one panel's height_ratio *decreases* all others proportionally. To move a panel up, **decrease** the row above it — don't increase the panel's own row.

```python
# Want Panel C to move UP? Decrease row above it:
height_ratios = [6, 0.3, 3, ...]  # was [6, 0.3, 4, ...] — shrunk the gap
# Do NOT increase C's ratio — that shrinks everything else
```

### Making one panel smaller than its row

If Panel B is 4×4 cm but shares a row with Panel A at 10×8 cm, B's grid cell is forced to the row height. Use spanning with spacer cells:

```python
# B occupies fewer rows than A, with spacer below
ax_A = fig.add_subplot(gs[0:6, 0], label="A")    # full height
ax_B = fig.add_subplot(gs[0:4, 2], label="B")    # shorter
# gs[4:6, 2] is empty spacer — B appears smaller than A
```

Or use inner padding (GridSpecFromSubplotSpec with padding cells) to shrink the axes within a full-height cell.

## Common Mistakes

| Mistake | Why it fails | Fix |
|---------|-------------|-----|
| Using subfigures for layout | Independent coordinate systems, axes can't align | Single master GridSpec |
| `wspace`/`hspace` > 0 in master GridSpec | Spacing becomes implicit and hard to control | Set to 0, use gap cells |
| `subplots_adjust()` per panel | Moves axes within subfigure, doesn't affect master alignment | Use gap cells or inner padding grid |
| Labeling panels before content is final | Content changes shift positions | Labels go last |
| Labels placed on subfigures | Different internal margins cause misalignment | Place on main `fig` with `fig.text()` |
| Retrying alignment visually | Slow, error-prone, self-deceptive | Compute from `verify_figure()` output |
| Claiming "square" without measurement | Visual judgment is unreliable for aspect ratios | Assert from `get_position()` every time |
| `fig.colorbar(im, ax=ax)` in composite | Steals space from axes, breaks row/col alignment | Use `inset_axes` for colorbar |
| `make_axes_locatable` for colorbar | Still shrinks parent axes (less than `fig.colorbar` but measurable) | Use `inset_axes` if alignment is critical |
| Asymmetric column ratios for "symmetric" layout | Left/right panels have different widths, C/D panels unequal | Mirror ratios: `[1, g, 1, G, 1, g, 1]` |
| Guessing row ratios for square cells | Trial-and-error, never exactly right | Solve algebraically: `R = col_w * non_R_sum / (H - N*col_w)` |
| Populating data before verifying grid structure | Wastes minutes per iteration on slow data loads | Debug grid script first, populate after approval |
