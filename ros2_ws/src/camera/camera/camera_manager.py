#!/usr/bin/env python3
import time, os, yaml, rclpy, cv2, threading, av, math
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from ament_index_python.packages import get_package_share_directory
from fractions import Fraction
import pyrealsense2 as rs
import numpy as np
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CompressedImage, Imu, CameraInfo
from geometry_msgs.msg import PoseWithCovarianceStamped
from rcl_interfaces.msg import SetParametersResult

# Camera manager class, handles all camera and camera feed interactions and live changes
class CameraManager(Node):
    def __init__(self):
        super().__init__("camera_manager")

        # Define a cameras config file parameter. Have it default to config/cameras.yaml if not specifiied
        cameras_config=os.path.join(get_package_share_directory("camera"), "config", "cameras.yaml")
        self.declare_parameter("cameras_config", cameras_config)
        # Create flattend params of all param configs
        with open(self.get_parameter("cameras_config").value, "r") as file: data=yaml.safe_load(file)
        self.declare_flatend_params(data["camera_manager"]["ros__parameters"])

        # Define a presistance parameter. Which when true makes the node record changes when an param change is detected, either local or an global change can be made
        self.declare_parameter("persistent", True)
        self.persistent=self.get_parameter("persistent").value
        self.declare_parameter("persistent_type", "global")
        self.persistent_type=self.get_parameter("persistent_type").value

        # Camera/Feed instances, holds key camera/feed info and methiods for accessing it, and our publisher bridge
        self.cameras={}
        self.feeds={}
        self.bridge=CvBridge()

        # Speical parma changes that relaunch cameras
        self.pending=set()
        self.pending_timer=self.create_timer(0.5, self.apply_param_changes)
        self.pending_timer.cancel()

        # Handle dynamic switching cameras
        self.active={}
        for name, param in self.get_parameters_by_prefix("feeds").items():
            group, feed_name, *field=name.split(".")
            if field==["camera"] and len(param.value): self.active[f"feeds.{group}.{feed_name}"]=int(param.value[0])

        # Launch the inital cameras
        self.open_cameras()

        # Create an parameters callback to support live camera config changes
        self.add_on_set_parameters_callback(self.on_params_change)

    # Event which triggers when parma change comments are sent to have live configuable cameras
    def on_params_change(self, params):
        # Check if persistent parmas are enabled and if so what type of persistent local or global
        for param in params:
            if param.name=="persistent": self.persistent=param.value
            if param.name=="persistent_type": self.persistent_type=param.value

        # Create a parms set change tracker to track changes
        changed=set()
        for param in params:
            # For cameras or feeds track each parm and each value
            if not param.name.startswith(("cameras.", "feeds.")): continue
            parts=param.name.split(".")
            if len(parts)==4 and parts[0]=="feeds" and parts[3]=="camera" and self.has_parameter(param.name) and len(param.value) and sorted(param.value)==sorted(self.get_parameter(param.name).value):
                self.active[".".join(parts[:3])]=int(param.value[0])
            else: changed.add(param.name)
        # When old cameras and feeds do not match new cameras and feeds queue a parmas update
        if changed:
            self.pending|=changed
            self.pending_timer.reset()

        # Get parma persistent variable
        if not self.persistent: return SetParametersResult(successful=True)
        if not any(param.name.startswith(("cameras.", "feeds.")) for param in params): return SetParametersResult(successful=True)

        # Create variables for the path to the config
        config_path=self.get_parameter("cameras_config").value
        config_paths=[config_path]
        if self.persistent_type=="global" and "/install/" in config_path: config_paths.append(os.path.join(config_path.split("/install/")[0], "src", "camera", "config", "cameras.yaml"))

        # If enabled loop through parmas saved in ram and push them to
        for path in dict.fromkeys(os.path.realpath(path) for path in config_paths):
            # Log comments to make them presistant between global parma changes
            if not os.path.exists(path): continue
            with open(path, "r") as file: old_text=file.read()
            data=yaml.safe_load(old_text)
            for param in params:
                if not param.name.startswith(("cameras.", "feeds.")): continue
                node=data["camera_manager"]["ros__parameters"]
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
        if isinstance(value, dict):
            for param_key, param_value in value.items(): self.declare_flatend_params(param_value, f"{path}{param_key}.")
        # Once flattened declare path as ros parameter for live param changes
        else:
            full_path=path.rstrip(".")
            if not self.has_parameter(full_path): self.declare_parameter(full_path, value)

    # Pull all aruco localizer parmas for when an apriltag is active
    def localizer_config(self, feed_key):
        configuration={}
        for name, param in self.get_parameters_by_prefix(f"{feed_key}.apriltag_localizer").items():
            *parents, leaf=name.split(".")
            node=configuration
            for key in parents: node=node.setdefault(key, {})
            node[leaf]=param.value
        return configuration

    # Camera/sensor location consist of xyz position and yaw, pitch, and roll relative to the camera base_link
    def offset_matrix(self, camera_name, feed_key):
        # Loop through camera location and sensor location parmas
        matrices=[]
        for prefix in (f"cameras.{camera_name}.location", f"{feed_key}.sensor_location"):
            # Get list of sensor and camera locations
            values=[]
            for name in ("position_offset", "angle_offset"):
                value=list(self.get_parameter(f"{prefix}.{name}").value) if self.has_parameter(f"{prefix}.{name}") else []
                values.append([float(item) for item in (value + [0.0] * 3)[:3]])

            # Split up position and angle and convert angle from degrees to radians
            position, angles=values
            pitch, yaw, roll=(math.radians(angle) for angle in angles)

            # Convert angles into vector form
            cr, sr = math.cos(roll), math.sin(roll)
            cp, sp = math.cos(pitch), math.sin(pitch)
            cy, sy = math.cos(yaw), math.sin(yaw)

            # Combine angle vectors into unit matrix
            Rz=np.array([[cy, -sy, 0.0],[sy, cy, 0.0],[0.0, 0.0, 1.0]])
            Ry=np.array([[cp, 0.0, sp],[0.0, 1.0, 0.0],[-sp, 0.0, cp]])
            Rx=np.array([[1.0, 0.0, 0.0],[0.0, cr, -sr],[0.0, sr, cr]])

            # Combine all angles and position into an single matrix, merging both the sensor and camera position matrices
            matrix=np.eye(4)
            matrix[:3, :3]=Rz @ Ry @ Rx
            matrix[:3, 3]=position
            matrices.append(matrix)

        # Return final angle and position matrix
        return matrices[0] @ matrices[1]

    # Query cameras and thier supported camera modes
    def get_supported_modes(self, device, stream, camera_format, sensor_index):
        # Query then loop through devices and profiles
        modes=set()
        for device_sensor in device.query_sensors():
            for profile in device_sensor.get_stream_profiles():
                # Make sure cameras match then save camera profile
                if profile.stream_type()!=stream or profile.stream_index()!=sensor_index: continue
                if camera_format and profile.format()!=camera_format: continue
                if not camera_format: modes.add((0, 0, profile.fps()))
                else:
                    video=profile.as_video_stream_profile()
                    modes.add((video.width(), video.height(), video.fps()))
        # Sort camera modes for easy access and return all camera modes
        return sorted(modes)

    # Mode pick which picks the best camera/feed modes depending on what is needed
    def pick_mode(self, modes, feeds):
        # Pull core camera settings
        width=max(int(feed.get("adjustments.width", 0)) for feed in feeds)
        height=max(int(feed.get("adjustments.height", 0)) for feed in feeds)
        fps=max(int(feed.get("adjustments.framerate", feed.get("fps", 0))) for feed in feeds)

        # If no parmas exist pull the default/largest values
        if not width and not height: width, height=max(mode[0] for mode in modes), max(mode[1] for mode in modes)
        if not fps: fps=max(mode[2] for mode in modes)

        # Check all parmas to find which width, hight, and fps works best
        fits=[mode for mode in modes if mode[0]>=width and mode[1]>=height and mode[2]>=fps]
        if fits: return min(fits, key=lambda mode:(mode[0]*mode[1], mode[2]))
        sized=[mode for mode in modes if mode[0]>=width and mode[1]>=height]
        if sized: return max(sized, key=lambda mode:(mode[2], -mode[0]*mode[1]))
        return max(modes, key=lambda mode:(mode[0]*mode[1], mode[2]))

    # Launch cameras and the diffrent needed camera sensors
    def open_cameras(self, camera_name=None, overrides=None):
        overrides=overrides or {}
        # Create set of cameras to loop through
        if camera_name is not None: camera_set=[camera_name]
        else:
            camera_set=set()
            for name in self.get_parameters_by_prefix("cameras"): camera_set.add(name.split(".")[0])
        for camera_name in camera_set:
            # Pull uuid/id from each camera instance
            camera_uuid=overrides.get(f"cameras.{camera_name}.uuid", self.get_parameter(f"cameras.{camera_name}.uuid").value)
            camera_id=overrides.get(f"cameras.{camera_name}.id", self.get_parameter(f"cameras.{camera_name}.id").value)

            # Check to see if pyrealsense2 sees camera device. Skip and output error if not found
            usb_camera=str(camera_uuid).startswith("/dev")
            if usb_camera: found=os.path.exists(camera_uuid)
            else:
                devices={device.get_info(rs.camera_info.serial_number): device for device in rs.context().query_devices()}
                found=camera_uuid in devices
            if not found:
                 self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: Not found")
                 continue

            # Enabled found camera devices
            camera_pipeline=camera_config=camera_capture=None
            if not usb_camera:
                camera_pipeline=rs.pipeline()
                camera_config=rs.config()
                camera_config.enable_device(camera_uuid)

            # Specifies how to open each realsense sensor/camera, formate, and sensor to use in the case of the infered camera
            camera_feed_mappings={
                "rgb": (rs.stream.color, rs.format.bgr8, 0),
                "depth": (rs.stream.depth, rs.format.z16, 0),
                "inferred1": (rs.stream.infrared, rs.format.y8, 1),
                "inferred2": (rs.stream.infrared, rs.format.y8, 2),
                "accel": (rs.stream.accel, None, 0),
                "gyro": (rs.stream.gyro, None, 0),
            }

            # Pull set of camera feeds and all of it's parameters
            feed_config=self.get_parameters_by_prefix("feeds")
            camera_feeds={}
            for name, param in feed_config.items():
                group, feed_name, *field=name.split(".")
                camera_feeds.setdefault((group, feed_name), {})[".".join(field)]=param.value

            # Create a types set which includes an set of all enabled camera types
            types_set=set()
            for camera_feed in camera_feeds.values():
                if camera_feed.get("enabled") and camera_id in camera_feed.get("camera", []): types_set.add(camera_feed.get("type"))

            # Speical handler for regular cameras which only support reg cameras
            if usb_camera:
                if types_set-{"rgb"}: self.get_logger().warning(f"Camera #{camera_id}, {camera_uuid}: only rgb is supported on regular cameras, ignoring {types_set-{'rgb'}}")
                types_set&={"rgb"}

            # For all of the camera types go and enable the needed camera streams
            if not types_set: continue
            camera_modes={}

            # Handler that handles opening usb cameras
            if usb_camera:
                # Start video capture on camera stream
                camera_capture=cv2.VideoCapture(camera_uuid, cv2.CAP_V4L2)
                if not camera_capture.isOpened():
                    self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: Could not open device")
                    continue
        
                # Sat vdeo format and buffer size
                camera_capture.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))   
                camera_capture.set(cv2.CAP_PROP_BUFFERSIZE, 1)     
        
                # Attempt to adjust framerate and resulutuion of camera
                width, height=int(camera_capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(camera_capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
                fps=int(camera_capture.get(cv2.CAP_PROP_FPS)) or 30

                # Save camera modes to variable
                camera_modes={"rgb": (width, height, fps)}

                # Return error if camera open fails
                if camera_capture is None:
                    self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: Could not open device")
                    continue
            # Else handle opening realsense camera
            else:
                # If am imu sensor request is made add accel and gyro to sensors to open, opening both for the imu sensor
                if "imu" in types_set: types_set|={"accel", "gyro"}

                # For each camera sensor, loop through the ones that need to be opened and open them
                for type in types_set:
                    if type not in camera_feed_mappings: continue
                    stream, camera_format, sensor=camera_feed_mappings[type]

                    # Pull default camera settings for each feed type, pulling the supported camera modes
                    wanted=(type, "imu") if type in ("accel", "gyro") else (type,)
                    matches=[feed for feed in camera_feeds.values() if feed.get("enabled") and camera_id in feed.get("camera", []) and feed.get("type") in wanted]
                    modes=self.get_supported_modes(devices[camera_uuid], stream, camera_format, sensor)
                    if not modes: continue
                    width, height, fps=self.pick_mode(modes, matches)
                    camera_modes[type]=(width, height, fps)

                    # Enable the camera stream based needed camera formates
                    if camera_format: 
                        if sensor: camera_config.enable_stream(stream, sensor, width, height, camera_format, fps)
                        else: camera_config.enable_stream(stream, width, height, camera_format, fps)
                    else: camera_config.enable_stream(stream, rs.format.motion_xyz32f, fps)

                if "imu" in types_set and "accel" in camera_modes and "gyro" in camera_modes: camera_modes["imu"]=camera_modes["gyro"]

            # Skip camera if camera modes are invalid
            if not camera_modes: continue

            # Camera has been fully configured, attempt to start the camera
            if not usb_camera:
                try: pipeline_profile=camera_pipeline.start(camera_config)
                except RuntimeError as e:
                    self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: {e}")
                    continue

            # Handle camera intrinsics, the internal info the camera provides, required by some nodes
            intrinsics, info_publisher=None, None
            info_topic=self.get_parameter(f"cameras.{camera_name}.camera_info_topic").value if self.has_parameter(f"cameras.{camera_name}.camera_info_topic") else ""

            # If a camera has intrinsics attempt to featch it. Only realsense cameras not normal use support it so only realsense camera data needs to be pulled
            if "rgb" in camera_modes and info_topic:
                intr=pipeline_profile.get_stream(rs.stream.color).as_video_stream_profile().get_intrinsics()
                intrinsics={"width": intr.width, "height": intr.height, "fx": intr.fx, "fy": intr.fy, "ppx": intr.ppx, "ppy": intr.ppy, "coeffs": list(intr.coeffs)}
                info_publisher=self.create_publisher(CameraInfo, info_topic, 10)

            # Loop through camera parmas to find camera settings
            camera_feed_list=[]
            for (group, feed_name), feed in camera_feeds.items():
                # Pull type, enabled, topic and create publisher for each indavidual camera type
                feed_type=feed.get("type")
                if not feed.get("enabled") or camera_id not in feed.get("camera", []) or feed_type not in camera_modes or feed_type in ("accel", "gyro"): continue

                # For compressed video feeds check the parma settings, used to determin of /topic, /topic/compressed, or /custom_name is used for compressed feed
                raw_topic=feed.get("topic") or f"/{camera_name}"
                compressed_topic=feed.get("compression.compression_topic") or f"{raw_topic.rstrip('/')}/compressed"
                if not compressed_topic.startswith("/"): compressed_topic=f"/{compressed_topic}"

                # Get compression methiod type with backup fallbacks if it does not match expected parmas
                can_compress=feed_type not in ("imu", "depth")
                mode=int(feed.get("compression.ros_compression", 0)) if can_compress else 0
                if mode not in (0, 1, 2) or (mode==2 and compressed_topic==raw_topic): mode=0
                raw_publisher=compressed_publisher=None

                # If current sensor is imu publish it's data otherwise publish image or compressed image depending on whats being used
                if feed_type=="imu": raw_publisher=self.create_publisher(Imu, raw_topic, 10)
                else:
                    if mode in (0, 2): raw_publisher=self.create_publisher(Image, raw_topic, 10)
                    if mode in (1, 2): compressed_publisher=self.create_publisher(CompressedImage, compressed_topic, qos_profile_sensor_data)

                # Localizer instance for when apriltag is active
                localizer_cfg=self.localizer_config(f"feeds.{group}.{feed_name}") if feed_type=="rgb" else None

                # Create an camera feed list that stores all camera settings and refrences anything that the camera feed requires or any operations it supports
                camera_feed_list.append({
                    "key": f"feeds.{group}.{feed_name}",
                    "type": feed_type,
                    "topic": raw_topic,
                    "width": int(feed.get("adjustments.width", 0)),
                    "height": int(feed.get("adjustments.height", 0)),
                    "grayscale": bool(feed.get("adjustments.grayscale", False)) and feed_type=="rgb",
                    "fps": int(feed.get("adjustments.framerate", feed.get("fps", 0))),
                    "last": 0.0,
                    "publisher": raw_publisher,
                    "compressed_publisher": compressed_publisher,
                    "localizer": ArucoLocalizer(self, localizer_cfg, self.offset_matrix(camera_name, f"feeds.{group}.{feed_name}")) if localizer_cfg else None,
                })

            # Add camera to set of saved cameras for quick access, and update camera modes based on quieried data
            self.cameras[camera_name]={
                "uuid": camera_uuid,
                "id": camera_id,
                "pipeline": camera_pipeline,
                "capture": camera_capture,
                "usb": usb_camera,
                "frames": {},
                "publishers": {},
                "lock": threading.Lock(),
                "running": True,
                "intrinsics": intrinsics, 
                "info_publisher": info_publisher,
                "align": rs.align(rs.stream.color) if {"rgb","depth"}<=set(camera_modes) else None
            }

            # Assign each camera stored in self.cameras it's camera settings and any active feeds that it has
            self.cameras[camera_name]["feeds"]=camera_feed_list
            self.cameras[camera_name]["modes"]=camera_modes

            # In addition start the camera on it's own thread allowing dynamical changes
            thread=threading.Thread(target=self.camera_render, args=(camera_name,), daemon=True)
            thread.start()
            self.cameras[camera_name]["thread"]=thread

            # Camera connected
            self.get_logger().info(f"\033[92mOpened camera #{camera_id}, {camera_uuid}: Connected\033[0m")

    # Function that reads frames from standard cameras
    def read_usb(self, camera):
        ok, frame=camera["capture"].read()
        if not ok: time.sleep(0.01); return None
        return {"rgb": frame}

    # Function that reads sensor data from realsense cameras
    def read_realsense(self, camera):
        # Wait for camera frames
        try: frames=camera["pipeline"].wait_for_frames(3000)
        except RuntimeError: return None

        # Pull latest color frame
        latest_frame={}
        color_frame=frames.get_color_frame()

        # Pull latest depth frame and algin it with color frame
        depth_source=camera["align"].process(frames) if camera["align"] else frames
        depth_frame=depth_source.get_depth_frame()

        # Pull the two infrared frames
        infrared_frame1=frames.get_infrared_frame(1)
        infrared_frame2=frames.get_infrared_frame(2)

        # Push frames if camera has active feed for that type of frame
        if color_frame: latest_frame["rgb"]=np.asanyarray(color_frame.get_data())
        if depth_frame: latest_frame["depth"]=np.asanyarray(depth_frame.get_data())
        if infrared_frame1: latest_frame["inferred1"]=np.asanyarray(infrared_frame1.get_data())
        if infrared_frame2: latest_frame["inferred2"]=np.asanyarray(infrared_frame2.get_data())

        # Pack motion frames into vectors
        for frame in frames:
            if not frame.is_motion_frame(): continue
            motion_frame=frame.as_motion_frame().get_motion_data()
            vector=np.array([motion_frame.x, motion_frame.y, motion_frame.z], dtype=np.float32)
            if frame.get_profile().stream_type()==rs.stream.gyro: latest_frame["gyro"]=vector
            elif frame.get_profile().stream_type()==rs.stream.accel: latest_frame["accel"]=vector

        # Return frames
        return latest_frame

    # Camera reader which reads all data from camera and handles ideling cameras
    def camera_render(self, camera_name):
        # Cameras can stay idle in the background, once running is enabled camera will constantly query new frames for each video feed
        camera=self.cameras[camera_name]
        while camera["running"]:
            # Look through each camera and find what camera streams are currently active
            active=[]
            for feed in camera["feeds"]:
                if self.active.get(feed["key"], camera["id"])==camera["id"]:
                    if not feed.get("live"): feed["settings"]=None; feed["next"]=0.0; feed["live"]=True
                    active.append(feed)
                else: feed["live"]=False

            # For ideling cameras currently not being using simply dump thier frames until they become active
            if not active:
                if camera["usb"]: 
                    if not camera["capture"].grab(): time.sleep(0.01)
                else:
                    try: camera["pipeline"].wait_for_frames(3000)
                    except RuntimeError: pass
                continue

            # If camera is not idling pull latest availible camera frames from camera
            latest_frame=self.read_usb(camera) if camera["usb"] else self.read_realsense(camera)
            if not latest_frame: continue

            # Cameras are threaded, so to unsure that are no conflicts during frame capture lock camera during frame update, releasing lock after updating the frames
            with camera["lock"]:
                camera["frames"].update(latest_frame)
                accel=camera["frames"].get("accel")
                if "gyro" in latest_frame and accel is not None: latest_frame["imu"]=np.concatenate([latest_frame["gyro"], accel])

            # Pull current time data for frame fps limits
            now=time.monotonic()
            stamp=self.get_clock().now().to_msg()

            # If frame doesn't pass fps limits, dump frame, otherwise stamp message and publish to ros topic
            for feed in active:
                if feed["type"] not in latest_frame: continue
                if feed["fps"] and feed["type"]!="imu":
                    next_time=feed.setdefault("next", 0.0)
                    if now<next_time: continue
                    period=1.0/feed["fps"]
                    feed["next"]=next_time+period if now-next_time<period else now+period
                self.publish_feed(camera_name, feed, latest_frame[feed["type"]], stamp)

    # Pull camera intrinsics and combine into message
    def build_camera_info(self, camera_name, width, height, stamp):
        # Pull camera intrinsice
        camera=self.cameras.get(camera_name)
        if not camera or not camera["intrinsics"]: return None
        i=camera["intrinsics"]

        # Pull camera scaling factors
        sx, sy=width/i["width"], height/i["height"]
        fx, fy, cx, cy=i["fx"]*sx, i["fy"]*sy, i["ppx"]*sx, i["ppy"]*sy

        # Create new camera info msg and add time stamp, camera name, and camera resultions to it
        msg=CameraInfo()
        msg.header.stamp=stamp
        msg.header.frame_id=camera_name
        msg.width, msg.height=width, height

        # Add default camera calibration data to msg, it can be changed later from the default to better match realsense cameras if deseried 
        msg.distortion_model="plumb_bob"
        msg.d=[float(c) for c in i["coeffs"]]
        msg.k=[fx, 0.0, cx,  0.0, fy, cy,  0.0, 0.0, 1.0]
        msg.r=[1.0, 0.0, 0.0,  0.0, 1.0, 0.0,  0.0, 0.0, 1.0]
        msg.p=[fx, 0.0, cx, 0.0,  0.0, fy, cy, 0.0,  0.0, 0.0, 1.0, 0.0]

        # Return camera info message
        return msg

    # Simple publisher to publish camera infomation creating one topic per call
    def publish_camera_info(self, camera_name, width, height, stamp):
        camera=self.cameras.get(camera_name)
        if not camera or not camera["info_publisher"]: return
        camera["info_publisher"].publish(self.build_camera_info(camera_name, width, height, stamp))

    # Finally after cameras have been open, frames have been pulled, the frames can be published on thier respectful topics 
    def publish_feed(self, camera_name, feed, data, stamp):
        # If using an imu sensor put togther an imu message with the pull frames, (orientation_covariance=-1 means o orientation estimate) then publish message
        if feed["type"]=="imu":
            msg=Imu()
            msg.header.stamp=stamp
            msg.header.frame_id=camera_name
            msg.orientation_covariance[0]=-1.0          # no orientation estimate
            msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z=(float(v) for v in data[:3])
            msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z=(float(v) for v in data[3:])
            feed["publisher"].publish(msg)
            return

        # Video resulution is attempted first directly on the camera, if the camera does not support it apply the resultion change here
        if feed["width"] and feed["height"] and (data.shape[1], data.shape[0])!=(feed["width"], feed["height"]):
            interp=cv2.INTER_NEAREST if feed["type"]=="depth" else cv2.INTER_AREA
            data=cv2.resize(data, (feed["width"], feed["height"]), interpolation=interp)

        # If an april tag is active on a camera feed pull camera info and apriltag parmas and sent to ArucoLocalize for processing
        if feed["localizer"]:
            size=data.shape[:2]
            if feed.get("info_size")!=size:
                info=self.build_camera_info(camera_name, data.shape[1], data.shape[0], stamp)
                if info is not None: feed["localizer"].set_camera_info(info); feed["info_size"]=size
            data=feed["localizer"].process(data, stamp)

        # Image modifcations
        data=self.crop_stream(data, feed)
        data=self.flip_stream(data, feed)
        data=self.grayscale_stream(data, feed)

        # If stream is compressed publish a compressed video feed
        if feed["compressed_publisher"]:
            msg=self.compress_stream(data, feed, camera_name, stamp)
            if msg is not None: feed["compressed_publisher"].publish(msg)

        # Else camera isn't compressed so publish standard video feed
        if feed["publisher"]:
            # Choice the correct video encoding format
            if data.dtype==np.uint16: encoding="16UC1"
            elif data.ndim==3: encoding="bgr8"
            else: encoding="mono8"

            # Add timestamp, frame_id, and encoding type to topic message
            msg=self.bridge.cv2_to_imgmsg(data, encoding)
            msg.header.stamp=stamp
            msg.header.frame_id=camera_name

            # Publish feed topic, and if camera has an info topic publish that aswell
            feed["publisher"].publish(msg)
            if feed["type"]=="rgb": self.publish_camera_info(camera_name, msg.width, msg.height, stamp)

    # Convert rgb streams to grayscale
    def grayscale_stream(self, data, feed):
        # Get grayscale parmas
        grayscale=self.has_parameter(f"{feed['key']}.adjustments.grayscale") and bool(self.get_parameter(f"{feed['key']}.adjustments.grayscale").value)
        
        # Based on the grayscale configuration change stream to grayscale, only convert 3 stream feeds
        if grayscale and data.ndim==3: data=cv2.cvtColor(data, cv2.COLOR_BGR2GRAY)
        return data

    # Flip video stream directions
    def flip_stream(self, data, feed):
        # Get flip parmas
        flip_horizontal=self.has_parameter(f"{feed['key']}.adjustments.horizontal_flip") and bool(self.get_parameter(f"{feed['key']}.adjustments.horizontal_flip").value)
        flip_vertical=self.has_parameter(f"{feed['key']}.adjustments.vertical_flip") and bool(self.get_parameter(f"{feed['key']}.adjustments.vertical_flip").value)

        # Based on the flip configuration flip the input camera stream
        if flip_horizontal and flip_vertical: return cv2.flip(data, -1)
        if flip_vertical: return cv2.flip(data, 0)
        if flip_horizontal: return cv2.flip(data, 1)
        return data

    # Crop stream in each direction based on precentage
    def crop_stream(self, data, feed):
        # Get crop parmas
        top=self.feed_param(feed, f"adjustments.top_crop", 0); bottom=self.feed_param(feed, f"adjustments.bottom_crop", 0)
        left=self.feed_param(feed, f"adjustments.left_crop", 0); right=self.feed_param(feed, f"adjustments.right_crop", 0)
        if not (top or bottom or left or right): return data

        # Calulate starting location
        height, width=data.shape[:2]
        y0, y1=int(height*top/100), height-int(height*bottom/100)
        x0, x1=int(width*left/100), width-int(width*right/100)

        # Round size down to make it even for things in the code that require it
        if top or bottom:
            size=y1-y0; size-=size%2
            if top: y0=y1-size
            else: y1=y0+size
        if left or right:
            size=x1-x0; size-=size%2
            if left: x0=x1-size
            else: x1=x0+size

        # Return cropped image
        return np.ascontiguousarray(data[y0:y1, x0:x1])

    # Pull parma, if it cannot be found pull default value
    def feed_param(self, feed, name, default):
        return self.get_parameter(f"{feed['key']}.{name}").value if self.has_parameter(f"{feed['key']}.{name}") else default

    # Compress video stream
    def compress_stream(self, data, feed, camera_name, stamp):
        # Check if a supported comression codec is being used
        codecs={"h264": "libx264", "h265": "libx265"}
        codec=str(self.feed_param(feed, "compression.codec", "h264"))
        if codec not in codecs: return None

        # Pull importain parmas needs for compression
        fps=feed["fps"] or 30
        avg_kbps=int(self.feed_param(feed, "compression.avg_bitrate_kbps", 150))
        max_kbps=int(self.feed_param(feed, "compression.max_bitrate_kbps", 300))
        gop=int(self.feed_param(feed, "compression.gop", 48))
        height, width=data.shape[:2]

        try:
            # Build out compression settings, if settings changed rebuild compression instance, else use previus ones
            settings=(codec, width, height, fps, avg_kbps, max_kbps, gop)
            if settings!=feed.get("settings"):
                ctx=av.CodecContext.create(codecs[codec], "w")
                ctx.width, ctx.height=width, height        
                ctx.pix_fmt="yuv420p"
                ctx.time_base=Fraction(1, fps)
                ctx.framerate=Fraction(fps, 1)
                ctx.bit_rate=avg_kbps*1000
                ctx.gop_size=gop
                ctx.max_b_frames=0                        
                options={"preset": "ultrafast", "tune": "zerolatency","maxrate": f"{max_kbps}k","bufsize": f"{max(max_kbps//2, 1)}k"}  
                if codec=="h265": options["x265-params"]="log-level=error"
                ctx.options=options
                ctx.open()
                feed["ctx"], feed["settings"], feed["pts"]=ctx, settings, 0

            # Feed in frame into compresser with it's settings, yeilding the output payload frame
            frame=av.VideoFrame.from_ndarray(np.ascontiguousarray(data), format="gray" if data.ndim==2 else "bgr24").reformat(format="yuv420p")
            frame.pts=feed["pts"]
            feed["pts"]+=1
            payload=b"".join(bytes(packet) for packet in feed["ctx"].encode(frame))
        except Exception as e: return None
        if not payload: return None

        # Build out a ros compressed image topic with camera name and time stanp, along with compression details and payload
        msg=CompressedImage()
        msg.header.stamp=stamp
        msg.header.frame_id=camera_name
        msg.format=codec
        msg.data=payload
        return msg

    # Ros supports live parma changes with camera relaunches
    def apply_param_changes(self):
        # Now that parma update is triggered cancel timer
        self.pending_timer.cancel()

        # For every feed create a set of cameras that are pending a relaunch 
        for name, param in self.get_parameters_by_prefix("feeds").items():
            group, feed_name, *field=name.split(".")
            if field==["camera"] and len(param.value): self.active[f"feeds.{group}.{feed_name}"]=int(param.value[0])
        changed, self.pending=self.pending, set()
        relaunch=set()

        # Loop through each camera, updating relaunching when required
        for name in changed:
            parts=name.split(".")

            # If an apriltag parma gets updated just propugate the new settings and the updated sensor locations
            if parts[0]=="cameras" and len(parts)>2 and parts[2]=="location":
                camera=self.cameras.get(parts[1])
                for feed in (camera["feeds"] if camera else []):
                    if feed["localizer"]: feed["localizer"].set_mount(self.offset_matrix(parts[1], feed["key"]))
                continue
            if parts[0]=="cameras" and len(parts)>2: relaunch.add(parts[1]); continue

            # Get a list of feeds parmas to check for camera relaunches
            if parts[0]!="feeds" or len(parts)<4: continue
            feed_key=".".join(parts[:3])
            field=".".join(parts[3:])

            # If any parmas that must have a relaunch, relaunch cameras
            if field in ("enabled", "camera", "type", "topic", "compression.ros_compression", "compression.compression_topic"):
                # From the feed find the camera that needs the relaunch, and add to relaunch list
                relaunch|={camera_name for camera_name, camera in self.cameras.items() if any(feed["key"]==feed_key for feed in camera["feeds"])}
                if self.has_parameter(f"{feed_key}.camera"):
                    ids=set(self.get_parameter(f"{feed_key}.camera").value)
                    names={name.split(".")[0] for name in self.get_parameters_by_prefix("cameras")}
                    relaunch|={name for name in names if self.get_parameter(f"cameras.{name}.id").value in ids}

            # Other parmas such as fps dependsm only relaunch if absolutly required
            elif field in ("adjustments.width", "adjustments.height", "adjustments.framerate", "fps"):
                for camera_name, camera in self.cameras.items():
                    for feed in camera["feeds"]:
                        # For each of key parmas, check agenst existing camera mode, if within the cameras limits it can simpliy update the classes lists, otherwise if it falls outside relaunch the camera to support new parma
                        if feed["key"]!=feed_key: continue
                        if camera["usb"] or (
                            int(self.feed_param(feed, "adjustments.width", 0)) <= camera["modes"][feed["type"]][0]
                            and int(self.feed_param(feed, "adjustments.height", 0)) <= camera["modes"][feed["type"]][1]
                            and int(self.feed_param(feed, "adjustments.framerate", self.feed_param(feed, "fps", 0))) <= camera["modes"][feed["type"]][2]): 
                                feed["width"] = int(self.feed_param(feed, "adjustments.width", 0))
                                feed["height"] = int(self.feed_param(feed, "adjustments.height", 0))
                                feed["fps"] = int(self.feed_param(feed, "adjustments.framerate", self.feed_param(feed, "fps", 0)))
                                feed["next"] = 0.0
                        else: relaunch.add(camera_name)

            # Addition apriltag changes that require a full camera relaunch
            elif field.startswith(("apriltag_localizer.", "sensor_location.")):
                for camera_name, camera in self.cameras.items():
                    for feed in camera["feeds"]:
                        if feed["key"]==feed_key and feed["localizer"]: feed["localizer"].configure(self.localizer_config(feed_key)); feed["localizer"].set_mount(self.offset_matrix(camera_name, feed_key))

        # For all cameras found that need a relaunch due to paramachanges, close and the reopen camera to relaunch it with updated settings
        for camera_name in relaunch:
            self.close_camera(camera_name)
            self.open_cameras(camera_name)

    # Wwen given an camera name, this will close the camera and stop the running thread
    def close_camera(self, camera_name):
        # Pull set of running cameras
        camera=self.cameras.pop(camera_name, None)
        if camera is not None:
            # Change camera running state to false, timeout thread, and request that usb or realsense camera turns off camera
            camera["running"]=False
            camera["thread"].join(timeout=1)
            if camera["usb"]: camera["capture"].release()
            else: camera["pipeline"].stop()

            # Cleanup old camera when system relaunches due to parma changes, destorying all topic publishers
            for feed in camera["feeds"]:
                for key in ("publisher", "compressed_publisher"):
                    if feed[key]: self.destroy_publisher(feed[key])
                if feed["localizer"]: feed["localizer"].close()
            if camera["info_publisher"]: self.destroy_publisher(camera["info_publisher"])

    # Stop node and close all cameras
    def destroy_node(self):
        for camera_name in list(self.cameras.keys()): self.close_camera(camera_name)
        super().destroy_node()

# April tag localizer
class ArucoLocalizer:
 
    TAG_FIELDS = (
        'enabled', 'id', 'x', 'y', 'yaw', 'marker_length',
        'max_distance', 'min_area_px', 'pos_sigma', 'yaw_sigma', 'min_interval',
    )

    OPTICAL_ROTATION = np.array([[0.0, 0.0, 1.0], [-1.0, 0.0, 0.0], [0.0, -1.0, 0.0]])
 
    def __init__(self, node, cfg, mount):
        self.node = node
        self.map_frame = 'map'
 
        self.cam_matrix   = None
        self.dist_coeffs  = None
        self._cam_info_received = False
 
        self._aruco_dict   = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_25H9)
        self._aruco_params = cv2.aruco.DetectorParameters_create()
        self._aruco_params.cornerRefinementMethod = cv2.aruco.CORNER_REFINE_SUBPIX
 
        self._last_publish_time: dict = {}
 
        self._pose_pub = self.node.create_publisher(
            PoseWithCovarianceStamped,
            '/aruco/pose_correction',
            10,
        )

        self.set_mount(mount)
        self.configure(cfg)
 
    def configure(self, cfg) -> None:
        self.enabled = bool(cfg['enabled'])
        self.overlay = bool(cfg['overlay'])
 
        self.tags = {}
        for name, tag in cfg['tags'].items():
            missing = [k for k in self.TAG_FIELDS if k not in tag]
            if missing:
                self.node.get_logger().error(f'Tag {name}: missing {missing}, skipped')
                continue
            if not tag['enabled']:
                continue
            self.tags[int(tag['id'])] = {
                'name':          name,
                'x':             float(tag['x']),
                'y':             float(tag['y']),
                'yaw':           math.radians(float(tag['yaw'])),
                'marker_length': float(tag['marker_length']),
                'max_distance':  float(tag['max_distance']),
                'min_area_px':   float(tag['min_area_px']),
                'pos_sigma':     float(tag['pos_sigma']),
                'yaw_sigma':     math.radians(float(tag['yaw_sigma'])),
                'min_interval':  float(tag['min_interval']),
            }
 
    def set_camera_info(self, msg: CameraInfo) -> None:
        k = msg.k
        self.cam_matrix = np.array([
            [k[0], k[1], k[2]],
            [k[3], k[4], k[5]],
            [k[6], k[7], k[8]],
        ], dtype=np.float64)
 
        self.dist_coeffs = np.array(msg.d, dtype=np.float64).reshape(1, -1)
 
        if not self._cam_info_received:
            self._cam_info_received = True

    def set_mount(self, mount) -> None:
        transform = np.eye(4)
        transform[:3, :3] = np.asarray(mount)[:3, :3] @ self.OPTICAL_ROTATION
        transform[:3, 3] = np.asarray(mount)[:3, 3]
        self.T_base_cam = transform
 
    def process(self, frame: np.ndarray, stamp=None) -> np.ndarray:
        if not self.enabled or not self._cam_info_received:
            return frame
 
        if stamp is None:
            stamp = self.node.get_clock().now().to_msg()
 
        if self.overlay and frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
 
        corners, ids, _ = cv2.aruco.detectMarkers(
            frame, self._aruco_dict, parameters=self._aruco_params
        )
 
        if ids is None:
            return frame
 
        now_sec = self.node.get_clock().now().nanoseconds * 1e-9
 
        for i, tag_id_arr in enumerate(ids):
            tag_id = int(tag_id_arr[0])
 
            tag = self.tags.get(tag_id)
            if tag is None:
                continue
 
            rvecs, tvecs, _ = cv2.aruco.estimatePoseSingleMarkers(
                [corners[i]], tag['marker_length'], self.cam_matrix, self.dist_coeffs
            )
            rvec = rvecs[0][0]
            tvec = tvecs[0][0]
 
            area = self._marker_area_px(corners[i])
            if area < tag['min_area_px']:
                self.node.get_logger().debug(
                    f'Tag {tag_id}: area {area:.0f}px² < min {tag["min_area_px"]:.0f}, skip'
                )
                continue
 
            z_dist = float(tvec[2])
            if z_dist > tag['max_distance'] or z_dist <= 0.0:
                self.node.get_logger().debug(
                    f'Tag {tag_id}: depth {z_dist:.2f}m out of range, skip'
                )
                continue
 
            try:
                robot_x, robot_y, robot_yaw = self._compute_robot_pose_in_map(
                    rvec, tvec,
                    tag['x'], tag['y'], tag['yaw'],
                    self.T_base_cam,
                )
            except Exception as exc:
                self.node.get_logger().error(
                    f'Pose computation failed for tag {tag_id}: {exc}'
                )
                continue
 
            if self.overlay:
                cv2.drawFrameAxes(
                    frame, self.cam_matrix, self.dist_coeffs,
                    rvec, tvec, tag['marker_length'] * 0.5
                )
                label = (
                    f'ID:{tag_id} '
                    f'({robot_x:.2f},{robot_y:.2f}) '
                    f'{math.degrees(robot_yaw):.0f}deg'
                )
                c = corners[i][0]
                cx_px = int(c[:, 0].mean())
                cy_px = int(c[:, 1].mean())
                cv2.putText(
                    frame, label, (cx_px - 60, cy_px - 15),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2
                )
 
            last_t = self._last_publish_time.get(tag_id, 0.0)
            if now_sec - last_t < tag['min_interval']:
                continue
            self._last_publish_time[tag_id] = now_sec
 
            pose_msg = self._build_pose_msg(
                stamp, robot_x, robot_y, robot_yaw,
                tag['pos_sigma'], tag['yaw_sigma']
            )
            self._pose_pub.publish(pose_msg)
 
        if self.overlay:
            cv2.aruco.drawDetectedMarkers(frame, corners, ids)
 
        return frame
 
    def _build_pose_msg(
        self,
        stamp,
        x: float,
        y: float,
        yaw: float,
        pos_sigma: float,
        yaw_sigma: float,
    ) -> PoseWithCovarianceStamped:
        msg = PoseWithCovarianceStamped()
        msg.header.stamp    = stamp
        msg.header.frame_id = self.map_frame
 
        q = self._yaw_to_quaternion(yaw)
        msg.pose.pose.position.x    = x
        msg.pose.pose.position.y    = y
        msg.pose.pose.position.z    = 0.0
        msg.pose.pose.orientation.x = q['x']
        msg.pose.pose.orientation.y = q['y']
        msg.pose.pose.orientation.z = q['z']
        msg.pose.pose.orientation.w = q['w']
 
        msg.pose.covariance = self._build_pose_covariance(pos_sigma, yaw_sigma)
        return msg
 
    @staticmethod
    def _marker_area_px(corners) -> float:
        return float(cv2.contourArea(np.asarray(corners, dtype=np.float32).reshape(4, 2)))
 
    @staticmethod
    def _yaw_to_quaternion(yaw: float) -> dict:
        return {'x': 0.0, 'y': 0.0, 'z': math.sin(yaw / 2.0), 'w': math.cos(yaw / 2.0)}
 
    @staticmethod
    def _build_pose_covariance(pos_sigma: float, yaw_sigma: float) -> list:
        cov = [0.0] * 36
        cov[0]  = pos_sigma ** 2
        cov[7]  = pos_sigma ** 2
        cov[14] = 1e6
        cov[21] = 1e6
        cov[28] = 1e6
        cov[35] = yaw_sigma ** 2
        return cov
 

    @staticmethod
    def _compute_robot_pose_in_map(rvec, tvec, tag_x: float, tag_y: float, tag_yaw: float, T_base_cam: np.ndarray):
        R_ct, _ = cv2.Rodrigues(np.asarray(rvec, dtype=np.float64).reshape(3, 1))
        t_ct = np.asarray(tvec, dtype=np.float64).reshape(3)

        T_tag_cam = np.eye(4)
        T_tag_cam[:3, :3] = R_ct.T
        T_tag_cam[:3, 3] = -R_ct.T @ t_ct

        c, s = math.cos(tag_yaw), math.sin(tag_yaw)
        T_map_tag = np.eye(4)
        T_map_tag[:3, :3] = [[-s, 0.0, c], [c, 0.0, s], [0.0, 1.0, 0.0]]
        T_map_tag[:3, 3] = [tag_x, tag_y, 0.0]

        T_map_base = T_map_tag @ T_tag_cam @ np.linalg.inv(T_base_cam)
        forward = T_map_base[:3, 0]
        return float(T_map_base[0, 3]), float(T_map_base[1, 3]), float(math.atan2(forward[1], forward[0]))

    def close(self) -> None:
        self.node.destroy_publisher(self._pose_pub)

# Node initalization 
def main():
    rclpy.init()
    node=CameraManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()