# ROS2 Day 6（收口）— 一键部署 + QoS 配置 + 项目定稿

## 核心任务
将五节点系统收口为"开箱即跑、有文档、有架构图"的完整作品：launch 一键部署
（命中 JD 部署要求）、按话题性质配置 DDS QoS（命中 JD DDS/进程间通信）、
干净退出、README 定稿。

## 完成
- launch 文件 system.launch.py：一条命令拉起 sim_node + executor_node + policy_node
- qos_profiles.py：统一 QoS 配置，按话题性质区分可靠性策略
- 三节点 main 加 if rclpy.ok() 判断，消除 Ctrl+C 退出时的 rcl_shutdown 报错
- README.md：系统架构图 + 核心技术点 + 快速开始
- 项目正式定稿

## DDS / QoS 配置（本日技术重点）
- /joint_states（50Hz 状态流）：BEST_EFFORT + depth 1
  → 容忍丢帧，绝不为重传卡住实时性，模拟真实传感器数据流
- /joint_commands、/action_chunk（指令/动作）：RELIABLE
  → 每条都重要，保证送达
- 用 ros2 topic info --verbose 验证：/joint_states 两端均 BEST_EFFORT，
  /joint_commands 两端均 RELIABLE，发布订阅两端 QoS 一致（兼容），数据正常流
- 关键认知：QoS 不兼容（如订阅端要求 RELIABLE 而发布端为 BEST_EFFORT）会导致
  "节点正常但数据静默丢失、不报错"——这是 DDS 系统最隐蔽的连通性 bug，
  对应 JD"跨模块连通性测试/问题定位"

## 一键部署验证
- ros2 launch panda_sim system.launch.py 成功拉起三节点（编号 -1/-2/-3）
- 单终端混合输出，三节点各自频率正常：sim 50Hz、executor 50Hz/hold 0、policy 2Hz
- Ctrl+C 退出 process has finished cleanly，无 shutdown 报错

## 系统问题定位：启动后偶发频率跌落（41.9Hz）
- 现象：启动后第二个 5s 窗口，executor mean=23.85ms/41.9Hz，max=982.67ms
- 定位：sim_node 同一窗口同时出现 max=995.16ms/41.9Hz，两个独立进程同时、
  同幅度卡顿 → 共同依赖的 OS/WSL 调度层在该时刻挂起进程，非单节点代码问题
- 佐证：policy 同窗口推理 mean 仍 8.1ms 正常（是整进程被挂起，非计算变慢）；
  前后窗口均稳定 20.00ms/50Hz（一次性偶发，不持续）；多发生在启动初期
  （进程初始化 + torch 预热阶段，资源调度最不稳）
- 工程意义：再次印证非实时 OS 跑控制回路必有偶发抖动（Day5 也观测到同类现象），
  这正是真实机器人硬实时控制需 RTOS/实时内核的原因；能从"多进程同时同幅度卡顿"
  特征区分"系统调度 vs 代码 bug"是系统问题定位的核心能力

## 项目主线（简历用）
多节点闭环集成（Day3）→ AI 推理模块接入并暴露延迟瓶颈（Day4）→ 架构解耦把慢推理
移出控制回路、参数调优收敛（Day5）→ 一键部署 + DDS/QoS 配置 + 干净退出收口（Day6）。
覆盖系统集成岗核心：模块整合联调、AI 推理集成、延迟优化、DDS 通信、问题定位、部署。