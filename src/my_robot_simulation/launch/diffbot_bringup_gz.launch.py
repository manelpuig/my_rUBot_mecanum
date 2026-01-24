import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable
from launch_ros.actions import Node

def generate_launch_description():
    pkg_share = get_package_share_directory("my_robot_simulation")

    world_path = os.path.join(pkg_share, "worlds", "diffbot_world.sdf")
    models_path = os.path.join(pkg_share, "models")

    # Mappings (ROS <-> GZ)
    # ROS Twist -> GZ Twist
    bridge_args = [
        "/cmd_vel@geometry_msgs/msg/Twist]gz.msgs.Twist",              # ROS -> GZ
        "/odom@nav_msgs/msg/Odometry[gz.msgs.Odometry",                # GZ -> ROS
        "/clock@rosgraph_msgs/msg/Clock[gz.msgs.Clock",                # GZ -> ROS
    ]

    return LaunchDescription([
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", models_path),

        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_path],
            output="screen",
        ),

        Node(
            package="ros_gz_bridge",
            executable="parameter_bridge",
            arguments=bridge_args,
            output="screen",
        ),
    ])
