# Jetson Services

Systemd startup is intentionally deferred. First validate manual SSH startup, container lifecycle, launch ordering, safe stop behavior, and recovery after process failure. Any future unit must stop the ROS stack cleanly and must not automatically resume actuator motion after a reboot or fault.