"""
执行器节点（Day5 核心）：连接"慢推理"与"快控制"的变速箱。
- 订阅 /action_chunk（策略低频产出的动作序列），存入缓冲队列
- 以固定 50Hz 从缓冲弹出一个动作，发布到 /joint_commands
- 缓冲快空时 hold 住最后一个动作（安全兜底，等新 chunk）
设计要点：控制回路全程只有快操作，频率稳定，不受推理延迟影响。
"""
from collections import deque
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

JOINT_NAMES = [f"panda_joint{i}" for i in range(1, 8)]
CHUNK_H = 30
N_JOINTS = 7


class ExecutorNode(Node):
    def __init__(self):
        super().__init__('executor_node')

        self.sub = self.create_subscription(
            Float64MultiArray, '/action_chunk', self.chunk_callback, 10)
        self.cmd_pub = self.create_publisher(JointState, '/joint_commands', 10)

        # 动作缓冲队列：每个元素是一个 7 维目标
        self.buffer = deque()
        self.last_action = None   # 缓冲空时 hold 用

        # 高频控制定时器：50Hz
        self.control_dt = 0.02
        self.timer = self.create_timer(self.control_dt, self.control_callback)

        # 统计
        self.pub_intervals = []
        self.last_pub_t = None
        self.empty_count = 0      # 缓冲空（hold）的次数
        self.total_pub = 0
        self.report_timer = self.create_timer(5.0, self.report)

        self.get_logger().info(
            f"执行器节点已启动 | 订阅 /action_chunk，@{1/self.control_dt:.0f}Hz "
            f"发布 /joint_commands")

    def chunk_callback(self, msg):
        # 收到新 chunk：reshape 回 H x 7，逐步压入缓冲
        data = np.array(msg.data, dtype=np.float64)
        if data.size != CHUNK_H * N_JOINTS:
            self.get_logger().warn(
                f"chunk 尺寸异常: {data.size}，期望 {CHUNK_H*N_JOINTS}")
            return
        chunk = data.reshape(CHUNK_H, N_JOINTS)
        # 新计划到来：清空旧缓冲，换上新 chunk（重规划，丢弃过期动作）
        self.buffer.clear()
        for row in chunk:
            self.buffer.append(row)

    def control_callback(self):
        import time
        now = time.perf_counter()
        if self.last_pub_t is not None:
            self.pub_intervals.append(now - self.last_pub_t)
        self.last_pub_t = now

        # 从缓冲取一个动作；空了就 hold 最后一个
        if self.buffer:
            action = self.buffer.popleft()
            self.last_action = action
        elif self.last_action is not None:
            action = self.last_action
            self.empty_count += 1
        else:
            return   # 还没收到任何 chunk

        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.name = JOINT_NAMES
        msg.position = action.tolist()
        self.cmd_pub.publish(msg)
        self.total_pub += 1

    def report(self):
        if not self.pub_intervals:
            return
        iv = np.array(self.pub_intervals) * 1000
        self.get_logger().info(
            f"[exec] /joint_commands 发布间隔 mean={iv.mean():.2f}ms "
            f"max={iv.max():.2f}ms (目标20ms，频率≈{1000/iv.mean():.1f}Hz) | "
            f"5s 内发布 {self.total_pub} 次，其中 hold(缓冲空) {self.empty_count} 次")
        self.pub_intervals.clear()
        self.empty_count = 0
        self.total_pub = 0


def main(args=None):
    rclpy.init(args=args)
    node = ExecutorNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
