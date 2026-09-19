#!/usr/bin/env python3

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Imu
import numpy as np
from scipy.spatial.transform import Rotation as R

GRAVITY = np.array([0.0, 0.0, 9.81])

class ImuPoseEstimater(Node):
    def __init__(self):

        # Initalize node and create IMU subscription 
        super().__init__("VIO_node")
        self.subscription = self.create_subscription(Imu,"/camera/imu/data",self.imu_callback,10)

        # Variables that store past IMU data
        self.orientation=R.identity()
        self.velocity=np.zeros(3)
        self.position=np.zeros(3)
        self.last_time=None

        # Variables that store currrent IMU data
        self.angular_acceleration=np.zeros(3)
        self.linear_acceleration=np.zeros(3)

    def imu_callback(self, msg):
        # Pull new IMU data
        timestamp=msg.header.stamp.sec+msg.header.stamp.nanosec*1e-9
        gyroscope=np.array([msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z])
        accelerometer=np.array([msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z])

        # Push new imu data
        if np.any(gyroscope!=0.0): self.angular_acceleration=gyroscope
        if np.any(accelerometer!=0.0): self.linear_acceleration=accelerometer

        # Create dt, the time period between IMU readings
        if self.last_time is None:
            self.last_time=timestamp
            return
        dt=timestamp-self.last_time
        self.last_time=timestamp
        if dt<=0: return

        # Apply new rotation with time factor to previus rotation to get a new estimated rotation vector
        angle=np.linalg.norm(self.angular_acceleration)*dt
        if angle > 0:
            axis=self.angular_acceleration/np.linalg.norm(self.angular_acceleration)
            delta_rotation=R.from_rotvec(axis*angle)
            self.orientation=self.orientation*delta_rotation

        # Create a world acceleration estimate with gravity removed
        world_acceleration=self.orientation.apply(self.linear_acceleration)
        world_acceleration=world_acceleration-GRAVITY

        # Intergrate acceleration and velocity to get a position estimate 
        self.position+=self.velocity*dt
        self.velocity+=world_acceleration*dt

        self.get_logger().info(f"pos: {self.position}, vel: {self.velocity}")


def main():
    rclpy.init()
    node = ImuPoseEstimater()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()