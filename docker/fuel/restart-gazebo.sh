#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
scene=${1:-complex}
case "$scene" in simple|complex) ;; *) echo "用法: $0 [complex|simple] [depth|lidar]" >&2; exit 2 ;; esac
sensor_mode=${2:-depth}
case "$sensor_mode" in depth|lidar) ;; *) echo "用法: $0 [complex|simple] [depth|lidar]" >&2; exit 2 ;; esac
container=fuel-gazebo
log_dir="$project_root/log"
mkdir -p "$log_dir"
log_stamp=$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)
log_file="$log_dir/${log_stamp}-gazebo.log"
container_log_file="/workspace/log/${log_stamp}-gazebo.log"

if [ "$(docker inspect --format '{{.State.Running}}' "$container")" != true ]; then
  docker start "$container" >/dev/null
fi

bash "$project_root/docker/fuel/stop-simulators.sh"

if ! docker exec "$container" bash -lc \
  'set -o noclobber; source /workspace/fuel_ws/devel/setup.bash && rosparam get /rosdistro >/dev/null 2>&1'; then
  docker exec -d "$container" bash -lc \
    'set -o noclobber; source /workspace/fuel_ws/devel/setup.bash && roscore > "$1" 2>&1' bash "/workspace/log/${log_stamp}-roscore-gazebo.log"
  for _ in $(seq 1 20); do
    if docker exec "$container" bash -lc \
      'set -o noclobber; source /workspace/fuel_ws/devel/setup.bash && rosparam get /rosdistro >/dev/null 2>&1'; then
      break
    fi
    sleep 1
  done
fi


docker exec -d "$container" bash -lc \
  'set -o noclobber; source /workspace/fuel_ws/devel/setup.bash && roslaunch fuel_gazebo fuel_gazebo.launch gui:=true rviz:=true scene:="$2" sensor_mode:="$3" > "$1" 2>&1' bash "$container_log_file" "$scene" "$sensor_mode"

for _ in $(seq 1 40); do
  if [ -f "$log_file" ] && grep -q 'WAIT_TRIGGER' "$log_file"; then
    echo 'Gazebo 已复位。请在 RViz 中点击 2D Nav Goal，在地图中按住左键拖动箭头并松开，开始探索。'
    exit 0
  fi
  sleep 1
done

echo "Gazebo 未在 40 秒内进入 WAIT_TRIGGER，请查看 $log_file" >&2
exit 1
