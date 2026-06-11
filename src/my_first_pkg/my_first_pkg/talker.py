"""
最简单的发布者节点：每 0.5 秒往 /chatter 话题发一句话。
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class TalkerNode(Node):
    def __init__(self):
        super().__init__('my_talker')
        self.publisher = self.create_publisher(String, '/chatter', 10)
        self.counter = 0
        self.timer = self.create_timer(0.5, self.timer_callback)
        self.get_logger().info('Talker 节点已启动')

    def timer_callback(self):
        msg = String()
        msg.data = f'你好 ROS 2，这是第 {self.counter} 条消息'
        self.publisher.publish(msg)
        self.get_logger().info(f'已发布: "{msg.data}"')
        self.counter += 1


def main(args=None):
    rclpy.init(args=args)
    node = TalkerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()