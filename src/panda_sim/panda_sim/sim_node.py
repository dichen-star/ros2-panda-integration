"""
MuJoCo 仿真节点：在内部步进 Franka Panda，把关节状态以
sensor_msgs/JointState 发布到 /joint_states。
复用原 Panda 项目的加载/步进/读取方式。
"""
import rclpy
from rclpy.node import Node
from sensor_msgs.msg import JointState
import mujoco
import numpy as np

# ！！改成你 Step 1 realpath 得到的绝对路径 ！！
PANDA_XML = "/home/xia/projects/mujoco-panda-control/assets/mujoco_menagerie/franka_emika_panda/panda.xml"

PANDA_HOME_THETA = np.array([0, -0.785, 0, -2.356, 0, 1.571, 0.785])
JOINT_NAMES = [f"panda_joint{i}" for i in range(1, 8)]   # 7 个臂关节的名字


class PandaSimNode(Node):
    def __init__(self):
        super().__init__('panda_sim_node')

        # ---- 加载 MuJoCo 模型（复用原项目方式）----
        self.model = mujoco.MjModel.from_xml_path(PANDA_XML)
        self.data = mujoco.MjData(self.model)
        self.data.qpos[:7] = PANDA_HOME_THETA
        if self.model.nq > 7:
            self.data.qpos[7:] = 0.04          # 夹爪张开（和原项目一致）
        mujoco.mj_forward(self.model, self.data)

        # ---- 发布者：/joint_states ----
        self.pub = self.create_publisher(JointState, '/joint_states', 10)

        # ---- 仿真步进定时器 ----
        # 控制周期 50Hz（0.02s）；每个周期内步进若干物理步以匹配 MuJoCo 时间步
        self.control_dt = 0.02
        self.physics_dt = self.model.opt.timestep
        self.n_substeps = max(1, int(round(self.control_dt / self.physics_dt)))
        self.timer = self.create_timer(self.control_dt, self.step_callback)

        self.get_logger().info(
            f"Panda 仿真节点已启动 | physics_dt={self.physics_dt:.4f}s "
            f"substeps={self.n_substeps} | 发布 /joint_states @50Hz")

    def step_callback(self):
        # 暂时不加控制力矩，让机械臂在重力下自由演化（Day 2 只验证状态发布）
        # 注意：panda.xml 默认带位置 actuator，data.ctrl 全 0 时会把关节拉向 0 位
        for _ in range(self.n_substeps):
            mujoco.mj_step(self.model, self.data)

        # ---- 打包 JointState 消息 ----
        msg = JointState()
        msg.header.stamp = self.get_clock().now().to_msg()   # 关键：打时间戳
        msg.header.frame_id = "panda_link0"
        msg.name = JOINT_NAMES
        msg.position = self.data.qpos[:7].tolist()
        msg.velocity = self.data.qvel[:7].tolist()
        # effort 可留空，也可填 qfrc
        self.pub.publish(msg)


def main(args=None):
    rclpy.init(args=args)
    node = PandaSimNode()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()