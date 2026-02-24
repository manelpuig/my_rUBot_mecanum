import os
from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, TimerAction, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    LaunchConfiguration, PythonExpression, TextSubstitution,
    PathJoinSubstitution
)
from launch_ros.actions import Node, SetParameter


def generate_launch_description():
    pkg_bringup = get_package_share_directory("my_robot_bringup")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")
    pkg_desc = get_package_share_directory("my_robot_description")

    # Args
    world = LaunchConfiguration("world")
    robot_name = LaunchConfiguration("robot")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    w = LaunchConfiguration("w")

    default_world = "sign_world_ign.world"
    default_robot = "rubot_mecanum"

    world_path = PathJoinSubstitution([TextSubstitution(text=pkg_bringup), "worlds", world])
    robot_sdf_path = PathJoinSubstitution([TextSubstitution(text=pkg_bringup), "models", robot_name, "model.sdf"])
    yaw_rad = PythonExpression([w, " * 3.141592653589793 / 180.0"])

    bridge_yaml = os.path.join(pkg_bringup, "config", "ros_gz_bridge_camera.yaml")

    # URDF for TF / RobotModel in RViz
    urdf_file = os.path.join(pkg_desc, "urdf", "rubot", "rubot_mecanum_gz.urdf")
    with open(urdf_file, "r") as f:
        robot_description_xml = f.read()

    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        output="screen",
        parameters=[{
            "use_sim_time": True,
            "robot_description": robot_description_xml,
        }],
    )

    # image_transport republishers (leave as-is)
    rgb_compressed = Node(
        package="image_transport",
        executable="republish",
        name="rgb_republisher",
        output="screen",
        arguments=["raw", "compressed"],
        remappings=[
            ("/in", "/camera/image"),
            ("/out/compressed", "/camera/image/compressed"),
        ],
        parameters=[{"use_sim_time": True}],
    )

    depth_compressed = Node(
        package="image_transport",
        executable="republish",
        name="depth_republisher",
        output="screen",
        arguments=["raw", "compressedDepth"],
        remappings=[
            ("/in", "/camera/depth_image"),
            ("/out/compressedDepth", "/camera/depth_image/compressedDepth"),
        ],
        parameters=[{"use_sim_time": True}],
    )

    # Gazebo Sim
    gz_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")),
        launch_arguments={"gz_args": ["-r ", world_path]}.items(),
    )

    # Spawn robot
    spawn = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name", robot_name,
            "-file", robot_sdf_path,
            "-x", x, "-y", y,
            "-z", "0.05",
            "-Y", yaw_rad,
        ],
    )

    # Bridge
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        arguments=[
            "--ros-args",
            "-p", f"config_file:={bridge_yaml}",
        ],
    )

    # Clock
    clock_relay = Node(
        package='topic_tools',
        executable='relay',
        name='clock_relay',
        output='screen',
        arguments=['/world/empty_world_ign/clock', '/clock'],
    )

    # Localization TF odom
    ekf_yaml = os.path.join(pkg_bringup, "config", "ekf_odom.yaml")
    ekf = Node(
        package="robot_localization",
        executable="ekf_node",
        name="ekf_filter_node",
        output="screen",
        parameters=[ekf_yaml],
    )

    # Link frame_id base_scan from ROS2 to frame_id from Gazebo Sim: <robot>/base_scan/lidar
    lidar_sensor_frame = PythonExpression(["'", robot_name, "/base_scan/lidar'"])
    static_lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        output="screen",
        # x y z qx qy qz qw parent child
        arguments=[
            "--x", "0", "--y", "0", "--z", "0",
            "--qx", "0", "--qy", "0", "--qz", "0", "--qw", "1",
            "--frame-id", "base_scan",
            "--child-frame-id", lidar_sensor_frame,
        ],
        parameters=[{"use_sim_time": True}],
    )
    # Link frame_id camera from ROS2 to frame_id from Gazebo Sim: <robot>/camera/rgbd_camera
    camera_sensor_frame = PythonExpression(["'", robot_name, "/camera/rgbd_camera'"])
    static_camera_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        output="screen",
        # x y z qx qy qz qw parent child
        arguments=[
            "--x", "0", "--y", "0", "--z", "0",
            "--qx", "0", "--qy", "0", "--qz", "0", "--qw", "1",
            "--frame-id", "camera",
            "--child-frame-id", camera_sensor_frame,
        ],
        parameters=[{"use_sim_time": True}],
    )
    # Link base_footprint --> base_link
    static_basefootprint_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        output="screen",
        arguments=[
            "--x", "0", "--y", "0", "--z", "0",
            "--qx", "0", "--qy", "0", "--qz", "0", "--qw", "1",
            "--frame-id", "base_footprint",
            "--child-frame-id", "base_link",
        ],
        parameters=[{"use_sim_time": True}],
    )

    delayed_gz = TimerAction(
        period=5.0,
        actions=[spawn, bridge, clock_relay, ekf, static_basefootprint_tf, static_lidar_tf, static_camera_tf],
    )

    return LaunchDescription([
        SetParameter(name="use_sim_time", value=True),

        DeclareLaunchArgument("world", default_value=default_world),
        DeclareLaunchArgument("robot", default_value=default_robot),
        DeclareLaunchArgument("x", default_value="0.0"),
        DeclareLaunchArgument("y", default_value="0.0"),
        DeclareLaunchArgument("w", default_value="0.0"),

        robot_state_publisher,
        rgb_compressed,
        depth_compressed,

        gz_launch,
        delayed_gz,
    ])