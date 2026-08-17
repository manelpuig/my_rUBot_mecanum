from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    parameters = {
        'distance_limit': LaunchConfiguration('distance_limit'),
        'tolerance': LaunchConfiguration('tolerance'),
        'right_detection_limit': LaunchConfiguration('right_detection_limit'),
        'forward_speed': LaunchConfiguration('forward_speed'),
        'turn_speed': LaunchConfiguration('turn_speed'),
        'lateral_gain': LaunchConfiguration('lateral_gain'),
        'alignment_gain': LaunchConfiguration('alignment_gain'),
        'time_to_stop': LaunchConfiguration('time_to_stop'),
    }

    return LaunchDescription([
        DeclareLaunchArgument('distance_limit', default_value='0.5'),
        DeclareLaunchArgument('tolerance', default_value='0.05'),
        DeclareLaunchArgument('right_detection_limit', default_value='1.0'),
        DeclareLaunchArgument('forward_speed', default_value='0.2'),
        DeclareLaunchArgument('turn_speed', default_value='0.4'),
        DeclareLaunchArgument('lateral_gain', default_value='0.5'),
        DeclareLaunchArgument('alignment_gain', default_value='0.5'),
        DeclareLaunchArgument('time_to_stop', default_value='30.0'),
        Node(
            package='my_robot_control',
            executable='my_rubot_wallfollower_holonomic_exec',
            name='rubot_wall_follower_holonomic_node',
            output='screen',
            parameters=[parameters],
        ),
    ])
