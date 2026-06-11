"""
最简单的订阅者节点：订阅 /chatter，收到就打印。
"""
import rclpy
from rclpy.node import Node
from std_msgs.msg import String


class ListenerNode(Node):
    def __init__(self):
        super().__init__('my_listener')
        self.subscription = self.create_subscription(
            String, '/chatter', self.listener_callback, 10)
        self.get_logger().info('Listener 节点已启动，等待消息...')

    def listener_callback(self, msg):
        self.get_logger().info(f'我收到了: "{msg.data}"')


def main(args=None):
    rclpy.init(args=args)
    node = ListenerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()