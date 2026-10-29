import time, rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParameters

# Node stuff
rclpy.init()
node=Node("param_setter")

# Set parameter after 5 seconds
client=node.create_client(SetParameters, "/serial_bridge/set_parameters")
time.sleep(5)
request=SetParameters.Request()
request.parameters=[Parameter("reconnect_time", Parameter.Type.DOUBLE, 2.0).to_parameter_msg()]

# Node stuff
rclpy.spin_until_future_complete(node, client.call_async(request))
node.destroy_node()
rclpy.shutdown()
