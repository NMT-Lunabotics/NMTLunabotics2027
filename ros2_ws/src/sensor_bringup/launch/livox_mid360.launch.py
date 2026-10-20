import ipaddress
import json
import os
import tempfile

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, OpaqueFunction
from launch.substitutions import EnvironmentVariable, LaunchConfiguration
from launch_ros.actions import Node


def _launch_driver(context):
    host_ip = LaunchConfiguration("host_ip").perform(context)
    lidar_ip = LaunchConfiguration("lidar_ip").perform(context)
    broadcast_code = LaunchConfiguration("broadcast_code").perform(context)
    for label, value in (("host_ip", host_ip), ("lidar_ip", lidar_ip)):
        if not value:
            raise RuntimeError(
                f"Set {label} for the MID-360 Ethernet link, for example with "
                f"LIVOX_{label.upper()} or a launch argument."
            )
        try:
            ipaddress.IPv4Address(value)
        except ipaddress.AddressValueError as error:
            raise RuntimeError(f"{label} must be an IPv4 address: {value}") from error
    if not broadcast_code:
        raise RuntimeError(
            "Set broadcast_code to the MID-360 broadcast code from its device label."
        )

    template_path = os.path.join(
        get_package_share_directory("sensor_bringup"),
        "config",
        "MID360_config.json.in",
    )
    with open(template_path, encoding="utf-8") as template_file:
        template = template_file.read()
    config_text = template.replace("@HOST_IP@", host_ip).replace("@LIDAR_IP@", lidar_ip)
    config = json.loads(config_text)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix="_mid360.json", prefix="nmt_", delete=False, encoding="utf-8"
    ) as config_file:
        json.dump(config, config_file, indent=2)
        config_path = config_file.name

    return [
        Node(
            package="livox_ros_driver2",
            executable="livox_ros_driver2_node",
            name="livox_lidar_publisher",
            output="screen",
            parameters=[
                {
                    "xfer_format": 0,
                    "multi_topic": 0,
                    "data_src": 0,
                    "publish_freq": 10.0,
                    "output_data_type": 0,
                    "frame_id": "livox_frame",
                    "user_config_path": config_path,
                    "cmdline_input_bd_code": broadcast_code,
                }
            ],
        )
    ]


def generate_launch_description():
    return LaunchDescription(
        [
            DeclareLaunchArgument(
                "host_ip",
                default_value=EnvironmentVariable("LIVOX_HOST_IP", default_value=""),
                description="Jetson IPv4 address on the dedicated MID-360 Ethernet link",
            ),
            DeclareLaunchArgument(
                "lidar_ip",
                default_value=EnvironmentVariable("LIVOX_LIDAR_IP", default_value=""),
                description="MID-360 IPv4 address on its Ethernet link",
            ),
            DeclareLaunchArgument(
                "broadcast_code",
                default_value=EnvironmentVariable("LIVOX_BROADCAST_CODE", default_value=""),
                description="MID-360 broadcast code from its device label",
            ),
            OpaqueFunction(function=_launch_driver),
        ]
    )