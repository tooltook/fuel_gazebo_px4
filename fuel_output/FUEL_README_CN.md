# FUEL（中文说明）

> 本文是项目根目录 [README.md](../FUEL/README.md) 的中文译版。命令、文件名和配置参数保留原文写法。

## 最新消息

- 2023 年 2 月 24 日：多无人机探索代码已发布，参见 [RACER](https://github.com/SYSU-STAR/RACER)。
- 2021 年 8 月 24 日：发布基于 CPU 的仿真版本，不再要求 CUDA，并提供了更多探索环境。

**FUEL**（**F**ast **U**AV **E**xp**L**oration）是一个快速无人机自主探索框架。论文发布时，作者报告其方法完成复杂探索任务的速度比当时的先进方法快 **3–8 倍**。

方法的核心是**前沿信息结构**（Frontier Information Structure，FIS）：它随着在线地图的更新，增量维护探索规划所需的信息。在此基础上，分层规划器依次规划前沿覆盖路径、优化局部观测视点，并生成最短时间轨迹，使无人机能够敏捷、安全地探索未知环境。可从[快速开始](#快速开始)运行演示。

<p align="center">
  <img src="../FUEL/files/1.gif" width="400" height="225"/>
  <img src="../FUEL/files/2.gif" width="400" height="225"/>
  <img src="../FUEL/files/3.gif" width="400" height="225"/>
  <img src="../FUEL/files/4.gif" width="400" height="225"/>
</p>

作者后来进一步开发了面向四旋翼机群的完全去中心化探索方法。机群在异步、受限通信条件下工作，无需中央控制；系统会优化和平衡各机的覆盖路径与工作分配。相关论文发表于 IEEE TRO，代码见 [RACER](https://github.com/SYSU-STAR/RACER)。

<p align="center">
  <img src="../FUEL/files/racer1.gif" width="400" height="225"/>
  <img src="../FUEL/files/racer2.gif" width="400" height="225"/>
</p>

**完整视频：**[视频 1](https://www.youtube.com/watch?v=_dGgZUrWk-8)、[视频 2](https://www.bilibili.com/video/BV1yf4y1P7Vj)。

**作者：**来自中山大学的 [Boyu Zhou](http://sysu-star.com)，以及来自[香港科技大学空中机器人团队](http://uav.ust.hk/)的 [Shaojie Shen](http://uav.ust.hk/group/)。

如果在研究中使用本项目，请引用论文：

- [**FUEL: Fast UAV Exploration using Incremental Frontier Structure and Hierarchical Planning**](https://arxiv.org/abs/2010.11561)，Boyu Zhou、Yichen Zhang、Xinyi Chen、Shaojie Shen，*IEEE Robotics and Automation Letters*（**RA-L**），ICRA 2021 会议选项。

```bibtex
@article{zhou2021fuel,
  title={FUEL: Fast UAV Exploration Using Incremental Frontier Structure and Hierarchical Planning},
  author={Zhou, Boyu and Zhang, Yichen and Chen, Xinyi and Shen, Shaojie},
  journal={IEEE Robotics and Automation Letters},
  volume={6},
  number={2},
  pages={779--786},
  year={2021},
  publisher={IEEE}
}
```

如果这个项目对你有帮助，作者也欢迎为仓库点星支持。

## 目录

- [快速开始](#快速开始)
- [探索不同环境](#探索不同环境)
- [创建 PCD 环境](#创建-pcd-环境)
- [致谢](#致谢)

## 快速开始

项目已在 Ubuntu 18.04（ROS Melodic）和 Ubuntu 20.04（ROS Noetic）上测试。

首先安装 **NLopt v2.7.1**：

```bash
git clone -b v2.7.1 https://github.com/stevengj/nlopt.git
cd nlopt
mkdir build
cd build
cmake ..
make
sudo make install
```

接着安装其他依赖：

```bash
sudo apt-get install libarmadillo-dev
```

然后将项目克隆到 catkin 工作空间并编译（原文使用 SSH 地址）：

```bash
cd ${YOUR_WORKSPACE_PATH}/src
git clone git@github.com:HKUST-Aerial-Robotics/FUEL.git
cd ../
catkin_make
```

编译完成后，先启动 RViz 进行可视化：

```bash
source devel/setup.bash && roslaunch exploration_manager rviz.launch
```

在**另一个终端**启动仿真：

```bash
source devel/setup.bash && roslaunch exploration_manager exploration.launch
```

默认显示类似办公室的环境。在 RViz 中使用 **2D Nav Goal** 工具触发四旋翼开始探索。下图示例中，灰色表示尚未探索的结构，彩色体素表示已探索区域；还会显示无人机视场（FoV）和飞行轨迹。

<p id="demo1" align="center">
  <img src="../FUEL/files/office.gif" width="600" height="325"/>
</p>

## 探索不同环境

仿真器通过 [.pcd 点云文件](https://pointclouds.org/documentation/tutorials/pcd_file_format.html)表示探索环境。项目提供了多个示例，可在 [simulator.xml](../FUEL/fuel_planner/exploration_manager/launch/simulator.xml) 中选择：

```xml
<!-- 修改 office.pcd 以指定探索环境 -->
<!-- 仓库提供 office.pcd、office2.pcd、office3.pcd 和 pillar.pcd -->
<node pkg="map_generator" name="map_pub" type="map_pub" output="screen" args="$(find map_generator)/resource/office.pcd"/>
```

其他环境示例：

*office2.pcd*：

<p id="demo2" align="center">
  <img src="../FUEL/files/office2.gif" width="600" height="325"/>
</p>

*office3.pcd*：

<p id="demo3" align="center">
  <img src="../FUEL/files/office3.gif" width="600" height="325"/>
</p>

*pillar.pcd*：

<p id="demo4" align="center">
  <img src="../FUEL/files/pillar.gif" width="320" height="325"/>
</p>

若要使用自己的环境，把 `.pcd` 文件放入 [map_generator/resource](../FUEL/uav_simulator/map_generator/resource)，并按上面的示例修改配置。你可能还需要在 [exploration.launch](../FUEL/fuel_planner/exploration_manager/launch/exploration.launch) 中调整探索空间的边界框：

```xml
<arg name="box_min_x" value="-10.0"/>
<arg name="box_min_y" value="-15.0"/>
<arg name="box_min_z" value=" 0.0"/>
<arg name="box_max_x" value="10.0"/>
<arg name="box_max_y" value="15.0"/>
<arg name="box_max_z" value=" 2.0"/>
```

创建自己的 `.pcd` 环境可参阅[下一节](#创建-pcd-环境)。

## 创建 PCD 环境

项目提供了一个简单的 `.pcd` 环境创建工具。先运行：

```bash
rosrun map_generator click_map
```

然后在 RViz 中使用 **2D Nav Goal** 工具（快捷键 `G`）绘制地图。连续点击的两个点会形成一面墙，例如：

<p id="demo5" align="center">
  <img src="../FUEL/files/create_map.gif" width="600" height="340"/>
</p>

绘制完成后，在另一个终端运行以下节点保存地图：

```bash
rosrun map_generator map_recorder ~/
```

通常会在 `~/` 目录下生成名为 **tmp.pcd** 的文件。也可以把命令中的 `~/` 替换为其他保存位置。最后按[探索不同环境](#探索不同环境)一节的方法使用该文件。

## 致谢

项目使用 **NLopt** 进行非线性优化，并使用 **LKH** 求解旅行商问题。
