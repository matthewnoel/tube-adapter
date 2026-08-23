# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

Parametric sleeve adapter that mates a hand-vacuum attachment to a larger vacuum's tube.
A single-file Python CLI (`generate.py`) that uses `build123d` to produce STLs.
All geometry is parameterized via named constants at the top of `generate.py`; a
subset is exposed via argparse — see `--help`. STL output, written to CWD, is
`tube-adapter-<component>.stl`; a bare `generate.py` writes
`tube-adapter-adapter.stl`.

This repo was scaffolded by Partwright. The real geometry is implemented in
`build_part`, which dispatches the two components (`adapter`, `fit_test`) to one
shared builder, `_build_sleeve`.

## Build plan

A `BUILD_PLAN.md` accompanies this repo. A build agent implementing the real geometry in `generate.py` should work from `BUILD_PLAN.md` as the implementation handoff, and `DESIGN_BRIEF.md` as the design record.

## Visual verification loop

This repo can render itself, so **verify geometry visually before declaring a
change done, and show the user the rendered preview.** For every geometry change:

1. Read `BUILD_PLAN.md` and `DESIGN_BRIEF.md` for the intended geometry, and
   check `reference/` for sketches (see below).
2. Implement or edit `build_part` in `generate.py`.
3. Run `.venv/bin/python generate.py` — exports the STL and surfaces build errors.
4. Run `.venv/bin/python preview.py` — renders `preview.png`, a 2x2 contact sheet
   (isometric, top, front, right).
5. **`Read` `preview.png`** and check it against the plan: right overall shape,
   +Z up, floor on z = 0, centered in X/Y, features placed correctly, no gaps
   from Boolean issues.
6. If it is wrong, fix `build_part` and repeat from step 3. If it is right,
   **show the user `preview.png`** and summarize what changed.

`preview.py` imports `build_part` from `generate.py` and calls it with only a
component name, so **`build_part` must stay callable with no arguments** (every
parameter keeps a default). The renderer is installed by
`uv pip install -r requirements.txt`. `preview.py --component fit_test` renders
the other component; pair it with `--output` so the two sheets do not overwrite
each other.

## Multi-component parts

When `DESIGN_BRIEF.md` declares more than one `component`, `generate.py` carries
a `COMPONENTS` tuple and the build/check/export contract is per-component:

- **`build_part` return contract.** `build_part(component=...)` dispatches to the
  named component's geometry. Called with **no arguments** it returns the **first**
  component (`COMPONENTS[0]`), so `preview.py` and the out-of-the-box run still
  work. Keep this shape when you implement the real geometry: one builder per
  component, dispatched by name, no-arg still returning the first.
- **STL export.** `--component <name>` builds and exports a single component to
  `<project>-<component>.stl`; `--all` exports every component, each to its own
  per-component filename, in one run. An explicit `--output` applies only when a
  single component is exported. (A single-component part still exports to
  `<project>.stl` with no `--component` flag.)
- **`check_part` iterates components.** It builds each component, prints its
  bounding box and solid count, and asserts **each** component is a single
  watertight solid — so a genuine multi-piece part no longer trips the
  "expected exactly one solid" check. Fill in the per-component expected-dimension
  map to turn the readout into a hard assert.

## Coordinate system

Right-handed:

- **+X** — radial; the mitred seat rises toward +X, so the flange is thickest at +X and thinnest at -X
- **+Y** — radial, completing the right-handed set; the part is mirror-symmetric about the XZ plane
- **+Z** — tube axis, up from the socket end (flat on the build plate at z = 0) toward the spigot tip

The part is centered in X and Y unless a geometry decision says otherwise. Most
geometry decisions in `generate.py` only make sense with this convention in
mind.

## Python environment caveat

The README uses `uv` because some local Homebrew Python installs have a broken
`pyexpat` that makes `python -m venv` fail at `ensurepip`. `uv` sidesteps this
by managing its own Python. Don't restructure `generate.py` to "work around" a
broken interpreter — use `uv` to get a clean Python 3.12.

## Code style

Python is formatted with [black](https://black.readthedocs.io/) (pinned in
`requirements-dev.txt`). Black is **not** in the runtime venv, so install the dev
deps once before formatting:

```sh
uv pip install -r requirements-dev.txt
```

Then run `.venv/bin/black generate.py` after edits — black is the source of
truth, so don't hand-align constants or wrap lines manually.

## Boolean-robustness conventions

OCCT booleans are flaky when an operation must resolve two coincident faces, and
the artifacts only show up after STL export. When you add a feature that cuts or
fuses to a face of the parent solid, give the cutter a small overshoot (a
`_FACE_OVERLAP_MM`-style tab) so the Boolean never resolves a coincident face.

Fillets need the same care on edge selection. A single scalar radius usually
cannot be applied to a whole edge set at once — at a tight concave corner the
requested radius exceeds the available room and OCCT raises
`ValueError: Failed creating a fillet`. Select the edges deliberately (filter by
position or orientation, e.g. only the four vertical outer corners) rather than
filleting every edge, and keep the radius within what the geometry allows.

## Reference sketches

The `reference/` folder holds design-intent drawings — SVGs from
`partwright sketch` and reference photos. **Look there before implementing
geometry** and reconcile `build_part` against what you find. Precise-mode SVGs
carry a real millimeter scale in their metadata; treat those dimensions as
authoritative.

## Non-obvious geometry decisions

- **The mitre blank margin is dropped when `mouth_rise == 0`.** `BUILD_PLAN.md`
  defines `mitre_blank_top = seat_high_z + 5.0` unconditionally, and separately
  says to skip the mitre cut entirely when `mouth_rise == 0`. Doing both leaves
  the 5 mm overshoot uncut, so the flat flange comes out 5 mm too thick and the
  part 5 mm too tall. `_build_sleeve` therefore adds `_MITRE_BLANK_MARGIN_MM`
  only when there is a mitre to cut. The margin exists solely so the cutting
  plane crosses a side wall instead of grazing a top edge; with no cut there is
  nothing to protect. Sanity check: `--mouth-rise 0` gives Z = 67.5 mm
  (`socket_depth + flange_min_thickness + spigot_depth`), not 72.5.

- **The mitre cutter is rotated about +Y by `-theta`, not `+theta`.** Right-hand
  rotation about +Y by `a` sends the box's bottom-face upward normal to
  `(sin a, 0, cos a)`; the seat plane's normal is `(-sin theta, 0, cos theta)`,
  so `a = -theta`. Verified in `preview.png`, not from the maths: the front (−Y)
  elevation shows the seat rising left-to-right, thin (2.5 mm) at −X and thick
  (22.26 mm) at +X. Flipping the sign mirrors the part and it will rock on the
  attachment's rim.

- **`fit_test` ignores `--socket-depth` / `--spigot-depth`.** Both are forced to
  `FIT_TEST_*_DEPTH_MM` inside `build_part` so the test print is always short;
  every other flag still applies, which is the point — the clearances are what
  the maker tunes between test prints.
