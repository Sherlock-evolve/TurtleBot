import os

from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, ExecuteProcess, OpaqueFunction
from launch.actions import SetEnvironmentVariable, TimerAction
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def launch_setup(context, *args, **kwargs):
    model = LaunchConfiguration('model').perform(context)
    use_sim_time = LaunchConfiguration('use_sim_time')
    x_pose = LaunchConfiguration('x_pose')
    y_pose = LaunchConfiguration('y_pose')

    turtlebot3_gazebo_share = get_package_share_directory('turtlebot3_gazebo')
    world = os.path.join(
        turtlebot3_gazebo_share,
        'worlds',
        'turtlebot3_world.world',
    )
    urdf_path = os.path.join(
        turtlebot3_gazebo_share,
        'urdf',
        f'turtlebot3_{model}.urdf',
    )
    sdf_path = os.path.join(
        turtlebot3_gazebo_share,
        'models',
        f'turtlebot3_{model}',
        'model.sdf',
    )

    with open(urdf_path, 'r', encoding='utf-8') as urdf_file:
        robot_description = urdf_file.read()

    gazebo_env = {
        'GAZEBO_MODEL_DATABASE_URI': '',
        'GAZEBO_MODEL_PATH': os.pathsep.join([
            os.path.join(turtlebot3_gazebo_share, 'models'),
            '/usr/share/gazebo-11/models',
        ]),
        'GAZEBO_PLUGIN_PATH': os.pathsep.join([
            '/opt/ros/humble/lib',
        ]),
        'GAZEBO_RESOURCE_PATH': os.pathsep.join([
            '/usr/share/gazebo-11',
        ]),
    }

    return [
        SetEnvironmentVariable('TURTLEBOT3_MODEL', model),
        ExecuteProcess(
            cmd=[
                'gzserver',
                world,
                '-s', 'libgazebo_ros_init.so',
                '-s', 'libgazebo_ros_factory.so',
                '-s', 'libgazebo_ros_force_system.so',
            ],
            output='screen',
            additional_env=gazebo_env,
        ),
        ExecuteProcess(
            cmd=[
                'gzclient',
                '--gui-client-plugin=libgazebo_ros_eol_gui.so',
            ],
            output='screen',
            additional_env=gazebo_env,
        ),
        Node(
            package='robot_state_publisher',
            executable='robot_state_publisher',
            name='robot_state_publisher',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'robot_description': robot_description,
            }],
        ),
        TimerAction(
            period=5.0,
            actions=[
                Node(
                    package='gazebo_ros',
                    executable='spawn_entity.py',
                    arguments=[
                        '-entity', model,
                        '-file', sdf_path,
                        '-x', x_pose,
                        '-y', y_pose,
                        '-z', '0.01',
                        '-timeout', '120',
                    ],
                    output='screen',
                ),
            ],
        ),
    ]


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'model',
            default_value='waffle',
            description='TurtleBot3 model: burger, waffle, or waffle_pi.',
        ),
        DeclareLaunchArgument(
            'use_sim_time',
            default_value='true',
            description='Use Gazebo simulation clock.',
        ),
        DeclareLaunchArgument(
            'x_pose',
            default_value='-2.0',
            description='Initial robot x position in Gazebo.',
        ),
        DeclareLaunchArgument(
            'y_pose',
            default_value='-0.5',
            description='Initial robot y position in Gazebo.',
        ),
        OpaqueFunction(function=launch_setup),
    ])
