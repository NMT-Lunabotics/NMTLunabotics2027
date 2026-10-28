#!/usr/bin/env python3
import os, yaml, rclpy
from rclpy.node import Node
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import SetParametersResult

# ########## manager class, handles all ########## and ########## feed interactions and live changes
class ##########Manager(Node):
    def __init__(self):
        super().__init__("##########_manager")
        # Package start message
        self.get_logger().info("\033[94m########## manager node started\033[0m")

        # Define a ########## config file parameter. Have it default to config/##########.yaml if not specifiied
        ##########_config=os.path.join(get_package_share_directory("##########"), "config", "##########.yaml")
        self.declare_parameter("##########_config", ##########_config)
        # Create flattend params of all param configs
        with open(self.get_parameter("##########_config").value, "r") as file: data=yaml.safe_load(file)
        self.declare_flatend_params(data["##########_manager"]["ros__parameters"])

        # Define a presistance parameter. Which when true makes the node record changes when an param change is detected, either local or an global change can be made
        self.declare_parameter("persistent", True)
        self.persistent=self.get_parameter("persistent").value
        self.declare_parameter("persistent_type", "global")
        self.persistent_type=self.get_parameter("persistent_type").value

        # Create an parameters callback to support live ########## config changes
        self.add_on_set_parameters_callback(self.on_params_change)

    # Event which triggers when parma change comments are sent to have live configuable ##########s
    def on_params_change(self, params):
        # Check if persistent parmas are enabled and if so what type of persistent local or global
        for param in params:
            if param.name=="persistent": self.persistent=param.value
            if param.name=="persistent_type": self.persistent_type=param.value

        # Get parma persistent variable
        if not self.persistent: return SetParametersResult(successful=True)
        if not any(param.name.startswith(("##########.",)) for param in params): return SetParametersResult(successful=True)

        # Create variables for the path to the config
        config_path=self.get_parameter("##########_config").value
        config_paths=[config_path]
        if self.persistent_type=="global" and "/install/" in config_path: config_paths.append(os.path.join(config_path.split("/install/")[0], "src", "##########", "config", "##########.yaml"))

        # If enabled loop through parmas saved in ram and push them to
        for path in dict.fromkeys(os.path.realpath(path) for path in config_paths):
            # Log comments to make them presistant between global parma changes
            if not os.path.exists(path): continue
            with open(path, "r") as file: old_text=file.read()
            data=yaml.safe_load(old_text)
            for param in params:
                if not param.name.startswith(("##########.",)): continue
                node=data["##########_manager"]["ros__parameters"]
                *parents, leaf=param.name.split(".")
                for key in parents: node=node.setdefault(key, {})
                node[leaf]=param.value if isinstance(param.value, (str, bool, int, float)) else list(param.value)
            above, inline, index={}, {}, 0

            # Reembed comments
            for line in old_text.splitlines():
                if line.strip().startswith("#"): above.setdefault(index, []).append(line.strip())
                elif line.strip() and not line.strip().startswith("-"):
                    if " #" in line: inline[index]=line[line.index(" #"):].strip()
                    index+=1
            output, index=[], 0
            for line in yaml.safe_dump(data, sort_keys=False).splitlines():
                if line.strip().startswith("-"): output.append(line); continue
                output+=[" "*(len(line)-len(line.lstrip()))+text for text in above.get(index, [])]
                output.append(f"{line:<50} {inline[index]}" if index in inline else line)
                index+=1
            with open(path, "w") as file: file.write("\n".join(output)+"\n")
        return SetParametersResult(successful=True)

    # Interative nested params flatener
    def declare_flatend_params(self, value, path=""):
        # Loop into nested param value building an path i.e. camera.type.rgb
        if isinstance(value, dict): for param_key, param_value in value.items(): self.declare_flatend_params(param_value, f"{path}{param_key}.")
        # Once flattened declare path as ros parameter for live param changes
        else:
            full_path=path.rstrip(".")
            if not self.has_parameter(full_path): self.declare_parameter(full_path, value)

    # Stop node and close all ##########s
    def destroy_node(self):
        super().destroy_node()

# Node initalization
def main():
    rclpy.init()
    node=##########Manager()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__":
    main()
