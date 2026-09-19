#!/usr/bin/env python3
import rclpy
import random
from rclpy.node import Node
from robot_interfaces.msg import Example

class Talker(Node):
    def __init__(self):
        super().__init__('talker_custom_datatype')
        self.publisher = self.create_publisher(Example, 'datastream', 10)
        self.timer = self.create_timer(0.5, self.publish_message)
    def publish_message(self):
        msg = Example()
        msg.voltage=random.random()
        msg.amperage=random.random()*10
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = Talker()

    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()