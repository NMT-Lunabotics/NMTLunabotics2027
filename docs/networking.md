# Networking

The Jetson has two distinct access paths:

- SSH is for administration, deployment, logs, and interactive shell access.
- ROS 2/DDS is for ROS nodes and operator tools that communicate with the robot.

The Docker launcher currently uses host networking to make ROS 2 discovery practical on a robot LAN. It starts with `ROS_DOMAIN_ID=42`; override it with `--ros-domain-id` so the robot and operator tools use the same domain. Choose a project domain that does not conflict with other robots on the network.

Host networking does not by itself guarantee discovery across Wi-Fi isolation, VPNs, routed networks, or firewalls. Before using a remote workstation, test discovery and topic flow in both directions on the actual network. Record the selected RMW implementation and any required DDS discovery/firewall settings here after testing.

For an operator outside the robot LAN, use a team-approved VPN or a deliberately configured WebSocket bridge. Do not assume SSH forwards DDS discovery or high-rate sensor data. Do not use a ROS topic as the sole emergency-stop path.

# Mostl likely ignore

We will have our own networking and setup for controlling the robot through wifi