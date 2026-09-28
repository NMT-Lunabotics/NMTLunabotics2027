#!/usr/bin/env bash
set -Eeuo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd -- "$SCRIPT_DIR/.." && pwd)"
IMAGE_NAME="${NMT_IMAGE_NAME:-nmtlunabotics2027/ros2:humble}"
CONTAINER_NAME="${NMT_CONTAINER_NAME:-nmtlunabotics2027-ros}"
ROS_DOMAIN_ID="${ROS_DOMAIN_ID:-42}"

BUILD_IMAGE=false
ACTION=""
COMMAND=""

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

Configuration:
  --ros-domain-id <id>    Set ROS_DOMAIN_ID (default: 42)
  -h, --help              Show this help

Examples:
  ./docker/start_docker.sh --build
  ./docker/start_docker.sh --smoke
  ./docker/start_docker.sh --command "ros2 pkg list"
  ./docker/start_docker.sh --stop

Run this script on the Jetson for access to robot-connected hardware. Hardware
launch modes will be added after the motor, E-stop, and sensor interfaces are
specified. Commands passed to --command are executed by bash inside the container.
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
    if container_exists; then
        local state
        state="$(docker container inspect --format '{{.State.Status}}' "$CONTAINER_NAME")"
        if [[ "$state" == running ]]; then
            return
        fi
        docker rm "$CONTAINER_NAME" >/dev/null
    fi

    if ! image_exists; then
        printf 'Docker image %s is missing. Build it with --build first.\n' "$IMAGE_NAME" >&2
        exit 1
    fi

    docker volume create nmtlunabotics2027-ros-logs >/dev/null
    docker run --detach \
        --name "$CONTAINER_NAME" \
        --network host \
        --env "ROS_DOMAIN_ID=$ROS_DOMAIN_ID" \
        --volume nmtlunabotics2027-ros-logs:/root/.ros/log \
        "$IMAGE_NAME" \
        tail -f /dev/null >/dev/null
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
    command)
        docker exec --interactive --tty "$CONTAINER_NAME" \
            /entrypoint.sh bash -lc "$COMMAND"
        ;;
esac