"""
一键启动整个 Panda 闭环系统：仿真 + 执行器 + 策略。
用法：ros2 launch panda_sim system.launch.py
"""
from launch import LaunchDescription
from launch_ros.actions import Node


def generate_launch_description():
    return LaunchDescription([
        Node(
            package='panda_sim',
            executable='sim_node',
            name='panda_sim_node',
            output='screen',
        ),
        Node(
            package='panda_sim',
            executable='executor_node',
            name='executor_node',
            output='screen',
        ),
        Node(
            package='panda_sim',
            executable='policy_node',
            name='policy_node',
            output='screen',
        ),
    ])
