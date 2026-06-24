"""
策略节点：把 Diffusion Policy（Day20 从零实现的扩散模型）接入 ROS 闭环。
- 订阅 /joint_states
- 每次回调跑真实的 50 步扩散采样（真实推理延迟）
- 发布 /joint_commands
- 测量并报告推理延迟

注意：本节点用于验证"AI 推理模块作为 ROS 节点的集成 + 延迟特性"，
加载的是 Day21 的 2D 避障 DP 模型（obs 4 维/动作 16 维），喂固定假观测、
取输出前 7 维当关节目标。不追求 Panda 端到端任务性能（需另训 Panda 版 DP）。
"""
import sys
import time
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState

import torch

# !!改!! 你原项目根目录（含 src/ 子目录的那一层）
PROJECT_ROOT = "/home/xia/projects/mujoco-panda-control"
# !!改!! 你训好的 DP 模型权重绝对路径
DP_MODEL = "/home/xia/projects/mujoco-panda-control/models/bc/dp_obstacle.pt"

sys.path.insert(0, PROJECT_ROOT)
from src.imitation.diffusion_policy import DiffusionPolicy   # noqa: E402

JOINT_NAMES = [f"panda_joint{i}" for i in range(1, 8)]
PANDA_HOME_THETA = np.array([0, -0.785, 0, -2.356, 0, 1.571, 0.785])

# DP 模型维度（Day21 2D 避障：obs=4, chunk=H*2=16）
DP_OBS_DIM = 4
DP_ACT_DIM = 16
DP_T = 50


class PolicyNode(Node):
    def __init__(self):
        super().__init__('policy_node')

        # ---- 加载 Diffusion Policy ----
        self.dp = DiffusionPolicy(obs_dim=DP_OBS_DIM, act_dim=DP_ACT_DIM, T=DP_T)
        self.dp.load_state_dict(torch.load(DP_MODEL, map_location="cpu"))
        self.dp.eval()
        self.get_logger().info(f"Diffusion Policy 已加载（T={DP_T} 步扩散采样）")

        self.sub = self.create_subscription(
            JointState, '/joint_states', self.state_callback, 10)
        self.pub = self.create_publisher(JointState, '/joint_commands', 10)

        self.current_q = None
        self.infer_times = []
        self.count = 0

        self.report_timer = self.create_timer(5.0, self.report)
        self.get_logger().info("策略节点已启动 | 订阅 /joint_states，发布 /joint_commands")

    def state_callback(self, msg):
        if len(msg.position) < 7:
            return
        self.current_q = np.array(msg.position[:7])

        # ---- 真实的扩散推理（50 步去噪）----
        t0 = time.perf_counter()
        fake_obs = np.zeros(DP_OBS_DIM, dtype=np.float32)
        action_chunk = self.dp.predict(fake_obs)
        infer_ms = (time.perf_counter() - t0) * 1000.0
        self.infer_times.append(infer_ms)

        delta = np.asarray(action_chunk[:7], dtype=np.float64) * 0.1
        cmd_q = PANDA_HOME_THETA + delta

        out = JointState()
        out.header.stamp = self.get_clock().now().to_msg()
        out.name = JOINT_NAMES
        out.position = cmd_q.tolist()
        self.pub.publish(out)
        self.count += 1

    def report(self):
        if not self.infer_times:
            self.get_logger().info("[infer] 暂无推理记录")
            return
        a = np.array(self.infer_times)
        self.get_logger().info(
            f"[infer] 扩散推理延迟 mean={a.mean():.1f}ms max={a.max():.1f}ms "
            f"min={a.min():.1f}ms | 5s 内推理 {len(a)} 次 "
            f"(≈{len(a)/5:.1f}Hz)")
        self.infer_times.clear()


def main(args=None):
    rclpy.init(args=args)
    node = PolicyNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()
