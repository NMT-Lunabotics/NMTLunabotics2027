# Livox MID-360 and RealSense D435

The Docker image targets ROS 2 Humble and contains:

- Livox SDK2 `v1.2.5` and Livox ROS driver `1.2.4`, pinned to commit `b6ff7d1c8b210a96b74e919823771e1e32249758`.
- ROS Humble's apt-managed `realsense2_camera` package and its librealsense dependency.
- `sensor_bringup` launch files for each sensor and both together.

The image is built on the host architecture. Build and validate it on the Orin Nano before robot use. The current development workstation image is `linux/amd64`; it is not evidence of ARM64 or JetPack compatibility.

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

## RealSense D435 USB

The D435 is connected to the Jetson over USB 3. Run the RealSense udev setup on the **Jetson host**, not inside Docker. The project image maps `/dev/bus/usb` only when the D435 mode is selected; the host still controls USB device permissions and kernel drivers.

On the Jetson host, using the matching RealSense SDK source release as the rule source:

1. Check that the camera is connected directly to a USB 3-capable port and is visible to the host with `lsusb`.
2. Follow the official [RealSense Jetson guide](https://github.com/realsenseai/librealsense/blob/master/doc/installation_jetson.md) for the installed JetPack/L4T release. Check the installed wrapper/SDK versions with `dpkg-query -W 'ros-humble-realsense2-camera' 'ros-humble-librealsense2*'`.
3. Obtain the matching v2.58.4 rule source and its helper dependency:

  ```bash
  sudo apt-get install v4l-utils
  git clone --depth 1 --branch v2.58.4 https://github.com/realsenseai/librealsense.git /tmp/librealsense-rules
  cd /tmp/librealsense-rules
  sudo ./scripts/setup_udev_rules.sh
  ```

  Review the official script before running it with elevated privileges. It may ask you to disconnect attached RealSense cameras while installing rules. It installs the upstream USB rules on the **host**; after it completes, reconnect the D435 and verify it appears in `lsusb` and the host device list.
4. Check Jetson kernel compatibility for the D435 and the chosen librealsense backend. The Docker image does not patch the Jetson kernel. Do not apply kernel patches unless host-level testing shows they are required and the team approves the change.

Launch the camera independently:

```bash
./docker/start_docker.sh --d435
```

The default launch enables color and depth at 640x480x30, synchronizes the streams, aligns depth to color, enables the point-cloud filter, and publishes diagnostics. These are a conservative starting profile, not a claim that the selected USB cable, hub, Jetson port, or system load has passed validation. If bandwidth or compute is constrained, lower the profile or disable point-cloud generation in the launch configuration.

Verify node and topic discovery from the container:

```bash
./docker/start_docker.sh --command "ros2 node list"
./docker/start_docker.sh --command "ros2 topic list"
./docker/start_docker.sh --command "ros2 topic hz /camera/d435/depth/image_rect_raw"
./docker/start_docker.sh --command "ros2 topic echo /diagnostics --once"
```

Expected image topics include `/camera/d435/color/image_raw`, `/camera/d435/depth/image_rect_raw`, and `/camera/d435/aligned_depth_to_color/image_raw`. Confirm actual topic names and frame IDs with the running camera; they may depend on wrapper version and launch namespace.

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

1. Record Jetson Orin Nano model, JetPack/L4T, kernel, camera firmware, and USB connection details.
2. Build the image natively on the Jetson and check `docker image inspect nmtlunabotics2027/ros2:sensors-humble --format '{{.Os}}/{{.Architecture}}'` reports `linux/arm64`.
3. Run the Livox test alone and verify UDP receipt, stable point-cloud frequency, IMU publication, and frame ID.
4. Run the D435 test alone and verify color/depth rates, aligned-depth topics, diagnostics, and no recurring USB reset/disconnect messages.
5. Run both together and record Jetson CPU, memory, temperature, USB stability, image rates, and Livox packet continuity.
6. Disconnect/reconnect the D435 and restart the Livox link deliberately; record whether each driver recovers or requires a container restart.
7. Repeat while motors are powered and moving. The known RPLiDAR dropout was diagnosed as a power brownout; this sensor stack must also pass a motor-load/power check. Do not modify the custom RPLiDAR ribbon cable, and use isolated sensor power where required.

## Known Gates

- The exact Orin Nano JetPack/L4T version is not recorded in the repository. The current container has not yet been built or run on that target.
- The team-specific MID-360 IPs and network configuration are intentionally not committed here.
- Real hardware is needed to confirm USB permissions, USB 3 throughput, camera firmware behavior, and MID-360 UDP reception.
- These sensor launches do not start motors, teleoperation, SLAM, or Nav2.
