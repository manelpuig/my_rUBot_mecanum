#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, OpaqueFunction, ExecuteProcess
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    pkg_sim = get_package_share_directory("my_robot_simulation")

    declare_world = DeclareLaunchArgument(
        "world",
        default_value="empty_world.sdf",
        description="World SDF filename inside my_robot_simulation/worlds"
    )
    declare_robot = DeclareLaunchArgument(
        "robot",
        default_value="rubot_differential",
        description="Robot model folder name inside my_robot_simulation/models"
    )
    declare_model_name = DeclareLaunchArgument(
        "model_name",
        default_value="",
        description="Spawned model name in Gazebo. If empty, uses robot argument."
    )
    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time"
    )

    declare_x = DeclareLaunchArgument("x", default_value="0.0", description="Initial X (m)")
    declare_y = DeclareLaunchArgument("y", default_value="0.0", description="Initial Y (m)")
    declare_z = DeclareLaunchArgument("z", default_value="0.10", description="Initial Z (m)")
    declare_yaw = DeclareLaunchArgument("yaw", default_value="0.0", description="Initial yaw (rad)")

    world = LaunchConfiguration("world")
    robot = LaunchConfiguration("robot")
    model_name = LaunchConfiguration("model_name")
    use_sim_time = LaunchConfiguration("use_sim_time")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    yaw = LaunchConfiguration("yaw")

    def launch_setup(context, *args, **kwargs):
        world_file = context.perform_substitution(world)
        robot_name = context.perform_substitution(robot)
        spawn_name = context.perform_substitution(model_name).strip() or robot_name

        world_path = os.path.join(pkg_sim, "worlds", world_file)
        model_file = os.path.join(pkg_sim, "models", robot_name, "model.sdf")

        if not os.path.exists(world_path):
            raise RuntimeError(f"World not found: {world_path}")
        if not os.path.exists(model_file):
            raise RuntimeError(f"Model not found: {model_file}")

        # 1) Start server (services enabled)
        gz_server = ExecuteProcess(
            cmd=["gz", "sim", "-r", "-s", world_path],
            output="screen",
        )

        # 2) Start GUI (connect to server)
        # Delay a bit so the server is already up.
        gz_gui = ExecuteProcess(
            cmd=["gz", "sim", "-g"],
            output="screen",
        )
        gz_gui_delayed = TimerAction(period=1.0, actions=[gz_gui])

        # 3) Spawn robot (needs UserCommands system in the world)
        spawn_robot = Node(
            package="ros_gz_sim",
            executable="create",
            output="screen",
            arguments=[
                "-world", "empty_world",
                "-name", spawn_name,
                "-file", model_file,
                "-x", context.perform_substitution(x),
                "-y", context.perform_substitution(y),
                "-z", context.perform_substitution(z),
                "-R", "0", "-P", "0",
                "-Y", context.perform_substitution(yaw),
            ],
        )
        spawn_robot_delayed = TimerAction(period=3.0, actions=[spawn_robot])

        # 4) Bridge
        use_sim_time_str = context.perform_substitution(use_sim_time)
        use_sim_time_bool = use_sim_time_str.strip().lower() in ("true", "1", "yes")

        bridge = Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            name="ros_gz_bridge",
            output="screen",
            arguments=[
                "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
                "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
                "/camera@sensor_msgs/msg/Image[gz.msgs.Image",
                "/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
            ],
            parameters=[{"use_sim_time": use_sim_time_bool}],
        )
        bridge_delayed = TimerAction(period=4.0, actions=[bridge])

        return [gz_server, gz_gui_delayed, spawn_robot_delayed, bridge_delayed]

    return LaunchDescription([
        declare_world,
        declare_robot,
        declare_model_name,
        declare_use_sim_time,
        declare_x, declare_y, declare_z, declare_yaw,
        OpaqueFunction(function=launch_setup),
    ])
