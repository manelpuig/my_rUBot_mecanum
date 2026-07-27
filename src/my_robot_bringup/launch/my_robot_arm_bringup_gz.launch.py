import os

from ament_index_python.packages import get_package_share_directory

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    ExecuteProcess,
    IncludeLaunchDescription,
    RegisterEventHandler,
    SetEnvironmentVariable,
    TimerAction,
)
from launch.event_handlers import OnProcessExit
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import (
    Command,
    EnvironmentVariable,
    LaunchConfiguration,
    PathJoinSubstitution,
)

from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue


def generate_launch_description():

    pkg_bringup = get_package_share_directory("my_robot_bringup")
    pkg_description = get_package_share_directory("my_robot_description")
    pkg_ros_gz_sim = get_package_share_directory("ros_gz_sim")

    install_share_path = os.path.dirname(pkg_description)

    # -------------------------------------------------------------------------
    # Launch configurations
    # -------------------------------------------------------------------------

    world = LaunchConfiguration("world")
    robot_model = LaunchConfiguration("robot_model")
    robot_name = LaunchConfiguration("robot_name")

    x = LaunchConfiguration("x")
    y = LaunchConfiguration("y")
    z = LaunchConfiguration("z")
    yaw = LaunchConfiguration("yaw")

    # -------------------------------------------------------------------------
    # Paths
    # -------------------------------------------------------------------------

    models_path = os.path.join(pkg_bringup, "models")
    worlds_path = os.path.join(pkg_bringup, "worlds")

    controllers_file = os.path.join(
        pkg_bringup,
        "config",
        "arm_controllers.yaml",
    )

    world_path = PathJoinSubstitution(
        [
            pkg_bringup,
            "worlds",
            world,
        ]
    )

    urdf_path = PathJoinSubstitution(
        [
            pkg_description,
            "urdf",
            robot_model,
        ]
    )

    # -------------------------------------------------------------------------
    # Robot description generated from Xacro
    # -------------------------------------------------------------------------

    robot_description = ParameterValue(
        Command(
            [
                "xacro ",
                urdf_path,
                " use_gazebo_plugin:=true",
                " hardware_plugin:=ign_ros2_control/IgnitionSystem",
                " ros2_control_params:=",
                controllers_file,
            ]
        ),
        value_type=str,
    )

    # -------------------------------------------------------------------------
    # Robot State Publisher
    # -------------------------------------------------------------------------

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

    # -------------------------------------------------------------------------
    # Gazebo Ignition / Fortress
    # -------------------------------------------------------------------------

    gazebo = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                pkg_ros_gz_sim,
                "launch",
                "gz_sim.launch.py",
            )
        ),
        launch_arguments={
            "gz_args": ["-r ", world_path],
        }.items(),
    )

    # -------------------------------------------------------------------------
    # Spawn robot
    # -------------------------------------------------------------------------

    spawn_robot = Node(
        package="ros_gz_sim",
        executable="create",
        name="spawn_robot",
        output="screen",
        arguments=[
            "-name",
            robot_name,
            "-topic",
            "robot_description",
            "-x",
            x,
            "-y",
            y,
            "-z",
            z,
            "-Y",
            yaw,
        ],
    )

    # -------------------------------------------------------------------------
    # ROS <-> Gazebo bridge
    # -------------------------------------------------------------------------

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
            # "/camera/camera_info@sensor_msgs/msg/CameraInfo"
            # "[ignition.msgs.CameraInfo",
            # "/camera/depth_image@sensor_msgs/msg/Image"
            # "[ignition.msgs.Image",
            # "/camera/points@sensor_msgs/msg/PointCloud2"
            # "[ignition.msgs.PointCloudPacked",
        ],
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
    )

    # -------------------------------------------------------------------------
    # Static transforms required by Gazebo sensor frame names
    # -------------------------------------------------------------------------

    static_lidar_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_lidar_tf",
        output="screen",
        arguments=[
            "--x",
            "0",
            "--y",
            "0",
            "--z",
            "0",
            "--qx",
            "0",
            "--qy",
            "0",
            "--qz",
            "0",
            "--qw",
            "1",
            "--frame-id",
            "base_scan",
            "--child-frame-id",
            "rubot_mecanum/base_link/lidar",
        ],
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
    )

    static_camera_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="static_camera_tf",
        output="screen",
        arguments=[
            "--x",
            "0",
            "--y",
            "0",
            "--z",
            "0",
            "--qx",
            "0",
            "--qy",
            "0",
            "--qz",
            "0",
            "--qw",
            "1",
            "--frame-id",
            "camera",
            "--child-frame-id",
            "rubot_mecanum/camera/rgbd_camera",
        ],
        parameters=[
            {
                "use_sim_time": True,
            }
        ],
    )

    # -------------------------------------------------------------------------
    # ros2_control controller spawners
    # -------------------------------------------------------------------------

    joint_state_broadcaster_spawner = Node(
        package="controller_manager",
        executable="spawner",
        name="joint_state_broadcaster_spawner",
        output="screen",
        arguments=[
            "joint_state_broadcaster",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
    )

    arm_controller_spawner = Node(
        package="controller_manager",
        executable="spawner",
        name="arm_controller_spawner",
        output="screen",
        arguments=[
            "arm_controller",
            "--controller-manager",
            "/controller_manager",
            "--controller-manager-timeout",
            "30",
        ],
    )

    # -------------------------------------------------------------------------
    # Initial arm pose
    # -------------------------------------------------------------------------

    initial_arm_pose = ExecuteProcess(
        cmd=[
            "ros2",
            "topic",
            "pub",
            "--once",
            "/arm_controller/joint_trajectory",
            "trajectory_msgs/msg/JointTrajectory",
            (
                "{joint_names: ["
                "arm_joint1, "
                "arm_joint2, "
                "arm_joint3, "
                "arm_joint4, "
                "arm_joint5, "
                "arm_joint6"
                "], "
                "points: [{"
                "positions: [0.0, -1.0, 1.5, 0.5, 0.0, 0.0], "
                "time_from_start: {sec: 2, nanosec: 0}"
                "}]}"
            ),
        ],
        output="screen",
    )

    # -------------------------------------------------------------------------
    # Startup sequence
    # -------------------------------------------------------------------------

    # Give Gazebo some time to start before spawning the robot and bridges.
    delayed_spawn_and_bridge = TimerAction(
        period=3.0,
        actions=[
            spawn_robot,
            bridge,
            static_lidar_tf,
            static_camera_tf,
        ],
    )

    # Start only the joint state broadcaster initially.
    # Its spawner waits until /controller_manager is available.
    delayed_joint_state_broadcaster = TimerAction(
        period=6.0,
        actions=[
            joint_state_broadcaster_spawner,
        ],
    )

    # Start arm_controller only after joint_state_broadcaster has been
    # configured and activated successfully.
    start_arm_controller = RegisterEventHandler(
        OnProcessExit(
            target_action=joint_state_broadcaster_spawner,
            on_exit=[
                arm_controller_spawner,
            ],
        )
    )

    # Send the initial pose only after the arm_controller spawner has finished.
    # The additional second allows its topic subscription to become available.
    send_initial_arm_pose = RegisterEventHandler(
        OnProcessExit(
            target_action=arm_controller_spawner,
            on_exit=[
                TimerAction(
                    period=1.0,
                    actions=[
                        initial_arm_pose,
                    ],
                )
            ],
        )
    )

    # -------------------------------------------------------------------------
    # Launch description
    # -------------------------------------------------------------------------

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "world",
                default_value="empty_world_ign.world",
                description="World file inside my_robot_bringup/worlds",
            ),
            DeclareLaunchArgument(
                "robot_model",
                default_value="rubot_arm/rubot_mecanum_arm.urdf.xacro",
                description=(
                    "Robot model path relative to "
                    "my_robot_description/urdf"
                ),
            ),
            DeclareLaunchArgument(
                "robot_name",
                default_value="rubot_mecanum",
            ),
            DeclareLaunchArgument(
                "x",
                default_value="0.0",
            ),
            DeclareLaunchArgument(
                "y",
                default_value="0.0",
            ),
            DeclareLaunchArgument(
                "z",
                default_value="0.08",
            ),
            DeclareLaunchArgument(
                "yaw",
                default_value="0.0",
            ),
            SetEnvironmentVariable(
                name="IGN_GAZEBO_RESOURCE_PATH",
                value=[
                    models_path,
                    ":",
                    worlds_path,
                    ":",
                    pkg_description,
                    ":",
                    install_share_path,
                    ":",
                    EnvironmentVariable(
                        "IGN_GAZEBO_RESOURCE_PATH",
                        default_value="",
                    ),
                ],
            ),
            SetEnvironmentVariable(
                name="GZ_SIM_RESOURCE_PATH",
                value=[
                    models_path,
                    ":",
                    worlds_path,
                    ":",
                    pkg_description,
                    ":",
                    install_share_path,
                    ":",
                    EnvironmentVariable(
                        "GZ_SIM_RESOURCE_PATH",
                        default_value="",
                    ),
                ],
            ),
            robot_state_publisher,
            gazebo,
            delayed_spawn_and_bridge,
            delayed_joint_state_broadcaster,
            start_arm_controller,
            send_initial_arm_pose,
        ]
    )