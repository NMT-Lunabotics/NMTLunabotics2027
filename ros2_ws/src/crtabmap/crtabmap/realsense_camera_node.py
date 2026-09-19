#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
import pyrealsense2 as rs
import numpy as np
from sensor_msgs.msg import Image, CameraInfo, Imu
from cv_bridge import CvBridge


class RealsenseNode(Node):
    def __init__(self):
        super().__init__("realsense_camera_node")

        self.declare_parameter("enable_color", True)
        self.declare_parameter("enable_depth", True)
        self.declare_parameter("enable_infra1", True)
        self.declare_parameter("enable_infra2", True)
        self.declare_parameter("enable_gyro", True)
        self.declare_parameter("enable_accel", True)

        self.enable_color = self.get_parameter("enable_color").value
        self.enable_depth = self.get_parameter("enable_depth").value
        self.enable_infra1 = self.get_parameter("enable_infra1").value
        self.enable_infra2 = self.get_parameter("enable_infra2").value
        self.enable_gyro = self.get_parameter("enable_gyro").value
        self.enable_accel = self.get_parameter("enable_accel").value
        self.enable_imu = self.enable_gyro or self.enable_accel

        self.bridge = CvBridge()

        self.pipeline = rs.pipeline()
        config = rs.config()

        if self.enable_color:
            config.enable_stream(rs.stream.color, 640, 480, rs.format.bgr8, 30)
        if self.enable_depth:
            config.enable_stream(rs.stream.depth, 640, 480, rs.format.z16, 30)
        if self.enable_infra1:
            config.enable_stream(rs.stream.infrared, 1, 640, 480, rs.format.y8, 30)
        if self.enable_infra2:
            config.enable_stream(rs.stream.infrared, 2, 640, 480, rs.format.y8, 30)
        if self.enable_gyro:
            config.enable_stream(rs.stream.gyro)
        if self.enable_accel:
            config.enable_stream(rs.stream.accel)

        self.profile = self.pipeline.start(config)

        if self.enable_color:
            self.color_intrinsics = self.profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
            self.rgb_pub = self.create_publisher(Image, "/camera/color/image_raw", 10)
            self.rgb_info_pub = self.create_publisher(CameraInfo, "/camera/color/camera_info", 10)

        if self.enable_depth:
            self.depth_intrinsics = self.profile.get_stream(rs.stream.depth).as_video_stream_profile().get_intrinsics()
            self.depth_pub = self.create_publisher(Image, "/camera/depth/image_raw", 10)
            self.depth_info_pub = self.create_publisher(CameraInfo, "/camera/depth/camera_info", 10)

        if self.enable_infra1:
            self.infra1_intrinsics = self.profile.get_stream(rs.stream.infrared, 1).as_video_stream_profile().get_intrinsics()
            self.infra1_pub = self.create_publisher(Image, "/camera/infra1/image_raw", 10)
            self.infra1_info_pub = self.create_publisher(CameraInfo, "/camera/infra1/camera_info", 10)

        if self.enable_infra2:
            self.infra2_intrinsics = self.profile.get_stream(rs.stream.infrared, 2).as_video_stream_profile().get_intrinsics()
            self.infra2_pub = self.create_publisher(Image, "/camera/infra2/image_raw", 10)
            self.infra2_info_pub = self.create_publisher(CameraInfo, "/camera/infra2/camera_info", 10)

        if self.enable_imu:
            self.imu_pub = self.create_publisher(Imu, "/camera/imu/data", 10)

        self.timer = self.create_timer(1.0 / 30.0, self.update)

    def make_camera_info(self, intrinsics, stamp, frame_id):
        info = CameraInfo()
        info.width = intrinsics.width
        info.height = intrinsics.height
        info.distortion_model = "plumb_bob"
        info.k = [intrinsics.fx, 0.0, intrinsics.ppx, 0.0, intrinsics.fy, intrinsics.ppy, 0.0, 0.0, 1.0]
        info.d = list(intrinsics.coeffs)
        info.r = [1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0]
        info.p = [intrinsics.fx, 0.0, intrinsics.ppx, 0.0, 0.0, intrinsics.fy, intrinsics.ppy, 0.0, 0.0, 0.0, 1.0, 0.0]
        info.header.stamp = stamp
        info.header.frame_id = frame_id
        return info

    def update(self):
        frames = self.pipeline.wait_for_frames()
        stamp = self.get_clock().now().to_msg()

        if self.enable_imu:
            for frame in frames:
                if not frame.is_motion_frame():
                    continue
                motion = frame.as_motion_frame().get_motion_data()
                stream_type = frame.get_profile().stream_type()

                imu_msg = Imu()
                imu_msg.header.stamp = stamp
                imu_msg.header.frame_id = "camera"
                imu_msg.orientation_covariance[0] = -1

                if stream_type == rs.stream.gyro and self.enable_gyro:
                    imu_msg.angular_velocity.x = motion.x
                    imu_msg.angular_velocity.y = motion.y
                    imu_msg.angular_velocity.z = motion.z
                elif stream_type == rs.stream.accel and self.enable_accel:
                    imu_msg.linear_acceleration.x = motion.x
                    imu_msg.linear_acceleration.y = motion.y
                    imu_msg.linear_acceleration.z = motion.z
                else:
                    continue

                self.imu_pub.publish(imu_msg)

        if self.enable_color:
            color_frame = frames.get_color_frame()
            if color_frame:
                color_image = np.asanyarray(color_frame.get_data())
                color_msg = self.bridge.cv2_to_imgmsg(color_image, "bgr8")
                color_msg.header.stamp = stamp
                color_msg.header.frame_id = "camera"
                self.rgb_pub.publish(color_msg)
                self.rgb_info_pub.publish(self.make_camera_info(self.color_intrinsics, stamp, "camera"))

        if self.enable_depth:
            depth_frame = frames.get_depth_frame()
            if depth_frame:
                depth_image = np.asanyarray(depth_frame.get_data())
                depth_msg = self.bridge.cv2_to_imgmsg(depth_image, "mono16")
                depth_msg.header.stamp = stamp
                depth_msg.header.frame_id = "camera"
                self.depth_pub.publish(depth_msg)
                self.depth_info_pub.publish(self.make_camera_info(self.depth_intrinsics, stamp, "camera"))

        if self.enable_infra1:
            infra1_frame = frames.get_infrared_frame(1)
            if infra1_frame:
                infra1_image = np.asanyarray(infra1_frame.get_data())
                infra1_msg = self.bridge.cv2_to_imgmsg(infra1_image, "mono8")
                infra1_msg.header.stamp = stamp
                infra1_msg.header.frame_id = "camera"
                self.infra1_pub.publish(infra1_msg)
                self.infra1_info_pub.publish(self.make_camera_info(self.infra1_intrinsics, stamp, "camera"))

        if self.enable_infra2:
            infra2_frame = frames.get_infrared_frame(2)
            if infra2_frame:
                infra2_image = np.asanyarray(infra2_frame.get_data())
                infra2_msg = self.bridge.cv2_to_imgmsg(infra2_image, "mono8")
                infra2_msg.header.stamp = stamp
                infra2_msg.header.frame_id = "camera"
                self.infra2_pub.publish(infra2_msg)
                self.infra2_info_pub.publish(self.make_camera_info(self.infra2_intrinsics, stamp, "camera"))

    def destroy_node(self):
        self.pipeline.stop()
        super().destroy_node()


def main():
    rclpy.init()
    node = RealsenseNode()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()