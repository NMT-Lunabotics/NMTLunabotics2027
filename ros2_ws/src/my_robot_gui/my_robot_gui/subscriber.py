import rclpy
from rclpy.node import Node
from std_msgs.msg import Float32

class BatterySubscriber(Node):
    def __init__(self):
        super().__init__('battery_gui_subscriber')

        self.subscription = self.create_subscription(
            Float32,
            '/battery_voltage',
            self.battery_callback,
            10)

    def battery_callback(self, msg):
        voltage = msg.data

        self.get_logger().info(f'Recieved battery voltage: {voltage: .2f} V')

def main(args=None):
    rclpy.init(args=args)

    node = BatterySubscriber()

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()