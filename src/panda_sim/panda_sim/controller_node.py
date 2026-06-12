"""
控制器节点:
- 订阅 /joint_states (当前关节角)
- 对一个固定目标位姿做关节空间比例控制
- 发布目标位置到 /joint_commands
这是闭环的"控制器"一环，与仿真节点是两个独立进程，通过话题通信。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import numpy as np

JOINT_NAMES = [f"panda_joint{i}" for i in range(1, 8)]

# 目标关节位形（让机械臂从 home 移动到这里）
TARGET_Q = np.array([0.5, -0.3, 0.2, -1.8, 0.0, 1.5, 0.785])


class ControllerNode(Node):
    def __init__(self):
        super().__init__('controller_node')

        self.sub = self.create_subscription(
            JointState, '/joint_states', self.state_callback, 10)
        self.pub = self.create_publisher(JointState, '/joint_commands', 10)

        self.current_q = None
        self.kp = 0.3   # 比例增益：每步朝目标移动的比例（位置指令，温和即可）
        self.count = 0
        self.get_logger().info("控制器节点已启动 | 订阅 /joint_states，发布 /joint_commands")

    def state_callback(self, msg):
        if len(msg.position) < 7:
            return
        self.current_q = np.array(msg.position[:7])

        # 关节空间比例控制：目标位置 = 当前 + kp*(目标-当前)
        # 输出的是“下一步该去的位置”，由 sim 的 actuator 执行
        cmd_q = self.current_q + self.kp * (TARGET_Q - self.current_q)

        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.name = JOINT_NAMES
        out.position = cmd_q.tolist()
        self.pub.publish(out)

        self.count += 1
        if self.count % 50 == 0:
            err = np.linalg.norm(TARGET_Q - self.current_q)
            self.get_logger().info(f"到目标的关节空间误差: {err:.4f} rad")


def main(args=None):
    rclpy.init(args=args)
    node = ControllerNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
