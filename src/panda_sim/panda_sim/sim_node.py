"""
MuJoCo 仿真节点（闭环版）:
- 发布 /joint_states (当前关节状态)
- 订阅 /joint_commands (目标关节位置)，作用到 MuJoCo 内置 actuator
- 记录每次步进回调的耗时，用于延迟分析
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
from panda_sim.qos_profiles import SENSOR_QOS, COMMAND_QOS
import mujoco
import numpy as np
import time

# ！！改成你的绝对路径！！
PANDA_XML = "/home/xia/projects/mujoco-panda-control/assets/mujoco_menagerie/franka_emika_panda/panda.xml"

PANDA_HOME_THETA = np.array([0, -0.785, 0, -2.356, 0, 1.571, 0.785])
JOINT_NAMES = [f"panda_joint{i}" for i in range(1, 8)]


class PandaSimNode(Node):
    def __init__(self):
        super().__init__('panda_sim_node')

        self.model = mujoco.MjModel.from_xml_path(PANDA_XML)
        self.data = mujoco.MjData(self.model)
        self.data.qpos[:7] = PANDA_HOME_THETA
        if self.model.nq > 7:
            self.data.qpos[7:] = 0.04
        mujoco.mj_forward(self.model, self.data)

        # 目标位置：初始为 home，等控制器发来指令后更新
        self.target_q = PANDA_HOME_THETA.copy()
        self.data.ctrl[:7] = self.target_q   # 内置 actuator 的目标

        self.pub = self.create_publisher(JointState, '/joint_states', SENSOR_QOS)
        self.sub = self.create_subscription(
            JointState, '/joint_commands', self.command_callback, COMMAND_QOS)

        self.control_dt = 0.02
        self.physics_dt = self.model.opt.timestep
        self.n_substeps = max(1, int(round(self.control_dt / self.physics_dt)))
        self.timer = self.create_timer(self.control_dt, self.step_callback)

        # 延迟统计
        self.cb_times = []          # 每次回调耗时
        self.last_cb_wall = None    # 上次回调的墙钟时刻
        self.intervals = []         # 相邻回调实际间隔
        self.report_timer = self.create_timer(5.0, self.report_timing)

        self.get_logger().info(
            f"Panda 仿真节点(闭环)已启动 | substeps={self.n_substeps} "
            f"| 发布 /joint_states，订阅 /joint_commands @50Hz")

    def command_callback(self, msg):
        # 收到目标位置指令，更新 actuator 目标
        if len(msg.position) >= 7:
            self.target_q = np.array(msg.position[:7])

    def step_callback(self):
        t0 = time.perf_counter()

        # 记录相邻回调间隔
        now = time.perf_counter()
        if self.last_cb_wall is not None:
            self.intervals.append(now - self.last_cb_wall)
        self.last_cb_wall = now

        # 把目标位置喂给内置 actuator，步进物理
        self.data.ctrl[:7] = self.target_q
        for _ in range(self.n_substeps):
            mujoco.mj_step(self.model, self.data)

        # 发布状态
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.header.frame_id = "panda_link0"
        msg.name = JOINT_NAMES
        msg.position = self.data.qpos[:7].tolist()
        msg.velocity = self.data.qvel[:7].tolist()
        self.pub.publish(msg)

        self.cb_times.append(time.perf_counter() - t0)

    def report_timing(self):
        if not self.cb_times:
            return
        cb = np.array(self.cb_times) * 1000      # ms
        iv = np.array(self.intervals) * 1000 if self.intervals else np.array([0.0])
        self.get_logger().info(
            f"[timing] 回调耗时 mean={cb.mean():.2f}ms max={cb.max():.2f}ms | "
            f"实际间隔 mean={iv.mean():.2f}ms max={iv.max():.2f}ms "
            f"(目标 {self.control_dt*1000:.0f}ms) | 实测频率≈{1000/iv.mean():.1f}Hz")
        self.cb_times.clear()
        self.intervals.clear()


def main(args=None):
    rclpy.init(args=args)
    node = PandaSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
