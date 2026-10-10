import rclpy
import random
from rclpy.node import Node
from std_msgs.msg import Float32

class VoltagePublisher(Node):

    def __init__(self):
        super().__init__('voltage_publisher') # identifies running ROS node

        self.voltage_pub = self.create_publisher(Float32, '/battery_voltage', 10) #/battery_voltage is the name of the ROS topic
        timer_period = 20 #seconds
        self.timer = self.create_timer(timer_period, self.publish_data)

    def publish_data(self):
        voltage_float = Float32()
        voltage_float.data = random.random()

        print(f"PUBLISHING: {voltage_float.data:.2f} V")
        self.voltage_pub.publish(voltage_float)

def main(args=None):
    rclpy.init(args=args) # Initializes ROS2

    voltage_publisher_object = VoltagePublisher()

    executor = rclpy.executors.SingleThreadedExecutor() # Continually process ROS events
    executor.add_node(voltage_publisher_object)

    try:
        executor.spin() # keep running & processing ROS events
    except KeyboardInterrupt:
        pass
    finally:
        voltage_publisher_object.destroy_node()
        rclpy.shutdown()

if __name__ == '__main__':
    main()
