import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import ExecuteProcess, SetEnvironmentVariable

def generate_launch_description():
    pkg_share = get_package_share_directory("my_robot_simulation")

    world_path = os.path.join(pkg_share, "worlds", "diffbot_world.sdf")
    models_path = os.path.join(pkg_share, "models")

    return LaunchDescription([
        # perquè <uri>model://diffbot</uri> funcioni
        SetEnvironmentVariable("GZ_SIM_RESOURCE_PATH", models_path),

        ExecuteProcess(
            cmd=["gz", "sim", "-r", world_path],
            output="screen",
        ),
    ])
