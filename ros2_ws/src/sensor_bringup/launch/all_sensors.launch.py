from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import EnvironmentVariable, LaunchConfiguration


def generate_launch_description():
    package_share = get_package_share_directory("sensor_bringup")
    livox_launch = package_share + "/launch/livox_mid360.launch.py"
    camera_launch = package_share + "/launch/realsense_d435.launch.py"
    host_ip = LaunchConfiguration("host_ip")
    lidar_ip = LaunchConfiguration("lidar_ip")
    broadcast_code = LaunchConfiguration("broadcast_code")

    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "host_ip",
                default_value=EnvironmentVariable("LIVOX_HOST_IP", default_value=""),
            ),
            DeclareLaunchArgument(
                "lidar_ip",
                default_value=EnvironmentVariable("LIVOX_LIDAR_IP", default_value=""),
            ),
            DeclareLaunchArgument(
                "broadcast_code",
                default_value=EnvironmentVariable("LIVOX_BROADCAST_CODE", default_value=""),
            ),
            IncludeLaunchDescription(
                PythonLaunchDescriptionSource(livox_launch),
                launch_arguments={
                    "host_ip": host_ip,
                    "lidar_ip": lidar_ip,
                    "broadcast_code": broadcast_code,
                }.items(),
            ),
            IncludeLaunchDescription(PythonLaunchDescriptionSource(camera_launch)),
        ]
    )