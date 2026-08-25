#!/usr/bin/env python3
"""Generate an STL for tube-adapter.

Parametric sleeve adapter that mates a hand-vacuum attachment to a larger vacuum's tube.
Coordinate system (right-handed):
    +X : radial; the mitred seat rises toward +X, so the flange is thickest at +X and thinnest at -X
    +Y : radial, completing the right-handed set; the part is mirror-symmetric about the XZ plane
    +Z : tube axis, up from the socket end (flat on the build plate at z = 0) toward the spigot tip

The part is modelled in its printed orientation: socket end face on z = 0,
centered on the Z axis in X and Y. The exported STL is print-ready as-is.

Two components are built, selected by --component:
    adapter  : the real part (54.0 x 54.0 x 87.26 mm with default parameters)
    fit_test : the same geometry with both engagements cut to 8 mm, so the two
               friction fits and the mitred seat can be checked in a short print

All geometry constants are at the top of this file; a subset is exposed on the
CLI. See --help.
"""

from __future__ import annotations

import argparse
import sys
from math import atan, cos, degrees, sin
from pathlib import Path

from build123d import Axis, Box, GeomType, Polyline, export_stl, make_face, revolve

# === Part geometry ==========================================================

# --- Measured interfaces ----------------------------------------------------
# The five diameters and the mitre rise that describe the two purchased parts,
# plus the two clearances and two engagement lengths. All nine are CLI flags:
# they are what changes when this adapter is re-used for a different tube pair.
VAC_TUBE_OD_MM = (
    39.5  # outer diameter of the big vacuum's tube, which the socket slides over
)
VAC_TUBE_ID_MM = (
    34.0  # inner bore of the big vacuum's tube; the spigot bore matches it exactly
)
ATTACHMENT_ID_MM = (
    40.0  # inner bore of the attachment's socket, which the spigot inserts into
)
FLANGE_OD_MM = (
    54.0  # outer diameter of the stop flange; set flush with the attachment's rim OD
)
MOUTH_RISE_MM = (
    15.0  # axial rise of the attachment's mitred mouth, measured across its bore
)
SOCKET_CLEARANCE_MM = (
    0.25  # radial clearance per side between the socket bore and the vac tube
)
SPIGOT_CLEARANCE_MM = (
    0.85  # radial clearance per side between the spigot OD and the attachment bore
)
SOCKET_DEPTH_MM = 35.0  # axial length of the socket section that grips the vac tube
SPIGOT_DEPTH_MM = (
    30.0  # spigot length measured above the highest point of the mitred seat plane
)

# --- Fixed ------------------------------------------------------------------
# Tuned once; not worth a flag.
WALL_THICKNESS_MM = 2.0  # wall thickness of the socket section
FLANGE_MIN_THICKNESS_MM = 2.5  # flange thickness at its thin (-X) edge
LEAD_IN_CHAMFER_MM = (
    1.0  # 45 deg lead-in chamfer at the socket mouth and the spigot tip
)
FIT_TEST_SOCKET_DEPTH_MM = 8.0  # socket length used by the fit_test component
FIT_TEST_SPIGOT_DEPTH_MM = 8.0  # spigot length used by the fit_test component

# Boolean-robustness constants (private). OCCT is flaky whenever a cut or fuse
# has to resolve two coincident faces, and the artifacts only surface after STL
# export, so every such operation gets a deliberate overshoot instead.
_FACE_OVERLAP_MM = 0.2  # cutter overshoot past a face, and the spigot's fuse overlap
_MITRE_BLANK_MARGIN_MM = 5.0  # flange blank overshoot above the seat's high point
_MITRE_CUTTER_SIZE_MM = 200.0  # edge of the half-space box that cuts the mitred seat

# --- Derived ----------------------------------------------------------------
# Relations, not numbers: `build_part` recomputes every one of these from its
# own arguments, so a run with non-default flags stays self-consistent. The
# module-level values below are the same formulas evaluated at the defaults, and
# exist only to seed the CLI help text.
SOCKET_BORE_MM = VAC_TUBE_OD_MM + 2 * SOCKET_CLEARANCE_MM  # socket inner diameter
SOCKET_OD_MM = SOCKET_BORE_MM + 2 * WALL_THICKNESS_MM  # socket outer diameter
SPIGOT_OD_MM = ATTACHMENT_ID_MM - 2 * SPIGOT_CLEARANCE_MM  # spigot outer diameter
SPIGOT_BORE_MM = (
    VAC_TUBE_ID_MM  # spigot bore; continues the vac tube's bore with no lip
)
# Radial depth of the 45 deg internal shoulder the vac tube's rim seats on.
SHOULDER_CHAMFER_MM = (SOCKET_BORE_MM - SPIGOT_BORE_MM) / 2
# The flange underside is a 45 deg cone, so its height equals its radial run.
FLANGE_UNDERSIDE_CHAMFER_MM = (FLANGE_OD_MM - SOCKET_OD_MM) / 2
# The mitre is a flat plane, so its rise scales linearly with diameter -- no
# trigonometry needed here. atan is reserved for the cutter's rotation angle.
FLANGE_RISE_MM = MOUTH_RISE_MM * FLANGE_OD_MM / ATTACHMENT_ID_MM

# The artifacts this part builds, seeded from DESIGN_BRIEF.md. build_part
# dispatches on these names; --component / --all select among them.
COMPONENTS = ("adapter", "fit_test")
DEFAULT_OUTPUT = "tube-adapter.stl"


# ----------------------------------------------------------------------------
# Geometry helpers
# ----------------------------------------------------------------------------


def _revolved(profile_rz):
    """Revolve a closed (r, z) polyline 360 deg about the Z axis.

    `profile_rz` is a sequence of (radius, height) pairs with r >= 0, drawn in
    the XZ plane and closed automatically from the last point back to the first.
    Everything in this part except the mitre is a solid of revolution, so this
    is the one shape factory the assembly needs.
    """
    outline = Polyline(*[(r, 0.0, z) for r, z in profile_rz], close=True)
    return revolve(make_face(outline), Axis.Z)


def _mitre_cutter(seat_mid_z, mitre_slope):
    """Half-space box whose underside is the mitred seat plane.

    The seat plane rises toward +X with `mitre_slope`, passes through
    (0, 0, `seat_mid_z`) on the axis, and has upward normal
    `(-sin theta, 0, cos theta)`. A box rotated about +Y by `-theta` has exactly
    that normal on its bottom face; translating it `size / 2` along the normal
    puts that face's center on the axis at `seat_mid_z`. Subtracting it leaves
    the material below the plane -- thick at +X, thin at -X.
    """
    theta = atan(mitre_slope)
    size = _MITRE_CUTTER_SIZE_MM
    normal = (-sin(theta), 0.0, cos(theta))
    cutter = Box(size, size, size).rotate(Axis.Y, -degrees(theta))
    return cutter.translate(
        (normal[0] * size / 2, 0.0, normal[2] * size / 2 + seat_mid_z)
    )


# ----------------------------------------------------------------------------
# Assembly
# ----------------------------------------------------------------------------


def _build_sleeve(
    socket_depth,
    spigot_depth,
    *,
    vac_tube_od,
    vac_tube_id,
    attachment_id,
    flange_od,
    mouth_rise,
    socket_clearance,
    spigot_clearance,
):
    """Build the sleeve adapter for one pair of engagement depths.

    Both components share this builder -- `adapter` and `fit_test` differ only
    in `socket_depth` and `spigot_depth`. Four operations, in this order:
    revolve the outer body, cut the mitred seat, fuse the spigot, cut the bore.
    The order matters: the seat plane passes through the spigot's radial range,
    so cutting the mitre after the fuse would slice the spigot in half, and the
    bore goes last so it is a single cut through the fully fused body.
    """
    socket_bore = vac_tube_od + 2 * socket_clearance
    socket_od = socket_bore + 2 * WALL_THICKNESS_MM
    spigot_od = attachment_id - 2 * spigot_clearance
    spigot_bore = vac_tube_id
    shoulder_chamfer = (socket_bore - spigot_bore) / 2
    flange_underside_chamfer = (flange_od - socket_od) / 2

    mitre_slope = mouth_rise / attachment_id
    flange_rise = mouth_rise * flange_od / attachment_id
    seat_low_z = socket_depth + FLANGE_MIN_THICKNESS_MM
    seat_high_z = seat_low_z + flange_rise
    seat_mid_z = seat_low_z + flange_rise / 2
    tip_z = seat_high_z + spigot_depth

    # The blank overshoots the seat so the cutting plane crosses the flange's
    # side wall cleanly instead of grazing its top edge. With no mitre to cut
    # there is nothing to overshoot, and the margin would just thicken the
    # flange, so the degenerate case takes the blank straight to the seat.
    mitre_blank_top = seat_high_z + (_MITRE_BLANK_MARGIN_MM if mouth_rise > 0 else 0.0)

    # 1. Outer body: socket wall, 45 deg flange underside cone, flange blank.
    #    Built as one revolve so the cone meets the socket wall on a tangent
    #    circle rather than as a separately fused Cone with a coincident face.
    part = _revolved(
        [
            (0.0, 0.0),
            (socket_od / 2, 0.0),
            (socket_od / 2, socket_depth - flange_underside_chamfer),
            (flange_od / 2, socket_depth),
            (flange_od / 2, mitre_blank_top),
            (0.0, mitre_blank_top),
        ]
    )

    # 2. Mitred seat: remove the half-space above the seat plane. A square-cut
    #    mouth (mouth_rise == 0) leaves the flange flat and perpendicular, and
    #    the cutter would be coplanar with its top face, so skip the cut.
    if mouth_rise > 0:
        part -= _mitre_cutter(seat_mid_z, mitre_slope)

    # 3. Spigot, fused after the mitre cut. It starts below the flange bottom so
    #    the fuse overlaps the body instead of butting against its bottom plane.
    #    The tip chamfer is in the profile -- selecting that edge afterwards is
    #    the brittle way to get it.
    part += _revolved(
        [
            (0.0, socket_depth - _FACE_OVERLAP_MM),
            (spigot_od / 2, socket_depth - _FACE_OVERLAP_MM),
            (spigot_od / 2, tip_z - LEAD_IN_CHAMFER_MM),
            (spigot_od / 2 - LEAD_IN_CHAMFER_MM, tip_z),
            (0.0, tip_z),
        ]
    )

    # 4. Through bore, cut last in one operation: 45 deg lead-in at the socket
    #    mouth, the socket bore, the 45 deg shoulder the vac tube's rim seats
    #    on, then the spigot bore. Above the shoulder the bore equals
    #    vac_tube_id exactly, so the tube's bore continues with no internal lip.
    #    The cutter overshoots both end faces so neither Boolean is coincident.
    part -= _revolved(
        [
            (0.0, -_FACE_OVERLAP_MM),
            (socket_bore / 2 + LEAD_IN_CHAMFER_MM, -_FACE_OVERLAP_MM),
            (socket_bore / 2 + LEAD_IN_CHAMFER_MM, 0.0),
            (socket_bore / 2, LEAD_IN_CHAMFER_MM),
            (socket_bore / 2, socket_depth),
            (spigot_bore / 2, socket_depth + shoulder_chamfer),
            (spigot_bore / 2, tip_z + _FACE_OVERLAP_MM),
            (0.0, tip_z + _FACE_OVERLAP_MM),
        ]
    )

    return part


def build_part(
    component=COMPONENTS[0],
    *,
    vac_tube_od: float = VAC_TUBE_OD_MM,
    vac_tube_id: float = VAC_TUBE_ID_MM,
    attachment_id: float = ATTACHMENT_ID_MM,
    flange_od: float = FLANGE_OD_MM,
    mouth_rise: float = MOUTH_RISE_MM,
    socket_clearance: float = SOCKET_CLEARANCE_MM,
    spigot_clearance: float = SPIGOT_CLEARANCE_MM,
    socket_depth: float = SOCKET_DEPTH_MM,
    spigot_depth: float = SPIGOT_DEPTH_MM,
):
    """Build one component's solid.

    Called with no arguments (e.g. by preview.py) it returns the FIRST
    component, so the repo still renders out of the box. `fit_test` is the same
    geometry with both engagements forced to their short test lengths; every
    other parameter, including the full flange and the mitred seat, is shared.
    """
    if component not in COMPONENTS:
        raise ValueError(
            f"unknown component {component!r}; expected one of {COMPONENTS}"
        )

    if component == "fit_test":
        socket_depth = FIT_TEST_SOCKET_DEPTH_MM
        spigot_depth = FIT_TEST_SPIGOT_DEPTH_MM

    _validate(
        vac_tube_od=vac_tube_od,
        vac_tube_id=vac_tube_id,
        attachment_id=attachment_id,
        flange_od=flange_od,
        mouth_rise=mouth_rise,
        socket_clearance=socket_clearance,
        spigot_clearance=spigot_clearance,
        socket_depth=socket_depth,
    )

    return _build_sleeve(
        socket_depth,
        spigot_depth,
        vac_tube_od=vac_tube_od,
        vac_tube_id=vac_tube_id,
        attachment_id=attachment_id,
        flange_od=flange_od,
        mouth_rise=mouth_rise,
        socket_clearance=socket_clearance,
        spigot_clearance=spigot_clearance,
    )


def _validate(
    *,
    vac_tube_od,
    vac_tube_id,
    attachment_id,
    flange_od,
    mouth_rise,
    socket_clearance,
    spigot_clearance,
    socket_depth,
):
    """Reject parameter sets that would silently build broken geometry."""
    problems = []
    if socket_clearance < 0:
        problems.append(f"socket_clearance must be >= 0 (got {socket_clearance})")
    if spigot_clearance < 0:
        problems.append(f"spigot_clearance must be >= 0 (got {spigot_clearance})")
    if mouth_rise < 0:
        problems.append(f"mouth_rise must be >= 0 (got {mouth_rise})")
    if vac_tube_od <= vac_tube_id:
        problems.append(
            f"vac_tube_od ({vac_tube_od}) must exceed vac_tube_id ({vac_tube_id}); "
            "the vac tube needs a wall"
        )
    spigot_od = attachment_id - 2 * spigot_clearance
    if spigot_od <= vac_tube_id:
        problems.append(
            f"spigot_od ({spigot_od:.3f}) must exceed vac_tube_id ({vac_tube_id}); "
            "the spigot needs a wall"
        )
    socket_od = vac_tube_od + 2 * socket_clearance + 2 * WALL_THICKNESS_MM
    flange_underside_chamfer = (flange_od - socket_od) / 2
    if flange_od < socket_od:
        problems.append(
            f"flange_od ({flange_od}) must be at least socket_od ({socket_od:.3f})"
        )
    elif socket_depth < flange_underside_chamfer:
        problems.append(
            f"socket_depth ({socket_depth}) must be >= the flange underside chamfer "
            f"({flange_underside_chamfer:.3f}), or its 45 deg cone breaks through "
            "the z = 0 face"
        )
    if problems:
        raise ValueError("invalid parameters:\n  - " + "\n  - ".join(problems))


# ----------------------------------------------------------------------------
# Geometry self-check
# ----------------------------------------------------------------------------

# Expected overall dimensions (X, Y, Z) in mm at default parameters, from
# BUILD_PLAN.md "Verification steps".
_EXPECTED_BBOX_MM = {
    "adapter": (54.0, 54.0, 87.75),
    "fit_test": (54.0, 54.0, 38.75),
}
_BBOX_TOLERANCE_MM = 0.05

# Every distinct cylindrical face in a finished component: socket OD, flange OD,
# spigot OD, socket bore, spigot bore. A wrong count means a Boolean dropped or
# duplicated a face -- the bounding box alone would not notice.
_EXPECTED_CYLINDERS = 5


def _check_one(component, solid) -> list[str]:
    """Check a single component's solid; return a list of problem strings."""
    bbox = solid.bounding_box()
    size = bbox.size
    n_solids = len(solid.solids())
    n_cylinders = sum(1 for f in solid.faces() if f.geom_type == GeomType.CYLINDER)

    print(f"  [{component}]")
    print(f"    solids        : {n_solids}")
    print(f"    cylinders     : {n_cylinders}")
    print(f"    bounding box  : {size.X:.2f} x {size.Y:.2f} x {size.Z:.2f} mm")
    print(
        f"    min .. max    : "
        f"({bbox.min.X:.2f}, {bbox.min.Y:.2f}, {bbox.min.Z:.2f}) .. "
        f"({bbox.max.X:.2f}, {bbox.max.Y:.2f}, {bbox.max.Z:.2f})"
    )

    problems = []
    if n_solids != 1:
        problems.append(
            f"{component}: expected a single watertight solid, got {n_solids} "
            "(a Boolean op may have split the part)"
        )
    want = _EXPECTED_BBOX_MM.get(component)
    if want is not None:
        for axis, got, target in zip("XYZ", (size.X, size.Y, size.Z), want):
            if abs(got - target) > _BBOX_TOLERANCE_MM:
                problems.append(
                    f"{component} {axis} = {got:.2f} mm, "
                    f"expected {target} +/- {_BBOX_TOLERANCE_MM}"
                )
    if n_cylinders != _EXPECTED_CYLINDERS:
        problems.append(
            f"{component}: expected {_EXPECTED_CYLINDERS} cylindrical faces, "
            f"found {n_cylinders}"
        )
    return problems


def check_part(solid=None) -> bool:
    """Sanity-check every component's geometry; return True if all pass.

    Iterates COMPONENTS, building each, printing its bounding box and solid
    count, and asserting each is a single watertight solid of the expected
    overall size (more than one solid usually means a Boolean silently split
    that component).

    `solid`, if given, is checked alone against the first component (the
    preview.py path); otherwise every component is built and checked.
    """
    print("geometry self-check:")
    problems = []
    if solid is not None:
        problems += _check_one(COMPONENTS[0], solid)
    else:
        for component in COMPONENTS:
            problems += _check_one(component, build_part(component))

    if problems:
        for p in problems:
            print(f"  FAIL: {p}")
        return False
    print("  OK")
    return True


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------


def _parse_args():
    p = argparse.ArgumentParser(
        description="Generate an STL for tube-adapter.",
    )
    p.add_argument(
        "--component",
        choices=list(COMPONENTS),
        default=COMPONENTS[0],
        help=(
            "Which component to build and export: the real adapter, or the "
            "short fit_test print that exercises both fits and the mitred "
            f"seat. Default {COMPONENTS[0]}."
        ),
    )
    p.add_argument(
        "--all",
        dest="all_components",
        action="store_true",
        help=(
            "Build and export every component, each to its own "
            "per-component STL filename. Overrides --component."
        ),
    )
    p.add_argument(
        "--vac-tube-od",
        type=float,
        default=VAC_TUBE_OD_MM,
        metavar="VALUE",
        help=f"outer diameter of the big vacuum's tube, which the socket slides over (default: {VAC_TUBE_OD_MM}).",
    )
    p.add_argument(
        "--vac-tube-id",
        type=float,
        default=VAC_TUBE_ID_MM,
        metavar="VALUE",
        help=f"inner bore of the big vacuum's tube; the spigot bore matches it exactly (default: {VAC_TUBE_ID_MM}).",
    )
    p.add_argument(
        "--attachment-id",
        type=float,
        default=ATTACHMENT_ID_MM,
        metavar="VALUE",
        help=f"inner bore of the attachment's socket, which the spigot inserts into (default: {ATTACHMENT_ID_MM}).",
    )
    p.add_argument(
        "--flange-od",
        type=float,
        default=FLANGE_OD_MM,
        metavar="VALUE",
        help=f"outer diameter of the stop flange; set flush with the attachment's rim OD (default: {FLANGE_OD_MM}).",
    )
    p.add_argument(
        "--mouth-rise",
        type=float,
        default=MOUTH_RISE_MM,
        metavar="VALUE",
        help=f"axial rise of the attachment's mitred mouth, measured across its bore (default: {MOUTH_RISE_MM}).",
    )
    p.add_argument(
        "--socket-clearance",
        type=float,
        default=SOCKET_CLEARANCE_MM,
        metavar="VALUE",
        help=f"radial clearance per side between the socket bore and the vac tube (default: {SOCKET_CLEARANCE_MM}).",
    )
    p.add_argument(
        "--spigot-clearance",
        type=float,
        default=SPIGOT_CLEARANCE_MM,
        metavar="VALUE",
        help=f"radial clearance per side between the spigot OD and the attachment bore (default: {SPIGOT_CLEARANCE_MM}).",
    )
    p.add_argument(
        "--socket-depth",
        type=float,
        default=SOCKET_DEPTH_MM,
        metavar="VALUE",
        help=f"axial length of the socket section that grips the vac tube (default: {SOCKET_DEPTH_MM}; fit_test always uses {FIT_TEST_SOCKET_DEPTH_MM}).",
    )
    p.add_argument(
        "--spigot-depth",
        type=float,
        default=SPIGOT_DEPTH_MM,
        metavar="VALUE",
        help=f"spigot length measured above the highest point of the mitred seat plane (default: {SPIGOT_DEPTH_MM}; fit_test always uses {FIT_TEST_SPIGOT_DEPTH_MM}).",
    )
    p.add_argument(
        "--output",
        type=Path,
        default=None,
        metavar="PATH",
        help=(
            "STL output path; applies only when a single component is exported. "
            f"Default: {Path(DEFAULT_OUTPUT).stem}-<component>.stl."
        ),
    )
    p.add_argument(
        "--check",
        action="store_true",
        help="run the geometry self-check (single solid + bounding box) and exit.",
    )
    return p.parse_args()


def _output_path_for(component, explicit):
    """Resolve the STL path for one component.

    An explicit --output wins; otherwise default to the per-component
    filename `<project>-<component>.stl`.
    """
    if explicit is not None:
        return Path(explicit)
    stem = Path(DEFAULT_OUTPUT).stem
    suffix = Path(DEFAULT_OUTPUT).suffix or ".stl"
    return Path(f"{stem}-{component}{suffix}")


def _export_component(component, *, params, explicit):
    """Build one component and write its STL; return the output path."""
    solid = build_part(component, **params)
    out_path = _output_path_for(component, explicit)
    if out_path.parent and str(out_path.parent) not in ("", "."):
        out_path.parent.mkdir(parents=True, exist_ok=True)
    export_stl(solid, str(out_path))
    print(f"Wrote STL: {out_path}")
    return out_path


def main():
    args = _parse_args()

    params = {
        "vac_tube_od": args.vac_tube_od,
        "vac_tube_id": args.vac_tube_id,
        "attachment_id": args.attachment_id,
        "flange_od": args.flange_od,
        "mouth_rise": args.mouth_rise,
        "socket_clearance": args.socket_clearance,
        "spigot_clearance": args.spigot_clearance,
        "socket_depth": args.socket_depth,
        "spigot_depth": args.spigot_depth,
    }

    if args.check:
        sys.exit(0 if check_part() else 1)

    targets = list(COMPONENTS) if args.all_components else [args.component]

    print("tube-adapter — resolved parameters:")
    print(f"  vac tube od         : {args.vac_tube_od}")
    print(f"  vac tube id         : {args.vac_tube_id}")
    print(f"  attachment id       : {args.attachment_id}")
    print(f"  flange od           : {args.flange_od}")
    print(f"  mouth rise          : {args.mouth_rise}")
    print(f"  socket clearance    : {args.socket_clearance}")
    print(f"  spigot clearance    : {args.spigot_clearance}")
    print(f"  socket depth        : {args.socket_depth}")
    print(f"  spigot depth        : {args.spigot_depth}")
    print(f"  Components to build : {', '.join(targets)}")
    print()

    # --output names a single file, so it only applies when exactly one
    # component is exported; with --all each component uses its own name.
    explicit = args.output if len(targets) == 1 else None
    try:
        for component in targets:
            _export_component(component, params=params, explicit=explicit)
    except ValueError as exc:
        sys.exit(f"error: {exc}")


if __name__ == "__main__":
    main()
