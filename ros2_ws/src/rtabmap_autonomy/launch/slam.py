from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, SetEnvironmentVariable
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    rgb = '/rgb'
    depth = '/depth'
    cam_info = '/camera1_info'

    roll_arg = DeclareLaunchArgument('roll', default_value='0.0')
    pitch_arg = DeclareLaunchArgument('pitch', default_value='0.0')
    z_arg = DeclareLaunchArgument('z', default_value='0.0')

    camera_mount_tf = Node(
        package='tf2_ros',
        executable='static_transform_publisher',
        name='camera_mount_tf',
        arguments=[
            '--x', '0', '--y', '0', '--z', LaunchConfiguration('z'),
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

    obstacles_detection = Node(
        package='rtabmap_util',
        executable='obstacles_detection',
        name='obstacles_detection',
        output='screen',
        parameters=[{
            'frame_id': 'base_link',
            'approx_sync': True,
            'Grid/MaxGroundAngle': '45',
            'Grid/MaxGroundHeight': '0.15',
            'Grid/MaxObstacleHeight': '1.5',
            'Grid/RangeMax': '4.0',
            'Grid/NoiseFilteringRadius': '0.1',
            'Grid/NoiseFilteringMinNeighbors': '3',
        }],
        remappings=[
            ('cloud', '/depth_points'),
            ('obstacles', '/obstacles'),
            ('ground', '/ground'),
        ],
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
        roll_arg,
        pitch_arg,
        z_arg,
        SetEnvironmentVariable('OMP_NUM_THREADS', '4'),
        camera_mount_tf,
        camera_optical_tf,
        rgbd_odom,
        depth_to_cloud,
        obstacles_detection,
        #rtabmap_viz,
    ])