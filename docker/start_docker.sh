#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${NMT_IMAGE_NAME:-nmtlunabotics2027/ros2:sensors-humble}"
CONTAINER_NAME="${NMT_CONTAINER_NAME:-nmtlunabotics2027-ros}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"
LIVOX_HOST_IP="${LIVOX_HOST_IP:-}"
LIVOX_LIDAR_IP="${LIVOX_LIDAR_IP:-}"
LIVOX_BROADCAST_CODE="${LIVOX_BROADCAST_CODE:-}"

BUILD_IMAGE=false
ACTION=""
COMMAND=""
REQUIRED_CAPABILITIES=()

usage() {
    cat <<'USAGE'
Usage: ./docker/start_docker.sh [OPTIONS]

Container operations:
  --build                 Build the Humble image (and replace its stopped container)
  --stop                  Stop the project container
  --restart               Restart the project container

Workspace operations:
  --shell                 Open an interactive shell (the default)
  --smoke                 Run the hardware-free ROS launch smoke test
  --command <command>     Run a command inside the container

Sensor operations (run these on the Jetson):
    --mid360                Start the Livox MID-360 driver
    --d435                  Start the Intel RealSense D435
    --sensors               Start both sensors

Configuration:
  --ros-domain-id <id>    Set ROS_DOMAIN_ID (default: 42)
    --host-ip <ipv4>        Jetson address on the MID-360 Ethernet link
    --lidar-ip <ipv4>       MID-360 address on its Ethernet link
    --broadcast-code <code> MID-360 broadcast code from its device label
  -h, --help              Show this help

Examples:
  ./docker/start_docker.sh --build
  ./docker/start_docker.sh --smoke
    ./docker/start_docker.sh --mid360 --host-ip 192.168.1.5 --lidar-ip 192.168.1.12 --broadcast-code <code>
    ./docker/start_docker.sh --d435
    ./docker/start_docker.sh --sensors --host-ip 192.168.1.5 --lidar-ip 192.168.1.12 --broadcast-code <code>
  ./docker/start_docker.sh --command "ros2 pkg list"
  ./docker/start_docker.sh --stop

Run sensor modes on the Jetson. The D435 mode requires host udev permissions and
mounts only the USB bus. Livox IPs must match the team's dedicated Ethernet setup.
Commands passed to --command are executed by bash inside the container.
USAGE
}

set_action() {
    if [[ -n "$ACTION" ]]; then
        printf 'Only one workspace operation can be selected.\n' >&2
        exit 2
    fi
    ACTION="$1"
}

while (($# > 0)); do
    case "$1" in
        --build)
            BUILD_IMAGE=true
            shift
            ;;
        --stop)
            set_action stop
            shift
            ;;
        --restart)
            set_action restart
            shift
            ;;
        --shell)
            set_action shell
            shift
            ;;
        --smoke)
            set_action smoke
            shift
            ;;
        --mid360)
            set_action mid360
            REQUIRED_CAPABILITIES+=(livox)
            shift
            ;;
        --d435)
            set_action d435
            REQUIRED_CAPABILITIES+=(realsense)
            shift
            ;;
        --sensors)
            set_action sensors
            REQUIRED_CAPABILITIES+=(livox realsense)
            shift
            ;;
        --command)
            if (($# < 2)); then
                printf '%s\n' '--command requires a command string.' >&2
                exit 2
            fi
            set_action command
            COMMAND="$2"
            shift 2
            ;;
        --ros-domain-id)
            if (($# < 2)); then
                printf '%s\n' '--ros-domain-id requires an integer.' >&2
                exit 2
            fi
            ROS_DOMAIN_ID="$2"
            shift 2
            ;;
        --host-ip)
            if (($# < 2)); then
                printf '%s\n' '--host-ip requires an IPv4 address.' >&2
                exit 2
            fi
            LIVOX_HOST_IP="$2"
            shift 2
            ;;
        --lidar-ip)
            if (($# < 2)); then
                printf '%s\n' '--lidar-ip requires an IPv4 address.' >&2
                exit 2
            fi
            LIVOX_LIDAR_IP="$2"
            shift 2
            ;;
        --broadcast-code)
            if (($# < 2)); then
                printf '%s\n' '--broadcast-code requires a value.' >&2
                exit 2
            fi
            LIVOX_BROADCAST_CODE="$2"
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            printf 'Unknown option: %s\n' "$1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

if [[ ! "$ROS_DOMAIN_ID" =~ ^[0-9]+$ ]] || ((ROS_DOMAIN_ID > 232)); then
    printf 'ROS_DOMAIN_ID must be an integer from 0 to 232.\n' >&2
    exit 2
fi

container_exists() {
    docker container inspect "$CONTAINER_NAME" >/dev/null 2>&1
}

image_exists() {
    docker image inspect "$IMAGE_NAME" >/dev/null 2>&1
}

build_image() {
    if container_exists; then
        local state
        state="$(docker container inspect --format '{{.State.Status}}' "$CONTAINER_NAME")"
        if [[ "$state" == running ]]; then
            printf 'Container %s is running. Stop it explicitly before rebuilding.\n' "$CONTAINER_NAME" >&2
            exit 1
        fi
        docker rm "$CONTAINER_NAME" >/dev/null
    fi
    docker build \
        --build-arg ROS_DISTRO=humble \
        --file "$SCRIPT_DIR/Dockerfile" \
        --tag "$IMAGE_NAME" \
        "$REPO_ROOT"
}

start_container() {
    local requested_profile=""
    local existing_profile=""
    local capability
    local has_capability=true
    for capability in "${REQUIRED_CAPABILITIES[@]}"; do
        requested_profile+="${requested_profile:+,}$capability"
    done

    if container_exists; then
        local state
        state="$(docker container inspect --format '{{.State.Status}}' "$CONTAINER_NAME")"
        existing_profile="$(docker container inspect \
            --format '{{index .Config.Labels "nmt.sensor-profile"}}' "$CONTAINER_NAME")"
        for capability in "${REQUIRED_CAPABILITIES[@]}"; do
            case ",$existing_profile," in
                *,"$capability",*) ;;
                *) has_capability=false ;;
            esac
        done
        if [[ "$state" == running ]]; then
            if [[ "$has_capability" == true ]]; then
                return
            fi
            printf 'Container %s is running without requested sensor access (%s). Stop it and start the sensor mode again.\n' \
                "$CONTAINER_NAME" "$requested_profile" >&2
            exit 1
        fi
        if [[ "$has_capability" == true ]]; then
            docker start "$CONTAINER_NAME" >/dev/null
            return
        fi
        docker rm "$CONTAINER_NAME" >/dev/null
    fi

    if ! image_exists; then
        printf 'Docker image %s is missing. Build it with --build first.\n' "$IMAGE_NAME" >&2
        exit 1
    fi

    docker volume create nmtlunabotics2027-ros-logs >/dev/null
    local -a docker_run_args=(
        --name "$CONTAINER_NAME" \
        --network host \
        --env "ROS_DOMAIN_ID=$ROS_DOMAIN_ID" \
        --volume nmtlunabotics2027-ros-logs:/root/.ros/log \
        --label "nmt.sensor-profile=$requested_profile"
    )

    if [[ ",$requested_profile," == *,livox,* ]]; then
        if [[ -z "$LIVOX_HOST_IP" || -z "$LIVOX_LIDAR_IP" || -z "$LIVOX_BROADCAST_CODE" ]]; then
            printf 'MID-360 mode requires --host-ip, --lidar-ip, and --broadcast-code (or the corresponding LIVOX_* environment variables).\n' >&2
            exit 2
        fi
        docker_run_args+=(
            --env "LIVOX_HOST_IP=$LIVOX_HOST_IP"
            --env "LIVOX_LIDAR_IP=$LIVOX_LIDAR_IP"
            --env "LIVOX_BROADCAST_CODE=$LIVOX_BROADCAST_CODE"
        )
    fi

    if [[ ",$requested_profile," == *,realsense,* ]]; then
        if [[ ! -d /dev/bus/usb ]]; then
            printf 'No /dev/bus/usb found. Connect the D435 to the Jetson first.\n' >&2
            exit 1
        fi
        docker_run_args+=(
            --device-cgroup-rule='c 189:* rmw'
            --volume /dev/bus/usb:/dev/bus/usb:rw
        )
        if [[ -d /run/udev ]]; then
            docker_run_args+=(--volume /run/udev:/run/udev:ro)
        fi
    fi

    docker run --detach "${docker_run_args[@]}" \
        "$IMAGE_NAME" tail -f /dev/null >/dev/null
}

if [[ "$BUILD_IMAGE" == true ]]; then
    build_image
    if [[ -z "$ACTION" ]]; then
        exit 0
    fi
fi

case "$ACTION" in
    stop)
        if container_exists; then
            docker stop "$CONTAINER_NAME"
        else
            printf 'Container %s does not exist.\n' "$CONTAINER_NAME"
        fi
        exit 0
        ;;
    restart)
        if container_exists; then
            docker restart "$CONTAINER_NAME"
        else
            start_container
        fi
        exit 0
        ;;
esac

if [[ -z "$ACTION" ]]; then
    ACTION=shell
fi

start_container

case "$ACTION" in
    shell)
        docker exec --interactive --tty "$CONTAINER_NAME" /entrypoint.sh bash
        ;;
    smoke)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh ros2 launch robot_bringup smoke_test.launch.py
        ;;
    mid360)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh ros2 launch sensor_bringup livox_mid360.launch.py
        ;;
    d435)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh ros2 launch sensor_bringup realsense_d435.launch.py
        ;;
    sensors)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh ros2 launch sensor_bringup all_sensors.launch.py
        ;;
    command)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh bash -lc "$COMMAND"
        ;;
esac