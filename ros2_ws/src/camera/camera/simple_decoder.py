#!/usr/bin/env python3
import av, cv2, rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage

class Viewer(Node):
    def __init__(self):
        super().__init__("simple_decoder")
        self.decoder=av.CodecContext.create("hevc", "r")
        self.create_subscription(CompressedImage, "/stream/compressed", self.on_image, qos_profile_sensor_data)

    def on_image(self, msg):
        try:
            for frame in self.decoder.decode(av.Packet(bytes(msg.data))):
                cv2.imshow("stream", frame.to_ndarray(format="bgr24"))
                cv2.waitKey(1)
        except av.AVError:
            pass

rclpy.init()
rclpy.spin(Viewer())