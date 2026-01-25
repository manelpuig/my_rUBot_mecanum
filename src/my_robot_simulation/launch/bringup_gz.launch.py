#!/usr/bin/env python3
import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, OpaqueFunction, ExecuteProcess
from launch.substitutions import LaunchConfiguration, Command
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():
    pkg_sim = get_package_share_directory("my_robot_simulation")

    # ----------------------------
    # Launch arguments
    # ----------------------------
    declare_world = DeclareLaunchArgument(
        "world",
        default_value="empty_world.sdf",
        description="World SDF filename inside my_robot_simulation/worlds"
    )

    declare_robot = DeclareLaunchArgument(
        "robot",
        default_value="rubot_mecanum",
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

    declare_x = DeclareLaunchArgument("x", default_value="0.0")
    declare_y = DeclareLaunchArgument("y", default_value="0.0")
    declare_z = DeclareLaunchArgument("z", default_value="0.10")
    declare_yaw = DeclareLaunchArgument("yaw", default_value="0.0")

    # Robot description (ROS-pure)
    declare_description_pkg = DeclareLaunchArgument(
        "description_pkg",
        default_value="my_robot_description"
    )

    declare_description_xacro = DeclareLaunchArgument(
        "description_xacro",
        default_value="rubot/rubot_mecanum_clean.urdf.xacro"
    )

    world = LaunchConfiguration("world")
    robot = LaunchConfiguration("robot")
    model_name = LaunchConfiguration("model_name")
    use_sim_time = LaunchConfiguration("use_sim_time")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    yaw = LaunchConfiguration("yaw")
    description_pkg = LaunchConfiguration("description_pkg")
    description_xacro = LaunchConfiguration("description_xacro")

    def launch_setup(context, *args, **kwargs):
        robot_name = context.perform_substitution(robot)
        spawn_name = context.perform_substitution(model_name).strip() or robot_name

        world_path = os.path.join(pkg_sim, "worlds", context.perform_substitution(world))
        model_file = os.path.join(pkg_sim, "models", robot_name, "model.sdf")

        use_sim_time_bool = context.perform_substitution(use_sim_time).lower() in ("true", "1", "yes")

        # ----------------------------
        # Gazebo
        # ----------------------------
        gz_server = ExecuteProcess(
            cmd=["gz", "sim", "-r", "-s", world_path],
            output="screen"
        )

        gz_gui = ExecuteProcess(
            cmd=["gz", "sim", "-g"],
            output="screen"
        )

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
                "-Y", context.perform_substitution(yaw),
            ],
        )

        # ----------------------------
        # Bridge
        # ----------------------------
        bridge = Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            output="screen",
            arguments=[
                "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",
                "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",
                "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",
                "/scan@sensor_msgs/msg/LaserScan[gz.msgs.LaserScan",
                "/camera@sensor_msgs/msg/Image[gz.msgs.Image",
                "/camera_info@sensor_msgs/msg/CameraInfo[gz.msgs.CameraInfo",
                "/tf@tf2_msgs/msg/TFMessage[gz.msgs.Pose_V",
            ],
            parameters=[{"use_sim_time": use_sim_time_bool}],
        )

        # ----------------------------
        # robot_state_publisher (TF ROS-pure)
        # ----------------------------
        pkg_desc = get_package_share_directory(context.perform_substitution(description_pkg))
        xacro_path = os.path.join(pkg_desc, "urdf", context.perform_substitution(description_xacro))

        robot_description = ParameterValue(
            Command(["xacro ", xacro_path]),
            value_type=str
        )

        rsp = Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            parameters=[
                {"robot_description": robot_description},
                {"use_sim_time": use_sim_time_bool},
            ],
            output="screen",
        )

        return [
            gz_server,
            TimerAction(period=1.0, actions=[gz_gui]),
            TimerAction(period=3.0, actions=[spawn_robot]),
            TimerAction(period=4.0, actions=[bridge, rsp]),
        ]

    return LaunchDescription([
        declare_world,
        declare_robot,
        declare_model_name,
        declare_use_sim_time,
        declare_x, declare_y, declare_z, declare_yaw,
        declare_description_pkg,
        declare_description_xacro,
        OpaqueFunction(function=launch_setup),
    ])
