import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription, TimerAction
from launch.actions import SetEnvironmentVariable
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, PathJoinSubstitution, EnvironmentVariable
from launch_ros.actions import Node


def generate_launch_description():

    pkg_bringup = get_package_share_directory("my_robot_bringup")
    pkg_description = get_package_share_directory("my_robot_description")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    # Launch arguments
    world = LaunchConfiguration("world")
    robot_name = LaunchConfiguration("robot_name")
    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    yaw = LaunchConfiguration("yaw")

    # Paths
    models_path = os.path.join(pkg_bringup, "models")
    worlds_path = os.path.join(pkg_bringup, "worlds")

    world_path = PathJoinSubstitution([
        pkg_bringup,
        "worlds",
        world,
    ])

    robot_sdf_path = PathJoinSubstitution([
        pkg_bringup,
        "models",
        "rubot_mecanum",
        "model.sdf",
    ])

    urdf_path = os.path.join(
        pkg_description,
        "urdf",
        "rubot",
        "rubot_mecanum_gz.urdf",
    )

    with open(urdf_path, "r") as f:
        robot_description = f.read()

    # Robot State Publisher: publishes TF from URDF
    robot_state_publisher = Node(
        package="robot_state_publisher",
        executable="robot_state_publisher",
        name="robot_state_publisher",
        output="screen",
        parameters=[
            {
                "use_sim_time": True,
                "robot_description": robot_description,
            }
        ],
    )
 
    # Start Gazebo Ignition / Gazebo Fortress
    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(pkg_ros_gz_sim, "launch", "gz_sim.launch.py")
        ),
        launch_arguments={
            "gz_args": ["-r ", world_path],
        }.items(),
    )

    # Spawn robot from SDF model
    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        output="screen",
        arguments=[
            "-name", robot_name,
            "-file", robot_sdf_path,
            "-x", x,
            "-y", y,
            "-z", z,
            "-Y", yaw,
        ],
    )

    # Minimal ROS <-> Gazebo bridge
    bridge = Node(
        package="ros_gz_bridge",
        executable="parameter_bridge",
        name="ros_gz_bridge",
        output="screen",
        arguments=[
            "/clock@rosgraph_msgs/msg/Clock[ignition.msgs.Clock",
            "/cmd_vel@geometry_msgs/msg/Twist]ignition.msgs.Twist",
            "/odom@nav_msgs/msg/Odometry[ignition.msgs.Odometry",
            "/scan@sensor_msgs/msg/LaserScan[ignition.msgs.LaserScan",
            "/tf@tf2_msgs/msg/TFMessage[ignition.msgs.Pose_V",

            "/camera/image@sensor_msgs/msg/Image[ignition.msgs.Image",
            "/camera/camera_info@sensor_msgs/msg/CameraInfo[ignition.msgs.CameraInfo",
            "/camera/depth_image@sensor_msgs/msg/Image[ignition.msgs.Image",
            "/camera/points@sensor_msgs/msg/PointCloud2[ignition.msgs.PointCloudPacked",
        ],
        parameters=[
            {"use_sim_time": True}
        ],
    )

    # Different frame name lidar in gz
    static_lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_lidar_tf",
        output="screen",
        arguments=[
            "--x", "0",
            "--y", "0",
            "--z", "0",
            "--qx", "0",
            "--qy", "0",
            "--qz", "0",
            "--qw", "1",
            "--frame-id", "base_scan",
            "--child-frame-id", "rubot_mecanum/base_scan/lidar",
        ],
        parameters=[{"use_sim_time": True}],
    )

    # Different frame name camera in gz
    static_camera_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_camera_tf",
        output="screen",
        arguments=[
            "--x", "0",
            "--y", "0",
            "--z", "0",
            "--qx", "0",
            "--qy", "0",
            "--qz", "0",
            "--qw", "1",
            "--frame-id", "camera",
            "--child-frame-id", "rubot_mecanum/camera/rgbd_camera",
        ],
        parameters=[{"use_sim_time": True}],
    )

    delayed_spawn_and_bridge = TimerAction(
        period=3.0,
        actions=[
            spawn_robot,
            bridge,
            static_lidar_tf,
            static_camera_tf,
        ],
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "world",
            default_value="empty_world_ign.world",
            description="World file inside my_robot_bringup/worlds",
        ),
        DeclareLaunchArgument("robot_name", default_value="rubot_mecanum"),
        DeclareLaunchArgument("x", default_value="0.0"),
        DeclareLaunchArgument("y", default_value="0.0"),
        DeclareLaunchArgument("z", default_value="0.05"),
        DeclareLaunchArgument("yaw", default_value="0.0"),

        SetEnvironmentVariable(
            name="IGN_GAZEBO_RESOURCE_PATH",
            value=[
                models_path,
                ":",
                worlds_path,
                ":",
                EnvironmentVariable("IGN_GAZEBO_RESOURCE_PATH", default_value=""),
            ],
        ),
        SetEnvironmentVariable(
            name="GZ_SIM_RESOURCE_PATH",
            value=[
                models_path,
                ":",
                worlds_path,
                ":",
                EnvironmentVariable("GZ_SIM_RESOURCE_PATH", default_value=""),
            ],
        ),
        robot_state_publisher,
        gazebo,
        delayed_spawn_and_bridge,
    ])