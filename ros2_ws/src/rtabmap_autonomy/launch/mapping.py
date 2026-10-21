import os

from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    rgb = '/rgb'
    depth = '/depth'
    cam_info = '/camera1_info'

    # rtabmap_params.yaml sits next to this file (realpath so --symlink-install resolves to src)
    default_params = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'mapping.yaml')
    params_arg = DeclareLaunchArgument('params_file', default_value=default_params)
    params_file = LaunchConfiguration('params_file')

    roll_arg = DeclareLaunchArgument('roll', default_value='0.0')
    pitch_arg = DeclareLaunchArgument('pitch', default_value='0.0')
    z_arg = DeclareLaunchArgument('z', default_value='0.0')
    # NEW: Grid/Footprint* is a box centred on base_link, so the camera's real x/y matter.
    # A wrong offset makes RTAB-Map delete real ground in front of the robot (or keep the robot body).
    x_arg = DeclareLaunchArgument('x', default_value='0.0')

    camera_mount_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_mount_tf',
        arguments=[
            '--x', LaunchConfiguration('x'), '--y', '0', '--z', LaunchConfiguration('z'),
            '--roll', LaunchConfiguration('roll'),
            '--pitch', LaunchConfiguration('pitch'),
            '--yaw', '0',
            '--frame-id', 'base_link',
            '--child-frame-id', 'camera_mount',
        ],
    )

    camera_optical_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_optical_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', '0',
            '--roll', '-1.5708', '--pitch', '0', '--yaw', '-1.5708',
            '--frame-id', 'camera_mount',
            '--child-frame-id', 'camera1',
        ],
    )

    # Unchanged: odometry stays on this node (the Odom/* params from the repo yaml do not apply to it)
    rgbd_odom = Node(
        package='rtabmap_odom',
        executable='rgbd_odometry',
        name='rgbd_odometry',
        output='screen',
        parameters=[{
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'publish_tf': True,
            'approx_sync': True,
            'wait_for_transform': 0.2,
            'sync_queue_size': 10,
            'Odom/Strategy': '0',
            'Odom/GuessMotion': 'true',
            'Odom/ResetCountdown': '1',
            'Vis/MinInliers': '15',
            'Vis/MaxDepth': '8.0',
            'Vis/MaxFeatures': '600',
        }],
        remappings=[
            ('rgb/image', rgb),
            ('depth/image', depth),
            ('rgb/camera_info', cam_info),
            ('odom', '/odom'),
            ('odom_info', '/odom_info'),
        ],
        arguments=['--ros-args', '--log-level', 'warn'],
    )

    # Unchanged
    depth_to_cloud = Node(
        package='rtabmap_util',
        executable='point_cloud_xyz',
        name='depth_to_cloud',
        output='screen',
        parameters=[{
            'approx_sync': True,
            'decimation': 2,
            'max_depth': 4.0,
            'min_depth': 0.2,
            'voxel_size': 0.05,
        }],
        remappings=[
            ('depth/image', depth),
            ('depth/camera_info', cam_info),
            ('cloud', '/depth_points'),
        ],
    )

    # Now uses the repo's ground-segmentation params (normals-based) via the shared yaml
    obstacles_detection = Node(
        package='rtabmap_util',
        executable='obstacles_detection',
        name='obstacles_detection',
        output='screen',
        parameters=[params_file, {
            'frame_id': 'base_link',
            'approx_sync': True,
        }],
        remappings=[
            ('cloud', '/depth_points'),
            ('obstacles', '/obstacles'),
            ('ground', '/ground'),
        ],
    )

    # NEW: the actual mapping node. Publishes /map and map->odom TF.
    rtabmap = Node(
        package='rtabmap_slam',
        executable='rtabmap',
        name='rtabmap',
        output='screen',
        parameters=[params_file, {
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'subscribe_depth': True,
            'approx_sync': True,
            'wait_for_transform': 0.2,
            'sync_queue_size': 10,
            'topic_queue_size': 10,
        }],
        remappings=[
            ('rgb/image', rgb),
            ('depth/image', depth),
            ('rgb/camera_info', cam_info),
            ('odom', '/odom'),
        ],
        arguments=['-d'],  # delete database on start
    )

    rtabmap_viz = Node(
        package='rtabmap_viz',
        executable='rtabmap_viz',
        name='rtabmap_viz',
        output='screen',
        parameters=[{
            'frame_id': 'base_link',
            'odom_frame_id': 'odom',
            'subscribe_depth': True,
            'subscribe_odom_info': True,
            'approx_sync': True,
            'queue_size': 10,
        }],
        remappings=[
            ('rgb/image', rgb),
            ('depth/image', depth),
            ('rgb/camera_info', cam_info),
            ('odom', '/odom'),
            ('odom_info', '/odom_info'),
        ],
        arguments=['--ros-args', '--log-level', 'warn'],
    )

    return LaunchDescription([
        params_arg,
        roll_arg,
        pitch_arg,
        z_arg,
        x_arg,
        SetEnvironmentVariable('OMP_NUM_THREADS', '4'),
        camera_mount_tf,
        camera_optical_tf,
        rgbd_odom,
        depth_to_cloud,
        obstacles_detection,
        rtabmap,
        rtabmap_viz,
    ])