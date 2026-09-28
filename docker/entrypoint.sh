#!/usr/bin/env bash
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"

WORKSPACE_SETUP="/opt/nmt/ros2_ws/install/setup.bash"
if [[ -f "$WORKSPACE_SETUP" ]]; then
    source "$WORKSPACE_SETUP"
fi

exec "$@"