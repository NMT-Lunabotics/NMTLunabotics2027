# Jetson Setup

## Platform Record

Before deploying robot hardware, record the exact Orin Nano module/devkit, JetPack release, L4T version, Ubuntu release, Docker version, and container architecture. The current Docker image is based on the official ROS 2 Humble `ros-base` image and does not enable CUDA or request the NVIDIA container runtime. Validate it on the target JetPack before adding camera or GPU workloads.

## Host Preparation

1. Install the JetPack release approved for the robot and record its version in the team hardware notes.
2. Install Docker using the supported Jetson/Ubuntu procedure for that JetPack release. Do not install a generic NVIDIA runtime or change the host's CUDA libraries without confirming compatibility.
3. Verify `docker run --rm hello-world` works for the deployment user. Membership in the `docker` group effectively grants root-level control of the host; restrict membership to trusted robot operators.
4. Configure SSH key authentication for authorized team members and set a stable hostname or DHCP reservation on the robot network. Do not commit private keys or passwords.
5. Configure the robot LAN/VPN and firewall with the operator-network plan in [networking.md](networking.md).
6. Install host udev rules only after each motor/sensor USB vendor, product, and serial identifier is recorded. Use stable aliases and grant only the required group access. Do not use `chmod 777` as a permanent device-permission solution.
7. Confirm persistent storage for Docker images, ROS logs, and future rosbag recordings. Keep recordings off the container's writable layer.

## Initial Image Check

From the repository on the Jetson:

```bash
docker version
uname -m
cat /etc/nv_tegra_release
./docker/start_docker.sh --build
./docker/start_docker.sh --smoke
```

The build is native to the host architecture. The current bootstrap deliberately does not expose `/dev`, `/dev/mem`, GPIO, I2C, video devices, or USB devices to the container. Add a narrowly scoped mapping only with the driver that needs it and after checking device permissions on the Jetson.