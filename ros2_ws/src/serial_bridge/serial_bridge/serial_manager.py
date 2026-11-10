#!/usr/bin/env python3
import os, time, yaml, serial, rclpy, subprocess, threading, struct, fcntl, signal, json
import serial.tools.list_ports
from ament_index_python.packages import get_package_share_directory
from rcl_interfaces.msg import SetParametersResult
from rclpy.node import Node
from rclpy.parameter import Parameter
from rclpy.qos import qos_profile_sensor_data
from functools import partial
from robot_interfaces.msg import SerialCommand
from geometry_msgs.msg import Twist, TwistStamped
from rosidl_runtime_py.utilities import get_message

class SerialBridgeNode(Node):
    #===========================================================================
    # Node startup, initialization, and parmas 
    #===========================================================================

    # Initalize class variables, any data objects, and initaliztion functions/loops
    def __init__(self):
        super().__init__("serial_manager")
        # Package start message
        self.get_logger().info("\033[94mSerial bridge node started\033[0m")

        # Define a serial config file parameter. Have it default to config/serial.yaml if not specifiied, declaring and logging all parmas
        serial_config=os.path.join(get_package_share_directory("serial_bridge"), "config", "serial.conf")
        self.declare_parameter("serial_config", serial_config)
        with open(self.get_parameter("serial_config").value, "r") as file: data=yaml.safe_load(file)
        self.declare_flattened_params(data["serial"], "serial.")

        # Declare parameter config options which are ment to be set at the node launch to decide how parmas are handled/stored
        self.declare_parameter("persistent", True)
        self.persistent=self.get_parameter("persistent").value
        self.declare_parameter("persistent_type", "global")
        self.persistent_type=self.get_parameter("persistent_type").value

        self.add_on_set_parameters_callback(self.on_params_change)

        # Class parmas

        # Valid microcontroller baud rates to look through if not given, and valid microcontrollers and settings
        self.VALID_BAUD_RATES=(115200, 9600, 57600, 38400, 19200, 230400, 250000, 1000000)
        self.KNOWN_DEVICES=[
                    {"name": "Arduino Uno", "vid": 0x2341, "pid": 0x0043, "fqbn": "arduino:avr:uno"},
                    {"name": "Arduino Uno", "vid": 0x2341, "pid": 0x0243, "fqbn": "arduino:avr:uno"},
                    {"name": "Makeblock uno", "vid": 0x1A86, "pid": 0x7523, "fqbn": "arduino:avr:uno"},
                    {"name": "Arduino Mega 2560", "vid": 0x2341, "pid": 0x0042, "fqbn": "arduino:avr:mega"},
                    {"name": "Arduino Mega 2560", "vid": 0x2341, "pid": 0x0010, "fqbn": "arduino:avr:mega"},
                ]
        self.KNOWN_DEVICE_DESCRIPTIONS=("Arduino",)

        # Color mappings to use for status/error messages
        self.COLORS={
            "red": "\033[22;31m",
            "bold_red": "\033[1;31m",
            "green": "\033[22;92m",
            "bold_green": "\033[1;92m",
            "white": "\033[22;97m",
            "bold_white": "\033[1;97m",
        }

        # Old command bytes and valid message types to send over serial
        self.START_BYTE=2
        self.END_BYTE=3
        self.COMMAND_DATA_TYPES={
            "int8": ("b", -128, 127), "uint8": ("B", 0, 255),
            "int16": ("h", -32768, 32767), "uint16": ("H", 0, 65535),
            "int32": ("i", -2**31, 2**31-1), "uint32": ("I", 0, 2**32-1),
            "float32": ("f", None, None), "bool": ("?", None, None),
        }

        # File data, the root path of repsoitory and node state date/time
        self.REPO_ROOT=os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__)), "..", "..", "..", "..", ".."))
        self.START_STAMP=time.strftime("%m-%d-%Y_%H-%M")

        # Objects to store the diffrent elements used for the microcontrollers
        self.microcontrollers={}
        self.pending_actions={}
        self.commands={"topics": {}, "subscriptions": {}, "data": {}, "blocking_timer": 0.0, "default_type": "int8"}
        self.telemetry={"data": {}, "lookup": {}, "default_type": "int8"}

        # Inital microcontroller opens, and start loops that handle connection checks and queue requests
        self.open_microcontroller()
        self.create_timer(0.5, self.check_microcontroller_connections)
        self.create_timer(0.05, self.process_pending_actions)
        self.initialize_commands()
        self.create_timer(0.01, self.process_data_commands)


        self.create_timer(1.0, self.topic_discovery)

        self.initialize_telemetry()
        self.create_timer(0.005, self.read_microcontrollers)
        self.create_timer(0.01, self.process_telemetry)

    # Handle live parma changes and triggers
    def on_params_change(self, params):
        # Loop through new parmas and split the parmas in parts to look through
        for parma in params:
            parts=parma.name.split(".")

            # Handle when command trigger action
            if len(parts)==4 and parts[:2]==["serial", "commands"] and parts[3]=="type" and parts[2] in self.commands["data"]:
                self.commands["data"][parts[2]]["type"]=str(parma.value)
                if parma.value=="data_trigger": self.pending_actions.setdefault((parts[2], "trigger"), time.monotonic())

            # In the case of triggers (restart, reset) don't accept parma change, create a queued action request
            if len(parts)!=4 or parts[:2]!=["serial", "microcontrollers"] or parts[3] not in ("restart", "reset", "upload"): continue
            if parma.value: self.pending_actions.setdefault((parts[2], parts[3]), time.monotonic())

        # Close parma callback
        return SetParametersResult(successful=True)

    # Take all parms, flatten, then declare them as parameters
    def declare_flattened_params(self, value, path=""):
        # If a parma is a dictionary that means it includes nested items, recursively iterate every array values until non-dictionary values are reached
        if isinstance(value, dict):
            for key, item in value.items():
                self.declare_flattened_params(item, f"{path}{key}.")
        # Once a non-dictionary value is reached stip out the last period, mark value as presistant and attempt to declare the parameter
        elif value is not None:
            full_path = path.rstrip(".")
            if not self.has_parameter(full_path):
                self.declare_parameter(full_path, value)

    # Handle the setup for telemetry data and thier published topics
    def initialize_telemetry(self):
        # Pull all parma telemetry data 
        params=self.get_parameters_by_prefix("serial.telemetry")
        default_type=str(params["default_type"].value) if "default_type" in params else "int8"
        self.telemetry["default_type"]=default_type if default_type in self.COMMAND_DATA_TYPES else "int8"

        # Loop through it and ensure that the system has created parameter for each telemetry argument
        raw={}
        for key, parameter in params.items():
            parts=key.split(".")
            if len(parts)==2: raw.setdefault(parts[0], {})[parts[1]]=parameter.value

        # Loop through each telemetry object, building a the logging object that the system needs
        for name, sensor in raw.items():
            # Pull primary telemetry state data, and ensure that it's a string
            sensor_id=str(sensor.get("id", ""))
            kind=str(sensor.get("type", "telemetry_last"))
            state=kind=="telemetry_state"
            topic=str(sensor.get("topic") or "")
            message_type=str(sensor.get("message_type") or ("std_msgs/msg/Bool" if state else ""))

            # Also make sure it has a valid id, skip all sensors that do not have an id
            if not sensor_id: continue

            # Pull target microcontrollers, handling the diffrent formates that it's supports or defaulting to self.microcontrollers if none or given
            value=sensor.get("microcontrollers")
            microcontrollers=[value] if isinstance(value, str) and value else [item for item in (value if isinstance(value, (list, tuple)) else []) if item]
            if not microcontrollers: microcontrollers=list(self.microcontrollers)

            # Pull /topic message class for later use, skipping if an invalid message_type was given in the config file
            message_class=None
            template=None
            if topic:
                try:
                    message_class=get_message(message_type)
                    template=message_class()
                except (ImportError, AttributeError, ValueError): continue

            # Variables that store diffrent values while system works through valid sensors
            paths=[]
            scales=[]
            kinds=[]
            fields=[]
            string="<"
            valid=True

            # Loop through the telemetry data parmas to handle type interactions
            for data_parma in (sensor.get("data") or []):
                # Pull the data element, and split it into it's lable and data type
                path, _, rest=data_parma.partition(":")
                data_type, _, scale=rest.partition("*")

                # Ensure data type matches valid data type, otherwise default to defualt type
                if data_type not in self.COMMAND_DATA_TYPES: data_type=self.telemetry["default_type"]

                # Pull /topic message class for indavidual use and make sure it's valid
                node=template
                if template is not None and not state:
                    # Build a message by working down the data path
                    try: 
                        for part in path.split("."): node=getattr(node, part)
                    except AttributeError: node=None

                    # Ensure that the built node is a valid type
                    if not isinstance(node, (int, float, bool)):
                        valid=False
                        break

                # Lastly add everything to the arrays for later use
                string+=self.COMMAND_DATA_TYPES[data_type][0]
                fields.append(path)
                paths.append(path.split("."))
                scales.append(float(scale) if scale else 1.0)
                kinds.append(type(node) if node is not None and not state else float)
            if not valid: continue

            # Lastly pull the rate and timeout data, and ensure it's valid
            rate=float(sensor.get("rate", 0.0))
            timeout=float(sensor.get("timeout", 0.0))
            if state and timeout<=0: timeout=max(rate*2, 0.5)

            # If all checks and message building passes combine everything into the telemetry object for later use
            self.telemetry["data"][name]={
                "type": kind, "id": sensor_id, "state": state, "topic": topic, "format": string, "size": struct.calcsize(string),
                "fields": fields, "paths": paths, "scales": scales, "kinds": kinds, "microcontrollers": microcontrollers,
                "message_class": message_class, "publisher": None,
                "rate": rate, "timeout": timeout, "mode": str(sensor.get("rate_mode", "latest")),
                "latest": None, "last_values": None, "fresh": False, "arrived": None, "last_sent": 0.0,
                "sums": [0.0]*len(fields), "count": 0,
            }

            # Also log valid micrcocontrollers, and create the telemetry publishers
            for microcontroller_name in microcontrollers: self.telemetry["lookup"].setdefault(microcontroller_name, {})[sensor_id]=name
            if message_class: self.telemetry["data"][name]["publisher"]=self.create_publisher(message_class, topic, 10)

    # Do all the work needed for the diffrent defined serial commands and thier needed topics
    def initialize_commands(self):
        # Pull inital command parmas, seting up the default command parmas that the class needs
        params=self.get_parameters_by_prefix("serial.commands")
        default_topic=params["default_topic"].value if "default_topic" in params else "/serial/command"
        self.commands["blocking_timer"]=float(params["blocking_timer"].value) if "blocking_timer" in params else 0.0
        default_type=str(params["default_type"].value) if "default_type" in params else "int8"
        self.commands["default_type"]=default_type if default_type in self.COMMAND_DATA_TYPES else "int8"

        # Remap the command parma into an directory
        raw={}
        for key, parameter in params.items():
            parts=key.split(".")
            if len(parts)==2: raw.setdefault(parts[0], {})[parts[1]]=parameter.value

        # Pull all microcontrollers that commands will be sent to
        for entry in raw.values():
            value=entry.get("microcontrollers")
            entry["microcontrollers"]=[value] if isinstance(value, str) and value else [name for name in (value if isinstance(value, (list, tuple)) else []) if name]

        # /cmd_vel is a special case and must be handled accordingly
        velocity_parma=raw.pop("cmd_vel", None)
        if velocity_parma is not None: 
            # Setup the command, making sure that motor commands are sent, along with other command properties that the command needs
            self.commands["cmd_vel"]={
                "target": velocity_parma.get("target") or "motor",
                "linear_direction":-1.0 if float(velocity_parma.get("linear_direction", 1.0))<0 else 1.0,
                "angular_direction":-1.0 if float(velocity_parma.get("angular_direction", 1.0))<0 else 1.0,
                "blocking_id": int(velocity_parma.get("blocking_id", 2)),
                "microcontrollers": velocity_parma["microcontrollers"],
                "scale": int(velocity_parma.get("scale", 127)),
            }
            # Lastly pull/get the topic and the message type
            topic=velocity_parma.get("topic") or "/cmd_vel"
            message_type=TwistStamped if velocity_parma.get("stamped", False) else Twist
            # Lastly create subscription for reading the topics data
            self.commands["subscriptions"]["cmd_vel"]=self.create_subscription(message_type, topic, partial(self.process_command, "cmd_vel"), 10)

        # After default settings and special cases have been handled, handle the standard command cases
        topics={}
        for name, command_parma in raw.items():

            ########## AI ##########
            command_type=str(command_parma.get("type") or ("data_last" if "message_type" in command_parma else "command"))
            if "message_type" in command_parma or command_type.startswith("data_"):
                data_id=str(command_parma.get("id", ""))
                if not data_id or (command_type!="data_state" and "message_type" not in command_parma):
                    self.get_logger().error(f"data command '{name}' skipped, it needs an id (and a message_type unless it is data_state)")
                    continue
                message_class=None
                template=None
                if command_type!="data_state":
                    try:
                        message_class=get_message(command_parma["message_type"])
                        template=message_class()
                    except (ImportError, AttributeError, ValueError):
                        self.get_logger().error(f"data command '{name}' skipped, unknown message_type '{command_parma['message_type']}'")
                        continue

                paths=[]
                scales=[]
                limits=[]
                field_names=[]
                string="<"
                valid=True
                if command_type=="data_state":
                    string="<?"
                    limits=[("?", None, None)]
                    field_names=["state"]
                else:
                    for data_parma in command_parma.get("data", []):
                        path, _, rest=data_parma.partition(":")
                        data_type, _, scale=rest.partition("*")
                        if data_type not in self.COMMAND_DATA_TYPES: data_type=self.commands["default_type"]
                        node=template
                        try:
                            for part in path.split("."): node=getattr(node, part)
                        except AttributeError: node=None
                        if not isinstance(node, (int, float, bool)):
                            self.get_logger().error(f"data command '{name}' skipped, '{path}' is not a number or bool field of {command_parma['message_type']}")
                            valid=False
                            break
                        data, low, high=self.COMMAND_DATA_TYPES[data_type]
                        string+=data
                        limits.append((data, low, high))
                        field_names.append(path)
                        paths.append(path.split("."))
                        scales.append(float(scale) if scale else 1.0)
                if not valid: continue

                data_topic=command_parma.get("topic") or default_topic
                rate=float(command_parma.get("rate", 0.0))
                timeout=float(command_parma.get("timeout", 0.0))
                if command_type=="data_state" and timeout<=0: timeout=max(rate*2, 0.5)
                self.commands["data"][name]={
                    "type": command_type,
                    "topic": data_topic if data_topic.startswith("/") else f"/{data_topic}",
                    "state": command_type=="data_state",
                    "command": {"name": name, "id": data_id, "format": string, "limits": limits, "fields": field_names, "microcontrollers": command_parma["microcontrollers"], "topic": data_topic},
                    "paths": paths, "scales": scales, "rate": rate, "timeout": timeout,
                    "mode": str(command_parma.get("rate_mode", "latest")),
                    "blocking_id": int(command_parma.get("blocking_id", -1)),
                    "latest": None, "last_values": None, "fresh": False, "arrived": None, "last_sent": 0.0,
                    "sums": [0.0]*len(limits), "count": 0,
                }
                if command_type!="data_state": self.commands["subscriptions"][name]=self.create_subscription(message_class, data_topic, partial(self.record_topic_data, name), qos_profile_sensor_data)
                continue
            ########## AI ##########
        
            # Pull the command id
            command_id=str(command_parma.get("id", ""))

            # For every command, store data for each command about it's byte limits, identifier which are not used arm_velocity, and if the command was defined
            limits=[]
            field_names=[]
            string="<"

            # Loop through the indavidual commands data, building a serial command
            for data_parma in command_parma.get("data", []):
                data_name, _, data_type=data_parma.partition(":")
                # If data type is not known default to the default_type data type 
                if data_type not in self.COMMAND_DATA_TYPES: data_type=self.commands["default_type"]

                # Build current data element into serial string
                data, low, high=self.COMMAND_DATA_TYPES[data_type]
                string+=data

                # Log the limits and names of the data string
                limits.append((data, low, high))
                field_names.append(data_name)

            # Finally record the serial command in the command object, along with it's other data
            command={"name": name, "id": command_id, "format": string, "limits": limits, "fields": field_names, "microcontrollers": command_parma["microcontrollers"], "topic": command_parma.get("topic") or default_topic}

            # Make sure that a topic exists before adding it to the command object
            topic=topics.setdefault(command["topic"], {})
            if command_id in topic: continue
            topic[command_id]=command

        # Loop throgh all topics, ensure that the command obejct has them logged, and ensure that subscription is created for each topic
        for topic_name, topic in topics.items():
            self.commands["topics"][topic_name]=topic
            self.commands["subscriptions"][topic_name]=self.commands["subscriptions"][topic_name]=self.create_subscription(SerialCommand, topic_name, partial(self.process_command, topic_name), 10)

    #===========================================================================
    # Microcontroller actions
    #===========================================================================

    # Open microcontrollers so that class can interact with them
    def open_microcontroller(self, microcontroller=None, state_messages=True):
        # Get the microcontroller name if given or from parmas
        if microcontroller==None: microcontroller_names=list(dict.fromkeys(key.split(".")[0] for key in self.get_parameters_by_prefix("serial.microcontrollers")))
        else: microcontroller_names={microcontroller}

        # Loop through all given microcontroller names
        for microcontroller_name in microcontroller_names:

            # Pull the microcontroller parma settings converting each layer to an object
            settings={}
            for key, parameter in self.get_parameters_by_prefix(f"serial.microcontrollers.{microcontroller_name}").items():
                splits=key.split(".")
                node=settings
                for split in splits[:-1]:
                    node=node.setdefault(split, {})
                node[splits[-1]]=parameter.value

            # Set each microcontroller settings equal to the latest parma value
            microcontroller_data=self.microcontrollers.setdefault(microcontroller_name, {"settings": {}, "serial": {}, "timing": {}})
            microcontroller_data["settings"]=settings

            # Record when the microcontroller was attempted to be opened, and attempt to open any none opened ones, ones already opened can be skipped, if microcontroller skip it
            if not settings.get("enabled", False): continue
            microcontroller_data["timing"].setdefault("last_attempt", time.monotonic())

            serial_connection=microcontroller_data["serial"].get("connection")
            if serial_connection is not None: continue

            # Attempt to connect to the microcontroller
            try:
                # If no port or baud rate is given attempt to find those parmas on it's own
                port=None
                try: port=settings.get("port") or self.find_port(microcontroller_name)
                except (serial.SerialException, OSError) as error: self.get_logger().error(f"{error}")
                baud_rate=settings.get("baud_rate") or self.find_baud_rate(port, settings.get("timeout", 0.1))
                if not port or not baud_rate: raise serial.SerialException("Missing microcontroller port/baud_rate")

                # Setup serial connection either with default settings or with parma settings
                connection=serial.Serial()
                connection.port=port
                # If baud rate is not given or detection fails default to standard port
                connection.baudrate=baud_rate or 115200         
                connection.timeout=settings.get("timeout", 0.1)

                # Ensure device won't reset and then open the device
                connection.dtr=False
                connection.rts=False
                connection.open()

                # Update connect state data
                microcontroller_data["serial"]["connection"]=connection
                microcontroller_data["timing"]["disconnection_error"]=False

                # If uplouding on start is enabled add queued uploud attempt
                upload_queued=False
                if settings.get("upload_on_start") and not microcontroller_data["timing"].get("start_upload_queued"):
                    microcontroller_data["timing"]["start_upload_queued"]=True
                    upload_queued=True
                    self.pending_actions.setdefault((microcontroller_name, "upload"), time.monotonic())

                # Return connection message
                if state_messages and not upload_queued: self.get_logger().info(f"{self.COLORS['bold_green']}{microcontroller_name}{self.COLORS['green']} Microcontroller started on {self.COLORS['bold_green']}{port}{self.COLORS['green']}")

            # If connection fails throw error, don't save any data and continue onto next device
            except (serial.SerialException, OSError) as error:
                # Pull microcontroller data needed for closing on error and timing info
                microcontroller_data["serial"]["connection"]=None
                reconnect_time=settings.get("reconnect_time", -1.0)
                timing=microcontroller_data["timing"]

                # If connection fails only report failure once, reconnection-attempts attempt in background
                if not timing.get("disconnection_error"):
                    timing["disconnection_error"]=True
                    # Log errors and disconnection status
                    if reconnect_time>=0.0: self.get_logger().info(f"{self.COLORS['bold_red']}{microcontroller_name}{self.COLORS['red']} microcontroller not detected on {port}, reattempting every {reconnect_time}s")
                    else: self.get_logger().info(f"{self.COLORS['bold_red']}{microcontroller_name}{self.COLORS['red']} microcontroller not detected on {port}, auto reconnect disabled")
                    self.get_logger().error(f"{error}")

                # Add board to queue system so that it can attempt to keep auto connecting
                if reconnect_time >= 0.0: self.pending_actions.setdefault((microcontroller_name, "reconnect"), time.monotonic()+reconnect_time)
                continue

    # Handle closing microcontrollers
    def close_microcontroller(self, microcontroller=None, state_messages=True):
        # Create a list of what microcontrollers to close
        if microcontroller is None: microcontroller_names=list(self.microcontrollers)
        else: microcontroller_names=[microcontroller]

        # For every micro controller do some check then attempt to close it
        for microcontroller_name in microcontroller_names:
            # Pull microcontroller data
            microcontroller_data=self.microcontrollers.get(microcontroller_name)

            # If it exists and is connected close connection, ignore errors, and log closure
            if microcontroller_data is None: continue
            connection=microcontroller_data["serial"].get("connection")
            if connection is not None:
                try: connection.close()
                except (serial.SerialException, OSError): pass
                if state_messages: self.get_logger().info(f"{self.COLORS['bold_red']}{microcontroller_name}{self.COLORS['red']} microcontroller closed")

            # Reset connection data
            microcontroller_data["serial"]["connection"]=None
            microcontroller_data["serial"].pop("buffer", None)

    # Handle restarting/reseting microcontrollers
    def restart_microcontroller(self, microcontroller_name=None, action="restart"):
        # Create a list of what microcontrollers to restart/reset
        if microcontroller_name is None: microcontroller_names=list(self.microcontrollers)
        else: microcontroller_names=[microcontroller_name]

        # For every attempt restart/reset behavoir
        for name in microcontroller_names:
            # Pull microcontroller connection data
            microcontroller_data=self.microcontrollers.get(name)
            if microcontroller_data is None: continue
            connection=microcontroller_data["serial"].get("connection")

            # If a reset is requested attempt to reset the microcontroller
            if action=="reset":
                if connection is None: continue
                try:
                    # Flipping dtr to true then false triggers a reset on the arduino
                    connection.dtr=True
                    time.sleep(0.1)
                    connection.dtr=False
                    connection.reset_input_buffer()
                    self.get_logger().info(f"{self.COLORS['bold_green']}{name}{self.COLORS['green']} Microcontroller reset")
                except (serial.SerialException, OSError): self.close_microcontroller(name, state_messages=False)
            # If a restart is requested attempt to restart the microcontroller
            elif action=="restart":
                # For a restart close connection and then reopen it
                self.close_microcontroller(name, state_messages=True)
                self.open_microcontroller(name, state_messages=True)

    # Upload sketch to micro controller
    def upload_sketch(self, name):
        # Pull sketch and microcontroller settings
        data=self.microcontrollers.get(name)
        if data is None: return
        settings=data["settings"]
        connection=data["serial"].get("connection")

        # Pull current sketch
        sketch=settings.get("sketch")
        sketch_param=self.get_parameters_by_prefix("serial.sketches").get(sketch)
        # Ensure that the sketch path actually exists, otherwise throw error
        if sketch_param is None:
            self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, '{self.COLORS['bold_red']}{sketch}{self.COLORS['red']}' not found")
            return
        # Also check to make sure that the file exists, by checking os, throwing error if os path does not exist
        sketch_file=os.path.join(self.REPO_ROOT, sketch_param.value)
        if not os.path.isfile(sketch_file):
            self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, '{self.COLORS['bold_red']}{sketch}{self.COLORS['red']}' not found")
            return

        # Ensure microcontroller is actually connected before uploading and get port
        if connection is None:
            self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, microcontroller not connected")
            return
        port=connection.port

        # Lastly pull the board type, either if it's defined or attempt to automatically find it, throw error otherwise
        board=settings.get("board") or self.find_board(port)
        if not board:
            self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, invalid board")
            return

        # If the microcontroller is open, make sure it is closed before uploading
        self.close_microcontroller(name, state_messages=False)

        # Attempt to upload the sketch to the microcontroller
        try:
            # Upload to microcontroller
            result=subprocess.run(["arduino-cli", "compile", "--upload", "--fqbn", board, "--port", port, os.path.dirname(sketch_file)], capture_output=True, text=True, timeout=300)

            # Based on result return status message
            if result.returncode==0: self.get_logger().info(f"{self.COLORS['bold_green']}{name}{self.COLORS['green']} uploaded sketch {self.COLORS['bold_green']}{sketch}{self.COLORS['green']} on {self.COLORS['bold_green']}{board}{self.COLORS['green']}, {self.COLORS['bold_green']}{port}{self.COLORS['green']}")
            else: self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed:\n{(result.stderr or result.stdout).strip()[-800:]}")
        # Handle additional errors that are thrown
        except FileNotFoundError: self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, arduino-cli not installed")
        except subprocess.TimeoutExpired: self.get_logger().error(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} upload failed, timed out")
        # Lastly reopen the microcontroller
        finally: self.open_microcontroller(name, state_messages=True)

    # Basic send command function
    def send_command(self, name, payload: bytes, command_id=""):
        # Pull microcontroller data
        data=self.microcontrollers.get(name)
        
        # Ensure microcontroller is connected 
        connection=data["serial"].get("connection") if data else None
        if connection is None: return False

        self.get_logger().info(f"{name}, {payload}")

        # Attempt to send command payload
        try: connection.write(payload)
        except (serial.SerialException, OSError): return False

        # Trigger replay logger to log payload if enabled
        self.log_replay(name, payload, command_id)
        return True
    
    #===========================================================================
    # Microcontroller infomation/states
    #===========================================================================

    # Loop through each microcontroller, read serial buffer data, and handle what happons to it's data
    def read_microcontrollers(self):
        # Loop through current list of microcontrollers for reading data
        for name, data in list(self.microcontrollers.items()):
            # Ensure target microcontroller is actually connected before attempting to read data
            connection=data["serial"].get("connection")
            if connection is None: continue

            # Create serial buffer and wait until buffer can be read, reading bytes on os to avoid blocking issues
            buffer=data["serial"].setdefault("buffer", bytearray())
            try: 
                if connection.in_waiting: buffer.extend(connection.read(connection.in_waiting))
            except (serial.SerialException, OSError): continue

            # Pull all telemetry and reorder for quick lookup
            ids=self.telemetry["lookup"].get(name, {})
            ordered=sorted(ids, key=len, reverse=True)

            # Loop which handles what happons to the serial buffer next
            while buffer:
                # Decode the buffer to find the telemetry id in the returned serial string to find the returned data
                telemetry_id=next((item for item in ordered if buffer.startswith(item.encode())), None)

                # No id was found in serial buffer, so dump the current buffer
                if telemetry_id is None:
                    if any(item.encode().startswith(bytes(buffer)) for item in ordered): break
                    del buffer[:1]
                    continue

                # If an id was found using the length record the data from the buffer (body), then delete the buffer
                entry=self.telemetry["data"][ids[telemetry_id]]
                end=len(telemetry_id)+entry["size"]
                if len(buffer)<end: break
                body=bytes(buffer[len(telemetry_id):end])
                del buffer[:end]

                # Lastly log the data results, recording properties about the data
                entry["arrived"]=time.monotonic()
                values=list(struct.unpack(entry["format"], body)) if entry["fields"] else []
                entry["latest"]=values
                entry["fresh"]=True
                entry["count"]+=1

                # Also create an average of the data for when the averaging mode is enabled
                for index, value in enumerate(values): entry["sums"][index]+=float(value)

    # Check if devices that have connection fails, to trigger reconnection code
    def check_microcontroller_connections(self):
        # For every microcontroller pull data and loop through them to handle connections
        for name, data in list(self.microcontrollers.items()):
            connection=data["serial"].get("connection")
            if connection is None: continue

            # Check device os connection, any detection failure or error triggers connection logic
            try:
                if not os.path.exists(connection.port): raise OSError("Device not detected")
                connection.in_waiting  
            # Device throw error or not detected, handle return error messages and restarting queue if enabled
            except (serial.SerialException, OSError): 
                # Pull microcontroller connection/name data, and ensure messages are not spammed
                data=self.microcontrollers.get(name)
                if data is None or data["serial"].get("connection") is None: return
                self.close_microcontroller(name, state_messages=False)
                data["timing"]["disconnection_error"]=True  
                reconnect_time=data["settings"].get("reconnect_time", -1.0)

                # If restarts are enabled create queued task that attempts device restarts based on restart time
                if reconnect_time>=0.0:
                    self.get_logger().info(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} microcontroller disconnected, reattempting every {reconnect_time}s")
                    self.pending_actions.setdefault((name, "reconnect"), time.monotonic()+reconnect_time)
                else: self.get_logger().info(f"{self.COLORS['bold_red']}{name}{self.COLORS['red']} microcontroller disconnected, auto reconnect disabled")

    # (Helper function) Attempt to automatically find the microcontroller port          
    def find_port(self, microcontroller_name):
        # Create a set of ports that are the config file to ensure they are not used
        active_ports=set()
        for key, parameter in self.get_parameters_by_prefix("serial.microcontrollers").items():
            parts=key.split(".")
            if len(parts)==2 and parts[1]=="port" and parts[0]!=microcontroller_name and parameter.value: active_ports.add(os.path.realpath(parameter.value))
        # Also ensure that no ports actively being used are not used for the new microcontroller
        for name, data in self.microcontrollers.items():
            connection=data.get("serial", {}).get("connection")
            if name!=microcontroller_name and connection is not None: active_ports.add(os.path.realpath(connection.port))

        # Create a list of all computer serial ports
        for found_port in serial.tools.list_ports.comports():
            # Skip any ports already in use
            if os.path.realpath(found_port.device) in active_ports: continue

            # Scan port vid, pid, and description if any of that matches known microcontrollers type accept it as a port connection
            if any(found_port.vid==known["vid"] and known["pid"] in (None, found_port.pid) for known in self.KNOWN_DEVICES): return found_port.device
            if any(text.lower() in (found_port.description or "").lower() for text in self.KNOWN_DEVICE_DESCRIPTIONS): return found_port.device
        return None

    # (Helper function) Attempt to automatically find microcontroller baud rate
    def find_baud_rate(self, port, timeout):
        # Attempt scan on each of known baud rates
        for baud_rate in self.VALID_BAUD_RATES:
            # Setup a basic microcontroller serial connection
            scan=serial.Serial()
            scan.port=port
            scan.baudrate=baud_rate
            scan.timeout=max(timeout, 3.0)
            scan.dtr=False
            scan.rts=False

            # Attempt to open connection and data microcontroller data
            try:
                scan.open()
                time.sleep(0.1)
                scan.reset_input_buffer()
                data=scan.read(64)
            except (serial.SerialException, OSError): return None
            # If it was able to read data close connection
            finally: scan.close()
            # Text check, check what baud rate returns physical lines which are diffrent from random jank data
            if b"\n" in data and sum(32<=byte<127 or byte in (9, 10, 13) for byte in data)/len(data)>=0.95: return baud_rate
        return None

    # (Helper function) Automatically send a request to arduino-cli to auto pull micro-controller board type
    def find_board(self, port):
        # Attempt to look for microcontroller baord
        try:
            # Create a process containing the arduino-cli board list command, to pull microcontroller data
            result=subprocess.run(["arduino-cli", "board", "list", "--format", "json"], capture_output=True, text=True, timeout=5)

            # Pull all return board data
            output=json.loads(result.stdout)
            detected=output.get("detected_ports", []) if isinstance(output, dict) else output

            # Loop through every return entry to find board data
            for entry in detected:
                # Check address, boards, and fqbn data to attempt to match the entry to the microcontroller
                address=entry.get("port", {}).get("address")
                if not address or os.path.realpath(address)!=os.path.realpath(port): continue
                matches=entry.get("matching_boards") or entry.get("boards") or []
                if matches and matches[0].get("fqbn"): return matches[0]["fqbn"]
        except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError, OSError): pass

        # Extra check to ensure the found boards match existing board stuff
        for found_port in serial.tools.list_ports.comports():
            if os.path.realpath(found_port.device)!=os.path.realpath(port): continue
            for known in self.KNOWN_DEVICES: 
                if found_port.vid==known["vid"] and known["pid"] in (None, found_port.pid): return known["fqbn"]
        return None

    #===========================================================================
    # Timers
    #===========================================================================

    # For queued actions run the them when possible or after a delay
    def process_pending_actions(self):
        # Pull the current requests, executing only if timing is correct
        now=time.monotonic()
        for (name, action), due in list(self.pending_actions.items()):
            if due>now: continue

            # Queue fulfilled, delete and do trigger actions
            del self.pending_actions[(name, action)]
            if action in ("restart", "reset", "upload"):

                # For requested triggers, reset parma and trigger function
                self.set_parameters([Parameter(f"serial.microcontrollers.{name}.{action}", Parameter.Type.BOOL, False)])
                if action=="upload": self.upload_sketch(name)
                else: self.restart_microcontroller(name, action)

            # Handle system actions without reseting parma
            elif action=="reconnect": self.open_microcontroller(name)

            # Handle serial trigger action
            elif action=="trigger":
                self.set_parameters([Parameter(f"serial.commands.{name}.type", Parameter.Type.STRING, "none")])
                self.process_data_commands(name, force=True)

    # Process all of the command data interactions like rate, averages, and other stuff that needs to be handled before command can be handled
    def process_data_commands(self, name=None, force=False):
        # Pull time data and data commands
        now=time.monotonic()
        names=[name] if name else list(self.commands["data"])

        # Loop through data commands to handle each one
        for data_name in names:
            # Pull data command and ensure that it has a valid entry
            entry=self.commands["data"].get(data_name)
            if entry is None: continue

            # Pull type, and ensure it matches valid types, and that the rate also matches the defined rate
            kind="data_trigger" if force else entry.get("type", "none")
            if not force and kind not in ("data_last", "data_repete", "data_state"): continue
            if not force and entry["rate"]>0 and now-entry["last_sent"]<entry["rate"]: continue

            # Ensure the microcontroller is still alive
            if entry["state"]: values=[entry["arrived"] is not None and now-entry["arrived"]<=entry["timeout"]]
            # If it alive continue with handling the normal interactions
            else:
                # If data is a fresh entry, reset all sums/counts to default
                if entry["fresh"]:
                    # Pull limits, averages, and create an empty array for storing updated data
                    codes=[limit[0] for limit in entry["command"]["limits"]]
                    average=entry["mode"]=="average" and entry["count"]>0
                    values=[]

                    # Loop through limit/average enetryies to update that data which is needed
                    for index, code in enumerate(codes):
                        value=entry["latest"][index]
                        if code=="?": values.append(value)
                        else: values.append((entry["sums"][index]/entry["count"] if average else value)*entry["scales"][index])
                    
                    # Update loop tracking variables
                    entry["last_values"]=values
                    entry["fresh"]=False
                    entry["sums"]=[0.0]*len(codes)
                    entry["count"]=0
                # For all loop data types just continue the loop
                elif kind=="data_last": continue
                elif entry["last_values"] is None: continue
                elif kind=="data_repete" and entry["timeout"]>0 and now-entry["arrived"]>entry["timeout"]: continue
                # Sepcial case for last value data type
                values=entry["last_values"]

            # Lastly update the timing and send command to be processed
            entry["last_sent"]=now
            self.process_command(data_name, {"command": entry["command"], "values": values, "blocking_id": entry["blocking_id"]})

    # Watch topics to see when they become active before subscribing to them
    def topic_discovery(self):
        # Loop through every command topic the system should be subscribed to
        topic_types=None
        for name, entry in self.commands["data"].items():
            # Ensure that topic is not already subscribed to
            if not entry["state"] or name in self.commands["subscriptions"]: continue

            # Pull topic and type, to ensure topic is the correct one the system is targeting
            if topic_types is None: topic_types=dict(self.get_topic_names_and_types())
            types=topic_types.get(entry["topic"])
            if not types: continue

            # All checks pass, create and store that subscription
            self.commands["subscriptions"][name]=self.create_subscription(get_message(types[0]), entry["topic"], partial(self.record_topic_data, name), qos_profile_sensor_data, raw=True)

    # Handle telemetry which includes publishing it
    def process_telemetry(self):
        # Get time that telemetry triggered, and loop through each telemetry element
        now=time.monotonic()
        for name, entry in self.telemetry["data"].items():
            # Pull publisher data, if it is invalid or if it exceeds the rate limit continue
            publisher=entry["publisher"]
            if publisher is None: continue
            if entry["rate"]>0 and now-entry["last_sent"]<entry["rate"]: continue

            # If telemetry is purly the state property and it passes timeout check, simply publish boolean 
            if entry["state"]:
                msg=entry["message_class"]()
                msg.data=entry["arrived"] is not None and now-entry["arrived"]<=entry["timeout"]
                entry["last_sent"]=now
                publisher.publish(msg)
                continue

            # Else handle the other telemetry interactions
            if entry["fresh"]:
                # Pull rate_mode data
                average=entry["mode"]=="average" and entry["count"]>0
                values=[]

                # For all of the recently pull values, correctly average them if mode is enabled
                for index, value in enumerate(entry["latest"]):
                    if isinstance(value, bool): values.append(value)
                    else: values.append((entry["sums"][index]/entry["count"] if average else value)*entry["scales"][index])
                
                # Updating infomation needed for averaging
                entry["last_values"]=values
                entry["fresh"]=False
                entry["sums"]=[0.0]*len(entry["fields"])
                entry["count"]=0
            # For the other modes nothing extra needs to be done, so skip them
            elif entry["type"]=="telemetry_last": continue
            elif entry["last_values"] is None: continue
            elif entry["timeout"]>0 and now-entry["arrived"]>entry["timeout"]: continue

            # Pull the message class for publishing
            msg=entry["message_class"]()

            # Correctly round values and formate the paths correctly
            for path, kind, value in zip(entry["paths"], entry["kinds"], entry["last_values"]):
                node=msg
                for part in path[:-1]: node=getattr(node, part)
                setattr(node, path[-1], int(round(value)) if kind is int else kind(value))
            
            # Lastly update message time, and publish message
            entry["last_sent"]=now
            publisher.publish(msg)

    #===========================================================================
    # Other
    #===========================================================================

    # Write command to replay file if enabled
    def log_replay(self, name, payload, command_id=""):
        # Make sure data was actually passed through and pull microcontroller name
        data=self.microcontrollers.get(name)
        if data is None: return

        # Pull settings and ensure replay logging is enabled
        settings=data["settings"]
        if not settings.get("replay_logging"): return

        # When a command is sent to be logged, pull include/exclude list, handling the logic to exclude/include certain commands
        include=settings.get("replay_logging_include") or []
        exclude=settings.get("replay_logging_exclude") or []
        if isinstance(include, str): include=[include]
        if isinstance(exclude, str): exclude=[exclude]
        include=[str(item) for item in include]
        exclude=[str(item) for item in exclude]
        if include and command_id not in include: return
        if command_id in exclude: return

        # Pull the current replay file, and ensure it's still valid
        if data["serial"].get("replay_file") is None: self.open_replay_log(name)
        replay_file=data["serial"].get("replay_file")
        if replay_file is None: return

        # Pull current time and formate into the formate that is required, updating the timing replay object
        now=time.monotonic()
        delta=min(int((now-data["timing"]["replay_last"])*1000), 0xFFFFFFFF)
        data["timing"]["replay_last"]=now

        # Write command to file
        try:
            replay_file.write(struct.pack("<IH", delta, len(payload))+payload)
            replay_file.flush()
        except (OSError, ValueError): pass 
        
    # Open replay file for command logging
    def open_replay_log(self, name):
        # Pull replay logging parmas
        data=self.microcontrollers[name]
        settings=data["settings"]
        if not settings.get("replay_logging") or data["serial"].get("replay_file") is not None or data["timing"].get("replay_failed"): return

        # Pull the folder using the REPO_ROOT
        folder=os.path.join(self.REPO_ROOT, settings.get("replay_logging_folder", "Logs/replays"))
        try:
            # Make sure folder exists, and create file name
            os.makedirs(folder, exist_ok=True)
            path=os.path.join(folder, f"replay_{self.START_STAMP}.bin")

            # Extra counter loop incase there are multiple microcontrollers tryring to saving logs to the same file
            counter=2
            while os.path.exists(path):
                path=os.path.join(folder, f"replay{counter}_{self.START_STAMP}.bin")
                counter+=1

            # Open file, writing start time
            replay_file=open(path, "wb")
            replay_file.write(b"RPL1"+struct.pack("<d", time.time()))
            replay_file.flush()

            # Record replay file data for later use
            data["serial"]["replay_file"]=replay_file
            data["timing"]["replay_last"]=time.monotonic()
        
        # If error occors stop replays
        except OSError:
            data["timing"]["replay_failed"]=True

    # Record all data that is needed by subscribed topics
    def record_topic_data(self, name, msg):
        # Pull command entery, and log current time
        entry=self.commands["data"][name]
        entry["arrived"]=time.monotonic()

        # Ensure passed in msg is a valid bytes msg
        if isinstance(msg, bytes): return

        # Loop through the config path, building a valid path that ros can use
        values=[]
        for path in entry["paths"]:
            node=msg
            for part in path: node=getattr(node, part)
            values.append(node)

        # Record the core details about the topic message, like if the message is "fresh" and isn't repeted, and everaging details
        entry["latest"]=values
        entry["fresh"]=True
        entry["count"]+=1
        for index, value in enumerate(values): entry["sums"][index]+=float(value)

    # For each defined command handling processing them and sending thier data with data formating
    def process_command(self, source, msg):
        # If a normal command was sent create variables for each part of the command: command, topic, microcontrollers etc
        if isinstance(msg, dict):
            command=msg["command"]
            topic=command["topic"]
            microcontrollers=command["microcontrollers"]
            blocking_id=msg["blocking_id"]
            values_in=msg["values"]
        # If the special cmd_vel case was used handle that special case
        elif isinstance(msg, (Twist, TwistStamped)):
            # Pull config andtwiest data
            config=self.commands["cmd_vel"]
            twist=getattr(msg, "twist", msg)

            # Find the twist data command, returning if no cmd_vel was found
            command=next((item for group in self.commands["topics"].values() for item in group.values() if item["name"]==config["target"]), None)
            if command is None: return

            # Calulate the linear and angular magnetudes, applying direction config term, and mapping between -1.0, and 1.0
            linear=max(-1.0, min(1.0, twist.linear.x))*config["linear_direction"]
            angular=max(-1.0, min(1.0, twist.angular.z))*config["angular_direction"]

            # Convert the power values into left and right motors magnetudes, and calulate a peak to handle cases where cmd_vel is above 1.0
            left=linear-angular
            right=linear+angular
            peak=max(abs(left), abs(right), 1.0)

            # Crate variables for terms, and rescale motor magnetudes based on peak value and scale value
            topic=command["topic"]
            microcontrollers=config["microcontrollers"]
            blocking_id=config["blocking_id"]
            values_in=[left/peak*config["scale"], right/peak*config["scale"]]

        # The last case is when an unknown command is sent, the system will still attempt to handle the unknown comamnd type
        else:
            # Create variables to store core command data
            topic=source
            microcontrollers=list(msg.microcontrollers)
            blocking_id=msg.blocking_id
            values_in=msg.data
            group=self.commands["topics"][topic]

            # Command ids, primary commands such as M, need to be handled diffrently from sensor commands such as IMU
            if msg.id: command=group.get(msg.id)
            elif len(group)==1: command=next(iter(group.values()))
            else: command=None

            # If command has a valid id handle the other data that the command needs
            if command is None and msg.id:
                # Pull command data type to make sure it's a valid format and get length of command
                type_name=self.commands["default_type"]
                code, low, high=self.COMMAND_DATA_TYPES[type_name]
                count=len(values_in)

                # Create an command object to store the commands data
                command={"name": f"unknown_{msg.id}", "id": msg.id, "format": "<"+code*count, "limits": [(code, low, high)]*count, "fields": [f"value{i}" for i in range(count)], "microcontrollers": [], "topic": topic}
            # If there is no id at all return, the command cannot be read
            elif command is None: return

        # For commands that are defined on the config return if an attempt is made without the full data
        if len(values_in)!=len(command["limits"]): return

        # Create serial message, first by looping through each bit of data
        values=[]
        for (code, low, high), field_name, value in zip(command["limits"], command["fields"], values_in):
            # For the standard data types the data can just be appended, with a type conversion
            if code=="?": values.append(bool(value))
            elif code=="f": values.append(float(value))
            # If a none standard data type is used, change the format and round the new number to ensure that it fits into the spcified data type
            else:
                number=int(round(value))
                if number<low or number>high: number=min(max(number, low), high)
                values.append(number)

        # Lastly packup the data by encoding it into the correct serial format.
        packed=struct.pack(command["format"], *values)
        # For standard command, pack into the 2026 serial format
        if len(command["id"])==1:
            payload=command["id"].encode()+packed
            frame=bytes([self.START_BYTE, len(payload)])+payload+bytes([self.END_BYTE])
        # Otherwise pack into just a base format, without using any special formates
        else: frame=command["id"].encode()+packed

        # Pull a list of connected mictocontrollers and target mictocontroller to send commands on
        targets=list(microcontrollers or command["microcontrollers"])
        if not targets: targets=[name for name, data in self.microcontrollers.items() if data["serial"].get("connection") is not None]
        if not targets: return

        # Pull blocking timer object and loop through each target microcontroller
        timer=self.commands["blocking_timer"]
        for name in targets:
            # Pull mmicocontroller instance
            data=self.microcontrollers.get(name)
            # When function is called, update blocking id and blocking timer so that each command is sent correctly
            if timer>0 and blocking_id>=0 and data is not None:
                timing=data["timing"]
                now=time.monotonic()
                level=timing.get("block_level", -1) if now<timing.get("block_until", 0.0) else -1
                if blocking_id<level: continue
                timing["block_level"]=blocking_id
                timing["block_until"]=now+timer

            # If all checks pass finally send serial command to target mictocontroller
            self.send_command(name, frame, command["id"])

    #===========================================================================
    # Node showdown
    #===========================================================================

    # Shut down ros node
    def destroy_node(self):
        # Close all opened microcontrollers
        self.close_microcontroller(state_messages=False)
        # Ensure all replay log files are closed, by pulling the replay file name and attempting to close it
        for data in self.microcontrollers.values():
            replay_file=data["serial"].pop("replay_file", None)
            if replay_file is not None:
                try: replay_file.close()
                except OSError: pass
        # Finally destory node
        super().destroy_node()

# Node initalization 
def main():
    rclpy.init()
    node=SerialBridgeNode()
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
            node.destroy_node()
            if rclpy.ok(): rclpy.shutdown()

if __name__ == "__main__":
    main()