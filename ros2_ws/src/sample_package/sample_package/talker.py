#!/usr/bin/env python3
import rclpy
import random
from rclpy.node import Node
from std_msgs.msg import Float32

class Talker(Node):
    def __init__(self):
        super().__init__('talker')
        self.publisher = self.create_publisher(Float32, 'talker', 10)
        self.timer = self.create_timer(0.5, self.publish_message)
    def publish_message(self):
        msg = Float32()
        msg.data = random.random()
        self.publisher.publish(msg)


class Talker2(Node):
    def __init__(self):
        super().__init__('talker2')
        self.publisher = self.create_publisher(Float32, 'talker2', 10)
        self.timer = self.create_timer(0.5, self.publish_message)
    def publish_message(self):
        msg = Float32()
        msg.data = random.random()
        self.publisher.publish(msg)

def main(args=None):
    rclpy.init(args=args)
    node = Talker()
    node2 = Talker2()
    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)
    executor.add_node(node2)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        node2.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()