# Build Plan — tube-adapter

The implementation handoff for the step-2 build agent. Turns `DESIGN_BRIEF.md`
(the *what*) into a concrete plan for `generate.py` (the *how*). Target: a
single-file `build123d` CLI of `phone-centipede` quality — named constants at the
top, a stated coordinate system, a deliberate CLI subset, and the non-obvious
decisions written down.

## Objective

`generate.py` builds a one-piece sleeve adapter that joins a hand-vacuum
attachment to a larger vacuum's tube: a **socket** that slides over the vac
tube, a **spigot** that inserts into the attachment, and a **mitred flange**
between them that seats on the attachment's angle-cut rim.

It builds two components, selected by `--component`:

- **`adapter`** (default) — the real part. Bounding box 54.0 × 54.0 × 87.26 mm.
- **`fit_test`** — identical geometry with both engagement lengths cut to 8 mm
  and the mitred seat retained, so both fits and the seat angle can be checked in
  a short print. Bounding box 54.0 × 54.0 × 38.26 mm.

Both must run out of the box with default parameters and emit a valid STL that
is a single watertight solid. `--all` exports both.

## Geometry approach

Right-handed, copied verbatim from the brief:

- **+X** — radial; the mitred seat rises toward +X, so the flange is thickest at
  +X and thinnest at −X.
- **+Y** — radial, completing the right-handed set; the part is mirror-symmetric
  about the XZ plane.
- **+Z** — tube axis, up from the socket end (flat on the build plate at z = 0)
  toward the spigot tip.

Centered on the Z axis in X and Y; socket end face on z = 0. **Model in the
printed orientation** — the STL is print-ready as exported, no rotation needed.

Everything except the mitre is a solid of revolution, so build the axisymmetric
mass with `revolve` of a 2-D profile and use exactly one non-axisymmetric
operation: a planar cut for the mitre. This keeps the Boolean count low and
avoids stacking coincident faces.

### Z landmarks (adapter, default parameters)

| z | Feature |
| --- | --- |
| 0.0 | Socket bottom face, on the build plate |
| 1.0 | Top of the socket's 45° lead-in chamfer |
| 29.45 | Bottom of the flange's 45° underside cone |
| 35.0 | Flange bottom / internal shoulder start (`socket_depth`) |
| 37.45 | Internal shoulder top (bore now `spigot_bore`) |
| 37.5 | Mitred seat, **low** point, at x = −27.0 |
| 57.256 | Mitred seat, **high** point, at x = +27.0 |
| 87.256 | Spigot tip |

### adapter

1. **Outer-body revolve.** Build a 2-D profile in the XZ plane (r ≥ 0) with
   `Polyline` + `make_face`, then `revolve` 360° about the Z axis. Vertices, in
   order, as (r, z):

   | r | z | what |
   | --- | --- | --- |
   | 0.0 | 0.0 | on the axis, bottom |
   | `socket_od/2` = 21.45 | 0.0 | socket outer, bottom face |
   | 21.45 | `socket_depth - flange_underside_chamfer` = 29.45 | socket outer wall |
   | `flange_od/2` = 27.0 | `socket_depth` = 35.0 | 45° flange underside cone |
   | 27.0 | `mitre_blank_top` = 62.26 | flange outer, run past the mitre |
   | 0.0 | 62.26 | close across the axis |

   `mitre_blank_top = seat_high_z + 5.0`. The blank deliberately overshoots the
   mitre so the cutting plane crosses its side wall cleanly instead of grazing a
   top edge.

2. **Cut the mitre.** Remove the half-space above the seat plane. The plane
   passes through (−27.0, 0, 37.5) and (+27.0, 0, 57.256); its midpoint on the
   axis is (0, 0, `seat_mid_z` = 47.378) and its normal is
   `(-sin θ, 0, cos θ)` with `θ = atan(mouth_rise / attachment_id)` = 20.0855°.

   Implement as an oversized `Box` (200 mm cube is ample), rotated about **Y by
   −θ** so its underside lies in that plane, translated so that underside passes
   through `(0, 0, seat_mid_z)`, then subtracted. `split(..., Keep.BOTTOM)` on a
   `Plane` with that origin and normal is an acceptable alternative.

   **Verify the sign in `preview.png`:** the flange must come out *thick at +X,
   thin at −X*. If it is mirrored, flip the rotation sign — do not guess from the
   maths alone.

   If `mouth_rise == 0`, skip this step entirely; the flange stays flat and
   perpendicular. Guard it so the degenerate case does not produce an empty cut.

3. **Fuse the spigot.** A second revolve, profile as (r, z):

   | r | z |
   | --- | --- |
   | 0.0 | `socket_depth - _FACE_OVERLAP_MM` = 34.8 |
   | `spigot_od/2` = 20.35 | 34.8 |
   | 20.35 | `tip_z - lead_in_chamfer` = 86.256 |
   | `spigot_od/2 - lead_in_chamfer` = 19.35 | `tip_z` = 87.256 |
   | 0.0 | 87.256 |

   Building the tip chamfer into the profile is preferred over selecting the edge
   afterwards — edge selection is the brittle part. The spigot starts *below*
   the flange bottom so the fuse overlaps rather than butts.

   Order matters: the spigot is fused **after** the mitre cut. The seat plane
   passes through the spigot's radial range (z = 54.82 at x = +20.35), so cutting
   it before the fuse would slice the spigot in half.

4. **Cut the through bore.** One more revolve, subtracted, as (r, z):

   | r | z | what |
   | --- | --- | --- |
   | 0.0 | −`_FACE_OVERLAP_MM` = −0.2 | overshoot below the plate face |
   | `socket_bore/2 + lead_in_chamfer` = 20.45 | −0.2 | lead-in mouth |
   | 20.45 | 0.0 | |
   | `socket_bore/2` = 19.45 | `lead_in_chamfer` = 1.0 | 45° lead-in |
   | 19.45 | `socket_depth` = 35.0 | socket bore |
   | `spigot_bore/2` = 17.0 | `socket_depth + shoulder_chamfer` = 37.45 | 45° shoulder |
   | 17.0 | `tip_z + _FACE_OVERLAP_MM` = 87.456 | spigot bore, overshoot the tip |
   | 0.0 | 87.456 | close |

   The bore is cut **last**, in one operation, through the fully fused body. The
   45° shoulder at z = 35.0–37.45 is what the vac tube's rim seats on; above it
   the bore equals `vac_tube_id` exactly, so the tube's bore continues into the
   spigot with no internal lip.

### fit_test

Identical construction with two substitutions and nothing else changed:

- `socket_depth` → `fit_test_socket_depth` = 8.0
- `spigot_depth` → `fit_test_spigot_depth` = 8.0

The mitred seat, both lead-in chamfers, the internal shoulder and the full
54.0 mm flange are all retained — the seat angle is the riskiest feature, so the
test print must exercise it. Z landmarks become: shoulder at 8.0–10.45, seat low
10.5, seat high 30.256, tip 38.256.

Implement this by parameterising the two builders through one function that
takes the two depths, not by duplicating the geometry code.

### Derived quantities (compute, do not hard-code)

The brief seeds six of these as constants carrying `# derived:` comments. **Those
literals are reference values only — replace each with its formula in the code.**
A run with non-default flags must recompute every one.

- `socket_bore = vac_tube_od + 2 * socket_clearance` → 38.9
- `socket_od = socket_bore + 2 * wall_thickness` → 42.9
- `spigot_od = attachment_id - 2 * spigot_clearance` → 40.7
- `spigot_bore = vac_tube_id` → 34.0
- `shoulder_chamfer = (socket_bore - spigot_bore) / 2` → 2.45
- `flange_underside_chamfer = (flange_od - socket_od) / 2` → 5.55
- `mitre_slope = mouth_rise / attachment_id` → 0.365854
- `mitre_angle_deg = degrees(atan(mitre_slope))` → 20.0855
- `flange_rise = mouth_rise * flange_od / attachment_id` → 19.756
- `seat_low_z = socket_depth + flange_min_thickness` → 37.5
- `seat_high_z = seat_low_z + flange_rise` → 57.256
- `seat_mid_z = seat_low_z + flange_rise / 2` → 47.378
- `tip_z = seat_high_z + spigot_depth` → 87.256
- `mitre_blank_top = seat_high_z + 5.0` → 62.256

Note that `flange_rise` needs no trigonometry — the mitre is a flat plane, so its
rise scales linearly with diameter. Use the ratio form; reserve `atan` for the
cutter's rotation angle alone.

## Constants to define

Named constants at the top of `generate.py`, grouped with section banners
(`# --- Measured interfaces ---`, `# --- Fixed ---`, `# --- Derived ---`). Units
are mm throughout.

| Constant | Default | CLI flag | Notes |
| --- | --- | --- | --- |
| `VAC_TUBE_OD_MM` | 38.5 | `--vac-tube-od` | big vacuum tube's outer diameter |
| `VAC_TUBE_ID_MM` | 34.0 | `--vac-tube-id` | big vacuum tube's bore |
| `ATTACHMENT_ID_MM` | 41.0 | `--attachment-id` | attachment socket's bore |
| `FLANGE_OD_MM` | 54.0 | `--flange-od` | stop flange OD, flush with the rim |
| `MOUTH_RISE_MM` | 15.0 | `--mouth-rise` | mitre rise across `ATTACHMENT_ID_MM` |
| `SOCKET_CLEARANCE_MM` | 0.20 | `--socket-clearance` | per-side, socket over tube |
| `SPIGOT_CLEARANCE_MM` | 0.15 | `--spigot-clearance` | per-side, spigot in bore |
| `SOCKET_DEPTH_MM` | 35.0 | `--socket-depth` | socket engagement length |
| `SPIGOT_DEPTH_MM` | 30.0 | `--spigot-depth` | spigot length above `seat_high_z` |
| `WALL_THICKNESS_MM` | 2.0 | — | socket wall |
| `FLANGE_MIN_THICKNESS_MM` | 2.5 | — | flange thickness at its −X edge |
| `LEAD_IN_CHAMFER_MM` | 1.0 | — | 45° lead-in, socket mouth and spigot tip |
| `FIT_TEST_SOCKET_DEPTH_MM` | 8.0 | — | fit_test socket length |
| `FIT_TEST_SPIGOT_DEPTH_MM` | 8.0 | — | fit_test spigot length |
| `_FACE_OVERLAP_MM` | 0.2 | — | private; cutter overshoot and fuse overlap |
| `_MITRE_BLANK_MARGIN_MM` | 5.0 | — | private; flange blank overshoot above the seat |

`SPIGOT_DEPTH_MM` is measured from the **highest** point of the seat plane, which
is the conservative reading: true contact length at the spigot surface runs from
32.4 mm (at +X) to 47.3 mm (at −X).

## CLI surface

`argparse`, mirroring `phone-centipede`. Only the nine `cli = true` parameters get
flags; everything else stays a constant.

- `--component {adapter,fit_test}` — which artifact to build. Default `adapter`.
- `--all` — export both components in one run.
- `--vac-tube-od`, `--vac-tube-id`, `--attachment-id`, `--flange-od`,
  `--mouth-rise`, `--socket-clearance`, `--spigot-clearance`, `--socket-depth`,
  `--spigot-depth` — all `float`, help text from each parameter's `meaning`.
- `--output PATH` — STL output path. Default `tube-adapter-adapter.stl` /
  `tube-adapter-fit_test.stl`. Applies only when a single component is exported.

**No `--units` flag.** The maker explicitly chose mm only; do not add inch
conversion.

Validate inputs and fail with a clear message rather than producing broken
geometry:

- `attachment_id - 2 * spigot_clearance > vac_tube_id` — the spigot needs a wall.
- `socket_depth >= flange_underside_chamfer` — otherwise the flange's 45° cone
  breaks through the z = 0 face.
- `vac_tube_od > vac_tube_id` and both clearances `>= 0`.
- `mouth_rise >= 0`.

## File layout

- `generate.py` — the single-file CLI: shebang, module docstring (carrying the
  coordinate system verbatim), constants block, geometry helpers, the shared
  builder, `argparse` CLI, `main()`.
- `preview.py` — headless matplotlib renderer writing a multi-view `preview.png`.
  Keep it working as geometry evolves; it calls `build_part()` with no arguments.
- `CLAUDE.md`, `README.md`, `requirements.txt`, `requirements-dev.txt`,
  `.gitignore`, `.claude/settings.local.json`, `reference/` — standard scaffold.

No extra modules. There is no size-preset lookup table — the part is fully
parametric.

## Verification steps

1. `generate.py` runs with no arguments and writes `tube-adapter-adapter.stl`.
2. `--component fit_test` writes `tube-adapter-fit_test.stl`; `--all` writes both.
3. **Bounding-box check**, default parameters:
   - `adapter`: X **54.0**, Y **54.0**, Z **87.26** mm
   - `fit_test`: X **54.0**, Y **54.0**, Z **38.26** mm
4. `check_part` asserts each component is a **single watertight solid**.
5. **Render and visually verify `preview.png`** before slicing. Confirm, in order:
   - the flange wedge is **thick at +X and thin at −X** (the mitre sign check);
   - the socket end face is flat on z = 0 and the part is centered in X/Y;
   - the bore steps down once, at the shoulder, and is smooth above it;
   - the spigot tip and socket mouth both carry their lead-in chamfers.
6. `black generate.py preview.py` leaves both files unchanged.
7. Slice `adapter` in Bambu Studio as exported, socket-end down: confirm the
   slicer adds **no supports**, and enable a brim (see Known risks).
8. Physical fit check — print `fit_test`, confirm the socket slides onto the vac
   tube snugly, the spigot enters the attachment, and the mitre seats flush
   without rocking. Tune `--socket-clearance` / `--spigot-clearance` and reprint
   until both are right, then print `adapter` with the settled values.

## Boolean-robustness conventions

OCCT Booleans are flaky when an operation must resolve two coincident faces, and
the artifacts only surface after STL export. The specific spots in this part:

- **Bore cutter, bottom.** Starts at z = −`_FACE_OVERLAP_MM`, not z = 0, so it
  never resolves against the plate face.
- **Bore cutter, top.** Ends at `tip_z + _FACE_OVERLAP_MM`, overshooting the
  spigot tip.
- **Spigot fuse.** The spigot revolve starts at `socket_depth - _FACE_OVERLAP_MM`
  so it overlaps the flange body instead of butting against its bottom plane.
- **Mitre cutter.** The 200 mm box extends well past the flange OD in X and Y and
  above `mitre_blank_top`; the flange blank itself overshoots the seat by
  `_MITRE_BLANK_MARGIN_MM` so the plane crosses a side wall, never a top edge.
- **Flange underside cone.** Its bottom radius equals `socket_od/2` exactly, so it
  meets the socket wall on a tangent circle rather than a coincident face. Build
  it as part of the single outer-body revolve profile — do **not** fuse it as a
  separate `Cone`.

## Known risks

- **Mitre rotation sign** — the flange comes out mirrored if the Y rotation sign
  is wrong, and the maths alone will not tell you. *Mitigation:* check
  `preview.png` for thick-at-+X before doing anything else; flip the sign if
  needed. This is the single most likely thing to be wrong on the first pass.
- **First-layer contact is a 1.0 mm-wide annulus.** The socket wall is 2.0 mm and
  the lead-in chamfer eats 1.0 mm of it at z = 0, leaving a thin ring under an
  87 mm-tall part. *Mitigation:* **enable a brim when slicing.** If it still lifts,
  drop `LEAD_IN_CHAMFER_MM` to 0.5 for a 1.5 mm ring — the geometry supports it.
- **Derived constants seeded as literals.** The scaffolder writes
  `SOCKET_BORE_MM = 38.9` and friends from the brief's `derived_from` entries.
  Leaving them as literals silently breaks every non-default run. *Mitigation:*
  replace each with its formula and confirm by running with a changed flag and
  watching the bounding box move.
- **Matte PLA runs tight.** Bambu Matte PLA prints a hair wider than Basic PLA, so
  the 0.15 mm spigot clearance may bind on the first attempt. *Mitigation:* the
  `fit_test` component exists for exactly this; raise the flag in 0.05 mm steps.
- **Spigot bottoming out.** The attachment's socket floor is *assumed*
  perpendicular; the tip should clear it by ~7.7 mm. If the flange will not seat,
  the tip is hitting the floor. *Mitigation:* reduce `--spigot-depth`.
- **`mouth_rise = 0` degenerate case.** A zero rise makes the mitre cutter
  coplanar with the flange top. *Mitigation:* branch and skip the cut entirely.
- **Small `socket_depth` values.** Below `flange_underside_chamfer` = 5.55 the
  flange cone punches through the bottom face. *Mitigation:* the CLI validation
  above rejects it.
