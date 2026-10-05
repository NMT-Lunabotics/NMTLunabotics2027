Required packages:
```
pip install av
```

### Core changes, camera switching and enabling/disabling feed
ros2 param set /camera_manager feeds.primary.camera0.camera "[0, 1]"
ros2 param set /camera_manager feeds.primary.camera0.enabled false

### Core camera feed settings, resultion and fps
ros2 param set /camera_manager feeds.primary.camera0.adjustments.width 320
ros2 param set /camera_manager feeds.primary.camera0.adjustments.height 180
ros2 param set /camera_manager feeds.primary.camera0.adjustments.framerate 10

#### Compression settings, max and avg bitrates and compression gop
ros2 param set /camera_manager feeds.primary.camera0.compression.max_bitrate_kbps 500
ros2 param set /camera_manager feeds.primary.camera0.compression.avg_bitrate_kbps 450
ros2 param set /camera_manager feeds.primary.camera0.compression.gop 24

### Camera adjustments, grayscale, camera flips, and image cropping
ros2 param set /camera_manager feeds.primary.camera0.adjustments.grayscale true
ros2 param set /camera_manager feeds.primary.camera0.adjustments.horizontal_flip true
ros2 param set /camera_manager feeds.primary.camera0.adjustments.vertical_flip true
ros2 param set /camera_manager feeds.primary.camera0.adjustments.top_crop 20
ros2 param set /camera_manager feeds.primary.camera0.adjustments.bottom_crop 10
ros2 param set /camera_manager feeds.primary.camera0.adjustments.left_crop 5
ros2 param set /camera_manager feeds.primary.camera0.adjustments.right_crop 5

### April tag enable/disable and visualizer
ros2 param set /camera_manager feeds.rtabmap.rgb_feed.apriltag_localizer.enabled true
ros2 param set /camera_manager feeds.rtabmap.rgb_feed.apriltag_localizer.overlay false


ros2 param set /camera_manager feeds.primary.camera0.apriltag_localizer.overlay false