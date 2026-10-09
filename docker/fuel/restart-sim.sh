#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)
log_dir="$project_root/log"
mkdir -p "$log_dir"
log_stamp=$(TZ=Asia/Shanghai date +%Y%m%d-%H%M%S)
log_file="$log_dir/${log_stamp}-simulation.log"
container_log_file="/workspace/log/${log_stamp}-simulation.log"
container=fuel-noetic
launch_pattern='^/usr/bin/python3 /opt/ros/noetic/bin/roslaunch exploration_manager exploration.launch$'

docker inspect --format '{{.State.Running}}' "$container" | grep -qx true

docker exec "$container" bash -lc \
  "pid=\$(pgrep -f '$launch_pattern' || true); if [ -n \"\$pid\" ]; then kill -INT \"\$pid\"; fi"

for _ in $(seq 1 30); do
  if ! docker exec "$container" pgrep -f "$launch_pattern" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

if docker exec "$container" pgrep -f "$launch_pattern" >/dev/null 2>&1; then
  echo "旧仿真进程未在 30 秒内退出。" >&2
  exit 1
fi


docker exec -d "$container" bash -lc \
  'set -o noclobber; source /workspace/fuel_ws/devel/setup.bash && roslaunch exploration_manager exploration.launch > "$1" 2>&1' bash "$container_log_file"

for _ in $(seq 1 30); do
  if [ -f "$log_file" ] && grep -q 'WAIT_TRIGGER' "$log_file"; then
    echo '仿真已复位，RViz 中使用 2D Nav Goal 再次触发探索。'
    exit 0
  fi
  sleep 1
done

echo "仿真未在 30 秒内进入 WAIT_TRIGGER，请查看 $log_file" >&2
exit 1
