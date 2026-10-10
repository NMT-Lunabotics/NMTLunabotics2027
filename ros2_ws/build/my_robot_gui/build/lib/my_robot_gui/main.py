# GUI Imports
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy, QPushButton, QTextEdit
from PyQt5.QtGui import QPixmap
from layout_one import Color
from ros_worker import ROSWorker
from PyQt5.QtCore import QThread, Qt


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
       rgb_button.clicked.connect(
            lambda: setattr(self, 'current_sensor', "RGB"))

       depth_button.clicked.connect(
            lambda: setattr(self, 'current_sensor', "DEPTH"))

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
       robot_updates = QTextEdit()
       robot_updates_title = QLabel("ROBOT UPDATES")
       left_vbox_layout.addWidget(robot_updates_title)
       left_vbox_layout.addWidget(robot_updates)

       # Robot Updates Placeholder Text
       robot_updates.setPlainText(
       "[ROBOT] System initialized\n"
       "[ROBOT] Connection: ACTIVE\n"
       "[ROBOT] Battery monitoring: ACTIVE\n"
       "[ROBOT] Sensors: ONLINE\n")
       robot_updates.setReadOnly(True)

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

   def update_sensor_view(self, sensor, q_image):
        if self.current_sensor == sensor:
            pixmap = QPixmap.fromImage(q_image)

            scaled_pixmap = pixmap.scaled(self.sensor_view.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.sensor_view.setPixmap(scaled_pixmap)



    
def main(): # Instructions to Start/Run GUI
    app = QApplication(sys.argv)
    app.setStyleSheet(styleSheet)
    window = MainWindow()

    # Start ROS...
    ros_thread = QThread() # Creates lane for ROS
    ros_worker = ROSWorker() # Creates ROS worker (object containing ROS work)
    ros_worker.moveToThread(ros_thread) # Runs ROS worker in ROS thread instead of GUI thread
    ros_worker.voltage_received.connect(window.update_battery_voltage)
    ros_worker.image_received.connect(window.update_sensor_view)
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

