# FUEL 文件结构与功能说明

整理日期：2026-10-09。项目目录：`/home/toolpride/drone_cv/fuel`。下文路径均以此目录为基准。

本文依据本地目录、启动脚本和代码介绍 FUEL 的模块用途与运行链路。目录树省略 Git 元数据、缓存内部文件及大量编译产物。

## 1. 总体结构

```text
fuel/
├── README.md                  场景、传感器模式与运行入口
├── learning/                  FUEL 学习文档
│   ├── README.md
│   └── PROJECT_STRUCTURE_CN.md 本文
├── FUEL/                      上游源码及本地修改
│   ├── fuel_planner/          建图、前沿检测、路径与轨迹规划
│   ├── uav_simulator/         上游仿真、控制及 ROS 工具包
│   └── files/                 README 演示动图等资源
├── fuel_ws/                   ROS catkin 工作区
│   ├── src/
│   │   ├── CMakeLists.txt     指向容器内 catkin 的链接
│   │   ├── FUEL -> ../../FUEL 源码链接
│   │   └── fuel_gazebo/       本地 Gazebo/PX4 适配包
│   ├── build/                 CMake 编译中间结果
│   └── devel/                 ROS 环境脚本、可执行文件和共享库
├── PX4-Autopilot/             PX4 飞控源码、SITL 工具及构建目录
├── docker/fuel/               Docker 构建与仿真启动脚本
├── fuel_output/               论文、译文和中文说明
└── log/                       构建、运行与排查日志
```

FUEL 根据传感器数据建立地图，寻找未探索区域，选择下一观测目标，并生成无人机可执行的探索轨迹。本项目还提供 Gazebo 与 PX4 SITL 接口，将规划、传感器和运动反馈连接起来。

## 2. FUEL 各部分的功能

### 2.1 `FUEL/`：探索算法源码

`fuel_planner/` 是学习 FUEL 的主要入口。

| 子目录 | 功能 | 适合查看的问题 |
|---|---|---|
| `exploration_manager/` | 探索节点、状态机、全局与局部探索调度，包含 launch 和参数配置 | 如何从等待触发进入规划、执行、重规划和结束 |
| `active_perception/` | 前沿检测、候选观测点、感知视场、航向与可见性处理 | 怎样找到未探索区域，怎样选择观察位置和朝向 |
| `plan_env/` | 深度图／点云融合、占据地图、障碍膨胀、距离场与地图发布 | 传感器数据怎样变成规划器可查询的地图 |
| `path_searching/` | 几何与动力学约束下的路径搜索 | 起点到目标怎样寻找可行路径 |
| `plan_manage/` | 组织路径与轨迹生成；`traj_server` 对轨迹采样并发布控制目标 | 规划结果怎样成为连续的位置、速度等命令 |
| `bspline/` | B 样条表示与操作，定义轨迹 ROS 消息 | 轨迹的控制点、时间与消息如何表达 |
| `bspline_opt/` | B 样条轨迹优化，使用 NLopt 等依赖 | 怎样处理平滑性、碰撞和运动约束 |
| `poly_traj/` | 多项式轨迹相关代码 | 多项式轨迹的表示与计算 |
| `traj_utils/` | 轨迹及规划可视化等辅助工具 | RViz 中的路径和轨迹怎样绘制 |
| `utils/` | TSP 求解器、调试等依赖工具 | 多个待访问区域怎样排序 |
| `bag/` | 上游预留的数据记录目录 | 需查看实际内容才能确定是否有可用记录 |

几个值得先读的文件：

- `exploration_manager/src/exploration_node.cpp`：探索节点入口。
- `exploration_manager/src/fast_exploration_fsm.cpp`：探索状态机。
- `exploration_manager/src/fast_exploration_manager.cpp`：探索目标与规划流程。
- `active_perception/src/frontier_finder.cpp`：前沿及候选观测点处理。
- `plan_env/src/map_ros.cpp`：ROS 传感器输入与地图输出。
- `plan_manage/src/traj_server.cpp`：轨迹采样与命令发布。

`uav_simulator/` 提供上游仿真组件：`map_generator/` 生成地图，`local_sensing/` 提供局部感知，`so3_quadrotor_simulator/` 与 `so3_control/` 处理原有动力学和控制，`poscmd_2_odom/` 提供位置命令到里程计的适配。`Utils/` 中有消息定义、航点触发、位姿工具、地图服务与 RViz 工具。Gazebo/PX4 模式仍可能复用其中的消息和航点工具，但不等于同时运行所有上游仿真节点。

### 2.2 `fuel_ws/`：编译与运行工作区

`src/FUEL` 是相对软链接，实际修改应落在 `FUEL/`。`src/CMakeLists.txt` 指向 `/opt/ros/noetic/...`，宿主机没有该 ROS 安装时可能显示为不可解析链接；它面向容器内编译环境。

`build/` 保存 CMake 缓存和对象文件；`devel/` 保存 ROS 包信息、环境脚本、程序与插件。运行前在容器内执行 `source /workspace/fuel_ws/devel/setup.bash`，ROS 才能找到这些包。两者是生成结果，日常应修改源码与配置，不直接编辑编译产物。

### 2.3 `fuel_gazebo/`：仿真与 FUEL 的接口层

| 路径 | 功能 |
|---|---|
| `launch/fuel_gazebo.launch` | 总启动入口，选择场景、传感器和控制后端，连接 FUEL、仿真与 RViz |
| `launch/px4_simulator.launch` | 启动 PX4 SITL、Gazebo Iris 模型与 MAVROS |
| `launch/rviz_depth.launch` | 按传感器模式选择 RViz 显示配置 |
| `worlds/fuel_room.world` | 原简单房间、障碍、无人机和传感器定义 |
| `worlds/fuel_complex.world` | 复杂多房间与走廊场景 |
| `src/fuel_gazebo_controller.cpp` | 理想受力控制插件：接收轨迹命令，对机体施加力／力矩并发布真值里程计 |
| `scripts/camera_pose.py` | 深度模式发布光学位姿；雷达模式过滤原始点、变换到世界系并发布点云和雷达位姿 |
| `scripts/px4_offboard.py` | SITL Offboard 适配：坐标对齐、起飞、位置与速度目标转发，以及里程计适配 |
| `config/gazebo_depth.rviz` | 深度图、地图和轨迹显示配置 |
| `config/gazebo_lidar.rviz` | 雷达点云、地图和轨迹显示配置 |
| `CMakeLists.txt`、`package.xml` | 定义 ROS 包依赖、插件编译和 Python 节点安装 |

PX4 模型生成脚本运行后会创建 `fuel_gazebo/generated/`，包含 `iris_fuel.sdf` 及 `px4_simple.world`、`px4_complex.world`。检查时该目录尚未出现在当前宿主机目录树中，应将其理解为生成输出，不能因存在启动文件就认定模型已经生成。

### 2.4 两种控制后端与数据链路

默认 `control_backend:=gazebo`，使用本地理想受力控制插件：

```text
Gazebo 深度图／雷达 → camera_pose.py → FUEL 地图融合
Gazebo 真值里程计 ───────────────────→ FUEL 状态反馈
FUEL 前沿检测与探索规划 → /planning/bspline
                       → traj_server → /planning/pos_cmd
                       → Gazebo 控制插件 → 运动、碰撞与新传感器数据
```

`control_backend:=px4` 使用飞控后端：

```text
FUEL → traj_server → /planning/pos_cmd → px4_offboard.py
     → /mavros/setpoint_raw/local → PX4 SITL → Gazebo Iris
MAVROS 本地里程计 → 坐标适配 → /state_ukf/odom → FUEL
```

两种后端的 `/state_ukf/odom` 含义不同：理想 Gazebo 后端发布仿真真值；PX4 后端代码从 MAVROS 本地里程计生成世界系反馈，并在未解锁时借助 Gazebo 真值做一次坐标对齐。不能仅凭话题名称把它都称为 UKF 输出。当前 Offboard 代码要求 `sitl_only=true`，包含自动切换模式和解锁逻辑，定位是仿真使用。

| 接口 | 用途 |
|---|---|
| `/gazebo_fuel/camera/depth/image_raw` | 深度模式的图像输入 |
| `/gazebo_fuel/lidar/points_raw` | Gazebo 原始雷达点云 |
| `/gazebo_fuel/lidar/points_world` | 雷达模式供 FUEL 融合的世界系点云 |
| `/gazebo_fuel/sensor_pose` | 与传感器消息使用相同时间戳的位姿 |
| `/state_ukf/odom` | 无人机运动状态反馈 |
| `/planning/bspline` | FUEL 生成的 B 样条轨迹 |
| `/planning/pos_cmd` | 轨迹采样后的控制目标 |
| `/traj_start_trigger` | 通过航点生成器触发探索 |
| `/sdf_map/occupancy_all` | 融合后的占据地图显示输出 |

相同消息时间戳不等于位姿已经精确插值：当前 `camera_pose.py` 使用最新收到的里程计计算传感器位姿。RViz 用于显示与触发；Gazebo 负责场景、传感器、物理与碰撞。

### 2.5 `PX4-Autopilot/`、Docker、文档与日志

`PX4-Autopilot/src/` 是飞控模块源码，`ROMFS/` 包含启动配置，`Tools/` 包含仿真工具，`launch/` 提供 ROS 启动入口，`boards/` 与 `platforms/` 保存目标平台定义，`build/` 是生成的构建结果。这里只说明目录用途，不据构建目录存在判断 SITL 验证完成。

`docker/fuel/` 的入口如下：

| 文件 | 功能 |
|---|---|
| `Dockerfile` | 基于 ROS Noetic 镜像构建 FUEL 所需 NLopt 依赖环境 |
| `restart-sim.sh` | 重启上游演示仿真，使用 `fuel-noetic` 容器 |
| `restart-gazebo.sh` | 重启理想 Gazebo 后端，支持 `simple/complex`、`depth/lidar`；默认 `complex depth` |
| `restart-px4.sh` | 使用 `fuel-px4` 容器，生成模型并重启 PX4 后端 |
| `px4-env.sh` | 在 PX4 容器中设置 ROS、Gazebo 与 PX4 搜索路径 |
| `generate-px4-model.py` | 给 Iris 添加传感器，生成不含理想控制无人机的 PX4 场景 |
| `README_CN.md` | 上游演示仿真的构建和运行说明 |
| `GAZEBO_README_CN.md` | Gazebo 接口、场景与运行说明 |

宿主机项目目录 `/home/toolpride/drone_cv/fuel/` 挂载为容器内 `/workspace`，例如宿主机 `fuel_ws/` 对应 `/workspace/fuel_ws/`。这使整理后的宿主目录仍能复用原有容器内编译路径。容器自身属于 Docker 管理对象，不是这里的一个文件夹。

`fuel_output/` 保存原论文 `2010.11561v2.pdf`、中文论文 Markdown/PDF 与中文 README。`log/` 保存构建和运行记录，现有主要命名为 `YYYYMMDD-HHMMSS-用途.log`，按北京时间生成。当前新增 PX4 脚本也使用日期前缀记录主运行日志，但 ROS master 仍写固定文件 `px4-roscore.log`，并非所有日志都已完全遵循日期规则。

## 3. 学习和修改时从哪里入手

| 想做的事情 | 优先查看 |
|---|---|
| 理解 FUEL 探索流程 | `FUEL/fuel_planner/exploration_manager/` |
| 修改前沿、观测点与视场策略 | `FUEL/fuel_planner/active_perception/` |
| 修改地图融合与障碍处理 | `FUEL/fuel_planner/plan_env/` |
| 修改 Gazebo 场景 | `fuel_ws/src/fuel_gazebo/worlds/` |
| 修改传感器坐标与点云适配 | `fuel_ws/src/fuel_gazebo/scripts/camera_pose.py` |
| 修改场景、传感器和控制后端参数 | `fuel_ws/src/fuel_gazebo/launch/fuel_gazebo.launch` |
| 研究 PX4 接入 | `px4_offboard.py`、`px4_simulator.launch` 与 `docker/fuel/` |
| 查询 FUEL 运行记录 | `log/` |

推荐先看FUEL README，再看启动配置与入口代码，最后沿数据流阅读算法模块。生成目录如 `build/`、`devel/`、`__pycache__/` 用于构建或运行；学习资料、源码、数据集与实验结果各有独立用途，整理时应按实际需要处理。

