# NMTLunabotics2027

Software workspace for the 2027 New Mexico Tech Lunabotics excavating robot.

The project uses ROS 2 Humble in Docker. The Jetson Orin Nano is the robot host: connect to it over SSH, then build and run the container on the Jetson so ROS nodes can access the robot's attached hardware. The container is headless by default. Visualization and future operator controls are developed separately from motor and sensor drivers.

## Repository Layout

- `docker/` contains the Humble image, entrypoint, and container command wrapper.
- `ros2_ws/src/` contains ROS 2 packages. `robot_bringup` provides a hardware-free smoke test; `sensor_bringup` launches the Livox MID-360 and Intel RealSense D435.
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

The image builds for the host's native architecture. Build on the Jetson for native Orin deployment; cross-platform builds are not configured yet. The image targets ROS 2 Humble. JetPack-specific GPU support is not enabled.

For the shared robot, SSH into the Jetson first, then run the commands from the checked-out repository there. See [docs/sensor-setup.md](docs/sensor-setup.md) before launching either sensor. These launches start sensors only; motor control and excavation actuators remain disabled until their controller interfaces and emergency stop are defined.

## Current Milestone

The sensor image pins Livox SDK2 `v1.2.5` and Livox ROS driver `1.2.4`; the RealSense ROS 2 Humble wrapper is installed from ROS packages. Before robot deployment, verify the exact JetPack/L4T version and test both sensors on the Orin Nano. The next hardware milestone is the motor-controller/E-stop interface, then base control and the RPLiDAR S3 with isolated power.



