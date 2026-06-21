# Mesh Conversion Tools

Convert a TetGen-style `.node` + `.ele` tetrahedral mesh into the Gmsh 2.2 ASCII `.msh` format read by libuipc.

Recommended asset layout:

```text
assets/sim_data/
  trimesh/                # Surface meshes used directly as triangle meshes.
  tetmesh/                # Libuipc-ready .msh tetrahedral meshes.
  tetmesh_src/<mesh_name> # External tetrahedralizer outputs, such as .node + .ele.
```

Default output goes to `output/converted_tetmesh`, which is ignored by git:

```bat
scripts\mesh\convert_node_ele_to_msh.bat assets\sim_data\trimesh\body_sit_1.5_80
```

When the source files are organized under `tetmesh_src`, use the mesh base path:

```bat
scripts\mesh\convert_node_ele_to_msh.bat assets\sim_data\tetmesh_src\body_sit_1.5_80\body_sit_1.5_80
```

After checking the result, install it for direct sample use:

```bat
scripts\mesh\convert_node_ele_to_msh.bat assets\sim_data\tetmesh_src\body_sit_1.5_80\body_sit_1.5_80 --install --force
```

The installed file is written to `assets/sim_data/tetmesh/<name>.msh`. The converter maps source node ids to continuous Gmsh 1-based ids and fixes negative tetrahedron orientation by default. Pass `--keep-orientation` to preserve the input ordering exactly.
