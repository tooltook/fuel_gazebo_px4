# FUEL 在本机 Docker 中复现

本说明针对当前机器的 `local/ros-noetic-dev:latest` 镜像（Ubuntu 20.04、ROS Noetic）和当前仓库的 `FUEL/` 源码。已验证 CPU 版本能够编译、启动 office 场景、接收触发消息并持续规划和飞行；不需要 CUDA。

以下命令均在 FUEL 项目目录 `/home/toolpride/drone_cv/fuel` 执行。

## 1. 构建依赖镜像

FUEL 的 `bspline_opt` 固定查找 `/usr/local/lib/libnlopt.so`。附带的 Dockerfile 从已有 ROS 镜像构建 NLopt 2.7.1：

```bash
docker build -t local/fuel-noetic:nlopt-2.7.1 -f docker/fuel/Dockerfile docker/fuel
```

首次构建需要从 GitHub 获取 NLopt 源码。当前基础镜像已具备 Armadillo、PCL、RViz 和 catkin。

## 2. 建立 catkin 工作区

```bash
mkdir -p fuel_ws/src
ln -s ../../FUEL fuel_ws/src/FUEL
```

如果软链接已经存在，跳过第二条命令。编译输出放在 `fuel_ws/build` 和 `fuel_ws/devel`，源码仍在 `FUEL/`。

## 3. 启动容器并编译

首次启动容器：

```bash
docker run -d --name fuel-noetic --network host --ipc host \
  --user "$(id -u):$(id -g)" -e HOME=/tmp \
  -e DISPLAY="$DISPLAY" -e XAUTHORITY=/tmp/fuel-Xauthority \
  -v "$PWD:/workspace" \
  -v /tmp/.X11-unix:/tmp/.X11-unix:rw \
  -v "$XAUTHORITY:/tmp/fuel-Xauthority:ro" \
  -w /workspace/fuel_ws --entrypoint bash \
  local/fuel-noetic:nlopt-2.7.1 -lc 'sleep infinity'
```

已有 `fuel-noetic` 容器但未运行时，使用 `docker start fuel-noetic`。当前机器上的旧容器 `ros1-noetic-dev` 不需要改动。

编译：

```bash
docker exec -it fuel-noetic bash -lc \
  'source /opt/ros/noetic/setup.bash && cd /workspace/fuel_ws && catkin_make -j4'
```

编译结束应看到 `Built target ...` 且命令退出码为 0。源码存在若干编译警告，当前版本在这台机器上已编译成功。

## 4. 运行 office 仿真

在一个终端启动仿真：

```bash
docker exec -it fuel-noetic bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && roslaunch exploration_manager exploration.launch'
```

在第二个终端启动 RViz：

```bash
docker exec -it fuel-noetic bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && roslaunch exploration_manager rviz.launch'
```

仿真进入 `WAIT_TRIGGER` 后，用 RViz 的 **2D Nav Goal** 工具点击地图，或者在第三个终端执行以下已验证的触发命令：

```bash
docker exec -it fuel-noetic bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && rostopic pub -1 /traj_start_trigger geometry_msgs/PoseStamped "{}"'
```

检查节点与位置：

```bash
docker exec -it fuel-noetic bash -lc \
  'source /workspace/fuel_ws/devel/setup.bash && rosnode list && rostopic echo -n 1 /state_ukf/odom/pose/pose/position'
```

正常运行时会看到 `/exploration_node`、`/pcl_render_node`、`/map_pub` 等节点，规划器从 `WAIT_TRIGGER` 转入 `PLAN_TRAJ`、`PUB_TRAJ`、`EXEC_TRAJ`，里程计位置随时间变化。RViz 当前使用软件图形回退，可能显示 Mesa `libGL` 警告；节点仍可运行。

## 5. 复现范围与后续实验

此处验证的是项目提供的 **office 演示场景**。论文表 II 的定量结果使用桥梁和大型迷宫场景，各方法各运行三次，还包含 NBVP 等对比方法。当前 FUEL 仓库只附带 `office.pcd`、`office2.pcd`、`office3.pcd`、`pillar.pcd`，因此单靠本仓库不能直接重算论文表 II 或确认论文所述的 3–8 倍加速。

可先用 `FUEL/fuel_planner/exploration_manager/launch/simulator.xml` 中的 PCD 文件名切换四个附带场景，并按场景大小修改 `exploration.launch` 的探索边界。要复现表 II，还需取得桥梁和迷宫地图、对比方法实现、统一的起点和传感器配置，再记录每次探索时间和飞行距离。

完成后用 `docker stop fuel-noetic` 停止容器；之后用 `docker start fuel-noetic` 恢复容器。ROS 仿真和 RViz 进程需要重新启动。

## 再运行一轮

如果 `fuel-noetic` 容器和 RViz 仍在运行，从FUEL 项目目录执行：

```bash
bash docker/fuel/restart-sim.sh
```

脚本会停止旧仿真、复位地图及无人机，并等待规划器进入 `WAIT_TRIGGER`。每轮日志保存在FUEL 项目目录 `log/`，按北京时间命名为 `YYYYMMDD-HHMMSS-simulation.log`，历史日志保留。RViz 保持打开；随后使用 **2D Nav Goal** 再次触发，或运行第 4 节的 `rostopic pub` 命令。

## PX4 飞控入口

本机独立 `fuel-px4` 容器已构建官方 Iris + PX4 SITL + MAVROS 闭环。启动、深度/激光接口切换及定位模式说明见 [PX4_README_CN.md](PX4_README_CN.md)。默认 `sim_vision` 使用仿真真值模拟外部定位测量输入 PX4 EKF；真实 VIO/SLAM 尚未接入。
