#!/usr/bin/env python3
"""Convert TetGen-style .node + .ele tetrahedral meshes to Gmsh 2.2 .msh."""

from __future__ import annotations

import argparse
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Node:
    source_id: int
    x: float
    y: float
    z: float


@dataclass(frozen=True)
class Tet:
    source_id: int
    nodes: tuple[int, int, int, int]


@dataclass(frozen=True)
class Mesh:
    nodes: list[Node]
    tets: list[Tet]


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def strip_known_suffix(path: Path) -> str:
    name = path.name
    lowered = name.lower()
    for suffix in (".node", ".ele", ".msh"):
        if lowered.endswith(suffix):
            return name[: -len(suffix)]
    return name


def sidecar_path(path: Path, suffix: str) -> Path:
    name = path.name
    lowered = name.lower()
    for known in (".node", ".ele"):
        if lowered.endswith(known):
            return path.with_name(name[: -len(known)] + suffix)
    return Path(str(path) + suffix)


def iter_records(path: Path) -> Iterable[tuple[int, list[str]]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_no, raw in enumerate(handle, start=1):
            line = raw.split("#", 1)[0].strip()
            if line:
                yield line_no, line.split()


def parse_int(token: str, path: Path, line_no: int) -> int:
    try:
        return int(token)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_no}: expected integer, got {token!r}") from exc


def parse_float(token: str, path: Path, line_no: int) -> float:
    try:
        return float(token)
    except ValueError as exc:
        raise ValueError(f"{path}:{line_no}: expected float, got {token!r}") from exc


def parse_node_file(path: Path) -> list[Node]:
    records = iter(iter_records(path))
    try:
        line_no, header = next(records)
    except StopIteration as exc:
        raise ValueError(f"{path}: empty .node file") from exc

    if len(header) < 2:
        raise ValueError(f"{path}:{line_no}: .node header must contain at least node count and dimension")

    expected_count = parse_int(header[0], path, line_no)
    dimension = parse_int(header[1], path, line_no)
    if dimension != 3:
        raise ValueError(f"{path}:{line_no}: only 3D .node files are supported, got dimension {dimension}")

    nodes: list[Node] = []
    seen: set[int] = set()
    for line_no, parts in records:
        if len(parts) < 4:
            raise ValueError(f"{path}:{line_no}: node record must be: id x y z")
        source_id = parse_int(parts[0], path, line_no)
        if source_id in seen:
            raise ValueError(f"{path}:{line_no}: duplicate node id {source_id}")
        seen.add(source_id)
        nodes.append(
            Node(
                source_id=source_id,
                x=parse_float(parts[1], path, line_no),
                y=parse_float(parts[2], path, line_no),
                z=parse_float(parts[3], path, line_no),
            )
        )

    if len(nodes) != expected_count:
        raise ValueError(f"{path}: header says {expected_count} nodes, parsed {len(nodes)}")

    return nodes


def parse_ele_file(path: Path) -> list[Tet]:
    records = iter(iter_records(path))
    try:
        line_no, header = next(records)
    except StopIteration as exc:
        raise ValueError(f"{path}: empty .ele file") from exc

    if len(header) < 2:
        raise ValueError(f"{path}:{line_no}: .ele header must contain at least element count and nodes per element")

    expected_count = parse_int(header[0], path, line_no)
    nodes_per_tet = parse_int(header[1], path, line_no)
    if nodes_per_tet != 4:
        raise ValueError(f"{path}:{line_no}: only 4-node tetrahedra are supported, got {nodes_per_tet}")

    tets: list[Tet] = []
    seen: set[int] = set()
    for line_no, parts in records:
        if len(parts) < 5:
            raise ValueError(f"{path}:{line_no}: element record must be: id n0 n1 n2 n3")
        source_id = parse_int(parts[0], path, line_no)
        if source_id in seen:
            raise ValueError(f"{path}:{line_no}: duplicate element id {source_id}")
        seen.add(source_id)
        tets.append(
            Tet(
                source_id=source_id,
                nodes=(
                    parse_int(parts[1], path, line_no),
                    parse_int(parts[2], path, line_no),
                    parse_int(parts[3], path, line_no),
                    parse_int(parts[4], path, line_no),
                ),
            )
        )

    if len(tets) != expected_count:
        raise ValueError(f"{path}: header says {expected_count} tetrahedra, parsed {len(tets)}")

    return tets


def load_mesh(node_path: Path, ele_path: Path) -> Mesh:
    if not node_path.exists():
        raise FileNotFoundError(f".node file not found: {node_path}")
    if not ele_path.exists():
        raise FileNotFoundError(f".ele file not found: {ele_path}")

    nodes = parse_node_file(node_path)
    tets = parse_ele_file(ele_path)

    node_ids = {node.source_id for node in nodes}
    for tet in tets:
        missing = [node_id for node_id in tet.nodes if node_id not in node_ids]
        if missing:
            raise ValueError(f"{ele_path}: element {tet.source_id} references missing node ids {missing}")

    return Mesh(nodes=nodes, tets=tets)


def signed_volume(node_lookup: dict[int, Node], tet_nodes: tuple[int, int, int, int]) -> float:
    a, b, c, d = (node_lookup[node_id] for node_id in tet_nodes)
    ux, uy, uz = b.x - a.x, b.y - a.y, b.z - a.z
    vx, vy, vz = c.x - a.x, c.y - a.y, c.z - a.z
    wx, wy, wz = d.x - a.x, d.y - a.y, d.z - a.z
    return (
        ux * (vy * wz - vz * wy)
        - uy * (vx * wz - vz * wx)
        + uz * (vx * wy - vy * wx)
    ) / 6.0


def output_path_from_args(args: argparse.Namespace, stem: str) -> Path:
    if args.output is None:
        return repo_root() / "output" / "converted_tetmesh" / f"{stem}.msh"

    output = Path(args.output)
    if output.suffix.lower() == ".msh":
        return output
    return output / f"{stem}.msh"


def install_path_from_args(args: argparse.Namespace, stem: str) -> Path:
    install_dir = Path(args.install_dir) if args.install_dir else repo_root() / "assets" / "sim_data" / "tetmesh"
    install_name = args.install_name or stem
    if not install_name.lower().endswith(".msh"):
        install_name += ".msh"
    return install_dir / install_name


def ensure_can_write(path: Path, force: bool) -> None:
    if path.exists() and not force:
        raise FileExistsError(f"{path} already exists; pass --force to overwrite it")


def write_msh(mesh: Mesh, output_path: Path, fix_orientation: bool, degenerate_eps: float) -> dict[str, int | float]:
    node_id_to_gmsh = {node.source_id: index for index, node in enumerate(mesh.nodes, start=1)}
    node_lookup = {node.source_id: node for node in mesh.nodes}

    positive = 0
    negative = 0
    degenerate = 0
    fixed = 0
    min_volume: float | None = None
    max_volume: float | None = None
    gmsh_tets: list[tuple[int, int, int, int]] = []

    for tet in mesh.tets:
        tet_nodes = tet.nodes
        volume = signed_volume(node_lookup, tet_nodes)
        min_volume = volume if min_volume is None else min(min_volume, volume)
        max_volume = volume if max_volume is None else max(max_volume, volume)

        if volume < -degenerate_eps:
            negative += 1
            if fix_orientation:
                tet_nodes = (tet_nodes[0], tet_nodes[1], tet_nodes[3], tet_nodes[2])
                fixed += 1
        elif volume > degenerate_eps:
            positive += 1
        else:
            degenerate += 1

        gmsh_tets.append(tuple(node_id_to_gmsh[node_id] for node_id in tet_nodes))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("$MeshFormat\n")
        handle.write("2.2 0 8\n")
        handle.write("$EndMeshFormat\n")
        handle.write("$Nodes\n")
        handle.write(f"{len(mesh.nodes)}\n")
        for node in mesh.nodes:
            gmsh_id = node_id_to_gmsh[node.source_id]
            handle.write(f"{gmsh_id} {node.x:.17g} {node.y:.17g} {node.z:.17g}\n")
        handle.write("$EndNodes\n")
        handle.write("$Elements\n")
        handle.write(f"{len(gmsh_tets)}\n")
        for element_id, tet_nodes in enumerate(gmsh_tets, start=1):
            handle.write(
                f"{element_id} 4 0 {tet_nodes[0]} {tet_nodes[1]} {tet_nodes[2]} {tet_nodes[3]}\n"
            )
        handle.write("$EndElements\n")

    return {
        "nodes": len(mesh.nodes),
        "tets": len(mesh.tets),
        "positive": positive,
        "negative": negative,
        "degenerate": degenerate,
        "fixed": fixed,
        "min_volume": min_volume or 0.0,
        "max_volume": max_volume or 0.0,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Convert TetGen-style .node + .ele files to a libuipc-readable Gmsh 2.2 .msh file."
    )
    parser.add_argument(
        "base",
        nargs="?",
        help="Mesh base path, .node file, or .ele file. Example: assets/sim_data/trimesh/body_sit_1.5_80",
    )
    parser.add_argument("--node", help="Explicit .node input path.")
    parser.add_argument("--ele", help="Explicit .ele input path.")
    parser.add_argument(
        "-o",
        "--output",
        help="Output .msh file or directory. Defaults to output/converted_tetmesh/<name>.msh.",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="Also copy the converted .msh into assets/sim_data/tetmesh for direct sample use.",
    )
    parser.add_argument("--install-dir", help="Directory used by --install. Defaults to assets/sim_data/tetmesh.")
    parser.add_argument("--install-name", help="File name used by --install. Defaults to the input base name.")
    parser.add_argument("--force", action="store_true", help="Overwrite existing output/install files.")
    parser.add_argument(
        "--keep-orientation",
        action="store_true",
        help="Do not auto-fix tetrahedra with negative signed volume.",
    )
    parser.add_argument(
        "--degenerate-eps",
        type=float,
        default=1e-16,
        help="Absolute signed-volume threshold for reporting degenerate tetrahedra.",
    )
    return parser


def resolve_inputs(args: argparse.Namespace) -> tuple[Path, Path, str]:
    if args.node or args.ele:
        if not (args.node and args.ele):
            raise ValueError("--node and --ele must be provided together")
        node_path = Path(args.node)
        ele_path = Path(args.ele)
        stem = strip_known_suffix(node_path)
        return node_path, ele_path, stem

    if not args.base:
        raise ValueError("provide a mesh base path, or provide --node and --ele")

    base = Path(args.base)
    node_path = sidecar_path(base, ".node")
    ele_path = sidecar_path(base, ".ele")
    stem = strip_known_suffix(base)
    return node_path, ele_path, stem


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        node_path, ele_path, stem = resolve_inputs(args)
        output_path = output_path_from_args(args, stem)
        install_path = install_path_from_args(args, stem) if args.install else None

        ensure_can_write(output_path, args.force)
        if install_path and install_path.resolve() != output_path.resolve():
            ensure_can_write(install_path, args.force)

        mesh = load_mesh(node_path, ele_path)
        stats = write_msh(
            mesh,
            output_path,
            fix_orientation=not args.keep_orientation,
            degenerate_eps=args.degenerate_eps,
        )

        copied_to = None
        if install_path:
            install_path.parent.mkdir(parents=True, exist_ok=True)
            if install_path.resolve() != output_path.resolve():
                shutil.copyfile(output_path, install_path)
            copied_to = install_path

    except Exception as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    print(f"wrote: {output_path}")
    if copied_to:
        print(f"installed: {copied_to}")
    print(
        "stats: "
        f"nodes={stats['nodes']} "
        f"tets={stats['tets']} "
        f"positive={stats['positive']} "
        f"negative={stats['negative']} "
        f"fixed={stats['fixed']} "
        f"degenerate={stats['degenerate']} "
        f"min_volume={stats['min_volume']:.6g} "
        f"max_volume={stats['max_volume']:.6g}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
