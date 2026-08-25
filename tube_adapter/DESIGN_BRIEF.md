+++
# === DESIGN_BRIEF.md frontmatter =============================================
# Conforms to templates/brief/SCHEMA.md. Parsed with stdlib `tomllib`.

project_name = "tube-adapter"
summary      = "Parametric sleeve adapter that mates a hand-vacuum attachment to a larger vacuum's tube."
units        = "mm"
components   = ["adapter", "fit_test"]

[coordinate_system]
x = "radial; the mitred seat rises toward +X, so the flange is thickest at +X and thinnest at -X"
y = "radial, completing the right-handed set; the part is mirror-symmetric about the XZ plane"
z = "tube axis, up from the socket end (flat on the build plate at z = 0) toward the spigot tip"

# --- Measured interface dimensions -------------------------------------------
# All nine are CLI flags: they are what changes when this part is re-used for a
# different pair of tubes.

[[parameters]]
name    = "vac_tube_od"
meaning = "outer diameter of the big vacuum's tube, which the socket slides over"
default = 39.5
cli     = true

[[parameters]]
name    = "vac_tube_id"
meaning = "inner bore of the big vacuum's tube; the spigot bore matches it exactly"
default = 34.0
cli     = true

[[parameters]]
name    = "attachment_id"
meaning = "inner bore of the attachment's socket, which the spigot inserts into"
default = 40.0
cli     = true

[[parameters]]
name    = "flange_od"
meaning = "outer diameter of the stop flange; set flush with the attachment's rim OD"
default = 54.0
cli     = true

[[parameters]]
name    = "mouth_rise"
meaning = "axial rise of the attachment's mitred mouth, measured across its bore"
default = 15.0
cli     = true

[[parameters]]
name    = "socket_clearance"
meaning = "radial clearance per side between the socket bore and the vac tube"
default = 0.25
cli     = true

[[parameters]]
name    = "spigot_clearance"
meaning = "radial clearance per side between the spigot OD and the attachment bore"
default = 0.85
cli     = true

[[parameters]]
name    = "socket_depth"
meaning = "axial length of the socket section that grips the vac tube"
default = 35.0
cli     = true

[[parameters]]
name    = "spigot_depth"
meaning = "spigot length measured above the highest point of the mitred seat plane"
default = 30.0
cli     = true

# --- Fixed constants ----------------------------------------------------------
# Tuned once; not worth a flag.

[[parameters]]
name    = "wall_thickness"
meaning = "wall thickness of the socket section"
default = 2.0
cli     = false

[[parameters]]
name    = "flange_min_thickness"
meaning = "flange thickness at its thin (-X) edge"
default = 2.5
cli     = false

[[parameters]]
name    = "lead_in_chamfer"
meaning = "45 deg lead-in chamfer at the socket mouth and the spigot tip"
default = 1.0
cli     = false

[[parameters]]
name    = "fit_test_socket_depth"
meaning = "socket length used by the fit_test component"
default = 8.0
cli     = false

[[parameters]]
name    = "fit_test_spigot_depth"
meaning = "spigot length used by the fit_test component"
default = 8.0
cli     = false

# --- Derived dimensions -------------------------------------------------------
# Seeded as named constants so the relations live in code. The defaults below are
# the values these formulas produce with the defaults above; the build agent MUST
# replace each literal with its formula, never keep the number.

[[parameters]]
name         = "socket_bore"
meaning      = "socket inner diameter"
default      = 40.00
cli          = false
derived_from = "socket_bore = vac_tube_od + 2 * socket_clearance"

[[parameters]]
name         = "socket_od"
meaning      = "socket outer diameter"
default      = 44.00
cli          = false
derived_from = "socket_od = socket_bore + 2 * wall_thickness"

[[parameters]]
name         = "spigot_od"
meaning      = "spigot outer diameter"
default      = 38.30
cli          = false
derived_from = "spigot_od = attachment_id - 2 * spigot_clearance"

[[parameters]]
name         = "spigot_bore"
meaning      = "spigot inner diameter; continues the vac tube's bore with no lip"
default      = 34.0
cli          = false
derived_from = "spigot_bore = vac_tube_id"

[[parameters]]
name         = "flange_rise"
meaning      = "axial rise of the mitred seat across the full flange diameter"
default      = 20.25
cli          = false
derived_from = "flange_rise = mouth_rise * flange_od / attachment_id"

[[parameters]]
name         = "shoulder_chamfer"
meaning      = "radial depth of the 45 deg internal shoulder the vac tube rim seats on"
default      = 3.00
cli          = false
derived_from = "shoulder_chamfer = (socket_bore - spigot_bore) / 2"
+++

# Design Brief — tube-adapter

A single-piece printed sleeve that lets a hand-vacuum attachment mount on a
larger vacuum's tube. One end is a **socket** that slides over the big vacuum's
39.5 mm tube; the other is a **spigot** that inserts into the attachment's
40.0 mm bore; between them a **mitred flange** seats against the attachment's
angle-cut rim and sets the insertion depth. It prints as one piece, socket-end
down, support-free. With default parameters it is **54.0 × 54.0 × 87.75 mm**.

## 1. Context & assembly

The maker has a hand-vacuum attachment they want to use on a full-size vacuum.
The two tubes very nearly fit already — the vac tube's 39.5 mm outside drops
into the attachment's 40.0 mm bore with 0.25 mm of radial slop — but the joint
is wobbly and leaks. This part fills that gap precisely. It is a finished
functional part, not a prototype or a jig, and lives indoors in a domestic
setting.

It assembles from **one printed piece** and mates with two purchased objects:

- **Socket end → the big vacuum's tube.** A plain cylindrical bore slides over
  the tube's 39.5 mm outside. Friction fit, no fasteners. The tube offers 75 mm
  of straight, constant-diameter length; the part uses 35 mm of it. The vac
  tube's rim seats on an internal 45° shoulder where the bore steps down.
- **Spigot end → the attachment's socket.** A cylindrical spigot inserts into
  the attachment's 40.0 mm bore, which is straight and constant-diameter for its
  full depth. Friction fit. Insertion depth is set by the flange bottoming on the
  attachment's rim.

The attachment's mouth is **cut on a flat mitre**: the bore diameter never
changes, but the rim plane is tilted, rising 15.0 mm across the 40.0 mm bore —
`atan(15.0 / 40.0)` = **20.6°** off perpendicular. A flange perpendicular to the
axis would touch that rim at one point and rock, so the flange's seating face
carries the same tilt. The maker rotates the adapter until the mitre seats flush.
Rotational alignment is free: the socket end is a plain round bore on the vac
tube, so the assembled stack still spins.

Because the mitre is a **flat plane**, its rise scales linearly with diameter —
`flange_rise = mouth_rise * flange_od / attachment_id` — so the geometry needs no
trigonometry. The flange is thinnest (2.5 mm) at −X, where the attachment's tube
is longest, and thickest (22.75 mm) at +X, where it is shortest.

**The controlling relationships at each interface:**

- `socket_bore = vac_tube_od + 2 * socket_clearance` — the socket must clear the
  tube it slides over.
- `spigot_od = attachment_id - 2 * spigot_clearance` — the spigot must clear the
  bore it enters.
- `spigot_bore = vac_tube_id` — **the key move.** Stepping the bore down to the
  vac tube's *inner* diameter rather than its outer diameter does two things at
  once: the vac tube's rim gets a shoulder to seat on, and its bore continues
  straight into the spigot's bore with no internal lip at all. It also rescues
  the wall thickness. Sized against the tube's outside, the spigot wall would be
  `(40.0 - 40.00) / 2` = **zero** — the sleeve could not exist at all; sized
  against its bore it is `(38.30 - 34.0) / 2` = **2.15 mm**.
- `flange_od = attachment_id + 2 * rim_wall` — set flush with the attachment's
  measured 54.0 mm rim OD so the flange covers the whole rim face and doubles as
  a grip surface for pulling a stuck joint apart. Dropping it to 48 saves about
  8 g and still overlaps the rim by 3.5 mm.

## 2. Tolerances & fits

Both interfaces are **friction fits**, and both clearances are CLI flags —
they are printer- and filament-dependent, and are the values the maker will tune
between test prints.

| Interface | Fit | Clearance/side | Flag |
| --- | --- | --- | --- |
| Socket bore over vac tube OD | snug friction | 0.25 mm | `--socket-clearance` |
| Spigot OD into attachment bore | snug press | 0.85 mm | `--spigot-clearance` |

**The seal is made by the spigot fit, not by the flange** — a minimum of 32.9 mm
of straight bore contact is what holds vacuum. The flange is a depth stop and a
secondary seal, so a degree or two of mitre mismatch costs nothing.

**`spigot_clearance = 0.85` is not a normal clearance, and should not be read as
one.** Reference values for a calibrated FDM printer are ~0.10–0.15 mm/side for a
snug press fit and ~0.20–0.30 mm/side for a sliding fit. This value is roughly
six times that because it is absorbing measurement error, not print error: the
attachment's bore was measured with a cloth tape at 41.0 mm and later corrected
to a nominal 40.0 mm, and the true figure is evidently smaller still. What is
actually validated by print testing is the **resulting spigot OD of 38.30 mm** —
`attachment_id` and `spigot_clearance` are simply the pair of numbers that
produce it. Anyone re-using this design for a different attachment should measure
the real bore with calipers and reset both values, rather than inheriting 0.85.

The socket side needs no such caveat: `socket_clearance = 0.25` is an ordinary
snug-fit value against a `vac_tube_od` of 39.5 mm, and both were confirmed by
print.

**Thin-feature check.** The thinnest wall is the socket at **2.0 mm** — five
perimeters at a 0.4 mm nozzle, comfortably above the FDM limit. The spigot wall
is 2.15 mm. The flange's thin edge is 2.5 mm. Nothing is marginal.

**Matte-filament note.** Bambu Matte PLA tends to print a hair wider on external
dimensions than Basic PLA, which contributed to the spigot printing tight through
several revisions before the clearance was settled empirically. Matte PLA
is also somewhat more brittle than Basic PLA; the flange's 2.5 mm thin edge is
the most likely thing to chip if the assembly is dropped.

## 3. Print constraints

**Orientation: socket end down, tube axis vertical, flat on the plate at z = 0.**
The 54 mm flange makes the part top-heavy in outline but the 44.0 mm socket base
gives a solid 87 mm-tall stance. The first layer is a plain annulus with no sharp
corners to lift, but a **narrow** one: the socket wall is 2.0 mm and the bore's
1.0 mm lead-in chamfer consumes half of it at z = 0, leaving a ring only 1.0 mm
wide. **Slice with a brim.** If the part still lifts, dropping
`lead_in_chamfer` to 0.5 widens the ring to 1.5 mm at no other cost.

This orientation makes the part **support-free**, which is the reason for
choosing it:

- The **mitred seat faces up** (+Z). Upward-facing surfaces are never overhangs.
  Printed the other way up it would need support across the whole seat.
- The **flange underside** is a 45° cone rising from `socket_od` to `flange_od`
  over `(flange_od - socket_od) / 2` = 5.00 mm of height — exactly at the 45°
  limit, no support.
- The **internal shoulder** is a 45° chamfer stepping the bore from 40.00 mm down
  to 34.0 mm over 3.00 mm — no support, and it self-centres the vac tube's rim.
- The socket mouth and spigot tip each get a 1.0 mm × 45° **lead-in chamfer** so
  the joints start easily. The socket's is an internal chamfer at z = 0, printed
  as a 45° inward taper over the first millimetre.

There are **no overhangs steeper than 45° and nothing that must bridge.**

**Boolean robustness.** Three operations need face-overlap treatment, all noted
in the build plan: the mitre half-space cutter must extend beyond the flange's
outer diameter and above its top; the through-bore cutter must overshoot both the
z = 0 face and the spigot tip; and the spigot must overlap the flange body rather
than butting against it at z = `socket_depth`.

## 4. Named size presets

**None — fully parametric.** The part is sized directly from four measured
diameters (`vac_tube_od`, `vac_tube_id`, `attachment_id`, `flange_od`) plus the
mitre's `mouth_rise`, all CLI flags. The defaults encode one specific pair: a
full-size vacuum's 39.5/34.0 mm tube and a hand-vacuum attachment with a 40.0 mm
bore, a 54.0 mm rim OD, and a mouth mitred 15.0 mm across the bore. Setting
`--mouth-rise 0` yields a flat, perpendicular flange for a square-cut mouth.

No lookup module is needed.

## 5. Verification approach

There are no automated tests. Verification is bounding box, render, slice, print.

1. `generate.py` runs with no arguments and writes a valid STL.
2. Each `--component` invocation writes its STL; `--all` writes both.
3. **Bounding-box check with default parameters** — the cheap sanity check:
   - `adapter`: X **54.0**, Y **54.0**, Z **87.75** mm
   - `fit_test`: X **54.0**, Y **54.0**, Z **38.75** mm
4. Both components must be a **single watertight solid**.
5. **Render and visually verify `preview.png`** before slicing: confirm the mitre
   tilts toward +X, the flange wedge is thin at −X and thick at +X, the bore steps
   down at the shoulder, and the socket face is flat on z = 0.
6. Slice in Bambu Studio, socket-end down, and confirm the slicer adds **no
   supports**.
7. **Physical fit check.** Print `fit_test` first — it reproduces both interfaces
   and the mitred seat at 8 mm engagements, so it takes a fraction of the time.
   Check that the socket slides onto the vac tube snugly, the spigot enters the
   attachment, and the mitre seats flush without rocking. Adjust
   `--socket-clearance` / `--spigot-clearance` and reprint until both are right,
   then print `adapter` with the settled values.

## 6. Reference sketches

**None — N/A.** No sketches were drawn and the reference photos were discarded
once direct measurements were taken. Every dimension the build agent needs is a
named parameter in the frontmatter above; nothing must be read off an image.

The one drawing that would most help a reader is a side section through the XZ
plane showing the three z landmarks — the internal shoulder at z = 35.0, the
mitred seat running from z = 37.5 at −X to z = 57.75 at +X, and the spigot tip at
z = 87.75 — with the vac tube dashed in place, seated on the shoulder.

## 7. Out of scope / non-goals

- **No latch, spring button, or bayonet.** Friction only.
- **No rotational keying.** The maker twists the adapter to seat the mitre; the
  attachment is not locked to a clock position.
- **No gasket groove, O-ring seat, or soft overmould.** The printed fits do the
  sealing.
- **No hose barb, cuff, or corrugated-hose interface.** Both ends are smooth
  cylinders.
- **No embossed text, logo, or size marking.**
- **No wall hook, stand, or storage feature.**
- **Not a reducer for arbitrary tube pairs in one print** — one adapter serves one
  pair; re-run with new parameters for a different pair.

## 8. Open questions

**None — all resolved by print testing (2026-08-24).** Both questions raised at
interview are closed:

1. ~~The clearances are unvalidated.~~ **Resolved.** Settled over seven printed
   revisions. `socket_clearance = 0.25` gives a snug, non-wobbling grip on the vac
   tube. `spigot_clearance = 0.85` (spigot OD 38.30 mm) enters and seats; the
   maker reported the final print as working and very slightly tight, and the
   committed default steps it 0.2 mm looser than that print.
2. ~~The attachment's socket bottom is assumed perpendicular to the axis.~~
   **Resolved.** A 30 mm spigot seats fully with the flange against the rim, so
   whatever the floor's geometry, it is deeper than the spigot reaches.
   `spigot_depth = 30.0` needs no reduction.

One dimension remains **inferred rather than measured**, and is recorded here as
a known fact rather than an open question, because nothing in the part depends on
resolving it: `vac_tube_id = 34.0` was never independently verified. It sets the
internal shoulder the vac tube's rim seats on. If it is wrong, the result is a
small step in the airflow path rather than a fit failure — nothing binds, nothing
leaks. It was left at its interview value deliberately.
