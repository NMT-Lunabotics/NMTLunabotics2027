# NMTLunabotics2027

Software workspace for the 2027 New Mexico Tech Lunabotics excavating robot.

The project uses ROS 2 Humble in Docker. The Jetson Orin Nano is the robot host: connect to it over SSH, then build and run the container on the Jetson so ROS nodes can access the robot's attached hardware. The container is headless by default. Visualization and future operator controls are developed separately from motor and sensor drivers.

## Repository Layout

- `docker/` contains the Humble image, entrypoint, and container command wrapper.
- `ros2_ws/src/` contains ROS 2 packages. `robot_bringup` currently provides a hardware-free launch smoke test.
- `scripts/` contains host setup and diagnostic helpers.
- `docs/` contains Jetson, SSH, networking, safety, and hardware procedures.
- `rviz2/` is reserved for shared visualization configurations.
- `operator_station/` is reserved for a workstation-side GUI.
- `Arduino/` is reserved for embedded controller firmware when that code is added.

See [docs/jetson-setup.md](docs/jetson-setup.md) and [docs/robot-operations.md](docs/robot-operations.md) for setup and operation. See [CONTRIBUTING.md](CONTRIBUTING.md) for the team workflow.

## Quick Start

On a Linux development machine with Docker installed:

```bash
./docker/start_docker.sh --build
./docker/start_docker.sh --smoke
```

The image builds for the host's native architecture. Build on the Jetson for native Orin deployment; cross-platform builds are not configured yet. The initial image targets ROS 2 Humble and does not assume JetPack-specific GPU support.

For the shared robot, SSH into the Jetson first, then run the same commands from the checked-out repository there. Do not start motors from this initial scaffold: only a smoke launch exists until the motor interface, emergency stop, and hardware permissions are specified.

## Current Milestone

This scaffold establishes the workspace and container workflow. The next hardware milestone is to confirm the JetPack/L4T version and motor-controller/E-stop interface, then add base control and the RPLiDAR S3 with a stable host device mapping and isolated sensor power.



