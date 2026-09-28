# Operator Station

This directory is reserved for future workstation-side visualization and teleoperation tools. Initially, use RViz 2 and a ROS 2 teleop client on a workstation connected to the Jetson over a tested robot LAN or VPN. The Jetson container does not run a GUI by default.

Any future custom interface must publish bounded teleoperation commands through the ROS control interface, display stale/disconnected state clearly, and never bypass the motor controller's watchdog or the physical emergency stop.