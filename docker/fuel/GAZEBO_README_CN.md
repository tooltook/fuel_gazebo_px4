# FUEL 的 Gazebo 仿真

这个适配版本在 **Gazebo Classic 11** 中运行场景、刚体碰撞和深度相机；FUEL 接收 Gazebo 的深度图与里程计并输出探索轨迹。RViz 可以同时打开，用于查看地图和规划结果，但不是仿真引擎。

默认场景为 `fuel_ws/src/fuel_gazebo/worlds/fuel_complex.world`：约 20 × 20 m 的平坦室内环境，外围墙高 3.2 m，包含八个房间、2.4 m 宽的十字走廊、2 m 门洞，以及不同高度的箱体和柱子。多条门洞连接形成可绕行路线，增加转角、遮挡和探索分支。无人机仍从 `(0, 0, 1)` 起飞，深度相机和控制接口保持原配置。FUEL 地图尺寸为 24 × 24 × 5 m，探索边界为 x/y ±9.7 m、z 0.1–2.8 m。

原 12 × 12 m 简单场景 `fuel_room.world` 保留。两者都是自定义测试环境，不是论文表 II 的桥梁或迷宫场景。


## 场景与数据接口切换

在任意目录执行以下命令。每次切换都会复位地图和无人机，并打开 Gazebo、RViz；等待 `WAIT_TRIGGER` 后，用 RViz 的 **2D Nav Goal** 在地图中拖出箭头启动探索。

```bash
# 复杂场景 + 深度图（默认）
bash ~/drone_cv/fuel/docker/fuel/restart-gazebo.sh complex depth
# 原简单房间 + 深度图
bash ~/drone_cv/fuel/docker/fuel/restart-gazebo.sh simple depth
# 复杂场景 + 激光雷达
bash ~/drone_cv/fuel/docker/fuel/restart-gazebo.sh complex lidar
# 原简单房间 + 激光雷达
bash ~/drone_cv/fuel/docker/fuel/restart-gazebo.sh simple lidar
```

`complex` 为 20×20 m 的八房间走廊场景；`simple` 为原 12×12 m 房间。不带参数时默认 `complex depth`。

两种正式输入为 `depth`（深度相机图像）和 `lidar`（独立三维激光雷达点云）。旧 `cloud` 模式已移除，请改用 `lidar`。

| 模式 | 传感器 | 视场 / 量程 / 频率 | FUEL 输入 |
|---|---|---|---|
| `depth` | Gazebo 深度相机 | 水平 80° / 0.2–5 m / 15 Hz | 深度图＋相机光学位姿 |
| `lidar` | Gazebo `ray` 三维激光雷达 | 水平 120°、垂直 60° / 0.2–8 m / 10 Hz，240×32 射线 | 世界系 XYZ 点云＋雷达位姿 |

雷达位于机体上方 0.15 m，坐标轴为 x 前、y 左、z 上。`libgazebo_ros_block_laser.so` 发布 `/gazebo_fuel/lidar/points_raw`（`sensor_msgs/PointCloud`），适配节点过滤无效点、无回波量程端点，以及按机体圆柱几何识别的自回波、转换到世界系，并发布 `/gazebo_fuel/lidar/points_world`（`PointCloud2`）和相同时间戳的 `/gazebo_fuel/sensor_pose`。FUEL 此时只融合激光点云，不融合深度图或相机生成的点云。RViz 雷达配置显示实时雷达点云和融合地图，深度模式显示深度图和融合地图。

雷达模式同步设置 FUEL 视场为 120°×60°、地图射线与可见性量程为 8 m，属于前向雷达，尚未配置 360° 雷达探索模型。雷达模式在已知无碰撞的仿真起点初始化机体周围 0.25 m 的未知体素为自由空间，以连接雷达安装偏移造成的近场盲区；只执行一次，不清除已观测障碍。移植到其他起点或真机时必须先确认此区域无障碍，或将 `map_ros/initial_free_radius` 设为 0。深度模式保留原相机参数和 4.5 m 地图射线量程，因此这两种配置不是传感器性能完全一致的定量对比实验。两种模式均使用仿真真值里程计；适配节点目前取最新里程计，尚未按传感器时刻插值，快速运动时需继续检查配准误差。

雷达采用 Gazebo 官方 [Block Laser 插件](https://github.com/ros-simulation/gazebo_ros_pkgs/blob/noetic-devel/gazebo_plugins/src/gazebo_ros_block_laser.cpp)，射线与场景碰撞几何相交生成测量。

直接启动时可用：

```bash
docker exec -it fuel-gazebo bash -lc 'source /workspace/fuel_ws/devel/setup.bash && roslaunch fuel_gazebo fuel_gazebo.launch scene:=complex sensor_mode:=lidar'
```

运行中的切换使用复位脚本，避免重复启动多个仿真。

## 系统链路

```text
Gazebo world + 无人机刚体
  ├─ 深度相机 → /gazebo_fuel/camera/depth/image_raw ──────────────┐
  └─ 模型控制插件 → /state_ukf/odom ──┬─→ 相机位姿适配节点 ──────┤
                                      │    /gazebo_fuel/sensor_pose │
                                      └─→ FUEL 状态反馈             │
                                                                  ↓
                   FUEL 地图融合 → 前沿检测 → 分层探索规划 → B 样条轨迹
                                                                  ↓
                   /planning/bspline → traj_server → /planning/pos_cmd
                                                                  ↓
                   Gazebo 模型控制插件 → 刚体受力、运动和碰撞 ──────┘
```

启动信号另走一条链路：`/traj_start_trigger` → `waypoint_generator` → `/waypoint_generator/waypoints` → FUEL 规划器。RViz 只订阅地图、轨迹等话题用于显示，不负责深度图生成、动力学或碰撞计算。

`/state_ukf/odom` 在本适配中是 Gazebo 插件发布的**仿真真值里程计**，不是 UKF 或视觉里程计的估计结果。`camera_pose.py` 根据里程计计算相机光学坐标系位姿，并用深度图时间戳发布，供 FUEL 将深度像素投影到地图。`traj_server` 以 100 Hz 对 FUEL 的 B 样条轨迹采样，控制插件据位置、速度、加速度和偏航目标给 Gazebo 刚体施加力与力矩。Gazebo 产生新的运动状态和深度图，构成闭环。

## 当前机器上直接运行

以下宿主机命令均在 `/home/toolpride/drone_cv/fuel` 执行，容器内仍使用 `/workspace`。

当前已创建 `fuel-gazebo` 容器，镜像是 `local/fuel-noetic:nlopt-2.7.1`，代码已经编译。若容器已停止：

```bash
docker start fuel-gazebo
```

在终端 1 启动 ROS master：

```bash
docker exec -it fuel-gazebo bash -lc 'source /workspace/fuel_ws/devel/setup.bash && roscore'
```

在终端 2 启动 Gazebo 和 FUEL：

```bash
docker exec -it fuel-gazebo bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && roslaunch fuel_gazebo fuel_gazebo.launch gui:=true rviz:=true'
```

Gazebo 图形窗口会显示房间、障碍和红色无人机；RViz 会同时打开，左侧显示深度图，右侧显示地图和轨迹。待日志出现 `WAIT_TRIGGER` 后，点击 RViz 工具栏的 **2D Nav Goal**，在右侧地图内按住鼠标左键拖出箭头，松开即可启动探索。

此操作与官方 `waypoint_type=point` 的启动链路一致：`/move_base_simple/goal` → `waypoint_generator` → FUEL。箭头用于触发自主探索，其位置和方向不作为探索终点。必须在地图视图内操作，不能在深度图面板中拖动。运行中再次拖动不会复位；重新开始一轮需先复位。

无图形界面时仍可使用命令触发：

```bash
docker exec -it fuel-gazebo bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && rostopic pub -1 /traj_start_trigger geometry_msgs/PoseStamped "{}"'
```

如果关闭了 RViz，可单独重新打开：

```bash
docker exec -it fuel-gazebo bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && roslaunch fuel_gazebo rviz_depth.launch'
```

可以检查模型位置、深度话题与规划状态：

```bash
docker exec -it fuel-gazebo bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && rostopic echo -n 1 /state_ukf/odom/pose/pose/position'
docker exec -it fuel-gazebo bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && rostopic list | grep gazebo_fuel'
```

后台运行日志统一保存在FUEL 项目目录 `log/`，按北京时间命名为 `YYYYMMDD-HHMMSS-gazebo.log`；ROS master 日志使用同一日期前缀和 `roscore-gazebo.log` 后缀。历史日志按最后修改时间整理，保留用途后缀。上面的终端命令运行时直接显示日志。

## 重新运行或停止

完成一轮后，在终端 2 按 `Ctrl+C` 退出 `roslaunch`，再次运行同一条 `roslaunch` 命令；Gazebo 场景、无人机和 FUEL 地图会从头初始化。保留终端 1 的 `roscore` 即可。重新出现 `WAIT_TRIGGER` 后，再用 RViz 的 **2D Nav Goal** 拖动启动。

当前这台机器也可以从FUEL 项目目录直接运行一键复位脚本。它会保留上一轮日志，并使 Gazebo 停在等待触发状态：

```bash
bash docker/fuel/restart-gazebo.sh
```

全部结束后按 `Ctrl+C` 停止各终端，再执行：

```bash
docker stop fuel-gazebo
```

## 构建与代码位置

如果修改了 `fuel_gazebo` C++ 插件，在FUEL 项目目录重新编译：

```bash
docker run --rm --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -v "$PWD:/workspace" -w /workspace/fuel_ws --entrypoint bash \
  local/fuel-noetic:nlopt-2.7.1 -lc \
  'source /opt/ros/noetic/setup.bash && catkin_make -j4'
```

- `fuel_ws/src/fuel_gazebo/launch/fuel_gazebo.launch`：Gazebo、FUEL、控制节点与话题连接。
- `fuel_ws/src/fuel_gazebo/worlds/fuel_room.world`：房间、障碍、无人机与 Gazebo 深度相机。
- `fuel_ws/src/fuel_gazebo/src/fuel_gazebo_controller.cpp`：把 FUEL 轨迹命令转成 Gazebo 刚体受力，并发布里程计。
- `fuel_ws/src/fuel_gazebo/scripts/camera_pose.py`：按模式发布同步相机位姿，或将独立激光雷达点云转换到世界系后发布。

## 仿真范围

Gazebo 中的障碍碰撞、深度图和刚体位置是真实由 Gazebo 计算的。当前控制插件使用**理想化机体受力控制**，没有逐个电机、螺旋桨或飞控 SITL；因此它验证了 FUEL 与 Gazebo 场景、传感器和运动的闭环，不等同于 PX4/ArduPilot 全栈仿真，也不能直接复现论文的定量对比结果。

## PX4 后端

已增加独立的 PX4 SITL + MAVROS + 官方 Iris 入口：

```bash
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh complex lidar
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh simple depth
```

该入口使用 PX4 EKF 里程计和电机控制，区别于上文的理想受力控制。脚本等待自动起飞就绪后，再用 2D Nav Goal 触发探索。完整说明见 [PX4_README_CN.md](PX4_README_CN.md)。
