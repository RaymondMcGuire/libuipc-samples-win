import numpy as np
import polyscope as ps
import uipc.builtin as builtin
from asset_dir import AssetDir
from polyscope import imgui
from uipc import Animation, Engine, Logger, Scene, Timer, Transform, Vector3, Vector12, World, view
from uipc.constitution import (
    AffineBodyConstitution,
    AffineBodyFreeJoint,
    AffineBodyPrismaticJoint,
    AffineBodyRevoluteJoint,
    ExternalArticulationConstraint,
)
from uipc.geometry import SimplicialComplex, SimplicialComplexIO, affine_body, label_surface
from uipc.gui import SceneGUI
from uipc.unit import GPa, MPa

Timer.enable_all()
Logger.set_level(Logger.Level.Info)

this_output_path = AssetDir.output_path(__file__)
trimesh_path = AssetDir.trimesh_path()

engine = Engine("cuda", this_output_path)
world = World(engine)

dt = 0.01
config = Scene.default_config()
config["gravity"] = [[0.0], [-9.8], [0.0]]
config["contact"]["enable"] = True
config["newton"]["velocity_tol"] = 0.1
config["newton"]["transrate_tol"] = 10
config["linear_system"]["tol_rate"] = 1e-4
config["contact"]["d_hat"] = 0.001
config["dt"] = dt
scene = Scene(config)

scene.contact_tabular().default_model(0.05, 1.0 * GPa)
default_element = scene.contact_tabular().default_element()

abd = AffineBodyConstitution()

pre_transform = Transform.Identity()
pre_transform.scale(0.4)
io = SimplicialComplexIO(pre_transform)

links = scene.objects().create("links")
abd_mesh = io.read(f"{trimesh_path}/cube.obj")
abd_mesh.instances().resize(3)
label_surface(abd_mesh)
abd.apply_to(abd_mesh, 100.0 * MPa)
default_element.apply_to(abd_mesh)

trans_view = view(abd_mesh.transforms())

t0 = Transform.Identity()
t0.translate(Vector3.UnitZ() * -0.8)
trans_view[0] = t0.matrix()

t1 = Transform.Identity()
t1.translate(Vector3.UnitZ() * 0.0)
trans_view[1] = t1.matrix()

t2 = Transform.Identity()
t2.translate(Vector3.UnitZ() * 0.8)
trans_view[2] = t2.matrix()

is_fixed = abd_mesh.instances().find(builtin.is_fixed)
is_fixed_view = view(is_fixed)
is_fixed_view[0] = 0  # NOT fixed (controlled by FreeJoint)
is_fixed_view[1] = 0
is_fixed_view[2] = 0

ref_dof_prev = abd_mesh.instances().create("ref_dof_prev", Vector12.Zero())
ref_dof_prev_view = view(ref_dof_prev)
transform_view = view(abd_mesh.transforms())
ref_dof_prev_view[:] = affine_body.transform_to_q(transform_view)

external_kinetic = abd_mesh.instances().find(builtin.external_kinetic)
external_kinetic_view = view(external_kinetic)
external_kinetic_view[:] = 1

geo_slot, rest_geo_slot = links.geometries().create(abd_mesh)


def update_ref_dof_prev(info: Animation.UpdateInfo):
    geo: SimplicialComplex = info.geo_slots()[0].geometry()
    rdp = geo.instances().find("ref_dof_prev")
    rdp_view = view(rdp)
    t_view = view(geo.transforms())
    rdp_view[:] = affine_body.transform_to_q(t_view)


scene.animator().insert(links, update_ref_dof_prev)

# FreeJoint on instance 0 (replaces fixed constraint)
abfj = AffineBodyFreeJoint()
free_joint_mesh = abfj.create_geometry([geo_slot], np.array([0], dtype=np.int32))
print(free_joint_mesh)
print(free_joint_mesh.vertices().find("dof_type").view())
fj_object = scene.objects().create("free_joint")
free_joint_slot, _ = fj_object.geometries().create(free_joint_mesh)

# Revolute joint: instance 0 -> instance 1
abrj = AffineBodyRevoluteJoint()
pos0s = np.array([[-0.5, 0.0, -0.4]], dtype=np.float32)
pos1s = np.array([[0.5, 0.0, -0.4]], dtype=np.float32)
revolute_mesh = abrj.create_geometry(
    pos0s, pos1s, [geo_slot], [0], [geo_slot], [1], [100.0]
)
revolute_object = scene.objects().create("joints_revolute")
revolute_slot, _ = revolute_object.geometries().create(revolute_mesh)

# Prismatic joint: instance 1 -> instance 2
abpj = AffineBodyPrismaticJoint()
pos0s = np.array([[0.0, 0.0, 0.0]], dtype=np.float32)
pos1s = np.array([[0.0, 0.0, 0.4]], dtype=np.float32)
prismatic_mesh = abpj.create_geometry(
    pos0s, pos1s, [geo_slot], [1], [geo_slot], [2], [100.0]
)
prismatic_object = scene.objects().create("joints_prismatic")
prismatic_slot, _ = prismatic_object.geometries().create(prismatic_mesh)

# Articulation: 6 FreeJoint DOFs + 1 revolute + 1 prismatic = 8 total
eac = ExternalArticulationConstraint()
n_free_dofs = 6
n_total = n_free_dofs + 2

joint_geos = [free_joint_slot] * n_free_dofs + [revolute_slot, prismatic_slot]
indices = list(range(n_free_dofs)) + [0, 0]
articulation = eac.create_geometry(joint_geos, indices)

mass = articulation["joint_joint"].find("mass")
mass_view = view(mass)
mass_mat = np.eye(n_total, dtype=np.float32) * 64.0
mass_view[:] = mass_mat.flatten()

articulation_object = scene.objects().create("articulation_object")
articulation_object.geometries().create(articulation)

gui = {
    "run": False,
    "fj_trans_x": 0.0,
    "fj_trans_y": 0.0,
    "fj_trans_z": 0.0,
    "fj_rot_x": 0.0,
    "fj_rot_y": 0.0,
    "fj_rot_z": 0.0,
    "revolute_vel": 0.0,
    "prismatic_vel": 0.0,
}


def update_articulation(info: Animation.UpdateInfo):
    dt = info.dt()
    geo = info.geo_slots()[0].geometry()
    delta_theta_tilde = geo["joint"].find("delta_theta_tilde")
    dtv = view(delta_theta_tilde)

    dtv[0] = gui["fj_trans_x"] * dt
    dtv[1] = gui["fj_trans_y"] * dt
    dtv[2] = gui["fj_trans_z"] * dt
    dtv[3] = gui["fj_rot_x"] * dt
    dtv[4] = gui["fj_rot_y"] * dt
    dtv[5] = gui["fj_rot_z"] * dt
    dtv[6] = gui["revolute_vel"] * dt
    dtv[7] = gui["prismatic_vel"] * dt


scene.animator().insert(articulation_object, update_articulation)

world.init(scene)
sgui = SceneGUI(scene, "split")

ps.init()
ps.set_ground_plane_height(-1.0)
sgui.register()
sgui.set_edge_width(1)


def on_update():
    if imgui.Button("Run & Stop"):
        gui["run"] = not gui["run"]

    imgui.Separator()
    imgui.Text("External Articulation Control (FreeJoint + Revolute + Prismatic)")
    imgui.Text("Body 0: FreeJoint (6 DOFs)")
    imgui.Text("Body 0 -> Body 1: Revolute Joint")
    imgui.Text("Body 1 -> Body 2: Prismatic Joint")
    imgui.Separator()

    imgui.Text("FreeJoint Translation (Body 0)")
    _, gui["fj_trans_x"] = imgui.SliderFloat("TransX (m/s)", gui["fj_trans_x"], -1.0, 1.0)
    _, gui["fj_trans_y"] = imgui.SliderFloat("TransY (m/s)", gui["fj_trans_y"], -1.0, 1.0)
    _, gui["fj_trans_z"] = imgui.SliderFloat("TransZ (m/s)", gui["fj_trans_z"], -1.0, 1.0)

    imgui.Separator()
    imgui.Text("FreeJoint Rotation (Body 0)")
    _, gui["fj_rot_x"] = imgui.SliderFloat("RotX (rad/s)", gui["fj_rot_x"], -np.pi, np.pi)
    _, gui["fj_rot_y"] = imgui.SliderFloat("RotY (rad/s)", gui["fj_rot_y"], -np.pi, np.pi)
    _, gui["fj_rot_z"] = imgui.SliderFloat("RotZ (rad/s)", gui["fj_rot_z"], -np.pi, np.pi)

    imgui.Separator()
    imgui.Text("Inter-body Joints")
    _, gui["revolute_vel"] = imgui.SliderFloat("Revolute (rad/s)", gui["revolute_vel"], -np.pi, np.pi)
    _, gui["prismatic_vel"] = imgui.SliderFloat("Prismatic (m/s)", gui["prismatic_vel"], -1.0, 1.0)

    imgui.Separator()
    imgui.Text(f"Frame: {world.frame()}")
    imgui.Text(f"Time: {world.frame() * dt:.2f}s")

    if gui["run"]:
        world.advance()
        world.retrieve()
        sgui.update()


ps.set_user_callback(on_update)
ps.show()
