# Jetson Setup

## Platform Record

The reported target is an NVIDIA Jetson AGX Orin Developer Kit, JetPack/L4T 36.4.7, Ubuntu 22.04.5, kernel 5.15.148-tegra, and aarch64. Record the actual values after system updates. The sensor image uses ROS 2 Humble `ros-base`; it does not enable CUDA or request the NVIDIA container runtime. D456 streaming and Livox MID-360 networking still require on-device validation.

## Host Preparation

1. Install the JetPack release approved for the robot and record its version in the team hardware notes.
2. Install Docker using the supported Jetson/Ubuntu procedure for that JetPack release. Do not install a generic NVIDIA runtime or change the host's CUDA libraries without confirming compatibility.
3. Verify `docker run --rm hello-world` works for the deployment user. Membership in the `docker` group effectively grants root-level control of the host; restrict membership to trusted robot operators.
4. Configure SSH key authentication for authorized team members and set a stable hostname or DHCP reservation on the robot network. Do not commit private keys or passwords.
5. Configure the robot LAN/VPN and firewall with the operator-network plan in [networking.md](networking.md).
6. The team owns the Wi-Fi and robot network setup. Coordinate with the network owner for its IPs and routes; do not apply generic static-IP or NetworkManager instructions.
7. Install the official RealSense host udev rules before starting the D456 driver. Follow [sensor-setup.md](sensor-setup.md) and verify the camera is visible to the Jetson host first. Install other udev rules only after the device IDs are recorded; do not use `chmod 777` as an improvised permanent fix.
8. Check free disk space before building. Docker images and builder cache are separate; do not remove images to make room. If necessary, inspect and prune only old builder cache as described in [sensor-setup.md](sensor-setup.md).
9. Confirm persistent storage for Docker images, ROS logs, and future rosbag recordings. Keep recordings off the container's writable layer.

## Initial Image Check

From the repository on the Jetson:

```bash
docker version
uname -m
cat /etc/nv_tegra_release
./docker/start_docker.sh --build
./docker/start_docker.sh --smoke
```

The build is native to the host architecture. Sensor modes add permissions only when requested: the D456 mode maps the USB bus; the MID-360 mode uses host networking and the team's configured Ethernet link. No motor device, `/dev/mem`, GPIO, or entire `/dev` tree is exposed.