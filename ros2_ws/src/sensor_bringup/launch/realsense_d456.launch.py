from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource


def generate_launch_description():
    camera_launch = (
        get_package_share_directory("realsense2_camera")
        + "/launch/rs_launch.py"
    )
    return LaunchDescription(
        [
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(camera_launch),
                launch_arguments={
                    "camera_namespace": "camera",
                    "camera_name": "d456",
                    "depth_module.depth_profile": "640x480x30",
                    "rgb_camera.color_profile": "640x480x30",
                    "enable_color": "true",
                    "enable_depth": "true",
                    "enable_sync": "true",
                    "align_depth.enable": "true",
                    "pointcloud.enable": "true",
                    "diagnostics_period": "1.0",
                    "reconnect_timeout": "6.0",
                }.items(),
            )
        ]
    )