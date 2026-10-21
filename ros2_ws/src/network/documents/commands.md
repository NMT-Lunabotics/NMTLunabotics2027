Required packages:

### Core changes, 
ros2 param set /network_monitor interface wlp2s0
ros2 param set /network_monitor interface wlan0

ros2 param set /network_monitor avg_bandwidth.reset true



Useful commands
```
sudo apt install v4l-utils
v4l2-ctl --list-devices
sudo usermod -aG video $USER
```