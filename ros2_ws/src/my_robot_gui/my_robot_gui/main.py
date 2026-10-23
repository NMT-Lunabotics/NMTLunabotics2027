import sys

# Camera Manager Imports
import subprocess
import os
import signal

# Auto-Robot Connect Imports
import socket
import json
import time

# GUI imports
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy, QPushButton, QTextEdit
# Auto-Robot Connect Imports
from PyQt5.QtWidgets import QDialog, QComboBox, QLineEdit, QMessageBox, QFormLayout
from PyQt5.QtGui import QPixmap
from ros_worker import ROSWorker
from PyQt5.QtCore import QThread, Qt

# Robot Discovery Settings (ported from 2026 Driver Station)
UDP_DESTINATION = ("0.0.0.0", 11000)
TELEMETRY_LISTEN = ("0.0.0.0", 10000)
COMMAND_DESTINATION = ("0.0.0.0", 10001)

DISCOVERY_PORT = 11010
DISCOVERY_MAGIC = b"F310_DISCOVERY_V1"
LEGACY_DISCOVERY_PORT = 10000

DISCOVERY_ATTEMPTS = 5
DISCOVERY_TIMEOUT = 0.6

CAMERA_HTTP_PORT = 8081

SAVED_IPS = [
    "192.168.0.207",
    "129.138.171.148",
    "192.168.2.127",
]

AUTO_IP_CONNECT = False

# Auto Robot Connect System (move if operational)
def discover_robot(attempts=DISCOVERY_ATTEMPTS, timeout=DISCOVERY_TIMEOUT):
    """Search for a robot using the 2026 Driver Station discovery protocol."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

    try:
        sock.bind(("", LEGACY_DISCOVERY_PORT))

        for _ in range(max(1, attempts)):
            # Send both current and legacy discovery requests.
            for port, payload in (
                (DISCOVERY_PORT, DISCOVERY_MAGIC),
                (LEGACY_DISCOVERY_PORT, b"B-NMT26"),
            ):
                try:
                    sock.sendto(payload, ("255.255.255.255", port))
                except OSError:
                    pass

            deadline = time.monotonic() + timeout

            while time.monotonic() < deadline:
                remaining = deadline - time.monotonic()
                sock.settimeout(max(0.01, remaining))

                try:
                    data, address = sock.recvfrom(1024)
                except socket.timeout:
                    break
                except OSError:
                    return None

                message = data.decode(errors="ignore").strip()

                if not message:
                    continue

                # Handle JSON discovery replies.
                try:
                    response = json.loads(message)
                except json.JSONDecodeError:
                    response = None

                if isinstance(response, dict):
                    return (
                        address[0],
                        int(response.get("udp_port", UDP_DESTINATION[1])),
                        int(response.get("command_port", COMMAND_DESTINATION[1])),
                        int(response.get("telemetry_port", TELEMETRY_LISTEN[1])),
                    )

                # Handle the legacy text reply.
                if message.startswith("NMT26:"):
                    return (
                        address[0],
                        UDP_DESTINATION[1],
                        COMMAND_DESTINATION[1],
                        TELEMETRY_LISTEN[1],
                    )

    except OSError as error:
        print(f"Robot discovery error: {error}")
    finally:
        sock.close()

    return None

class RobotSelectionDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.setWindowTitle("Find and Connect to Berminator Jr.")
        self.setMinimumWidth(450)


        ## GUI style - move later
        # Match the BERMINATOR JR. MONITOR theme
        self.setStyleSheet("""
            QDialog {
                background-color: #121212;
                color: white;
            }

            QLabel {
                color: white;
                font-family: "Segoe UI";
                font-size: 11pt;
                padding: 4px;
                border: none;
            }

            QComboBox, QLineEdit {
                background-color: #242424;
                color: white;
                border: 1px solid #444444;
                border-radius: 6px;
                padding: 8px;
                font-size: 11pt;
            }

            QComboBox QAbstractItemView {
                background-color: #242424;
                color: white;
                selection-background-color: #2A3F55;
                selection-color: white;
            }

            QPushButton {
                background-color: #2A3F55;
                color: white;
                border: 1px solid #3A526B;
                border-radius: 8px;
                padding: 10px;
                font-family: "Segoe UI";
                font-size: 11pt;
                font-weight: bold;
            }

            QPushButton:hover {
                background-color: #385675;
                border: 1px solid #587895;
            }

            QPushButton:pressed {
                background-color: #1B2A3A;
            }

            QPushButton:disabled {
                background-color: #242424;
                color: #777777;
                border: 1px solid #333333;
            }
        """)
        ####################################
        self.robot_connection = None

        layout = QVBoxLayout(self)

        layout.addWidget(QLabel("Discover a robot on the network:"))

        self.discovered_label = QLabel("No robot discovered yet.")
        layout.addWidget(self.discovered_label)

        self.find_button = QPushButton("Find Robot")
        self.find_button.clicked.connect(self.find_robot)
        layout.addWidget(self.find_button)

        layout.addWidget(QLabel("Saved robot addresses:"))

        self.saved_ip_combo = QComboBox()
        self.saved_ip_combo.addItems(SAVED_IPS)
        layout.addWidget(self.saved_ip_combo)

        layout.addWidget(QLabel("Or enter an IP address manually:"))

        self.manual_ip_input = QLineEdit()
        self.manual_ip_input.setPlaceholderText("Example: 192.168.0.207")
        layout.addWidget(self.manual_ip_input)

        self.connect_button = QPushButton("Connect")
        self.connect_button.clicked.connect(self.accept_selection)
        layout.addWidget(self.connect_button)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        layout.addWidget(self.cancel_button)

    def find_robot(self):
        self.find_button.setEnabled(False)
        self.discovered_label.setText("Searching for robot...")
        QApplication.processEvents()

        result = discover_robot()

        self.find_button.setEnabled(True)

        if result:
            self.robot_connection = result
            self.discovered_label.setText(
                f"Robot discovered at {result[0]}"
            )
        else:
            self.discovered_label.setText("No robot found.")

    def accept_selection(self):
        manual_ip = self.manual_ip_input.text().strip()

        if manual_ip:
            self.robot_connection = (
                manual_ip,
                UDP_DESTINATION[1],
                COMMAND_DESTINATION[1],
                TELEMETRY_LISTEN[1],
            )

        elif self.robot_connection is None and self.saved_ip_combo.currentText():
            self.robot_connection = (
                self.saved_ip_combo.currentText(),
                UDP_DESTINATION[1],
                COMMAND_DESTINATION[1],
                TELEMETRY_LISTEN[1],
            )

        if self.robot_connection is None:
            QMessageBox.warning(
                self,
                "Robot Not Selected",
                "Find a robot or select/enter an IP address first.",
            )
            return

        self.accept()

class MainWindow(QMainWindow):
   def __init__(self):
       super().__init__()


       # Window Settings
       self.setWindowTitle("BERMINATOR JR. MONITOR")
       self.setMinimumSize(1700,1100) # Sets initial/minimum size


       # All Layouts
       main_layout = QVBoxLayout() # Main 2 Boxes Layout
       header_panel = QWidget() # Header Widget (Height Constraint)
       header_panel.setMaximumHeight(60)
       header_layout = QHBoxLayout() # Connection Status and Battery Level Layout
       content_layout = QHBoxLayout() # Content Layout (Left and Right Boxes)
       left_vbox_layout = QVBoxLayout() # Cameras, LiDAR, and Errors Layout
       right_vbox_layout = QVBoxLayout() # Stats and Autonomous Cycle Updates Layout
       sensor_buttons = QHBoxLayout() # Toggle buttons for camera views
       autonomous_buttons = QVBoxLayout() # Autonomous Cycle Buttons Layout
       
       # Main Layout
       main_layout.addWidget( header_panel )
       main_layout.setStretch(0,1)


       main_layout.addLayout( content_layout )
       main_layout.setStretch(1,11)


       # Connection Status and Battery Level Layout
       header_layout.addWidget(QLabel("STATUS: " + str(self.robot_connection_status()))) # Connection Status

       self.voltage_label = QLabel("BATTERY: -- V")
       header_layout.addWidget(self.voltage_label)

       # Header Panel Layout
       header_panel.setLayout( header_layout )

       # Content Layout
       content_layout.addLayout( left_vbox_layout )
       content_layout.setStretch(0,3)


       content_layout.addLayout( right_vbox_layout )
       content_layout.setStretch(1,1)

       # Left VBox Layout Located in Camera Layout

       # Camera Layout
       self.sensor_view = QLabel("SENSOR VIEW")
       self.current_sensor = None
       self.sensor_view.setAlignment(Qt.AlignCenter)
       left_vbox_layout.addWidget(self.sensor_view) # Left Vbox Layout
       left_vbox_layout.setStretch(0,5)

       # Sensor Buttons Layout
       left_vbox_layout.addLayout(sensor_buttons)

       # Sensor View Buttons
       rgb_button = QPushButton("RGB")
       depth_button = QPushButton("DEPTH")
       lidar_button = QPushButton("LIDAR")
       ir_button = QPushButton("IR")

       sensor_buttons.addWidget(rgb_button)
       sensor_buttons.addWidget(depth_button)
       sensor_buttons.addWidget(lidar_button)
       sensor_buttons.addWidget(ir_button)

       # BUTTON SETTINGS
       rgb_button.clicked.connect(self.select_rgb)

       depth_button.clicked.connect(self.select_depth)

       lidar_button.clicked.connect(
            lambda: setattr(self, 'current_sensor', "LIDAR"))

       ir_button.clicked.connect(
            lambda: setattr(self, 'current_sensor', "IR")
       )

       # LiDAR Layout
       LiDAR = QLabel()
       LiDAR.setPixmap(QPixmap('LiDAR.png'))
       LiDAR.setScaledContents(True)
       left_vbox_layout.addWidget(LiDAR)
       left_vbox_layout.setStretch(1,4)
       LiDAR.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)

       # Errors/Warnings Layout
       errors_panel = QWidget()
       errors_panel.setObjectName("errors_panel")
       left_vbox_layout.addWidget(errors_panel)
       left_vbox_layout.setStretch(2,2)

       # Robot Updates Terminal
       self.robot_updates = QTextEdit()
       robot_updates_title = QLabel("ROBOT UPDATES")
       left_vbox_layout.addWidget(robot_updates_title)
       left_vbox_layout.addWidget(self.robot_updates)

       # Robot Updates Placeholder Text
       self.robot_updates.setPlainText(
       "Robot Updates Terminal (Errors & Stats)")
       self.robot_updates.setReadOnly(True)

       #Autonomous Updates Terminal
       autonomous_updates = QTextEdit()
       autonomous_updates_title = QLabel("AUTONOMOUS CYCLE UPDATES")
       
       # Autonomous Updates Placeholder Text
       autonomous_updates.setPlainText(
       "[AUTO] Autonomous system initialized\n"
       "[AUTO] Waiting for procedure... \n"
       "[AUTO] Status: STANDBY\n")
       
       # Right VBox Layout: Stats & Auto-Cycle Updates
         #Stats Panel
       stats_panel = QWidget()
       stats_panel.setObjectName("stats_panel")
       right_vbox_layout.addWidget(stats_panel)
       right_vbox_layout.setStretch(0,5)
         #Autonomous Cycle Updates
       autonomous_panel = QWidget()
         #Autonomous Cycle Updates Layout
       autonomous_panel.setObjectName("autonomous_panel")
       autonomous_panel.setLayout(autonomous_buttons)
       
       # Autonomous Cycle Buttons
       dig_button = QPushButton("DIG")
       dump_button = QPushButton("DUMP")
       auto_cycle_button = QPushButton("RUN AUTO CYCLE")
       emergency_stop_button = QPushButton("EMERGENCY STOP")
       emergency_stop_button.setStyleSheet("background-color: red; color: white; font-weight: bold;")

       autonomous_buttons.addWidget(dig_button)
       autonomous_buttons.addWidget(dump_button)
       autonomous_buttons.addWidget(auto_cycle_button)
       autonomous_buttons.addWidget(emergency_stop_button)
       
       right_vbox_layout.addWidget(autonomous_panel)
       right_vbox_layout.setStretch(1,1)

       right_vbox_layout.addWidget(autonomous_updates_title)
       right_vbox_layout.addWidget(autonomous_updates)


       widget = QWidget()
       widget.setLayout(main_layout)
       self.setCentralWidget(widget)



   def robot_connection_status(self):
       # Placeholder for robot connection status code once hooked up to the robot
       connection_status = "Connected" # Placeholder for actual connection status
       return connection_status

   def update_battery_voltage(self, voltage):
        self.voltage_label.setText(f"BATTERY: {voltage:.2f} V")

   def add_robot_update(self, message):
        if message.startswith("[ERROR]"):
             self.robot_updates.append(
                  f'<span style="color:red;">{message}</span>'
             )
        else:
            self.robot_updates.append(f"[ROBOT] {message}")
   
   def update_sensor_view(self, sensor, q_image):
        if self.current_sensor == sensor:
            pixmap = QPixmap.fromImage(q_image)

            scaled_pixmap = pixmap.scaled(self.sensor_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.sensor_view.setPixmap(scaled_pixmap)

   def select_rgb(self):
        self.current_sensor = "RGB"

   def select_depth(self):
        self.current_sensor = "DEPTH"

   def start_camera_manager(self):
        result = subprocess.run(["pgrep", "-af", "camera_manager.py"], capture_output=True,text=True)
        
        if result.stdout.strip():
            print("Camera Manager is already running.")
            self.camera_manager_process = None
            self.camera_manager_node_pid = None
        else:
            self.camera_manager_process = subprocess.Popen(["ros2", "run","camera","camera_manager.py"], start_new_session=True)
            self.camera_manager_node_pid = None
            
            print("Camera Manager Started!")
   
   def closeEvent(self,event):
        print("Shutting down ROS worker...")

        # Stop the ROS Worker
        if hasattr(self, "ros_worker"):
             self.ros_worker.stop()


        # Stop the ROS Thread
        if hasattr(self, "ros_thread"):
             self.ros_thread.quit()
             self.ros_thread.wait(3000)

        # Stop the Camera Manager
        print("Shutting down Camera Manager...")

        result = subprocess.run(
            ["pgrep", "-af", "[c]amera_manager.py"],
            capture_output=True,
            text=True
        )

        for line in result.stdout.splitlines():
            parts = line.split(maxsplit=1)

            if len(parts) == 2 and "install/camera/lib/camera/camera_manager.py" in parts[1]:
                pid = int(parts[0])
                try:
                    os.kill(pid, signal.SIGINT)
                    print(f"Stopped Camera Manager (PID {pid}).")
                except ProcessLookupError:
                    print(f"Camera Manager (PID {pid}) was already stopped.")

        if hasattr(self, "camera_manager_process") and self.camera_manager_process:
            try:
                self.camera_manager_process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.camera_manager_process.kill()
                self.camera_manager_process.wait()

        event.accept()
    
def main(): # Instructions to Start/Run GUI
    app = QApplication(sys.argv)
    app.setStyleSheet(styleSheet)
    window = MainWindow()

    
    # Ask the operator to find or select a robot.
    selection_dialog = RobotSelectionDialog()
    if selection_dialog.exec_() != QDialog.Accepted:
        print("Robot selection canceled.")
        return

    robot_ip, udp_port, command_port, telemetry_port = (
        selection_dialog.robot_connection
    )

    print(f"Selected robot: {robot_ip}")
    print(f"UDP port: {udp_port}")
    print(f"Command port: {command_port}")
    print(f"Telemetry port: {telemetry_port}")

    window = MainWindow()
    window.robot_ip = robot_ip
    window.udp_destination = (robot_ip, udp_port)
    window.command_destination = (robot_ip, command_port)
    window.telemetry_listen = ("0.0.0.0", telemetry_port)

    # Start Camera Manager
    window.start_camera_manager()

    # Start ROS...
    window.ros_thread = QThread() # Creates lane for ROS
    window.ros_worker = ROSWorker() # Creates ROS worker (object containing ROS work)

    ros_thread = window.ros_thread
    ros_worker = window.ros_worker

    ros_worker.moveToThread(ros_thread) # Runs ROS worker in ROS thread instead of GUI thread

    ros_worker.voltage_received.connect(window.update_battery_voltage)
    ros_worker.image_received.connect(window.update_sensor_view)
    ros_worker.message_received.connect(window.add_robot_update)

    ros_thread.started.connect(ros_worker.run)

    ros_thread.start()

    window.show()
    app.exec() # Starts the event loop

styleSheet = """
QMainWindow {
    background-color: #121212;}
QLabel {
    color: white;
    font-size: 16pt;
    font-family: "Segoe UI";
    padding: 5px;
    border: 1px solid #333333;
    border-radius: 10px;}
QTextEdit {
    background-color: #111111;
    color: #00FF00;
    font-family: "Courier New";
    font-size: 12pt;
    border: 1px solid #333333;
    border-radius: 10px;}
#stats_panel {
    background-color: #2A3F55;
    border: 1px solid #333333;
    border-radius: 10px;}
#autonomous_panel {
    background-color: #242424;
    border: 1px solid #333333;
    border-radius: 10px;}
#errors_panel {
    background-color: #3A3020;
    border: 1px solid #5A4A2A;
    border-radius: 10px;
    }
"""

if __name__ == '__main__': # If the file is run directly, execute main()
       main()

