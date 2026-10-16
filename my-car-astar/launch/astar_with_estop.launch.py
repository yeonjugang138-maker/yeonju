# 주행 노드 + 공 검출 노드를 함께 실행
# (Gazebo/AMCL/RViz 는 tb3_localization.launch.py 로 따로 먼저 실행)
from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node


def generate_launch_description():
    use_sim_time = LaunchConfiguration('use_sim_time')
    source = LaunchConfiguration('source')
    model = LaunchConfiguration('model')
    target_classes = LaunchConfiguration('target_classes')

    return LaunchDescription([
        DeclareLaunchArgument('use_sim_time', default_value='true'),
        DeclareLaunchArgument('source', default_value='topic',
                              description="'topic' (터틀봇 카메라) 또는 'webcam' (노트북 웹캠)"),
        DeclareLaunchArgument('model', default_value='~/ball_best.pt',
                              description='ball_dataset으로 학습한 YOLO 가중치 경로'),
        DeclareLaunchArgument('target_classes', default_value='all',
                              description="정지할 클래스 (쉼표 구분). 'all'이면 모델의 모든 클래스"),

        Node(
            package='my_car_astar',
            executable='astar_navigation',
            output='screen',
            parameters=[{'use_sim_time': use_sim_time}],
        ),
        Node(
            package='my_car_astar',
            executable='object_detector',
            output='screen',
            parameters=[{
                'use_sim_time': use_sim_time,
                'source': source,
                'model': model,
                'target_classes': target_classes,
            }],
        ),
    ])
