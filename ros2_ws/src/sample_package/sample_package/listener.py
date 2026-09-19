#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

class Listener(Node):
    def __init__(self):
        super().__init__('listener')
        self.subscription = self.create_subscription(Float32,'talker',self.listener_callback,10)
        self.subscription2 = self.create_subscription(Float32,'talker2',self.listener_callback2,10)
    def listener_callback(self, msg):
        self.get_logger().info(f'1: {msg.data}')
    def listener_callback2(self, msg):
            self.get_logger().info(f'2: {msg.data}')

def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()