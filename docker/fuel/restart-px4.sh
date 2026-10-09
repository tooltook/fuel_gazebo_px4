#!/usr/bin/env bash
set -euo pipefail
scene=${1:-complex}; sensor=${2:-lidar}; localization=${3:-sim_vision}
case "$localization" in sim_vision|gps) ;; *) echo "定位: sim_vision 或 gps" >&2; exit 2;; esac
case "$scene" in simple|complex) ;; *) echo '场景: simple 或 complex' >&2; exit 2;; esac
case "$sensor" in depth|lidar) ;; *) echo '传感器: depth 或 lidar' >&2; exit 2;; esac
root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
mkdir -p "$root/log"
stamp=$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)
log_file="$root/log/${stamp}-px4.log"
docker start fuel-px4 >/dev/null
docker exec fuel-px4 test -x /workspace/PX4-Autopilot/build/px4_sitl_default/bin/px4
bash "$root/docker/fuel/stop-simulators.sh"
docker exec fuel-px4 bash -lc 'source /workspace/docker/fuel/px4-env.sh; python3 /workspace/docker/fuel/generate-px4-model.py'
if ! docker exec fuel-px4 bash -lc 'source /opt/ros/noetic/setup.bash; rosparam get /rosdistro' >/dev/null 2>&1; then
 docker exec -d fuel-px4 bash -lc 'source /opt/ros/noetic/setup.bash; roscore > /workspace/log/px4-roscore.log 2>&1'
 sleep 2
fi
docker exec -d fuel-px4 bash -lc 'source /workspace/docker/fuel/px4-env.sh; export DISABLE_ROS1_EOL_WARNINGS=1 PYTHONUNBUFFERED=1; roslaunch fuel_gazebo fuel_gazebo.launch control_backend:=px4 scene:="$2" sensor_mode:="$3" localization:="$4" gui:=true rviz:=true > "$1" 2>&1' bash "/workspace/log/${stamp}-px4.log" "$scene" "$sensor" "$localization"
echo "PX4 启动中，日志: $log_file"
for _ in $(seq 1 90); do
 if [ -f "$log_file" ] && grep -q 'PX4_READY' "$log_file" && grep -q 'WAIT_TRIGGER' "$log_file"; then
  echo 'PX4 已起飞悬停，FUEL 已就绪。请在 RViz 用 2D Nav Goal 拖动启动探索。'; exit 0
 fi
 if [ -f "$log_file" ] && grep -q 'REQUIRED process.*has died' "$log_file"; then break; fi
 sleep 1
done
echo "PX4 未在 90 秒内就绪，请查看 $log_file" >&2
exit 1
