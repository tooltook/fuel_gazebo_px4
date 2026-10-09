# FUEL 复现项目

此目录集中保存 FUEL 相关文件，与同级 `SplaTAM/` 分开。

- `FUEL/`：上游源码及本地修改。
- `fuel_ws/`：ROS catkin 工作区、Gazebo 适配代码及编译结果。
- `docker/fuel/`：Dockerfile、启动脚本和运行说明。
- `fuel_output/`：论文、中文译文和项目说明。
- `learning/`：文件结构、模块功能与运行链路说明。
- `log/`：按北京时间日期命名的构建、运行日志。

在此目录执行 Docker 构建和重启脚本。容器把此目录挂载到 `/workspace`，内部路径保持不变。

学习文档见 [文件结构与功能说明](learning/PROJECT_STRUCTURE_CN.md)。

运行说明见 [Docker 复现](docker/fuel/README_CN.md) 和 [Gazebo 仿真](docker/fuel/GAZEBO_README_CN.md) 和 [PX4 闭环仿真](docker/fuel/PX4_README_CN.md)。


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

雷达模式同步设置 FUEL 视场为 120°×60°、地图射线与可见性量程为 8 m，属于前向雷达，尚未配置 360° 雷达探索模型。雷达模式在已知无碰撞的仿真起点初始化机体周围 0.25 m 的未知体素为自由空间，以连接雷达安装偏移造成的近场盲区；只执行一次，不清除已观测障碍。移植到其他起点或真机时必须先确认此区域无障碍，或将 `map_ros/initial_free_radius` 设为 0。深度模式保留原相机参数和 4.5 m 地图射线量程，因此这两种配置不是传感器性能完全一致的定量对比实验。在原 Gazebo 理想控制后端中，两种模式均使用仿真真值里程计；适配节点目前取最新里程计，尚未按传感器时刻插值，快速运动时需继续检查配准误差。

雷达采用 Gazebo 官方 [Block Laser 插件](https://github.com/ros-simulation/gazebo_ros_pkgs/blob/noetic-devel/gazebo_plugins/src/gazebo_ros_block_laser.cpp)，射线与场景碰撞几何相交生成测量。

直接启动时可用：

```bash
docker exec -it fuel-gazebo bash -lc 'source /workspace/fuel_ws/devel/setup.bash && roslaunch fuel_gazebo fuel_gazebo.launch scene:=complex sensor_mode:=lidar'
```

运行中的切换使用复位脚本，避免重复启动多个仿真。

## PX4 飞控闭环

使用官方 Iris 电机/动力学与 PX4 SITL，等待自动起飞悬停后同样用 RViz **2D Nav Goal** 启动：

```bash
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh complex lidar
# 深度相机也可用
bash ~/drone_cv/fuel/docker/fuel/restart-px4.sh simple depth
```

PX4 模式使用经一次坐标对齐的 PX4 EKF 里程计；默认 `sim_vision` 将仿真真值作为外部定位测量输入 PX4，尚未接入真实 VIO/SLAM。第三参数 `gps` 可用于对照，复杂场景长测尚未通过。原 Gazebo 理想控制模式使用真值里程计。两种后端切换时会停止旧仿真。配置、检查命令与验证范围见 [PX4 说明](docker/fuel/PX4_README_CN.md)。
