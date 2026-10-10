import rclpy
from PyQt5.QtCore import QObject, pyqtSignal # Qt Bridge Communicator Imports
from rclpy.executors import SingleThreadedExecutor
from threading import Event

from battery_subscriber import BatterySubscriber
from intel_subscriber import IntelSubscriber
from PyQt5.QtGui import QImage

class ROSWorker(QObject):
    voltage_received = pyqtSignal(float)
    image_received = pyqtSignal(str, QImage)

    def __init__(self):
        super().__init__()
        self.stop_event = Event()
        self.executor = None

    def run(self):
        print("ROS WORKER STARTED")

        rclpy.init()

        self.subscriber = BatterySubscriber(
            self.voltage_received.emit
        )

        self.intel_subscriber = IntelSubscriber(
            self.image_received.emit)

        self.executor = SingleThreadedExecutor()
        self.executor.add_node(self.subscriber)
        self.executor.add_node(self.intel_subscriber)

        try:
            self.executor.spin()
        finally:
            self.subscriber.destroy_node()
            self.intel_subscriber.destroy_node()

            if rclpy.ok():
                rclpy.shutdown()

    def stop(self):
        self.stop_event.set()

        if self.executor is not None:
            self.executor.shutdown()