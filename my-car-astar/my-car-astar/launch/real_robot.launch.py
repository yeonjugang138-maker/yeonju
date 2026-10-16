# 실제 터틀봇용: 위치 추정(AMCL) + RViz 를 한 번에 실행 (주행 노드는 따로 실행)
import os
from ament_index_python.packages import get_package_share_directory
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    nav2 = get_package_share_directory('nav2_bringup')
    map_yaml = LaunchConfiguration('map')

    return LaunchDescription([
        DeclareLaunchArgument('map', default_value=os.path.expanduser('~/my_ws/src/my_bot/maps/map_tt.yaml')),

        # 위치 추정 (map_server + AMCL)
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(os.path.join(nav2, 'launch', 'localization_launch.py')),
            launch_arguments={
                'map': map_yaml,
                'use_sim_time': 'false',
                'params_file': os.path.join(nav2, 'params', 'nav2_params.yaml'),
            }.items()),

        # RViz
        Node(package='rviz2', executable='rviz2', output='screen',
             arguments=['-d', os.path.join(nav2, 'rviz', 'nav2_default_view.rviz')]),
    ])
