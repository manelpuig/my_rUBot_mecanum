import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, ThisLaunchFileDir
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")
    use_rviz = LaunchConfiguration("use_rviz", default="false")

    pkg_share = get_package_share_directory("my_robot_cartographer")

    cartographer_config_dir = LaunchConfiguration(
        "cartographer_config_dir",
        default=os.path.join(pkg_share, "config"),
    )
    configuration_basename = LaunchConfiguration(
        "configuration_basename",
        default="my_robot_lds_2d.lua",
    )

    resolution = LaunchConfiguration("resolution", default="0.05")
    publish_period_sec = LaunchConfiguration("publish_period_sec", default="1.0")

    rviz_config_file = os.path.join(pkg_share, "rviz", "my_robot_cartographer2.rviz")

    cartographer_node = Node(
        package="cartographer_ros",
        executable="cartographer_node",
        name="cartographer_node",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        arguments=[
            "-configuration_directory", cartographer_config_dir,
            "-configuration_basename", configuration_basename,
        ],
        remappings=[
            ("scan", "/scan"),
        ],
    )

    occupancy_grid = IncludeLaunchDescription(
        PythonLaunchDescriptionSource([ThisLaunchFileDir(), "/occupancy_grid.launch.py"]),
        launch_arguments={
            "use_sim_time": use_sim_time,
            "resolution": resolution,
            "publish_period_sec": publish_period_sec,
        }.items(),
    )

    rviz2 = Node(
        package="rviz2",
        executable="rviz2",
        name="rviz2",
        arguments=["-d", rviz_config_file],
        parameters=[{"use_sim_time": use_sim_time}],
        condition=IfCondition(use_rviz),
        output="screen",
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "cartographer_config_dir",
            default_value=cartographer_config_dir,
            description="Full path to config directory to load",
        ),
        DeclareLaunchArgument(
            "configuration_basename",
            default_value=configuration_basename,
            description="Name of lua file for cartographer",
        ),
        DeclareLaunchArgument(
            "use_sim_time",
            default_value="true",
            description="Use simulation (gz-sim) clock if true",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="true",
            description="Launch RViz2 if true (OFF by default for Docker OpenGL stability)",
        ),
        DeclareLaunchArgument(
            "resolution",
            default_value=resolution,
            description="Resolution of a grid cell in the published occupancy grid",
        ),
        DeclareLaunchArgument(
            "publish_period_sec",
            default_value=publish_period_sec,
            description="OccupancyGrid publishing period (seconds)",
        ),
        cartographer_node,
        occupancy_grid,
        rviz2,
    ])
