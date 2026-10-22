# Livox MID-360 and RealSense D456

The Docker image targets ROS 2 Humble and contains:

- Livox SDK2 `v1.2.5` and Livox ROS driver `1.2.4`, pinned to commit `b6ff7d1c8b210a96b74e919823771e1e32249758`.
- librealsense `v2.58.4` with the RSUSB backend and ROS 2 Humble wrapper `v4.58.4`, built from pinned upstream tags. RealSense lists D456 support starting with SDK `v2.58.4` and firmware `5.17.3.10` or later.
- `sensor_bringup` launch files for each sensor and both together.

The target is the NVIDIA Jetson AGX Orin Developer Kit, JetPack/L4T `36.4.7`, Ubuntu `22.04.5`, kernel `5.15.148-tegra`, `aarch64`. The image is built on the host architecture; it has not yet been built or hardware-tested on this Jetson. The RealSense SDK and wrapper compile from source in Docker, so allow adequate disk space. Check space before building:

```bash
df -h /
docker system df
docker builder du
```

Do not run `docker image prune` or `docker system prune`; no Docker images need to be deleted for this setup. If more space is required, review the build-cache report and optionally prune only old build cache with `docker builder prune --filter until=168h`. This preserves images and prompts before deleting cache.

## Livox MID-360 Ethernet

The MID-360 communicates over Ethernet/UDP, not USB. The Jetson must have an Ethernet interface connected to the LiDAR. The team's network setup must provide a stable IPv4 address for that Jetson interface and the LiDAR's IPv4 address on the same link. Do not copy the documentation example addresses into production unless they match the team's configured network.

The launch file reads the IP values and broadcast code at startup and renders an untracked temporary JSON config from `config/MID360_config.json.in`. Read the broadcast code from the MID-360 label/configuration. The upstream MID-360 port values stay in the template; extrinsics are initially zero and must be calibrated after mounting.

On the Jetson, first verify the interface and route with the team-approved network configuration. Then build the image and launch only the Livox driver:

```bash
./docker/start_docker.sh --build
./docker/start_docker.sh --mid360 \
  --host-ip <JETSON_LIVOX_INTERFACE_IPV4> \
  --lidar-ip <MID360_IPV4> \
  --broadcast-code <MID360_BROADCAST_CODE>
```

The values can instead be provided through `LIVOX_HOST_IP`, `LIVOX_LIDAR_IP`, and `LIVOX_BROADCAST_CODE`. Do not commit the actual team IPs or device code to this repository. To change configuration after the container has started, stop it and start the sensor mode again so the new values enter the container.

Verify that the driver node is present, list the point-cloud and IMU topics, and confirm the reported point-cloud frame is `livox_frame`:

```bash
./docker/start_docker.sh --command "ros2 node list"
./docker/start_docker.sh --command "ros2 topic list"
./docker/start_docker.sh --command "ros2 topic hz <point-cloud-topic-from-topic-list>"
```

Validate UDP reception and point-cloud continuity while the robot network is under normal load.

## RealSense D456 USB

The device label and USB ID `8086:0b5c` identify the camera as a D456. It connects to the Jetson over USB 3. Run the RealSense udev setup on the **Jetson host**, not inside Docker. The project image maps `/dev/bus/usb` only when D456 mode is selected; the host still controls USB device permissions and kernel drivers. The observed topology currently reports `480M` through a USB 2 hub; move the camera to a USB 3-capable port/cable and confirm `lsusb -t` reports `5000M` or faster before streaming tests.

On the Jetson host, using the matching RealSense SDK source release as the rule source:

1. Check that the camera is connected directly to a USB 3-capable port and is visible to the host with `lsusb`; confirm `lsusb -t` reports `5000M` or faster.
2. Follow the official [RealSense Jetson guide](https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md) for the installed JetPack/L4T release. The SDK is built in the project image; the host needs the USB udev rules and compatible kernel support, not a separately installed ROS wrapper.
3. Obtain the matching v2.58.4 rule source and its helper dependency:

  ```bash
  sudo apt-get install v4l-utils
  git clone --depth 1 --branch v2.58.4 https://github.com/realsenseai/librealsense.git /tmp/librealsense-rules
  cd /tmp/librealsense-rules
  sudo ./scripts/setup_udev_rules.sh
  ```

  Review the official script before running it with elevated privileges. It may ask you to disconnect attached RealSense cameras while installing rules. It installs the upstream USB rules on the **host**; after it completes, reconnect the D456 and verify it appears in `lsusb` and the host device list.
4. The image builds librealsense with the user-space RSUSB backend and does not patch the Jetson kernel. Do not apply kernel patches unless testing shows they are required and the team approves the change.

Launch the camera independently:

```bash
./docker/start_docker.sh --d456
```

The default launch enables color and depth at 640x480x30, synchronizes the streams, aligns depth to color, enables the point-cloud filter, and publishes diagnostics. These are a conservative starting profile, not a claim that the selected USB cable, hub, Jetson port, or system load has passed validation. If bandwidth or compute is constrained, lower the profile or disable point-cloud generation in the launch configuration.

Verify node and topic discovery from the container:

```bash
./docker/start_docker.sh --command "ros2 node list"
./docker/start_docker.sh --command "ros2 topic list"
./docker/start_docker.sh --command "ros2 topic hz /camera/d456/depth/image_rect_raw"
./docker/start_docker.sh --command "ros2 topic echo /diagnostics --once"
```

Expected image topics include `/camera/d456/color/image_raw`, `/camera/d456/depth/image_rect_raw`, and `/camera/d456/aligned_depth_to_color/image_raw`. Confirm actual topic names, firmware version, and frame IDs with the running camera; topic layout can vary with wrapper version.

## Start Both Sensors

After each sensor succeeds independently, start them together. Supply the actual IPs for the dedicated Livox link:

```bash
./docker/start_docker.sh --sensors \
  --host-ip <JETSON_LIVOX_INTERFACE_IPV4> \
  --lidar-ip <MID360_IPV4> \
  --broadcast-code <MID360_BROADCAST_CODE>
```

The Livox driver receives UDP over host networking; the RealSense driver receives only the USB bus mapping and USB device cgroup access. The container profile is fixed at creation. To add a missing hardware capability to an existing container, stop it and start the desired sensor mode again.

## Acceptance Checks

1. Record the AGX Orin model, JetPack/L4T, kernel, D456 firmware, and USB connection speed.
2. Build the image natively on the Jetson and check `docker image inspect nmtlunabotics2027/ros2:sensors-humble --format '{{.Os}}/{{.Architecture}}'` reports `linux/arm64`.
3. Run the Livox test alone and verify UDP receipt, stable point-cloud frequency, IMU publication, and frame ID.
4. Run the D456 test alone and verify firmware is `5.17.3.10` or later, color/depth rates, aligned-depth topics, diagnostics, and no recurring USB reset/disconnect messages.
5. Run both together and record Jetson CPU, memory, temperature, USB stability, image rates, and Livox packet continuity.
6. Disconnect/reconnect the D456 and restart the Livox link deliberately; record whether each driver recovers or requires a container restart.
7. Repeat while motors are powered and moving. The known RPLiDAR dropout was diagnosed as a power brownout; this sensor stack must also pass a motor-load/power check. Do not modify the custom RPLiDAR ribbon cable, and use isolated sensor power where required.

## Known Gates

- The AGX Orin reports JetPack/L4T `36.4.7`; the image still needs a native ARM64 build and hardware run on that target.
- The team-specific MID-360 IPs and network configuration are intentionally not committed here.
- Real hardware is needed to confirm USB permissions, USB 3 throughput, camera firmware behavior, and MID-360 UDP reception.
- These sensor launches do not start motors, teleoperation, SLAM, or Nav2.
