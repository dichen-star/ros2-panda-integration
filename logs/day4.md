# ROS2 Day 4 — Diffusion Policy 接入 ROS 策略节点 + 推理延迟测量

## 核心任务
把一个神经网络推理模块（Day20 从零实现的 Diffusion Policy）作为独立 ROS 节点
接入系统，订阅 /joint_states、发布 /joint_commands，并测出其真实推理延迟。
正面对应 JD 第一条"RL/VLA 推理模块的整合联调"。

## 完成
- 系统 Python(3.12) 安装 CPU 版 torch，打通 AI 推理模块的运行环境
- 新增 policy_node：加载 DiffusionPolicy，每次回调跑真实 50 步扩散采样，
  发布 /joint_commands，并打点报告推理延迟
- sim_node 作为参照系：50.0Hz 稳定运行，回调耗时仅 0.3~0.4ms（Day3 已验证的健康基线）

## 环境融合（JD 第一条）
- 障碍1：torch 在 conda(Python 3.10)，ROS2 Jazzy 在系统 Python(3.12)，
  一个节点无法默认同时 import rclpy 与 torch
- 解决1：系统 Python 装 CPU 版 torch（--break-system-packages）；
  节点内 sys.path 引入原项目，复用自实现的 DiffusionPolicy
- 障碍2：原项目 __init__.py 用绝对导入 from src.imitation.bc_policy ...，
  要求"项目根目录"在 sys.path 上，而非 src 目录本身
- 报错：ModuleNotFoundError: No module named 'src'
- 解决2：PROJECT_ROOT 指向项目根（src 的上一层），import 改为
  from src.imitation.diffusion_policy import DiffusionPolicy，与原项目约定一致
- 选 CPU 推理：50 步采样 CPU 足够，避开 GPU 驱动(cu130 vs 驱动12.7)问题

## 核心发现：AI 推理延迟 >> 控制回路（JD 第三条）
- 扩散推理（50 步去噪）延迟：mean≈6.0ms，max≈29.4ms（首次）/7~8ms（稳态），min≈5.3ms
- 对比 sim_node 控制回调耗时仅 0.3~0.4ms → 推理慢约一个数量级
- max 29.4ms 出现在第一次推理：torch 首次前向的预热/缓存效应，之后回落到 7~8ms
- 原因：扩散模型一次采样 = 50 次网络前向（BC 仅 1 次）
- 现状：单次 mean 6ms 尚能跟上 50Hz 状态流，但 max 偶发超过 20ms 控制周期，
  说明随扩散步数增大或网络变大，延迟会顶破周期 → 真实的"高负载响应延迟"

## 重要说明（诚实标注）
- 本节点加载 Day21 的 2D 避障 DP 模型（obs 4 维 / 动作 16 维），喂固定假观测、
  取输出前 7 维当关节目标，仅用于验证"AI 推理节点的集成与延迟特性"
- 不代表 Panda 端到端任务性能；做真任务需另训 Panda 版 DP（obs23/act7），属独立工作量

## 踩的坑
- import 根路径约定不统一（src 目录 vs 项目根）→ 跨代码库集成的典型问题，
  必须与被集成项目的导入约定保持一致
- torch 首次推理延迟显著高于稳态（预热效应），测延迟时应区分首次与稳态

## 下一步
用 action chunking + 低频推理解耦"慢推理"与"快控制"：策略节点低频输出一整段动作，
控制节点高频逐个执行（复用 Day21 动作分块思想），把"测到延迟"升级为"解决延迟"。