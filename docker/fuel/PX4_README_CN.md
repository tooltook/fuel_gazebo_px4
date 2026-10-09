# FUEL + PX4 SITL

此入口使用 PX4 v1.14.4、官方 Gazebo Classic Iris、MAVROS 1.20.1 与 ROS Noetic。独立容器为 `fuel-px4`，原理想控制入口仍为 `fuel-gazebo`。两个入口共享 ROS master，切换脚本会先停止两边旧的 FUEL 仿真，再启动选定后端。

## 启动与切换

在宿主机任意目录执行：

```bash
# PX4 + 复杂场景 + 三维激光雷达
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh complex lidar
# PX4 + 简单场景 + 深度相机
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh simple depth
# 对照：仅 GPS/气压计定位，复杂场景长测未通过
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh simple lidar gps
# 回到理想控制后端
bash ~/drone_cv/fuel/docker/fuel/restart-gazebo.sh complex depth
```

PX4 脚本默认 `complex lidar sim_vision`，同时支持四种场景/传感器组合。等待脚本提示“PX4 已起飞悬停，FUEL 已就绪”，或日志同时出现 `PX4_READY`、`WAIT_TRIGGER`，然后在 RViz 点击 **2D Nav Goal**，按住左键拖出箭头并松开，开始自主探索。箭头只触发探索，其位置不是指定航点。启动会自动切换 Offboard、解锁并起飞到估计世界坐标 z=1 m；它只面向本地 SITL，不能直接用于真机。

## 数据链路与配置位置

`Gazebo 深度图或激光点云 → FUEL 建图与探索 → /planning/pos_cmd → Offboard 适配节点 → MAVROS → PX4 姿态/电机控制 → Gazebo Iris`。

| 内容 | 文件或话题 |
|---|---|
| 后端、场景、传感器、速度、障碍膨胀 | `fuel_ws/src/fuel_gazebo/launch/fuel_gazebo.launch` |
| 官方 PX4/MAVROS 仿真入口 | `fuel_ws/src/fuel_gazebo/launch/px4_simulator.launch` |
| 起飞、坐标对齐、位置＋速度前馈 | `fuel_ws/src/fuel_gazebo/scripts/px4_offboard.py` |
| 传感器外参、点云转换 | `fuel_ws/src/fuel_gazebo/scripts/camera_pose.py` |
| 模型生成 | `docker/fuel/generate-px4-model.py` |
| FUEL 里程计 | `/state_ukf/odom`，world 坐标系 |
| PX4 原始局部里程计 | `/mavros/local_position/odom` |
| 仿真外部定位（仅 sim_vision） | `/mavros/vision_pose/pose`，约 50 Hz 仿真时间 |
| PX4 接收的控制指令 | `/mavros/setpoint_raw/local`，50 Hz 仿真时间 |
| 仿真真值（外部定位、校准及验证） | `/gazebo_fuel/ground_truth` |

PX4 后端始终把 **PX4 EKF 输出**作为 FUEL 里程计。支持两种定位来源：

- `sim_vision`（默认）：Gazebo 真值以约 50 Hz 发布到 `/mavros/vision_pose/pose`，作为理想外部定位传感器输入给 PX4。启动前配置 `EKF2_EV_CTRL=11`（水平位置、垂直位置、偏航），`EKF2_HGT_REF=3`，关闭 GPS、气压计和磁力计融合。此模式验证定位接口、EKF、规划、飞控和动力学闭环，**不验证真实 VIO/SLAM**。
- `gps`：不发布仿真外部定位，融合 GPS/气压计。当前复杂场景长测失败，出现实际车辆停在地面而 EKF 高度继续漂移的现象，保留此模式供对照与排查。

连接后先等待 8 秒，再在解锁前用 Gazebo 真值对齐一次 PX4 局部坐标系的平移和偏航。之后坐标变换固定。`gps` 模式只在校准及诊断时使用真值；`sim_vision` 模式持续使用真值模拟外部定位测量，但 FUEL 仍订阅 PX4 EKF 输出。等待触发时固定保持起飞目标。MAVROS 接口值为 ROS ENU，MAVROS 完成 MAVLink NED 转换。传感器位姿由估计机体位姿加外参得到，点云也转换到估计 world 系。

外部定位接口依据 [PX4 v1.14 官方说明](https://docs.px4.io/v1.14/en/ros/external_position_estimation)。未来接真实定位时，应以 VIO 或激光 SLAM 的位姿替换仿真真值发布端，并重新验证外参、延迟、坐标系和噪声参数。

传感器安装在 Iris 前方 x=0.35 m、上方 z=0.15 m，避开机体。两种传感器都存在于模型中，但 FUEL 每次只融合所选接口。PX4 模式的规划速度/加速度参数各设为 0.5 m/s、0.5 m/s²（规划器按分量约束，实际合速度可能更高），障碍膨胀 0.35 m，候选点对未知区的排斥距离 0.21 m（独立于 0.35 m 障碍膨胀）；起飞悬停后仅一次把已知安全起点周围 0.5 m 内的未知体素初始化为自由，不覆盖测得障碍。此初始化依赖当前场景中心无障碍的假设。

模型和 world 位于 `fuel_ws/src/fuel_gazebo/generated/`，每次启动重新生成。模型生成脚本还在 PX4 的构建目录 `etc/init.d-posix/px4-rc.params` 中维护带标记的本项目 EKF 启动配置，在估计器启动前应用参数；重新编译后下次启动会重新生成。修改源场景 `worlds/fuel_room.world` 或 `worlds/fuel_complex.world`，不要直接修改 generated。PX4 world 移除了原理想无人机，仅保留官方 Iris，由 PX4 控制。

## 已构建环境与重新编译

本机 `fuel-px4` 已安装 MAVROS、GeographicLib 数据和 PX4 编译依赖。PX4 源码位于 `~/drone_cv/fuel/PX4-Autopilot`；第一次构建较慢，重启脚本只启动已编译程序。依赖安装当前保存在容器中，删除容器后需重新安装；原 `Dockerfile` 是 FUEL 基础镜像，不包含这些额外依赖。

```bash
# 在本机既有 fuel-px4 容器重新编译
 docker exec -it fuel-px4 bash -lc 'cd /workspace/PX4-Autopilot && DONT_RUN=1 make px4_sitl_default gazebo-classic_iris -j4'
 docker exec -it fuel-px4 bash -lc 'source /opt/ros/noetic/setup.bash && cd /workspace/fuel_ws && catkin_make -j4'
```

## 检查与停止

触发探索后，可采集 30 秒只读统计：

```bash
docker exec fuel-px4 bash -lc 'source /workspace/docker/fuel/px4-env.sh && python3 /workspace/docker/fuel/verify-px4.py'
```

输出包括实际移动距离、估计位置与规划位置的跟随误差、估计与真值偏差、Offboard/解锁状态和传感器频率。统计按墙钟计时，Gazebo 运行较慢时墙钟频率会低于配置的仿真频率。它是短时功能检查，不能证明完整场景探索率或长期稳定性。

日志在 `~/drone_cv/fuel/log/日期-px4.log`。停止所有本项目仿真：

```bash
bash ~/drone_cv/fuel/docker/fuel/stop-simulators.sh
```

当前不包含 VIO/激光 SLAM 输入、真机链路、手动遥控接管和失联策略的完整验证。两种定位模式的验证范围不同；实测跟随误差需结合地图净空评估，不能把本配置直接视为真机避障方案。

## 本机验证记录

构建与逐轮飞行记录保存在 `log/PX4_VERIFICATION_20261009.md`；原始统计为 `log/px4-*-verification.json` 及 `log/px4-complex-lidar-fixed-*.json`。请按该记录中的具体测试范围判断接口状态，不把短时飞行通过等同于完整复杂场景探索完成。

已验证的默认 `sim_vision` 组合：complex/lidar 连续 90 秒、simple/depth 连续 30 秒，均实际生成并执行探索轨迹，平均跟随误差约 0.16–0.22 m；其余组合可切换但尚未完成同等飞行采样。详见上述验证记录。
