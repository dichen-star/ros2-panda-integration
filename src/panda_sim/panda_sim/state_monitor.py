"""
状态监控节点：订阅 /joint_states，定期打印 7 个关节角度。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState


class StateMonitor(Node):
    def __init__(self):
        super().__init__('state_monitor')
        self.sub = self.create_subscription(
            JointState, '/joint_states', self.cb, 10)
        self.count = 0
        self.get_logger().info('状态监控节点已启动，订阅 /joint_states ...')

    def cb(self, msg):
        self.count += 1
        # 降频打印：每收到 25 条（约 0.5s）打一次，避免刷屏
        if self.count % 25 == 0:
            q = [f"{p:+.3f}" for p in msg.position]
            stamp = msg.header.stamp.sec + msg.header.stamp.nanosec * 1e-9
            self.get_logger().info(f"[t={stamp:.2f}] 关节角(rad): {q}")


def main(args=None):
    rclpy.init(args=args)
    node = StateMonitor()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()