from launch import LaunchDescription
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.actions import SetEnvironmentVariable
from ament_index_python.packages import get_package_share_directory
import os

SetEnvironmentVariable(name='OMP_NUM_THREADS', value='4')

def generate_launch_description():

    rtabmap_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            os.path.join(
                get_package_share_directory('rtabmap_launch'),
                'launch',
                'rtabmap.launch.py'
            )
        ),
        launch_arguments={
            'rgb_topic': '/rgb',
            'depth_topic': '/depth',
            'camera_info_topic': '/camera1_info',

            'approx_sync': 'true',
            'visual_odometry': 'true',

            'args': ' '.join([
                '-d',

                '--Rtabmap/DetectionRate 5',
                '--RGBD/LinearUpdate 0.1',
                '--RGBD/AngularUpdate 0.1',

                '--Rtabmap/TimeThr 0',
                '--Rtabmap/ImageBufferSize 1',
                '--Mem/IncrementalMemory true',

                '--RGBD/NeighborLinkRefining false',
                '--RGBD/OptimizeMaxError 3.0',
                '--Kp/MaxFeatures 400',
                '--Vis/MinInliers 15',
                '--Vis/MaxDepth 4.0',

                '--Grid/FromDepth true',
                '--Grid/RangeMax 4.0',
                '--Grid/CellSize 0.05',
                '--Grid/3D false',
                '--Grid/RayTracing true',
                '--Grid/DepthDecimation 2',
                '--Grid/NoiseFilteringRadius 0.1',
                '--Grid/NoiseFilteringMinNeighbors 3',
                '--Grid/MaxGroundHeight 0.15',
                '--Grid/MaxGroundAngle 45',
                '--Grid/MaxObstacleHeight 1.5',
                '--Grid/MapFrameProjection true',
            ]),

            'OMP_NUM_THREADS': '4',

            'map_topic': '/map',
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'map_frame_id': 'map',
            'publish_tf_map': 'true',

            'rtabmap_viz': 'true',
            'log_level': 'warn',

            'odom_args': ' '.join([
                '--Odom/ResetCountdown 1', # Will make camera guess where it is if it loses odemtry
                '--Odom/Strategy 0',
                '--Odom/GuessMotion true',
                '--Vis/MinInliers 15',
                '--Vis/MaxDepth 8.0',
                '--Vis/MaxFeatures 600',
            ]),




            # Modes
            #'stereo': 'false',
            #'localization': 'false',
            #'rtabmap_viz': 'false',
            #'rviz': 'false',
            #'use_sim_time': 'false',
            #'log_level': 'info',

            # Config files
            #'cfg': '',
            #'gui_cfg': '~/.ros/rtabmap_gui.ini',
            #'rviz_cfg': '/opt/ros/humble/share/rtabmap_launch/launch/config/rgbd.rviz',

            # Frame/tf
            #'frame_id': 'base_link',
            #'odom_frame_id': 'odom',
            #'map_frame_id': 'map',
            #'publish_tf_map': 'true',

            # Topic names
            #'namespace': 'rtabmap',
            #'map_topic': 'map',
            #'output_goal_topic': '/goal_pose',
            #'use_action_for_goal': 'false',

            # Database
            #'database_path': '/tmp/rtabmap.db',
            #'delete_db_on_start': 'true',

            # Sync/queue
            #'topic_queue_size': '10',
            #'queue_size': '10',
            #'qos': '0',
            #'wait_for_transform': '0.2',

            # Initalize
            #'initial_pose': '',
            #'ground_truth_frame_id': '',
            #'ground_truth_base_frame_id': '',

            # RGB-D
            #'approx_sync': 'true',
            #'approx_sync_max_interval': '0.0',
            #'rgb_topic': '/camera/camera/color/image_raw',
            #'depth_topic': '/camera/camera/aligned_depth_to_color/image_raw',
            #'camera_info_topic': '/camera/camera/color/camera_info',

            # RGB-D sync
            #'rgbd_sync': 'false',
            #'approx_rgbd_sync': 'true',
            #'subscribe_rgbd': 'false',
            #'rgbd_topic': 'rgbd_image',
            #'depth_scale': '1.0',

            # Image transport
            #'compressed': 'false',
            #'rgb_image_transport': 'compressed',
            #'depth_image_transport': 'compressedDepth',

            # Scan/lidar
            #'subscribe_scan': 'false',
            #'scan_topic': '/scan',
            #'subscribe_scan_cloud': 'false',
            #'scan_cloud_topic': '/scan_cloud',
            #'scan_normal_k': '0',

            # Odometry
            #'visual_odometry': 'true',
            #'icp_odometry': 'false',
            #'odom_topic': 'odom',
            #'vo_frame_id': 'odom',
            #'publish_tf_odom': 'true',

            # Odometry variance
            #'odom_tf_angular_variance': '0.01',
            #'odom_tf_linear_variance': '0.001',

            # Imu
            #'imu_topic': '/imu/data',
            #'wait_imu_to_init': 'false',
            #'always_check_imu_tf': 'true',

            # Fixed point data
            #'subscribe_user_data': 'false',
            #'user_data_topic': '/user_data',
            #'user_data_async_topic': '/user_data_async',
            #'gps_topic': '/gps/fix',
            #'tag_topic': '/detections',
            #'tag_linear_variance': '0.0001',
            #'tag_angular_variance': '9999.0',
            #'fiducial_topic': '/fiducial_transforms',

            # Core Rtab-map
            #'Rtabmap/DetectionRate': '5',
            #'Rtabmap/TimeThr': '0',
            #'Rtabmap/ImageBufferSize': '1',
            #'Rtabmap/PublishCloud': 'false',
            #'Rtabmap/PublishGridMap': 'false',
            #'Rtabmap/CloudVoxelSize': '0.05',

            # Motion filtering
            #'RGBD/LinearUpdate': '0.2',
            #'RGBD/AngularUpdate': '0.1',

            # Memery
            #'Mem/IncrementalMemory': 'true',

            # Grid
            #'Grid/FromDepth': 'true',
            #'Grid/CellSize': '0.1',
            #'Grid/RangeMax': '5.0',
            #'Grid/3D': 'false',
        }.items()
    )

    return LaunchDescription([
        SetEnvironmentVariable('OMP_NUM_THREADS', '4'),
        rtabmap_launch
    ])