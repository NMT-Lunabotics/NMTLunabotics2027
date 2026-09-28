# Robot Operations

## Connect to the Jetson

Use the team-provided hostname or address and your authorized SSH key. Example:

```bash
ssh <robot-user>@<jetson-host>
cd <path-to-NMTLunabotics2027>
```

Do not place team credentials or a private key in the repository. Before updating the shared robot, make sure nobody else is testing it and check the checkout:

```bash
git status --short --branch
git log -1 --oneline
```

Only update a clean checkout to an approved revision, for example with `git pull --ff-only`. Do not discard uncommitted changes to deploy another person's work.

## Build and Smoke Test

Build the image on the Jetson, then launch the hardware-free smoke test:

```bash
./docker/start_docker.sh --build
./docker/start_docker.sh --smoke
```

The first build downloads the ROS base image and packages and may take several minutes. The workspace is copied into the image, so changing ROS source requires rebuilding the image.

Open a shell or run a diagnostic command:

```bash
./docker/start_docker.sh
./docker/start_docker.sh --command "ros2 pkg list"
```

Stop the persistent container when finished:

```bash
./docker/start_docker.sh --stop
```

These commands do not start motors or sensors. No hardware launch mode is available until its driver, device mapping, safety behavior, and acceptance test are implemented. Never use an arbitrary ROS command to publish actuator commands.

## Logs and Runtime

The launcher creates a named container and a named Docker volume for ROS logs. Inspect state with `docker ps --filter name=nmtlunabotics2027-ros` and logs with `docker logs nmtlunabotics2027-ros`. The current smoke launch exits after reporting that the workspace is ready; it is not a robot runtime service.