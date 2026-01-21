#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, Command, PathJoinSubstitution, TextSubstitution
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare


def generate_launch_description():
    pkg_sim = get_package_share_directory("my_robot_simulation")

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
        default_value="rubot",
        description="Name of the spawned model in Gazebo Sim"
    )

    declare_xacro_file = DeclareLaunchArgument(
        "xacro_file",
        default_value=PathJoinSubstitution([
            FindPackageShare("my_robot_description"),
            "urdf",
            "rubot_mecanum.urdf.xacro",
        ]),
        description="Path to the robot xacro file"
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

    world = LaunchConfiguration("world")
    model_name = LaunchConfiguration("model_name")
    xacro_file = LaunchConfiguration("xacro_file")
    use_sim_time = LaunchConfiguration("use_sim_time")
    bridge_config = LaunchConfiguration("bridge_config")

    # -----------------------------
    # Gazebo Sim launch (ros_gz_sim)
    # -----------------------------
    # Uses the official launch file provided by ros_gz_sim, if available.
    ros_gz_sim_share = get_package_share_directory("ros_gz_sim")
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(ros_gz_sim_share, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": [TextSubstitution(text="-r "), world],
        }.items(),
    )

    # -----------------------------
    # robot_state_publisher (publishes /robot_description + TF)
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

    # -----------------------------
    # Spawn robot in Gazebo Sim from /robot_description
    # -----------------------------
    # Note:
    # - This spawns the model using the URDF provided on /robot_description.
    # - Any Gazebo Classic <gazebo> plugins in the URDF will NOT run in gz_sim.
    spawn_robot = ExecuteProcess(
        cmd=[
            "ros2", "run", "ros_gz_sim", "create",
            "-name", model_name,
            "-topic", "robot_description",
            "-z", "0.10",
        ],
        output="screen",
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

    return LaunchDescription([
        declare_world,
        declare_model_name,
        declare_xacro_file,
        declare_use_sim_time,
        declare_bridge_config,

        gz_launch,
        robot_state_publisher,
        spawn_robot,
        bridge,
    ])
