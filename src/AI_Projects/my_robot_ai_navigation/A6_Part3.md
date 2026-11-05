# A6 - Part 3: Build i arrencar la simulació

Abans de llançar el node `traffic_sign_navigation` (Part 4) cal compilar el paquet i tenir Gazebo i Nav2 funcionant.

## 1. Compilar

```bash
cd ~/my_rUBot_mecanum
colcon build --packages-select my_robot_ai_navigation
source install/setup.bash
```

Si surt l'error de NumPy (`np.maximum_sctype`):

```bash
pip3 install --user --upgrade transforms3d
```

## 2. Gazebo (terminal 1)

Món del grup i mateixa posició inicial que el node (`initial_pose: [-0.5, 0.0, 0.0]`):

```bash
ros2 launch my_robot_bringup my_robot_bringup_gz.launch.py world:=group2_custom.world robot_model:=rubot/rubot_mecanum.urdf.xacro x:=-0.5 y:=0.0 yaw:=0.0
```

## 3. Nav2 (terminal 2)

Mapa del grup i fitxer de paràmetres d'aquesta activitat:

```bash
cd ~/my_rUBot_mecanum
source install/setup.bash
ros2 launch my_robot_navigation2 navigation2_robot.launch.py use_sim_time:=true map_file:=group2_map.yaml params_file:=rubot_sw_lidar_ign_ai.yaml
```

## Comprovació

- A Gazebo es veu el robot a (-0.5, 0) sense xocar.
- A RViz es veu el mapa `group2_map` i el robot ben situat.

Després ja es pot llançar el node (Part 4) amb `config_file:=traffic_sign_navigation_sw_group_02.yaml`.
