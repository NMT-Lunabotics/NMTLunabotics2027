#!/usr/bin/env python3

import os
import yaml
import rclpy
from rclpy.node import Node
from rcl_interfaces.msg import SetParametersResult
from ament_index_python.packages import get_package_share_directory
import pyrealsense2 as rs
import threading
import numpy as np
import cv2
import functools
from cv_bridge import CvBridge
from sensor_msgs.msg import Image, CompressedImage, Imu

class CameraManager(Node):
    def __init__(self):
        super().__init__("camera_manager2")

        # Default camera/feed config file 
        default_config=os.path.join(get_package_share_directory("camera"), "config", "cameras.yaml")
        self.declare_parameter("config_file", default_config)
        config_path=self.get_parameter("config_file").value
        self.load_config(config_path)

        # Node parm presistance 
        self.declare_parameter("persistent", True)
        self.ppersistent = self.get_parameter("persistent").value

        # Global class variables
        self.cameras={}
        self.feeds={}
        self.bridge=CvBridge()

        # Start cameras and stream feeds
        self.open_camera(None)
        self.open_feeds(None)

        # Trigger update on parms change
        self.add_on_set_parameters_callback(self.on_params_change)

    # Load parms file
    def load_config(self, config_path):
        with open(config_path, "r") as f: data=yaml.safe_load(f)
        params=data["camera_manager"]["ros__parameters"]
        self.declare_nested_params("", params)

    # For each parm and nested parm if no parm exists load in blank one
    def declare_nested_params(self, prefix, value):
        if isinstance(value, dict):
            for k, v in value.items(): self.declare_nested_params(f"{prefix}{k}.", v)
        else:
            name = prefix.rstrip(".")
            if not self.has_parameter(name): self.declare_parameter(name, value)

    # Attempt to start all cameras from config file, or one camera with fresh overrides
    def open_camera(self, camera_namee, overrides=None):
        overrides = overrides or {}
        for camera_name in self.get_camera_names(camera_namee):
            # Pull camera uuid and id, preferring a just-changed value over the stale stored one
            uuid_key = f"cameras.{camera_name}.uuid"
            id_key = f"cameras.{camera_name}.id"
            camera_uuid = overrides.get(uuid_key, self.get_parameter(uuid_key).value)
            camera_id = overrides.get(id_key, self.get_parameter(id_key).value)

            # Check pyrealsense2 to see if detects that camera is connect, else throw error
            connected_serials=[d.get_info(rs.camera_info.serial_number) for d in rs.context().query_devices()]
            if camera_uuid not in connected_serials:
                self.get_logger().error(f"Failed to open camera {camera_id}, {camera_uuid}: Not connected")
                continue

            # Camera was detected; enable it
            pipeline=rs.pipeline()
            config=rs.config()
            config.enable_device(camera_uuid)

            # Configuration of camera streams what what is actually opened on the camera
            stream_map = {
                "rgb": (rs.stream.color, rs.format.bgr8, 0),
                "depth": (rs.stream.depth, rs.format.z16, 0),
                "infered": (rs.stream.infrared, rs.format.y8, 1),
                "accel": (rs.stream.accel, None, 0),
                "gyro": (rs.stream.gyro, None, 0),
            }

            # Find all parm stream types, and pass them to pyrealsense2, using stream_map to decide what to open
            for feed_type in self.get_camera_types(camera_id):
                if feed_type not in stream_map: continue
                stream, fmt, index=stream_map[feed_type]
                if fmt: config.enable_stream(stream, index, fmt=fmt) if index else config.enable_stream(stream, fmt)
                else: config.enable_stream(stream)

            # Attempt to start the camera
            try: pipeline.start(config)
            except RuntimeError as e:
                self.get_logger().error(f"Failed to open camera {camera_id}, {camera_uuid}: {e}")
                continue

            # Add camera uuid, id, and thread of camera to camera object list
            self.cameras[camera_name]={"uuid": camera_uuid, "id": camera_id, "pipeline": pipeline, "frames": {}, "lock": threading.Lock(), "running": True}

            # Add each camera to eperate thread so they can be changed indavidually 
            thread=threading.Thread(target=self.camera_reader, args=(camera_name,), daemon=True)
            thread.start()
            self.cameras[camera_name]["thread"]=thread

            # Return status message
            self.get_logger().info(f"Opened camera {camera_id}, {camera_uuid}: Connected")

    # For each camera thread render out each of the enabled camera frame types
    def camera_reader(self, camera_name):
        camera=self.cameras[camera_name]
        pipeline=camera["pipeline"]

        while camera["running"]:
            try: frames=pipeline.wait_for_frames(1000)
            except RuntimeError: continue

            try:
                latest={}
                color=frames.get_color_frame()
                if color: latest["rgb"]=np.asanyarray(color.get_data())
                depth=frames.get_depth_frame()
                if depth: latest["depth"]=np.asanyarray(depth.get_data())

                try:
                    ir=frames.get_infrared_frame(1)
                    if ir: latest["infered"]=np.asanyarray(ir.get_data())
                except RuntimeError:
                    pass

                for frame in frames:
                    if not frame.is_motion_frame(): continue
                    motion_frame=frame.as_motion_frame().get_motion_data()
                    vector=np.array([motion_frame.x, motion_frame.y, motion_frame.z], dtype=np.float32)
                    if frame.get_profile().stream_type() == rs.stream.gyro: latest["gyro"]=vector
                    elif frame.get_profile().stream_type() == rs.stream.accel: latest["accel"]=vector

                with camera["lock"]: camera["frames"].update(latest)
            except Exception as e:
                self.get_logger().error(f"{camera_name} reader error: {e}")

    def publish_feed(self, group, feed_name):
        feed = self.feeds.get((group, feed_name))
        if feed is None: return
        config = feed["config"]

        camera_name = self.get_camera_name_by_id(config["camera"])
        if camera_name is None or camera_name not in self.cameras: return
        cam = self.cameras[camera_name]

        with cam["lock"]:
            raw = cam["frames"].get(config["type"])
        if raw is None: return

        stamp = self.get_clock().now().to_msg()

        if config["type"] in ("rgb", "depth", "infered"):
            crop_x = config.get("crop.x", 0)
            crop_y = config.get("crop.y", 0)
            crop_w = config.get("crop.width", raw.shape[1])
            crop_h = config.get("crop.height", raw.shape[0])
            c = raw[crop_y:crop_y+crop_h, crop_x:crop_x+crop_w]
            resized = cv2.resize(c, (config["width"], config["height"]))
            quality = config.get("compression.jpeg_quality", 0)

            if quality > 0:
                ok, buf = cv2.imencode(".jpg", resized, [cv2.IMWRITE_JPEG_QUALITY, quality])
                if not ok: return
                msg = CompressedImage()
                msg.format = "jpeg"
                msg.data = buf.tobytes()
            else:
                encoding = "mono16" if config["type"]=="depth" else "mono8" if config["type"]=="infered" else "bgr8"
                msg = self.bridge.cv2_to_imgmsg(resized, encoding)
        else:
            msg = Imu()
            vec = [float(v) for v in raw]
            if config["type"]=="gyro":
                msg.angular_velocity.x, msg.angular_velocity.y, msg.angular_velocity.z = vec
            else:
                msg.linear_acceleration.x, msg.linear_acceleration.y, msg.linear_acceleration.z = vec

        msg.header.stamp = stamp
        msg.header.frame_id = camera_name
        feed["pub"].publish(msg)

    def open_feeds(self, feed_key, overrides=None):
        for group, feed_name in self.get_feed_names(feed_key):
            config = self.get_feed_config(group, feed_name, overrides)
            if not config.get("enabled"): continue

            msg_type = self.get_feed_msg_type(config)
            pub = self.create_publisher(msg_type, config["topic"], 10)
            timer = self.create_timer(1.0 / config.get("fps", 30), functools.partial(self.publish_feed, group, feed_name))

            self.feeds[(group, feed_name)] = {"pub": pub, "timer": timer, "config": config}
            self.get_logger().info(f"Opened feed {group}/{feed_name} -> {config['topic']}")

    def close_feed(self, key):
        feed = self.feeds.pop(key, None)
        if feed is not None:
            feed["timer"].cancel()
            self.destroy_publisher(feed["pub"])

    # Search through config file to determin what video streams need to be enabled
    def get_camera_types(self, camera_id):

        # Find all needed feeds from feed parameter
        feed_params = self.get_parameters_by_prefix("feeds")
        feeds = {}
        for name, param in feed_params.items():
            group, feed_name, *field=name.split(".")
            feeds.setdefault((group, feed_name), {})[".".join(field)]=param.value

        # Return a set containing the types of streams rgar aee needed
        types=set()
        for feed in feeds.values():
            if feed.get("enabled") and feed.get("camera") == camera_id: types.add(feed.get("type"))
        return types

    # Pull camera names to use as indexer
    def get_camera_names(self, camera_namee):
        if camera_namee is not None: return [camera_namee]
        names=set()
        for name in self.get_parameters_by_prefix("cameras"): names.add(name.split(".")[0])
        return names

    # Given an camera id pull the camera name
    def get_camera_name_by_id(self, camera_id):
        for name, cam in self.cameras.items():
            if cam["id"] == camera_id: return name
        return None

    # Find camera in list of stored cameras and close it, destorying it from list and shuting down it's thread
    def close_camera(self, camera_name):
        cam=self.cameras.pop(camera_name, None)
        if cam is not None:
            cam["running"]=False
            cam["thread"].join(timeout=1)
            cam["pipeline"].stop()

    # Update camera feeds when parms get updated
    def on_params_change(self, params):
        # Grab the incoming new values directly, since get_parameter still returns the old ones here
        changed={p.name: p.value for p in params if p.name.startswith("cameras.")}
        affected=set(name.split(".")[1] for name in changed)

        # For the changed camera relaunch it using the new values, not the stale stored ones
        for camera_name in affected:
            self.close_camera(camera_name)
            self.open_camera(camera_namee=camera_name, overrides=changed)

        return SetParametersResult(successful=True)

    # Message feed type config, determin what message needs to be published
    def get_feed_msg_type(self, config):
        if config["type"] in ("accel", "gyro"): return Imu
        return CompressedImage if config.get("compression.jpeg_quality", 0) > 0 else Image

    # Pull all of the diffrent camera feeds like what was done for the cameras
    def get_feed_names(self, feed_key):
        if feed_key is not None: return [feed_key]
        names=set()
        for name in self.get_parameters_by_prefix("feeds"):
            parts=name.split(".")
            names.add((parts[0], parts[1]))
        return names

    # Pull the configurations of each camera feed
    def get_feed_config(self, group, feed_name, overrides=None):
        overrides=overrides or {}
        prefix=f"feeds.{group}.{feed_name}."
        config={}
        for name, param in self.get_parameters_by_prefix(f"feeds.{group}.{feed_name}").items():
            config[name] = overrides.get(prefix+name, param.value)
        return config

    # Stop node and close all cameras
    def destroy_node(self):
        for camera_name in list(self.cameras.keys()): self.close_camera(camera_name)
        super().destroy_node()

# Node initalization 
def main():
    rclpy.init()
    node = CameraManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()