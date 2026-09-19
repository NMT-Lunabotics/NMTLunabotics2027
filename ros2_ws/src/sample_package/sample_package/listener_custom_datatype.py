#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from robot_interfaces.msg import Example

class Listener(Node):
    def __init__(self):
        super().__init__('listener_custom_datatype')
        self.subscription = self.create_subscription(Example,'datastream',self.listener_callback,10)
    def listener_callback(self, msg):
        self.get_logger().info(f'{msg.voltage} {msg.amperage}')

def main(args=None):
    rclpy.init(args=args)
    node = Listener()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()