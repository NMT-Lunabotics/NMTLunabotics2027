import rclpy
import random
from rclpy.node import Node
from std_msgs.msg import Float32

class VoltageNode(Node):

    def __init__(self):
        super().__init__('voltage_node')

        self.voltage_pub = self.create_publisher(Float32, '/battery_voltage', 10)
        timer_period = 0.5 #seconds
        self.timer = self.create_timer(timer_period, self.publish_data)

    def publish_data(self):
        voltage = Float32()
        voltage.data = random.random()

        self.voltage_pub.publish(voltage)

def main(args=None):
    rclpy.init(args=args)

    node = VoltageNode()

    executor = rclpy.executors.SingleThreadedExecutor()
    executor.add_node(node)

    try:
        executor.spin()
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
