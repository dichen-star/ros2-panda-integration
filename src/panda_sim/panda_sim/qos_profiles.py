"""
统一的 QoS 配置：按话题性质选择可靠性策略。
- 状态流（高频、可容忍丢帧）：BEST_EFFORT，只保留最新
- 指令/动作（每条都重要）：RELIABLE，保证送达
"""
from rclpy.qos import QoSProfile, ReliabilityPolicy, HistoryPolicy, DurabilityPolicy

# 状态流：高频传感器数据，丢帧无妨，绝不为重传卡住实时性
SENSOR_QOS = QoSProfile(
    reliability=ReliabilityPolicy.BEST_EFFORT,
    history=HistoryPolicy.KEEP_LAST,
    depth=1,                                   # 只要最新一帧
    durability=DurabilityPolicy.VOLATILE,
)

# 控制指令：每条都重要，必须可靠送达
COMMAND_QOS = QoSProfile(
    reliability=ReliabilityPolicy.RELIABLE,
    history=HistoryPolicy.KEEP_LAST,
    depth=10,
    durability=DurabilityPolicy.VOLATILE,
)
