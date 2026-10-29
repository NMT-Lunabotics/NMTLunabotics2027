import rclpy
from rclpy.node import Node
from rclpy.parameter import Parameter
from rcl_interfaces.srv import SetParameters

# Sample parma send node
class ParamSetter(Node):
    def __init__(self):
        super().__init__("param_setter")

######################################## CODE NEEDED ########################################

        # Define all packages that parmas will be changed in, add to your nodes __init__
        self.clients_by_node={name: self.create_client(SetParameters, f"/{name}/set_parameters") for name in ("serial_bridge", "camera_manager")}

        # Send parma commands, this can be ran anywhere from your node class
        self.send_param("serial_bridge", "reconnect_time", 2.0)
        self.send_param("camera_manager", "persistent", True)

    # Add function to your node class, this handling the sending
    def send_param(self, node_name, name, value):
        request=SetParameters.Request()
        request.parameters=[Parameter(name, value=value).to_parameter_msg()]
        self.clients_by_node[node_name].call_async(request)

######################################## CODE NEEDED ########################################

# Other node stuff
def main():
    rclpy.init()
    node=ParamSetter()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__":
    main()
