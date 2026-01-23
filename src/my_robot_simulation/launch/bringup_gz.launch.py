#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription, TimerAction
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, TextSubstitution, Command
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_sim = get_package_share_directory("my_robot_simulation")
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")

    # -----------------------------
    # Launch arguments
    # -----------------------------
    declare_world = DeclareLaunchArgument(
        "world",
        default_value=os.path.join(pkg_sim, "worlds", "empty_world.sdf"),
        description="Full path to an SDF world file"
    )

    declare_model_name = DeclareLaunchArgument(
        "model_name",
        default_value="rubot_mecanum",
        description="Name of the spawned model in Gazebo Sim"
    )

    declare_model_file = DeclareLaunchArgument(
        "model_file",
        default_value=os.path.join(pkg_sim, "models", "rubot_mecanum", "model.sdf"),
        description="Full path to model.sdf (Gazebo Sim model)"
    )

    declare_use_sim_time = DeclareLaunchArgument(
        "use_sim_time",
        default_value="true",
        description="Use simulation time"
    )

    declare_bridge_config = DeclareLaunchArgument(
        "bridge_config",
        default_value=os.path.join(pkg_sim, "config", "gz_bridge.yaml"),
        description="YAML config file for ros_gz_bridge parameter_bridge"
    )

    # Spawn pose arguments (x, y, z, w=yaw)
    declare_x = DeclareLaunchArgument(
        "x",
        default_value="0.0",
        description="Initial X position of the robot in the world frame (m)"
    )
    declare_y = DeclareLaunchArgument(
        "y",
        default_value="0.0",
        description="Initial Y position of the robot in the world frame (m)"
    )
    declare_w = DeclareLaunchArgument(
        "w",
        default_value="0.0",
        description="Initial yaw (rotation about Z) of the robot in the world frame (rad)"
    )

    # Optional: run robot_state_publisher using a *clean* URDF/Xacro (recommended)
    declare_publish_tf = DeclareLaunchArgument(
        "publish_tf",
        default_value="true",
        description="Run robot_state_publisher (TF) from my_robot_description"
    )

    declare_xacro_file = DeclareLaunchArgument(
        "xacro_file",
        default_value=PathJoinSubstitution([
            FindPackageShare("my_robot_description"),
            "urdf",
            "rubot/rubot_mecanum_clean.urdf.xacro",
        ]),
        description="Path to CLEAN robot xacro (no Gazebo plugins)"
    )

    # LaunchConfigurations
    world = LaunchConfiguration("world")
    model_name = LaunchConfiguration("model_name")
    model_file = LaunchConfiguration("model_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    bridge_config = LaunchConfiguration("bridge_config")
    publish_tf = LaunchConfiguration("publish_tf")  # kept for compatibility (not used as condition here)
    xacro_file = LaunchConfiguration("xacro_file")

    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    w = LaunchConfiguration("w")  # yaw

    # -----------------------------
    # Gazebo Sim launch
    # -----------------------------
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": [TextSubstitution(text="-r "), world],
        }.items(),
    )

    # -----------------------------
    # Spawn robot in Gazebo Sim from model.sdf
    # -----------------------------
    spawn_robot = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_sim", "create",
            "-name", model_name,
            "-file", model_file,
            "-x", x, "-y", y, "-z", "0.1",
            "-R", "0", "-P", "0", "-Y", w,
        ],
        output="screen",
    )

    spawn_robot_delayed = TimerAction(
        period=2.0,
        actions=[spawn_robot]
    )

    # -----------------------------
    # Bridge (topics defined in YAML)
    # -----------------------------
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="gz_bridge",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "config_file": bridge_config,
        }],
    )

    bridge_delayed = TimerAction(
        period=3.0,
        actions=[bridge]
    )

    # -----------------------------
    # robot_state_publisher (TF from clean URDF)
    # -----------------------------
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": use_sim_time,
            "robot_description": Command(["xacro ", xacro_file]),
        }],
    )

    return LaunchDescription([
        declare_world,
        declare_model_name,
        declare_model_file,
        declare_use_sim_time,
        declare_bridge_config,

        declare_x,
        declare_y,
        declare_w,

        declare_publish_tf,
        declare_xacro_file,

        gz_launch,
        spawn_robot_delayed,
        bridge_delayed,
        robot_state_publisher,
    ])
