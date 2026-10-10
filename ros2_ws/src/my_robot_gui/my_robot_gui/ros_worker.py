import rclpy
from PyQt5.QtCore import QObject, pyqtSignal # Qt Bridge Communicator Imports
from rclpy.executors import SingleThreadedExecutor

from battery_subscriber import BatterySubscriber
from intel_subscriber import IntelSubscriber
from PyQt5.QtGui import QImage

class ROSWorker(QObject):
    voltage_received = pyqtSignal(float)
    image_received = pyqtSignal(str, QImage)

    def __init__(self):
        super().__init__()

    def run(self):
        print("ROS WORKER STARTED")

        rclpy.init()

        self.subscriber = BatterySubscriber(
            self.voltage_received.emit
        )

        self.intel_subscriber = IntelSubscriber(
            self.image_received.emit)

        executor = SingleThreadedExecutor()
        executor.add_node(self.subscriber)
        executor.add_node(self.intel_subscriber)
        executor.spin()

        self.subscriber.destroy_node()
        rclpy.shutdown()
