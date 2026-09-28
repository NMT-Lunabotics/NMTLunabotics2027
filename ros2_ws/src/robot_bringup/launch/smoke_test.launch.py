from launch import LaunchDescription
from launch.actions import LogInfo


def generate_launch_description():
    return LaunchDescription(
        [
            LogInfo(
                msg=(
                    "NMT Lunabotics ROS 2 Humble workspace is ready. "
                    "This smoke test does not start hardware."
                )
            )
        ]
    )