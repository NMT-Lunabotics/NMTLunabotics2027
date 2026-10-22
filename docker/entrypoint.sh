#!/usr/bin/env bash
set -e

source "/opt/ros/${ROS_DISTRO:-humble}/setup.bash"

LIVOX_SETUP="/opt/nmt/livox_ws/install/setup.bash"
if [[ -f "$LIVOX_SETUP" ]]; then
    source "$LIVOX_SETUP"
fi

REALSENSE_SETUP="/opt/nmt/realsense_ws/install/setup.bash"
if [[ -f "$REALSENSE_SETUP" ]]; then
    source "$REALSENSE_SETUP"
fi

WORKSPACE_SETUP="/opt/nmt/ros2_ws/install/local_setup.bash"
if [[ -f "$WORKSPACE_SETUP" ]]; then
    source "$WORKSPACE_SETUP"
fi

exec "$@"