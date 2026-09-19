# GUI Imports
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QSizePolicy
from PyQt5.QtGui import QPixmap
from layout_one import Color

class MainWindow(QMainWindow):
   def __init__(self):
       super().__init__()


       # Window Settings
       self.setWindowTitle("BERMINATOR JR. MONITOR")
       self.setMinimumSize(1700,1100) # Sets initial/minimum size


       # All Layouts
       main_layout = QVBoxLayout() # Main 2 Boxes Layout
       header_layout = QVBoxLayout() # Header Layout
       header_stats_layout = QHBoxLayout() # Connection Status and Battery Level Layout
       content_layout = QHBoxLayout() # Content Layout (Left and Right Boxes)
       left_vbox_layout = QVBoxLayout() # Cameras, LiDAR, and Errors Layout
       camera_layout = QHBoxLayout() # Camera Layout
       right_vbox_layout = QVBoxLayout() # Stats and Autonomous Cycle Updates Layout
      
       # Main Layout
       main_layout.addLayout( header_layout )
       main_layout.setStretch(0,1)


       main_layout.addLayout( content_layout )
       main_layout.setStretch(1,11)


       # Header Layout
       header_layout.addWidget(Color('blue')) # Title
       header_layout.addLayout( header_stats_layout ) # Connection Status and Battery Level Layout


       # Connection Status and Battery Level Layout
       header_stats_layout.addWidget(QLabel("STATUS: " + str(self.robot_connection_status()))) # Connection Status
       header_stats_layout.addWidget(QLabel("BATTERY: " + str(self.robot_battery_level()) + "%")) # Battery Level


       # Content Layout
       content_layout.addLayout( left_vbox_layout )
       content_layout.setStretch(0,3)


       content_layout.addLayout( right_vbox_layout )
       content_layout.setStretch(1,1)


       # Left VBox Layout
       left_vbox_layout.addLayout( camera_layout )
       left_vbox_layout.setStretch(0,5)


       LiDAR = QLabel()
       LiDAR.setPixmap(QPixmap('LiDAR.png'))
       LiDAR.setScaledContents(True)
       left_vbox_layout.addWidget(LiDAR)
       left_vbox_layout.setStretch(1,4)
       LiDAR.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)


       left_vbox_layout.addWidget(Color('yellow')) # Errors
       left_vbox_layout.setStretch(2,2)


       # Camera Layout
       camera_1 = QLabel()
       camera_1.setPixmap(QPixmap('camera_feed.png'))
       camera_1.setScaledContents(True)
       camera_layout.addWidget(camera_1)
       camera_layout.setStretch(0,1)
       camera_1.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)


       camera_2 = QLabel()
       camera_2.setPixmap(QPixmap('camera_feed.png'))
       camera_2.setScaledContents(True)
       camera_layout.addWidget(camera_2)
       camera_layout.setStretch(1,1)
       camera_2.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)


       # Right VBox Layout
       right_vbox_layout.addWidget(Color('red')) # Stats
       right_vbox_layout.setStretch(0,1)
       right_vbox_layout.addWidget(Color('red')) # Autonomous Cycle Updates
       right_vbox_layout.setStretch(1,1)


       widget = QWidget()
       widget.setLayout(main_layout)
       self.setCentralWidget(widget)


   def robot_connection_status(self):
       # Placeholder for robot connection status code once hooked up to the robot
       connection_status = "Connected" # Placeholder for actual connection status
       return connection_status


   def robot_battery_level(self):
       # Placeholder for robot battery level code once hooked up to the robot
       battery_level = 100 # Placeholder for actual battery level 
       return battery_level




app = QApplication(sys.argv)


window = MainWindow()
window.show()
app.exec() # Starts the event loop
