ARG ROS_DISTRO=humble
FROM ros:${ROS_DISTRO}-ros-base

ENV ROS_DISTRO=${ROS_DISTRO}
ENV ROS_DOMAIN_ID=42
ENV ROS_LOG_DIR=/root/.ros/log

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        python3-colcon-common-extensions \
        ros-${ROS_DISTRO}-launch \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/nmt/ros2_ws
COPY ros2_ws/src ./src

RUN /bin/bash -c \
    'source /opt/ros/${ROS_DISTRO}/setup.bash && colcon build --symlink-install'

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]