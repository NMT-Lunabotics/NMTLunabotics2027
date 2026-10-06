#!/usr/bin/env python3
import time
import collections
import cv2
import av
import rclpy

from rclpy.node import Node
from rclpy.executors import ExternalShutdownException
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import CompressedImage

class StreamViewer(Node):
    def __init__(self):
        super().__init__("stream_viewer")
        self.topic = "/stream/compressed"
        self.decoder = None
        self.format = None
        self.window = collections.deque()
        self.total_bytes = 0
        self.first = None
        self.sized = False

        cv2.namedWindow(self.topic, cv2.WINDOW_NORMAL | cv2.WINDOW_KEEPRATIO)
        self.create_subscription(CompressedImage, self.topic, self.on_image, qos_profile_sensor_data)
        self.create_timer(1 / 60, self.show)

    def bandwidth(self, size):
        now = time.monotonic()
        if self.first is None: self.first = now
        self.total_bytes += size
        self.window.append((now, size))
        while self.window[0][0] < now - 1.0: self.window.popleft()
        span = now - self.window[0][0]
        total = now - self.first
        current = sum(s for _, s in self.window) * 8 / max(span, 1.0) / 1e6
        average = self.total_bytes * 8 / max(total, 1e-6) / 1e6
        return current, average

    def on_image(self, msg):
        current, average = self.bandwidth(len(msg.data))

        fmt = msg.format.lower()
        if fmt not in ("h264", "h265", "hevc"): return

        if self.decoder is None or self.format != fmt:
            self.decoder = av.CodecContext.create("h264" if fmt == "h264" else "hevc", "r")
            self.format = fmt

        try:
            decoded = self.decoder.decode(av.Packet(bytes(msg.data)))
        except Exception:
            return

        for frame in decoded:
            image = frame.to_ndarray(format="bgr24")
            text = f"{current:.2f} Mbps   {average:.2f} Mbps avg"
            cv2.putText(image, text, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 0), 3, cv2.LINE_AA)
            cv2.putText(image, text, (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1, cv2.LINE_AA)
            if not self.sized:
                cv2.resizeWindow(self.topic, image.shape[1], image.shape[0])
                self.sized = True
            cv2.imshow(self.topic, image)

    def show(self):
        if cv2.waitKey(1) in (27, ord("q")): rclpy.shutdown()

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()

def main():
    rclpy.init()
    node = StreamViewer()
    try:
        rclpy.spin(node)
    except (KeyboardInterrupt, ExternalShutdownException):
        pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__":
    main()