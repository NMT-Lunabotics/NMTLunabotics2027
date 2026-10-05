**Install**

```
sudo apt update
sudo apt install ros-humble-rtabmap-ros
```

```
source /opt/ros/humble/setup.bash
source ~/NMTLunabotics2027/ros2_ws/install/setup.bash
ros2 launch rtabmap_autonomy slam.py
```


```
ros2 run camera camera_manager.py
```


```
ros2 run tf2_ros static_transform_publisher --x 0 --y 0 --z -1 --yaw 0 --pitch 0 --roll 0 --frame-id base_link --child-frame-id camera1
```

```
ros2 launch rtabmap_autonomy slam.py
```

```
ros2 run rtabmap_autonomy imu_merge.py
```