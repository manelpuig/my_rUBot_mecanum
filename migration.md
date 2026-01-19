# MIGRATION.md — ROS 2 Humble → ROS 2 Jazzy

This document tracks the migration of this workspace from **ROS 2 Humble (Ubuntu 22.04)** to **ROS 2 Jazzy (Ubuntu 24.04)** using a **package-by-package** approach.

## Branching policy

- **`humble`**: Stable baseline (ROS 2 Humble). Default branch on GitHub.
- **`jazzy`**: Migration branch (ROS 2 Jazzy). All porting work happens here.

Rules:
- Do **not** introduce Jazzy-specific changes into `humble`.
- If a bugfix applies to both distros, commit it on `humble` and `cherry-pick` into `jazzy`.
- Keep commits small and scoped (ideally one logical change per commit).

## Migration strategy (package-by-package)

We migrate in dependency order to avoid cascading failures:

1. **Custom message/interface packages** (`*_msgs`, `*_interfaces`)
2. **Robot description** (`*_description`: URDF/Xacro/meshes)
3. **Core drivers / robot base** (mecanum driver, odom, tf, cmd_vel, sensors)
4. **Bringup / launch orchestration**
5. **Simulation (Gazebo / ros_gz / plugins)**
6. **Navigation / SLAM / Perception (Nav2, cameras, YOLO, etc.)**

## Definition of Done (per package)

A package is considered “DONE” on Jazzy when:

- **Dependencies**
  - `rosdep` resolves all dependencies on Ubuntu 24.04 + Jazzy
  - `package.xml` dependencies are correct and minimal

- **Build**
  - `colcon build --packages-select <pkg>` succeeds on Jazzy
  - If relevant: `colcon test --packages-select <pkg>` succeeds

- **Runtime smoke test**
  - Node or launch file runs with no fatal errors
  - If it defines interfaces: `ros2 interface show ...` works
  - If it publishes/subscribes: basic topic check (`ros2 topic list/echo/hz`) is OK

## Workspace validation commands (Jazzy)

From the workspace root:

```bash
source /opt/ros/jazzy/setup.bash

# Install dependencies (repeat after changing deps)
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy

# Build a single package (plus its deps if needed)
colcon build --packages-up-to <pkg> --symlink-install

# Source overlay
source install/setup.bash
````
Common pitfalls (notes)

Windows paths / OneDrive: long paths and file locking can cause Git issues. Prefer working outside OneDrive when possible.

Simulation: Gazebo integration may require refactoring (Classic vs gz / ros_gz_*). Defer until core robot stack builds.

Launch/params: expect small changes in defaults or parameter sets between Humble and Jazzy.

Migration tracker

Update this table as packages are migrated.

| Package                | Type            | Status | Notes |
| ---------------------- | --------------- | ------ | ----- |
| `<custom_msgs_pkg_1>`  | msgs/interfaces | TODO   |       |
| `<custom_msgs_pkg_2>`  | msgs/interfaces | TODO   |       |
| `<description_pkg>`    | description     | TODO   |       |
| `<mecanum_driver_pkg>` | driver          | TODO   |       |
| `<bringup_pkg>`        | bringup         | TODO   |       |


Status legend: TODO / WIP / DONE

Commit message convention (recommended)

jazzy: port <pkg> (build fixes)

jazzy: update deps for <pkg>

jazzy: refactor <pkg> for ros_gz

humble: fix <issue> (then cherry-pick into jazzy if applicable)