# Copyright 2019 Open Source Robotics Foundation, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Author: Darby Lim
#
# Updated for rUBot mecanum + gz-sim: lidar frame alias + docker-friendly RViz default.

import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.conditions import IfCondition
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration, ThisLaunchFileDir
from launch_ros.actions import Node


def generate_launch_description():
    # --- Launch arguments ---
    use_sim_time = LaunchConfiguration("use_sim_time", default="true")

    # In Docker, RViz commonly fails due to OpenGL/GLSL; keep it OFF by default.
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

    # --- IMPORTANT: lidar frame alias ---
    # Your /scan has header.frame_id = "rubot_mecanum/base_scan/lidar"
    # but TF tree contains: base_link -> base_scan
    # This static TF makes the scan frame resolvable by TF consumers (Cartographer, RViz).
    lidar_alias_tf = Node(
        package="tf2_ros",
        executable="static_transform_publisher",
        name="lidar_alias_tf",
        # x y z roll pitch yaw parent child
        arguments=["0", "0", "0", "0", "0", "0", "base_scan", "rubot_mecanum/base_scan/lidar"],
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
    )

    cartographer_node = Node(
        package="cartographer_ros",
        executable="cartographer_node",
        name="cartographer_node",
        output="screen",
        parameters=[{"use_sim_time": use_sim_time}],
        arguments=[
            "-configuration_directory",
            cartographer_config_dir,
            "-configuration_basename",
            configuration_basename,
        ],
        # Make scan topic explicit (avoids issues if node expects 'scan' without '/')
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
            description="Use simulation (Gazebo/gz-sim) clock if true",
        ),
        DeclareLaunchArgument(
            "use_rviz",
            default_value="false",
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

        # Order matters: publish TF alias first, then cartographer
        lidar_alias_tf,
        cartographer_node,
        occupancy_grid,
        rviz2,
    ])
