# ROS2 Day 2 — MuJoCo 仿真节点发布 Panda 关节状态

## 完成
- 创建 panda_sim 包，写 sim_node（MuJoCo 步进 + 发布 JointState）和 state_monitor
- 复用原 Panda 项目加载/步进/读取（panda.xml 绝对路径, mj_step, qpos[:7]/qvel[:7]）
- /joint_states 用标准消息 sensor_msgs/JointState，每条带 header.stamp 时间戳
- 三终端验证：sim_node 发布、state_monitor 每 0.5s 打印、topic hz 测频率

## 关键工程问题1：两套 Python 环境融合
- 障碍：MuJoCo 在 conda(3.10)，ROS2 Jazzy 用系统 Python(3.12)，一个节点无法同时 import
- 方案：在系统 Python(3.12) 用 pip 装 mujoco（先 apt 装 python3-pip，再 --break-system-packages）
- 评估过的备选：RoboStack 把 ROS 装进 conda / 双进程桥接；本阶段选系统 pip 最快打通

## 关键工程问题2：实测频率低于设定 + 抖动（重要，待后续优化）
- 设定 create_timer(0.02)=50Hz，但 ros2 topic hz 实测仅 41~44Hz
- 原因：每次回调要跑 n_substeps 次 mj_step + 打包发布，计算耗时 + Python 单线程
  + WSL2 调度，定时器追不上设定周期
- 观察到 max 间隔 2.976s 的尖峰、std dev≈0.1s：存在偶发大停顿（切窗口/调度/打印阻塞）
- 对应 JD 第三条"高负载响应延迟/时间戳跳变"——作为后续延迟优化的起点

## 踩的坑（debug 三连）
1. Package not found：终端没 source 工作空间（每个 shell 独立，必须 source setup.bash）
2. No executable found：setup.py 的 entry_points 的 console_scripts 是空的，没注册可执行名
3. SyntaxError line 25：nano 手改 entry_points 时括号配对错乱
   → 解决：用 cat > setup.py << 'EOF' 整体覆盖，避免逐字符手改；改完必须重新 colcon build

## 核心认知
- JointState 是机器人状态的标准消息，/joint_states 是约定话题，RViz 等工具直接认
- header.stamp 时间戳是时序对齐基础
- 标准消息类型 = 跨模块连通性的前提
- 设定频率 ≠ 实测频率，真实系统永远有调度/计算开销，必须用 topic hz 实测验证