import rclpy
from rclpy.node import Node
from sensor_msgs.msg import Image
from cv_bridge import CvBridge
import cv2

#TEMP
import numpy as np

# GUI Imports
from PyQt5.QtGui import QImage

class IntelSubscriber(Node):
    def __init__(self, send_image = None):
        # RGB Subscriber
        super().__init__('intel_subscriber')
        self.subscription_rgb = self.create_subscription(Image,"/rgb", self.rgb_frame_callback, 10)
        self.bridge_rgb = CvBridge()

        # Depth Subscriber
        self.subscription_depth = self.create_subscription(Image, "/depth", self.depth_frame_callback, 10)
        self.bridge_depth = CvBridge()

        self.send_image = send_image

    def rgb_frame_callback(self, data):
        self.get_logger().warning('Received RGB frame')
        current_frame = self.bridge_rgb.imgmsg_to_cv2(data)
        height, width, channels = current_frame.shape
        bytes_per_line = channels * width

        q_image = QImage(
            current_frame.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888).copy()

        if self.send_image:
            self.send_image("RGB", q_image) # Emit signal to GUI with QImage

    def depth_frame_callback(self, data):
        self.get_logger().warning('Received depth frame')

        current_depth = self.bridge_depth.imgmsg_to_cv2(data)
        print("Depth Range:", current_depth.min(), "to", current_depth.max())

        valid_mask = (current_depth >= 600) & (current_depth <= 6000)  
        depth_display = np.zeros_like(current_depth, dtype=np.uint8)

        valid_pixels = np.sum(valid_mask)
        print("Valid pixels:", valid_pixels, "/", current_depth.size,
            f"({100 * valid_pixels / current_depth.size:.1f}%)")

        depth_display[valid_mask] = np.clip(
            (current_depth[valid_mask].astype(np.float32) - 600) * 255 / (2000 - 600), 0, 255
        ).astype(np.uint8)

        print("Display range:", depth_display.min(), "to", depth_display.max())
        
        depth_colored = cv2.applyColorMap(
            depth_display,
            cv2.COLORMAP_JET)

        # convert BGR to RGB
        depth_colored = cv2.cvtColor(depth_colored, cv2.COLOR_BGR2RGB)
        height, width, channels = depth_colored.shape
        bytes_per_line = channels * width

        q_image = QImage(
            depth_colored.data,
            width,
            height,
            bytes_per_line,
            QImage.Format_RGB888).copy()

        valid_depth = current_depth[valid_mask]

        if valid_depth.size > 0:
            print(
                "Depth:",
                "min =", valid_depth.min(),
                "median =", np.median(valid_depth),
                "max =", valid_depth.max())
        else:
            print("Depth: NO VALID PIXELS")
    
        if self.send_image:
            self.send_image("DEPTH", q_image) # Emit signal to GUI with QImage

def main(args=None):
    rclpy.init(args=args)
    intel_subscriber = IntelSubscriber()
    rclpy.spin(intel_subscriber)

    intel_subscriber.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()