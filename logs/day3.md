# ROS2 Day 3 — 控制器节点 + 闭环 + 延迟测量

## 完成
- 改造 sim_node：订阅 /joint_commands，把目标位置作用到 MuJoCo actuator；内部加回调计时打点
- 新增 controller_node：订阅 /joint_states，关节空间比例控制，发布 /joint_commands
- 三节点闭环：状态 → 指令 → 执行 → 新状态
- topic info 验证闭环拓扑（两话题方向相反，各 1 发 1 订）

## 闭环结果
- 控制器关节空间误差收敛并稳定在 0.0253 rad（≈1.4°），机械臂从 home 移到目标位形附近
- 稳态残差非零的原因：控制器纯比例(P) + actuator 自身 PD，两层比例控制 + 重力 →
  经典 P 控制稳态误差；如需消除可加积分项(I)
- 话题方向：/joint_states (sim发→controller收)，/joint_commands (controller发→sim收)

## 系统问题定位：Day2 的 43Hz 之谜被推翻
- Day2 现象：ros2 topic hz 测出 ~43Hz、max 间隔 2.976s，怀疑"回调太慢追不上"
- Day3 改用进程内 time.perf_counter() 直接打点测量，结论完全不同：
  - 回调耗时 mean≈0.45~0.52ms，max≈0.8~1.2ms（仅占 20ms 周期的 ~2.5%）
  - 实际间隔 mean=20.00ms，max≈20.x ms
  - 实测频率 ≈ 50.0Hz（稳定达标）
- 真相：定时器其实很准，系统无性能瓶颈；Day2 的偏低与尖峰来自
  跨进程测量工具(topic hz)受 WSL2 调度/启动抖动/切窗口影响
- 工程教训：测量工具与测量位置会影响结论；进程内打点比跨进程工具更可信；
  "假设→换更准的测量→推翻假设→定位真因"是系统 debug 的标准流程

## 核心认知
- 闭环 = 把进程内函数调用换成跨进程话题通信，引入通信/时序维度
- 同一节点可在不同话题上同时是发布者和订阅者，多节点用话题串成数据流图
- 位置指令对通信延迟鲁棒（actuator 兜底），适合上层指令；力矩指令对延迟敏感

## 踩的坑
- rqt_graph 在 WSLg 下窗口弹出但图空白（渲染问题），拓扑改用 topic info 命令验证