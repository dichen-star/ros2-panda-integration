# ROS 2 具身智能系统集成 · Panda 机械臂闭环控制与策略推理

基于 ROS 2 (Jazzy) 将自研的机械臂控制与学习栈封装为分布式多节点系统，打通从
MuJoCo 仿真、实时控制到 Diffusion Policy 推理的全链路，并通过架构解耦与 QoS 配置
解决了 AI 推理延迟、控制实时性、跨模块通信可靠性等真实系统集成问题。

## 系统架构

五个独立 ROS 2 节点，通过 DDS 话题通信，构成闭环：
policy_node ──/action_chunk──▶ executor_node ──/joint_commands──▶ sim_node

(2Hz,扩散推理)   (RELIABLE)     (50Hz,缓冲变速箱)   (RELIABLE)    (50Hz,仿真+控制)

▲                              │

└──────/joint_states───────────┘

(50Hz, BEST_EFFORT)

- **sim_node**：运行 MuJoCo Franka Panda 仿真，发布关节状态 `/joint_states`，
  订阅并执行 `/joint_commands`
- **policy_node**：加载从零实现的 Diffusion Policy（50 步扩散采样），低频(2Hz)
  产出动作序列 chunk，发布到 `/action_chunk`
- **executor_node**：连接"慢推理"与"快控制"的缓冲层，50Hz 从缓冲弹出动作，
  缓冲见底时 hold 兜底
- **controller_node** / **state_monitor**：可选的经典 PD 控制器与状态监控节点

## 核心技术点

### 1. 多模块集成与环境隔离
- MuJoCo (conda Python 3.10) 与 ROS 2 (系统 Python 3.12) 的环境融合
- 从零实现的 Diffusion Policy (PyTorch) 作为独立 ROS 节点接入闭环推理

### 2. 推理延迟瓶颈的定位与解决（系统问题闭环）
- 定位：扩散推理单次 mean≈6ms / max≈29ms，偶发超过 20ms 控制周期，威胁实时性
- 解决：action chunking + 执行器缓冲，将慢推理(2Hz)移出控制回路
- 结果：控制回路稳定 50Hz（发布间隔 mean=20.00ms），不受推理尖峰影响；
  通过 chunk 长度调优(H=30) 将缓冲见底(hold)从 68% 降至 0%，运动连续

### 3. DDS / QoS 按话题性质配置
- 状态流 `/joint_states`：BEST_EFFORT + depth 1（容忍丢帧，不为重传卡实时性）
- 控制指令 `/joint_commands`、动作 `/action_chunk`：RELIABLE（保证送达）
- 通过 `ros2 topic info --verbose` 验证两端 QoS 一致性；理解 QoS 不兼容会导致
  "节点正常但数据静默丢失"——跨模块连通性排查的关键认知

### 4. 一键部署
- launch 文件一条命令拉起整个多节点闭环系统

## 快速开始

```bash
# 编译
cd ~/ros2_ws
colcon build --packages-select panda_sim
source install/setup.bash

# 一键启动整个系统
ros2 launch panda_sim system.launch.py

# 另开终端：查看话题 QoS / 频率
ros2 topic info /joint_states --verbose     # Reliability: BEST_EFFORT
ros2 topic info /joint_commands --verbose   # Reliability: RELIABLE
ros2 topic hz /joint_commands               # ≈ 50Hz
```

## 技术栈
ROS 2 Jazzy · rclpy · DDS / QoS · MuJoCo · PyTorch · Diffusion Policy · WSL2 / Ubuntu 24.04

## 开发日志
逐日开发与系统问题排查记录见 [logs/](logs/)。