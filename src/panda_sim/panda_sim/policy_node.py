"""
策略节点（Day5 解耦版）：低频跑 Diffusion Policy 推理，一次产出一段动作 chunk。
- 订阅 /joint_states（拿最新状态）
- 用定时器以 ~2Hz 触发推理（不再绑在状态频率上）
- 每次产出 H 步动作 chunk，发布到 /action_chunk（Float64MultiArray，拉平传输）
设计要点：推理慢没关系，因为它低频、且不在控制回路里。
"""
import sys
import time
import numpy as np

import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from std_msgs.msg import Float64MultiArray

import torch

# !!改!! 你原项目根目录（含 src/ 的那一层）
PROJECT_ROOT = "/home/xia/projects/mujoco-panda-control"
# !!改!! 你训好的 DP 模型权重
DP_MODEL = "/home/xia/projects/mujoco-panda-control/models/bc/dp_obstacle.pt"

sys.path.insert(0, PROJECT_ROOT)
from src.imitation.diffusion_policy import DiffusionPolicy   # noqa: E402

PANDA_HOME_THETA = np.array([0, -0.785, 0, -2.356, 0, 1.571, 0.785])

DP_OBS_DIM = 4
DP_ACT_DIM = 16        # Day21 模型：H=8 x 2
DP_T = 50

# 本节点对外约定的 chunk 形状：H 步 x 7 关节
CHUNK_H = 30
N_JOINTS = 7


class PolicyNode(Node):
    def __init__(self):
        super().__init__('policy_node')

        self.dp = DiffusionPolicy(obs_dim=DP_OBS_DIM, act_dim=DP_ACT_DIM, T=DP_T)
        self.dp.load_state_dict(torch.load(DP_MODEL, map_location="cpu"))
        self.dp.eval()
        self.get_logger().info(f"Diffusion Policy 已加载（T={DP_T}）")

        self.sub = self.create_subscription(
            JointState, '/joint_states', self.state_callback, 10)
        self.chunk_pub = self.create_publisher(Float64MultiArray, '/action_chunk', 10)

        self.current_q = None

        # 关键：推理用独立定时器，低频 2Hz（每 0.5s 一次），不再绑状态频率
        self.infer_dt = 0.5
        self.infer_timer = self.create_timer(self.infer_dt, self.infer_callback)

        self.infer_times = []
        self.report_timer = self.create_timer(5.0, self.report)
        self.get_logger().info(
            f"策略节点（解耦版）已启动 | 推理 @{1/self.infer_dt:.0f}Hz，"
            f"产出 {CHUNK_H} 步 chunk → /action_chunk")

    def state_callback(self, msg):
        if len(msg.position) >= 7:
            self.current_q = np.array(msg.position[:7])

    def infer_callback(self):
        if self.current_q is None:
            return   # 还没收到状态，先不推理

        # ---- 真实 50 步扩散推理 ----
        t0 = time.perf_counter()
        fake_obs = np.zeros(DP_OBS_DIM, dtype=np.float32)
        raw = self.dp.predict(fake_obs)        # 16 维
        self.infer_times.append((time.perf_counter() - t0) * 1000.0)

        # 把模型输出映射成 H 步、每步 7 关节的目标位置 chunk
        # （演示用：以当前 q 为基准 + 小幅扰动，构造一段平滑目标序列）
        base = self.current_q.copy()
        chunk = np.zeros((CHUNK_H, N_JOINTS), dtype=np.float64)
        for h in range(CHUNK_H):
            delta = raw[:7] * 0.1 * (h + 1) / CHUNK_H   # 沿 chunk 渐进
            chunk[h] = base + delta

        # 拉平成一维发布
        msg = Float64MultiArray()
        msg.data = chunk.flatten().tolist()    # 长度 = CHUNK_H * N_JOINTS
        self.chunk_pub.publish(msg)

    def report(self):
        if not self.infer_times:
            return
        a = np.array(self.infer_times)
        self.get_logger().info(
            f"[infer] 扩散推理 mean={a.mean():.1f}ms max={a.max():.1f}ms | "
            f"5s 内 {len(a)} 次 (≈{len(a)/5:.1f}Hz，目标 {1/self.infer_dt:.0f}Hz)")
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
