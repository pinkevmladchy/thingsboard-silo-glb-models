"""Shared geometry & material helpers for silo GLB generation.

All functions here are PURE — they take parameters and return trimesh.Trimesh
or trimesh.visual objects. No I/O. The two `build_*.py` scripts compose these
into full scenes.

Design contract (also in references/conventions.md):
  - Geometry is source of truth (no baked node transforms)
  - Each independently-controllable part = its own named mesh
  - Each mesh = unique PBR material (use `unique_pbr` to ensure uniqueness)
"""

import numpy as np
import trimesh


# ----------------------------------------------------------------------------
# Materials
# ----------------------------------------------------------------------------

def unique_pbr(name: str,
               color,
               metallic: float = 0.0,
               roughness: float = 0.7,
               double_sided: bool = False,
               salt: int = 0):
    """Build a PBR material that won't be merged with other identical ones.

    Adds a microscopic offset to roughness based on `salt` so the glTF exporter
    treats this as a unique material. Required when several meshes should have
    independently-controllable colors at runtime.

    Args:
        name: Material name.
        color: Either [r, g, b] (3 floats 0..1), [r, g, b, a], or a scalar float
               for gray. RGB values are linear (PBR baseColorFactor).
        metallic: 0.0 = dielectric, 1.0 = metal.
        roughness: 0.0 = mirror, 1.0 = matte.
        double_sided: Set True for thin surfaces (e.g., wavy grain top).
        salt: Integer; tiny epsilon offset added to roughness to ensure
              material uniqueness across meshes.
    """
    if isinstance(color, (int, float)):
        base = [float(color), float(color), float(color), 1.0]
    elif len(color) == 3:
        base = list(color) + [1.0]
    else:
        base = list(color)

    mat = trimesh.visual.material.PBRMaterial(
        name=name,
        baseColorFactor=base,
        metallicFactor=float(metallic),
        roughnessFactor=float(roughness) + salt * 1e-4,
        doubleSided=double_sided,
    )
    return trimesh.visual.TextureVisuals(material=mat)


# ----------------------------------------------------------------------------
# Basic geometry pieces (full cylinders/cones — for yard scene)
# ----------------------------------------------------------------------------

def make_silo_body_with_cone(radius: float, body_height: float, cone_height: float,
                              sections: int = 48) -> trimesh.Trimesh:
    """Cylinder body + cone top as ONE mesh, base at y=0."""
    angles = np.linspace(0, 2 * np.pi, sections, endpoint=False)
    cos_a, sin_a = np.cos(angles), np.sin(angles)

    bot_ring = np.column_stack([radius * cos_a, np.zeros(sections), radius * sin_a])
    top_ring = np.column_stack([radius * cos_a, np.full(sections, body_height), radius * sin_a])
    apex     = np.array([[0, body_height + cone_height, 0]])
    bot_ctr  = np.array([[0, 0, 0]])

    vertices = np.vstack([bot_ring, top_ring, apex, bot_ctr])
    B, T = 0, sections
    APEX = 2 * sections
    BC = 2 * sections + 1

    faces = []
    for i in range(sections):
        nxt = (i + 1) % sections
        faces.append([B + i,   B + nxt, T + nxt])
        faces.append([B + i,   T + nxt, T + i])
        faces.append([T + i,   T + nxt, APEX])
        faces.append([B + nxt, B + i,   BC])

    mesh = trimesh.Trimesh(vertices=vertices, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def make_torus(major_r: float, minor_r: float,
               major_seg: int = 48, minor_seg: int = 10) -> trimesh.Trimesh:
    """Torus in XZ plane (axis = Y), centered at origin."""
    u = np.linspace(0, 2 * np.pi, major_seg, endpoint=False)
    v = np.linspace(0, 2 * np.pi, minor_seg, endpoint=False)
    U, V = np.meshgrid(u, v, indexing='ij')
    X = (major_r + minor_r * np.cos(V)) * np.cos(U)
    Z = (major_r + minor_r * np.cos(V)) * np.sin(U)
    Y = minor_r * np.sin(V)
    verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

    faces = []
    for i in range(major_seg):
        for j in range(minor_seg):
            i2 = (i + 1) % major_seg
            j2 = (j + 1) % minor_seg
            a = i  * minor_seg + j
            b = i2 * minor_seg + j
            c = i2 * minor_seg + j2
            d = i  * minor_seg + j2
            faces.append([a, b, c])
            faces.append([a, c, d])
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


# ----------------------------------------------------------------------------
# Cutaway geometry (with front wedge removed)
# ----------------------------------------------------------------------------

def make_cutaway_silo_shell(radius, body_height,
                             wall_thickness=0.04, sections=64,
                             cut_start_deg=-45, cut_end_deg=45):
    """Hollow silo cylinder with a front wedge removed."""
    cs = np.deg2rad(cut_start_deg)
    ce = np.deg2rad(cut_end_deg)
    arc_span = (cs + 2 * np.pi) - ce
    n = sections
    angles = ce + np.linspace(0, arc_span, n)

    inner_r = radius - wall_thickness
    h = body_height
    cos_a, sin_a = np.cos(angles), np.sin(angles)

    outer_bot = np.column_stack([radius * cos_a, np.zeros(n), radius * sin_a])
    outer_top = np.column_stack([radius * cos_a, np.full(n, h), radius * sin_a])
    inner_bot = np.column_stack([inner_r * cos_a, np.zeros(n), inner_r * sin_a])
    inner_top = np.column_stack([inner_r * cos_a, np.full(n, h), inner_r * sin_a])

    verts = np.vstack([outer_bot, outer_top, inner_bot, inner_top])
    OB, OT, IB, IT = 0, n, 2 * n, 3 * n

    faces = []
    for i in range(n - 1):
        faces.append([OB + i, OB + i + 1, OT + i + 1])
        faces.append([OB + i, OT + i + 1, OT + i])
        faces.append([IB + i + 1, IB + i, IT + i])
        faces.append([IB + i + 1, IT + i, IT + i + 1])
        faces.append([OT + i, OT + i + 1, IT + i + 1])
        faces.append([OT + i, IT + i + 1, IT + i])
        faces.append([OB + i + 1, OB + i, IB + i])
        faces.append([OB + i + 1, IB + i, IB + i + 1])
    faces.append([OB, OT, IT])
    faces.append([OB, IT, IB])
    last = n - 1
    faces.append([OT + last, OB + last, IB + last])
    faces.append([OT + last, IB + last, IT + last])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def make_cutaway_cone_roof(radius, height, sections=64,
                            cut_start_deg=-45, cut_end_deg=45):
    """Cone roof with matching front wedge cut."""
    cs = np.deg2rad(cut_start_deg)
    ce = np.deg2rad(cut_end_deg)
    arc_span = (cs + 2 * np.pi) - ce
    n = sections
    angles = ce + np.linspace(0, arc_span, n)

    ring = np.column_stack([radius * np.cos(angles), np.zeros(n), radius * np.sin(angles)])
    apex = np.array([[0, height, 0]])
    base_ctr = np.array([[0, 0, 0]])
    verts = np.vstack([ring, apex, base_ctr])
    APEX, BC = n, n + 1

    faces = []
    for i in range(n - 1):
        faces.append([i, i + 1, APEX])
    for i in range(n - 1):
        faces.append([BC, i + 1, i])
    faces.append([BC, 0, APEX])
    faces.append([BC, APEX, n - 1])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def make_cutaway_floor(radius, thickness=0.06, sections=64,
                       cut_start_deg=-45, cut_end_deg=45):
    """Solid disk (with front wedge cut), spanning y=0..thickness."""
    cs = np.deg2rad(cut_start_deg)
    ce = np.deg2rad(cut_end_deg)
    arc_span = (cs + 2 * np.pi) - ce
    n = sections
    angles = ce + np.linspace(0, arc_span, n)

    top_ring = np.column_stack([radius * np.cos(angles), np.full(n, thickness), radius * np.sin(angles)])
    bot_ring = np.column_stack([radius * np.cos(angles), np.zeros(n),            radius * np.sin(angles)])
    top_ctr = np.array([[0, thickness, 0]])
    bot_ctr = np.array([[0, 0, 0]])

    verts = np.vstack([top_ring, bot_ring, top_ctr, bot_ctr])
    TR, BR, TC, BC = 0, n, 2 * n, 2 * n + 1

    faces = []
    for i in range(n - 1):
        faces.append([TC, TR + i, TR + i + 1])
    for i in range(n - 1):
        faces.append([BC, BR + i + 1, BR + i])
    for i in range(n - 1):
        faces.append([TR + i, TR + i + 1, BR + i + 1])
        faces.append([TR + i, BR + i + 1, BR + i])
    faces.append([TC, TR + 0, BR + 0])
    faces.append([TC, BR + 0, BC])
    last = n - 1
    faces.append([TC, BR + last, TR + last])
    faces.append([TC, BC, BR + last])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def make_cutaway_torus(major_r, minor_r, major_seg=64, minor_seg=8,
                        cut_start_deg=-45, cut_end_deg=45):
    """Torus arc matching the silo's cut."""
    cs = np.deg2rad(cut_start_deg)
    ce = np.deg2rad(cut_end_deg)
    arc_span = (cs + 2 * np.pi) - ce
    u = ce + np.linspace(0, arc_span, major_seg)
    v = np.linspace(0, 2 * np.pi, minor_seg, endpoint=False)
    U, V = np.meshgrid(u, v, indexing='ij')
    X = (major_r + minor_r * np.cos(V)) * np.cos(U)
    Z = (major_r + minor_r * np.cos(V)) * np.sin(U)
    Y = minor_r * np.sin(V)
    verts = np.column_stack([X.ravel(), Y.ravel(), Z.ravel()])

    faces = []
    for i in range(major_seg - 1):
        for j in range(minor_seg):
            j2 = (j + 1) % minor_seg
            a = i  * minor_seg + j
            b = (i + 1) * minor_seg + j
            c = (i + 1) * minor_seg + j2
            d = i  * minor_seg + j2
            faces.append([a, b, c])
            faces.append([a, c, d])
    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    mesh.fix_normals()
    return mesh


def make_wavy_grain(radius, base_height, sections=64,
                     cut_start_deg=-45, cut_end_deg=45,
                     wave_amp=0.08, n_radial_waves=3, n_angular_waves=4,
                     center_bump=0.15):
    """Solid wedge of grain with a wavy, heap-like top surface.

    Built as a watertight mesh with explicit winding and a shared center vertex
    so there are no degenerate triangles or normal-flipping artifacts.
    """
    cs = np.deg2rad(cut_start_deg)
    ce = np.deg2rad(cut_end_deg)
    arc_span = (cs + 2 * np.pi) - ce
    n_ang = sections
    n_rad = 12

    angles = ce + np.linspace(0, arc_span, n_ang)
    radii_outer = np.linspace(radius / (n_rad - 1), radius, n_rad - 1)
    A  = np.tile(angles, (n_rad - 1, 1))
    R_ = np.tile(radii_outer.reshape(-1, 1), (1, n_ang))

    norm_r = R_ / radius
    bump   = center_bump * (1.0 - norm_r) ** 1.5
    ripple = (wave_amp * 0.6) * np.sin(n_radial_waves * np.pi * norm_r) \
           + (wave_amp * 0.4) * np.sin(n_angular_waves * A + norm_r * 3.0)
    edge_settle = -0.04 * (norm_r ** 4)
    H_top = base_height + bump + ripple + edge_settle

    X = R_ * np.cos(A)
    Z = R_ * np.sin(A)

    top_outer = np.column_stack([X.ravel(), H_top.ravel(), Z.ravel()])
    bot_outer = np.column_stack([X.ravel(), np.zeros(top_outer.shape[0]), Z.ravel()])
    top_center = np.array([[0.0, base_height + center_bump, 0.0]])
    bot_center = np.array([[0.0, 0.0, 0.0]])

    N_OUT = top_outer.shape[0]
    verts = np.vstack([top_center, top_outer, bot_center, bot_outer])

    TC = 0
    def ti(r, c): return 1 + r * n_ang + c
    BC = 1 + N_OUT
    def bi(r, c): return 1 + N_OUT + 1 + r * n_ang + c

    faces = []
    # Top fan
    for c in range(n_ang - 1):
        faces.append([TC, ti(0, c), ti(0, c + 1)])
    for r in range(n_rad - 2):
        for c in range(n_ang - 1):
            a, b, d, e = ti(r, c), ti(r, c + 1), ti(r + 1, c), ti(r + 1, c + 1)
            faces.append([a, b, e]); faces.append([a, e, d])
    # Bottom fan (reverse)
    for c in range(n_ang - 1):
        faces.append([BC, bi(0, c + 1), bi(0, c)])
    for r in range(n_rad - 2):
        for c in range(n_ang - 1):
            a, b, d, e = bi(r, c), bi(r, c + 1), bi(r + 1, c), bi(r + 1, c + 1)
            faces.append([a, e, b]); faces.append([a, d, e])
    # Outer wall
    rmax = n_rad - 2
    for c in range(n_ang - 1):
        tA, tB, bA, bB = ti(rmax, c), ti(rmax, c + 1), bi(rmax, c), bi(rmax, c + 1)
        faces.append([tA, bA, bB]); faces.append([tA, bB, tB])
    # Cut walls
    faces.append([TC, BC, bi(0, 0)])
    faces.append([TC, bi(0, 0), ti(0, 0)])
    for r in range(n_rad - 2):
        tA, tB, bA, bB = ti(r, 0), ti(r + 1, 0), bi(r, 0), bi(r + 1, 0)
        faces.append([tA, bA, bB]); faces.append([tA, bB, tB])
    last = n_ang - 1
    faces.append([TC, ti(0, last), BC])
    faces.append([BC, ti(0, last), bi(0, last)])
    for r in range(n_rad - 2):
        tA, tB, bA, bB = ti(r, last), ti(r + 1, last), bi(r, last), bi(r + 1, last)
        faces.append([tA, bB, bA]); faces.append([tA, tB, bB])

    mesh = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    if mesh.is_watertight and mesh.volume < 0:
        mesh.invert()
    return mesh


# ----------------------------------------------------------------------------
# Composite builders — used by yard and cutaway scripts
# ----------------------------------------------------------------------------

def build_silo_with_details(x, z, radius, body_height, cone_height,
                             n_rings=8, n_ribs=12,
                             add_ladder=True, add_railing=True):
    """Build a detailed full silo (body + cone + rings + ribs).

    Returns:
        (silo_mesh, hardware_mesh_or_none)
        - silo_mesh:     everything that shares the silo body color
        - hardware_mesh: ladder + top railing (different/darker color), or None
    """
    silo_parts = []
    hw_parts = []

    body = make_silo_body_with_cone(radius, body_height, cone_height, sections=48)
    body.apply_translation([x, 0, z])
    silo_parts.append(body)

    # Slightly oversized cone shell to give the roof its own color (added later)
    angles = np.linspace(0, 2 * np.pi, 48, endpoint=False)
    ring_r = radius * 1.002
    ring = np.column_stack([
        x + ring_r * np.cos(angles),
        np.full(48, body_height),
        z + ring_r * np.sin(angles),
    ])
    apex = np.array([[x, body_height + cone_height * 1.002, z]])
    verts = np.vstack([ring, apex])
    faces = []
    for i in range(48):
        nxt = (i + 1) % 48
        faces.append([i, nxt, 48])
    roof_skin = trimesh.Trimesh(vertices=verts, faces=np.array(faces), process=False)
    silo_parts.append(roof_skin)

    # Corrugation rings
    ring_minor = max(0.012, radius * 0.025)
    heights = np.linspace(body_height * 0.06, body_height * 0.94, n_rings)
    for hy in heights:
        t = make_torus(major_r=radius * 1.005, minor_r=ring_minor,
                       major_seg=48, minor_seg=8)
        t.apply_translation([x, hy, z])
        silo_parts.append(t)

    # Vertical ribs
    rib_w = max(0.025, radius * 0.04)
    rib_d = max(0.02, radius * 0.03)
    for i in range(n_ribs):
        ang = 2 * np.pi * i / n_ribs
        rx = x + (radius + rib_d * 0.4) * np.cos(ang)
        rz = z + (radius + rib_d * 0.4) * np.sin(ang)
        rib = trimesh.creation.box(extents=[rib_w, body_height * 0.98, rib_d])
        rot = trimesh.transformations.rotation_matrix(-ang, [0, 1, 0])
        rib.apply_transform(rot)
        rib.apply_translation([rx, body_height * 0.49, rz])
        silo_parts.append(rib)

    # Ladder
    if add_ladder:
        lx = x + (radius + 0.025)
        lz = z
        for off in (-0.06, 0.06):
            rail = trimesh.creation.box(extents=[0.02, body_height, 0.02])
            rail.apply_translation([lx + 0.03, body_height / 2, lz + off])
            hw_parts.append(rail)
        n_rungs = max(6, int(body_height / 0.18))
        for i in range(n_rungs):
            ry = body_height * (i + 0.5) / n_rungs
            rung = trimesh.creation.box(extents=[0.015, 0.015, 0.14])
            rung.apply_translation([lx + 0.03, ry, lz])
            hw_parts.append(rung)

    # Top railing
    if add_railing:
        n_posts = 14
        post_h = 0.12
        for i in range(n_posts):
            ang = 2 * np.pi * i / n_posts
            px = x + radius * 0.95 * np.cos(ang)
            pz = z + radius * 0.95 * np.sin(ang)
            post = trimesh.creation.box(extents=[0.02, post_h, 0.02])
            post.apply_translation([px, body_height + post_h / 2, pz])
            hw_parts.append(post)
        topring = make_torus(major_r=radius * 0.95, minor_r=0.012,
                              major_seg=48, minor_seg=6)
        topring.apply_translation([x, body_height + post_h, z])
        hw_parts.append(topring)

    silo_mesh = trimesh.util.concatenate(silo_parts)
    hw_mesh = trimesh.util.concatenate(hw_parts) if hw_parts else None
    return silo_mesh, hw_mesh
