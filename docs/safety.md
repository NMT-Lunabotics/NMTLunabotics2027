# Safety and Hardware Integration

This scaffold has no actuator drivers and must not be treated as a robot-ready control system.

Before adding motor or excavator control, document the physical emergency-stop circuit, controller watchdog, safe startup state, command limits, stale-command timeout, and expected behavior after ROS, DDS, SSH, Docker, or Jetson failure. The physical emergency stop must operate independently of ROS and networking.

The RPLiDAR S3 has previously lost power while the motors run. Treat this as an electrical power-integrity issue: test isolated, adequately rated 5 V power for the Slamtec adapter (for example, an appropriate powered USB hub or approved power-injection solution). Do not modify the custom four-wire ribbon cable. The supply must be designed for the robot battery's maximum charged voltage and confirmed with electrical measurements under motor load.

Every new sensor/controller requires an isolated smoke test, device permission review, documented topic/frame/QoS contract, reconnect behavior, and a concurrent-load test before inclusion in the combined robot launch.