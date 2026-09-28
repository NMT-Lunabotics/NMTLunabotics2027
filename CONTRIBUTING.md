# Contributing

## Changes

- Work on a feature branch and open a pull request into `main`.
- Keep pull requests focused and request review from the owner of the affected package or subsystem.
- Do not commit passwords, SSH keys, `.env` files, bag recordings, generated ROS build output, or machine-specific device paths.
- Update package documentation and tests when changing a ROS interface, launch mode, parameter, or hardware behavior.

## Shared Robot

The Jetson is shared hardware. Coordinate a test session before deploying or commanding actuators. Deploy only reviewed revisions, record the tested commit, and tell the next operator when the robot is available. Never test motor commands until the physical emergency stop and controller watchdog have been verified.

## ROS Workspace

ROS packages live under `ros2_ws/src/`. Build the container with `./docker/start_docker.sh --build`, then run the hardware-free check with `./docker/start_docker.sh --smoke`. Hardware launch modes are added only with a documented device, safety, and acceptance-test procedure.