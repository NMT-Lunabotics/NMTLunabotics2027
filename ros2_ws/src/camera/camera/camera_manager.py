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
        super().__init__("camera_manager")

        # Define a cameras config file parameter. Have it default to config/cameras.yaml if not specifiied
        cameras_config=os.path.join(get_package_share_directory("camera"), "config", "cameras.yaml")
        self.declare_parameter("cameras_config", cameras_config)
        # Create flattend params of all param configs
        with open(self.get_parameter("cameras_config").value, "r") as file: data=yaml.safe_load(file)
        self.declare_flatend_params(data["camera_manager"]["ros__parameters"])

        # Define a presistance parameter. Which when true makes the node record changes when an param change is detected
        self.declare_parameter("persistent", True)
        self.ppersistent = self.get_parameter("persistent").value

        # Camera/Feed instances, holds key camera/feed info and methiods for accessing it, and our publisher bridge
        self.cameras={}
        self.feeds={}
        self.bridge=CvBridge()

        # Launch the inital cameras
        self.open_cameras()

        # Create an parameters callback to support live camera config changes
        self.add_on_set_parameters_callback(self.on_params_change)

    # 
    def on_params_change(self, params):
        ...

    # Interative nested params flatener
    def declare_flatend_params(self, value, path=""):
        # Loop into nested param value building an path i.e. camera.type.rgb
        if isinstance(value, dict):
            for param_key, param_value in value.items(): self.declare_flatend_params(param_value, f"{path}{param_key}.")
        # Once flattened declare path as ros parameter for live param changes
        else:
            full_path=path.rstrip(".")
            if not self.has_parameter(full_path): self.declare_parameter(full_path, value)

    # Launch cameras and the diffrent needed camera sensors
    def open_cameras(self, camera_name=None, overrides=None):
        overrides=overrides or {}
        # Create set of cameras to loop through
        if camera_name is not None: camera_set=[camera_name]
        else:
            camera_set=set()
            for name in self.get_parameters_by_prefix("cameras"): camera_set.add(name.split(".")[0])
        for camera_name in camera_set:
            # Create an uuid/id keys for lookup
            uuid_key=f"cameras.{camera_name}.uuid"
            id_key=f"cameras.{camera_name}.id"

            # Pull uuid/id from each camera instance
            camera_uuid=overrides.get(uuid_key, self.get_parameter(uuid_key).value)
            camera_id=overrides.get(id_key, self.get_parameter(id_key).value)

            # Check to see if pyrealsense2 sees camera device. Skip and output error if not found
            if camera_uuid not in [device.get_info(rs.camera_info.serial_number) for device in rs.context().query_devices()]:
                 self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: Not found")
                 continue

            # Enabled found camera devices
            camera_pipeline=rs.pipeline()
            camera_config=rs.config()
            camera_config.enable_device(camera_uuid)

            # Specifies how to open each realsense sensor/camera, formate, and sensor to use in the case of the infered camera
            camera_feed_mappings={
                "rgb": (rs.stream.color, rs.format.bgr8, 0),
                "depth": (rs.stream.depth, rs.format.z16, 0),
                "inferred1": (rs.stream.infrared, rs.format.y8, 0),
                "inferred2": (rs.stream.infrared, rs.format.y8, 1),
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

            # For all of the camera types go and enable the needed camera streams
            if not types_set: continue
            for type in types_set:
                if type not in camera_feed_mappings: continue
                stream, camera_format, sensor=camera_feed_mappings[type]

                # Pull default camera settings for each feed type
                matches=[feed for feed in camera_feeds.values() if feed.get("enabled") and camera_id in feed.get("camera", []) and feed.get("type") == type]
                width=matches[0].get("width", 0) if matches else 0
                height=matches[0].get("height", 0) if matches else 0
                fps=matches[0].get("fps", 30) if matches else 30


                if camera_format: 
                    if sensor: camera_config.enable_stream(stream, sensor, width, height, camera_format, fps)
                    else: camera_config.enable_stream(stream, width, height, camera_format, fps)
                else: camera_config.enable_stream(stream)

            # Camera has been fully configured, attempt to start the camera
            try: camera_pipeline.start(camera_config)
            except RuntimeError as e:
                self.get_logger().error(f"Failed to open camera #{camera_id}, {camera_uuid}: {e}")
                continue

            active_profile = camera_pipeline.get_active_profile()
            color_stream = active_profile.get_stream(rs.stream.color).as_video_stream_profile()
            self.get_logger().info(f"Color stream actually running as: {color_stream.format()}")

            # Add camera to set of saved cameras for quick access
            self.cameras[camera_name]={"uuid": camera_uuid, "id": camera_id, "pipeline": camera_pipeline, "frames": {}, "publishers": {}, "lock": threading.Lock(), "running": True}
            #self.cameras[camera_name]={"uuid": camera_uuid, "id": camera_id, "pipeline": camera_pipeline, "frames": {}, "lock": threading.Lock(), "running": True}

            # In addition start the camera on it's own thread allowing dynamical changes
            thread=threading.Thread(target=self.camera_render, args=(camera_name,), daemon=True)
            thread.start()
            self.cameras[camera_name]["thread"]=thread

            # Camera connected
            self.get_logger().info(f"\033[92mOpened camera #{camera_id}, {camera_uuid}: Connected\033[0m")

    def camera_render(self, camera_name):
        camera=self.cameras[camera_name]
        camera_pipeline=camera["pipeline"]
        while camera["running"]:
            # Wait for camera frames, if none arrive within 3s, close the camera thread
            try: frames=camera_pipeline.wait_for_frames(3000)
            except RuntimeError: continue

            # Get frame methiod for each sensor
            latest_frame={}
            color_frame=frames.get_color_frame()
            depth_frame=frames.get_depth_frame()
            infrared_frame=frames.get_infrared_frame()

            # If camera set contains any of the sensor push the latest frame into a set
            if color_frame: latest_frame["rgb"]=np.asanyarray(color_frame.get_data())
            if depth_frame: latest_frame["depth"]=np.asanyarray(depth_frame.get_data())
            if infrared_frame: latest_frame["infered"]=np.asanyarray(infrared_frame.get_data())


            # Handle frames for imu sensor
            for frame in frames:
                # Check if any camera motion frames were returned
                if not frame.is_motion_frame(): continue
                motion_frame=frame.as_motion_frame().get_motion_data()
                vector=np.array([motion_frame.x, motion_frame.y, motion_frame.z], dtype=np.float32)

                # If gyro or accel frames were found push them respectfuly to frame set
                if frame.get_profile().stream_type()==rs.stream.gyro: latest_frame["gyro"]=vector
                elif frame.get_profile().stream_type()==rs.stream.accel: latest_frame["accel"]=vector

            # Push new frames to camera buffer
            with camera["lock"]: camera["frames"].update(latest_frame)

            for frame_type, data in latest_frame.items():
                if frame_type in ("gyro", "accel"): continue
                if frame_type not in camera["publishers"]:
                    camera["publishers"][frame_type]=self.create_publisher(Image, f"/{camera_name}/{frame_type}", 10)
                encoding = "rgb8" if frame_type=="rgb" else "mono16" if frame_type=="depth" else "mono8"
                msg=self.bridge.cv2_to_imgmsg(data, encoding)
                msg.header.stamp=self.get_clock().now().to_msg()
                msg.header.frame_id=camera_name
                camera["publishers"][frame_type].publish(msg)

    # Wwen given an camera name, this will close the camera and stop the running thread
    def close_camera(self, camera_name):
        camera=self.cameras.pop(camera_name, None)
        if camera is not None:
            camera["running"]=False
            camera["thread"].join(timeout=1)
            camera["pipeline"].stop()

    # Stop node and close all cameras
    def destroy_node(self):
        for camera_name in list(self.cameras.keys()): self.close_camera(camera_name)
        super().destroy_node()


# Node initalization 
def main():
    rclpy.init()
    node=CameraManager()
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()