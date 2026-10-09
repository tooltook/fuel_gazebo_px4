# PX4 验证记录（2026-10-09）

构建：PX4 v1.14.4 `px4_sitl_default gazebo-classic_iris` 成功（`px4-build.log`），FUEL catkin 构建成功（`px4-fuel-build.log`）。MAVROS 1.20.1。

第一轮 simple/lidar：触发后进入 EXEC_TRAJ，30 秒最大位移 10.36 m，平均/最大位置跟随误差 0.482/0.853 m，全部采样保持解锁与 OFFBOARD。随后 PX4 规划速度/加速度参数由 1.0 降为 0.5。

降速 complex/lidar：30 秒最大位移 4.91 m，平均/最大跟随误差 0.150/0.379 m，平均估计-真值差 0.308 m，全部保持解锁与 OFFBOARD。后续反复出现 No path to next viewpoint。该轮仍包含等待阶段悬停目标漂移问题；不能据此宣称长期稳定。原日志 `20261009-164945-px4.log`；统计 `px4-complex-lidar-verification.json`。

初次 simple/depth：深度图编码 32FC1，位姿 world；等待阶段机体升到 z≈2.35 m，超过 simple 规划盒上限 2.3 m，触发即无路径。定位到桥接节点等待命令时反复以当前位置作为新目标。修复为 PX4_READY 时锁定起飞目标，后续一直保持固定目标直到收到规划命令。

修复后 simple/depth：等待时 z≈1.04 m；触发后 EXEC_TRAJ。30 秒最大位移 5.453 m，平均/最大跟随误差 0.239/0.434 m，平均估计-真值差 0.124 m；深度图 14.9 Hz，里程计 29.9 Hz，指令约 99.6 Hz（均墙钟）；全部保持解锁与 OFFBOARD。统计 `px4-simple-depth-verification.json`，运行日志 `20261009-165424-px4.log`，可视化 `px4-depth-preview-fixed.png`。接口有深度图、位姿和融合地图。

切换：PX4→Gazebo simple/depth 成功进入 WAIT_TRIGGER；`20261009-165706-gazebo.log`。修复切换脚本残留循环后，所有 shell 文件逐个 bash -n 通过；launch XML 和 Python AST 解析通过。

限制：这些是短时功能验证，没有完成整幅地图的探索率统计，没有验证真机/VIO/SLAM/失联策略。里程计来自 PX4 仿真 EKF，仿真真值只用于解锁前一次坐标对齐和误差统计；地图仍受 EKF 漂移及当前传感器使用最新里程计、未做时间插值的影响。

修复悬停后第一次 complex/lidar 复测：没有收到规划 PositionCommand；FUEL 报 No coverable frontier 并进入 FINISH，虽然仍有 dormant frontier。代码检查发现 `frontier/min_candidate_clearance` 检查的是候选点附近未知体素，并非额外物理障碍距离；PX4 入口错误地把此参数从原 0.21 增到 0.4。已恢复 0.21，保留障碍膨胀 0.35。此失败轮日志 `20261009-165745-px4.log`，fixed-early/middle/late 文件保留缺失数据结果，不应当作通过指标。

恢复候选未知区距离后 complex/lidar GPS 模式 90 秒长测失败：前/中/后 30 秒平均跟随误差 0.355/1.600/3.059 m，后段平均估计-真值差 3.962 m。后段真值位置固定在约 (-6.01,-0.67,0.055)，估计 z 从 3.21 增到 4.31；Offboard/armed 仍正常，说明仅看模式不足以判断安全/成功。先碰撞还是定位异常导致偏航/规划错误，尚未确定。该轮 `20261009-170041-px4.log`，统计 `px4-complex-lidar-clearance-*.json`。因此新增 `sim_vision` 外部定位模式，用理想定位输入给 PX4 EKF，以验证定位接口和其余闭环；不等同于真实 VIO/SLAM。

启用 sim_vision 后 complex/lidar 连续 90 秒功能检查：

| 30 秒窗口 | 最大位移 m | 跟随均值/最大 m | 估计-真值均值 m | 全部 Offboard/armed |
|---|---:|---:|---:|---|
| early | 8.214 | 0.158/0.367 | 0.013 | True |
| middle | 7.398 | 0.214/0.502 | 0.012 | True |
| late | 6.135 | 0.217/0.497 | 0.023 | True |

已持续生成/执行轨迹，进入房间后返回走廊。期间出现 No path to next viewpoint，但后续重新规划并恢复 EXEC_TRAJ，未观察到此前的持续漂移/停滞。日志 `20261009-170855-px4.log`；统计 `px4-complex-lidar-sim-vision-*.json`。这证明理想外部定位条件下的 90 秒闭环，不证明整图探索完成或真实 SLAM 可靠性。

sim_vision + simple/depth 30 秒通过：最大位移 6.128 m，平均/最大跟随误差 0.171/0.520 m，估计-真值均值 0.016 m，所有采样解锁/Offboard 正常，深度图 14.6 Hz（墙钟）。统计 `px4-simple-depth-sim-vision.json`，日志 `20261009-171248-px4.log`。
