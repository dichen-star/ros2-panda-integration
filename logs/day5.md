# ROS2 Day 5 — 动作分块解耦慢推理与快控制

## 核心任务
解决 Day4 发现的延迟瓶颈：扩散推理（mean 6ms、max 29ms）进入控制回路时，偶发尖峰会
顶破 20ms 控制周期。本日用 action chunking + 执行器缓冲，把"慢推理"移出控制回路，
让控制频率稳定 50Hz 不受推理影响。对应 JD 第三条"驱动问题闭环解决"。

## 架构改造：三层速率
- policy_node（2Hz，慢）：独立定时器低频跑 50 步扩散，一次产出 H 步动作 chunk，
  发布到 /action_chunk（Float64MultiArray 拉平传输）
- executor_node（50Hz，新增核心）：订阅 /action_chunk 存入缓冲队列，每 20ms 弹出
  一个动作发布到 /joint_commands；缓冲空时 hold 最后一个动作（安全兜底）
- sim_node（50Hz，不变）：执行 + 发布 /joint_states
- 数据流：policy →(/action_chunk,2Hz)→ executor →(/joint_commands,50Hz)→ sim →(/joint_states)→ policy

## 实测：解耦成功
- executor /joint_commands 发布间隔 mean=20.00ms（稳定 50Hz），尽管 policy 仅 2Hz
- policy 扩散推理 mean=7~10ms、首次 max=33.9ms（torch 预热）、稳态 max≈8ms，频率稳定 ≈2Hz
- sim 控制回调耗时 mean=0.38~0.49ms、稳定 50Hz
- 对比 Day4（推理在控制回路、max 29ms 威胁 20ms 周期）：Day5 控制回路全程只有
  "取缓冲+发消息"的快操作，推理尖峰被完全隔离 → 控制频率不再被推理拖累

## 发现并修正：chunk 长度过短致缓冲频繁见底
- 初版 H=8：executor 250 次发布中 hold 170 次（68%），机器人动 160ms 停 340ms，不连续
- 原因：policy 2Hz=每 500ms 一个 chunk，executor 每 500ms 消费 25 个动作，
  但 H=8 仅够 160ms（8×20ms），剩 340ms 缓冲见底靠 hold 撑
- 修正：H 增至 30（30×20ms=600ms > 500ms 推理间隔），一个 chunk 覆盖整个间隔，
  新 chunk 在见底前到达 → hold 从 170 次降到 0 次，运动连续
- 认知：解耦架构正确 ≠ 参数正确；chunk 长度必须 ≥ 推理间隔内消费量 + 余量

## 其他观测
- 初次测试时 sim 与 executor 同一时刻同时出现 ~730ms 尖峰（瞬时跌到 43.8Hz）：
  多进程同时、幅度一致 → 确认是 WSL2/OS 系统级调度事件，非单节点问题，
  印证非实时系统固有抖动
- Ctrl+C 退出报 rcl_shutdown already called：无害（退出时信号已触发 shutdown、
  finally 又调一次）；已用 if rclpy.ok() 判断后再 shutdown 消除，实现干净退出

## 价值
完整闭环：Day4 发现延迟瓶颈 → Day5 架构解耦 → 参数调优收敛。"发现问题→架构方案→
参数调优→数据验证"是系统集成岗的核心能力。chunk + 执行器缓冲 + hold 兜底是
π0/ACT 等真实策略落地的标准范式的最小实现。