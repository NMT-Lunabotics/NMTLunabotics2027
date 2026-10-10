import rclpy #ROS2
from rclpy.node import Node #Lets BatterySubscriber be node
from std_msgs.msg import Float32 #Message type

# Battery Subscriber Class & Node
class BatterySubscriber(Node):

    def __init__(self, send_voltage=None):
        super().__init__('battery_gui_subscriber')

        self.send_voltage = send_voltage

        self.subscription = self.create_subscription(
            Float32, 
            '/battery_voltage',
            self.battery_callback,
            10)
        
    def battery_callback(self, msg):
        voltage = msg.data
        print(f"SUBSCRIBER RECIEVED: {voltage:.2f} V")

        self.get_logger().info(f'Recieved battery voltage: {voltage: .2f} V')

        if self.send_voltage:
            self.send_voltage(voltage)

def main(args=None):
    rclpy.init(args=args)

    node = BatterySubscriber() # creates ROS node & subscription

    rclpy.spin(node)

    node.destroy_node()
    rclpy.shutdown()

if __name__ == '__main__':
    main()