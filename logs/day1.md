# ROS2 Day 1 — 环境搭建与第一对 pub/sub 节点

## 完成
- WSL2 Ubuntu 24.04 上安装 ROS 2 Jazzy（非 Humble，按系统版本对应）
- 创建 colcon 工作空间 ~/ros2_ws，建 ament_python 包 my_first_pkg
- 写 talker / listener 两个节点，/chatter 话题 std_msgs/String 通信
- colcon build 通过，三终端验证：node list / topic info 正常

## 踩的坑（面试素材）
1. .bashrc 里 source 的是 /opt/ros/humble，但实际装的是 jazzy → 路径不存在报错。
   教训：ROS 发行版与 Ubuntu 版本绑定（24.04→Jazzy）。
2. 第二个终端报 "Package not found"：该终端没 source 工作空间。
   根因：每个终端是独立 shell，环境变量不共享，必须先 source setup.bash。
   → 解决：把 jazzy + 工作空间两行 source 写进 .bashrc（顺序：先 jazzy 后 ws）。
3. conda base 自动激活会干扰 ROS（系统 Python 3.12 vs conda 3.10）→ 关闭自动激活。

## 核心认知
- 节点=独立进程；话题=发布订阅通道；包=容器，节点=容器里的代码
- 调试三件套：ros2 topic echo / hz / info —— 看数据流是否打通
- ROS2 去中心化、基于 DDS，区别于 ROS1 的 master 中心节点