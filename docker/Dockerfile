ARG ROS_DISTRO=humble
FROM ros:${ROS_DISTRO}-ros-base

ENV ROS_DISTRO=${ROS_DISTRO}
ENV ROS_DOMAIN_ID=42
ENV ROS_LOG_DIR=/root/.ros/log

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        build-essential \
        cmake \
        git \
        libapr1-dev \
        libboost-all-dev \
        libgl1-mesa-dev \
        libglu1-mesa-dev \
        libgtk-3-dev \
        libglfw3-dev \
        libssl-dev \
        libudev-dev \
        libusb-1.0-0-dev \
        pkg-config \
        python3-colcon-common-extensions \
        python3-rosdep \
        ros-${ROS_DISTRO}-launch \
        ros-${ROS_DISTRO}-ament-cmake-auto \
        ros-${ROS_DISTRO}-pcl-conversions \
        ros-${ROS_DISTRO}-pcl-ros \
        ros-${ROS_DISTRO}-rclcpp-components \
        ros-${ROS_DISTRO}-rosidl-default-generators \
    && rm -rf /var/lib/apt/lists/*

# Build the Livox SDK and driver in a separate workspace. The upstream
# build.sh removes its workspace build/install directories before compiling.
ARG LIVOX_SDK2_COMMIT=6a940156dd7151c3ab6a52442d86bc83613bd11b
RUN git clone https://github.com/Livox-SDK/Livox-SDK2.git /tmp/Livox-SDK2 \
    && git -C /tmp/Livox-SDK2 checkout "${LIVOX_SDK2_COMMIT}" \
    && cmake -S /tmp/Livox-SDK2 -B /tmp/Livox-SDK2/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_TESTING=OFF \
    && cmake --build /tmp/Livox-SDK2/build --parallel 2 \
    && cmake --install /tmp/Livox-SDK2/build \
    && ldconfig \
    && rm -rf /tmp/Livox-SDK2

ARG REALSENSE_SDK_VERSION=2.58.4
RUN git clone --depth 1 --branch "v${REALSENSE_SDK_VERSION}" \
        https://github.com/realsenseai/librealsense.git /tmp/librealsense \
    && cmake -S /tmp/librealsense -B /tmp/librealsense/build \
        -DCMAKE_BUILD_TYPE=Release \
        -DBUILD_EXAMPLES=OFF \
        -DBUILD_GRAPHICAL_EXAMPLES=OFF \
        -DBUILD_TOOLS=OFF \
        -DBUILD_UNIT_TESTS=OFF \
        -DBUILD_PYTHON_BINDINGS=OFF \
        -DBUILD_WITH_CUDA=OFF \
        -DBUILD_WITH_DDS=OFF \
        -DFORCE_RSUSB_BACKEND=ON \
    && cmake --build /tmp/librealsense/build --parallel 2 \
    && cmake --install /tmp/librealsense/build \
    && ldconfig \
    && rm -rf /tmp/librealsense

ARG REALSENSE_ROS_VERSION=4.58.4
RUN mkdir -p /opt/nmt/realsense_ws/src \
    && git clone --depth 1 --branch "v${REALSENSE_ROS_VERSION}" \
        https://github.com/realsenseai/realsense-ros.git \
        /opt/nmt/realsense_ws/src/realsense-ros \
    && rosdep install \
        --from-paths \
            /opt/nmt/realsense_ws/src/realsense-ros/realsense2_camera \
            /opt/nmt/realsense_ws/src/realsense-ros/realsense2_camera_msgs \
            /opt/nmt/realsense_ws/src/realsense-ros/realsense2_description \
        --ignore-src \
        --rosdistro ${ROS_DISTRO} \
        --skip-keys=librealsense2 \
        -y \
    && /bin/bash -c 'source /opt/ros/${ROS_DISTRO}/setup.bash \
        && cd /opt/nmt/realsense_ws \
        && colcon build --packages-up-to realsense2_camera \
            --cmake-args -DCMAKE_BUILD_TYPE=Release -DBUILD_TESTING=OFF \
        && source install/setup.bash \
        && ros2 pkg prefix realsense2_camera'

ARG LIVOX_DRIVER2_COMMIT=b6ff7d1c8b210a96b74e919823771e1e32249758
RUN mkdir -p /opt/nmt/livox_ws/src \
    && git clone https://github.com/Livox-SDK/livox_ros_driver2.git \
        /opt/nmt/livox_ws/src/livox_ros_driver2 \
    && git -C /opt/nmt/livox_ws/src/livox_ros_driver2 checkout "${LIVOX_DRIVER2_COMMIT}" \
    && /bin/bash -c 'source /opt/ros/${ROS_DISTRO}/setup.bash \
        && cd /opt/nmt/livox_ws/src/livox_ros_driver2 \
        && ./build.sh humble \
        && source /opt/nmt/livox_ws/install/setup.bash \
        && ros2 pkg prefix livox_ros_driver2'

WORKDIR /opt/nmt/ros2_ws
COPY ros2_ws/src ./src
COPY ros2_ws/src/sensor_bringup ./src/sensor_bringup

RUN rosdep update \
    && rosdep install --from-paths src --ignore-src --rosdistro ${ROS_DISTRO} \
    --skip-keys="livox_ros_driver2 realsense2_camera librealsense2" -y \
    && /bin/bash -c \
        'source /opt/ros/${ROS_DISTRO}/setup.bash \
        && source /opt/nmt/livox_ws/install/setup.bash \
        && source /opt/nmt/realsense_ws/install/setup.bash \
        && colcon build --symlink-install'

COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod 0755 /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
CMD ["bash"]