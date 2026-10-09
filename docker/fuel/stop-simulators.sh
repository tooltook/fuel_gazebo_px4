#!/usr/bin/env bash
# Stop project launchers in both backends before reusing the shared ROS master.
set -euo pipefail
pattern='^/usr/bin/python3 /opt/ros/noetic/bin/roslaunch fuel_gazebo fuel_gazebo.launch'
for container in fuel-gazebo fuel-px4; do
  if [ "$(docker inspect -f '{{.State.Running}}' "$container" 2>/dev/null || true)" != true ]; then continue; fi
  docker exec "$container" bash -lc 'pkill -INT -f "$1" || true' bash "$pattern"
  for _ in $(seq 1 30); do
    if ! docker exec "$container" pgrep -f "$pattern" >/dev/null; then break; fi
    sleep 1
  done
  if docker exec "$container" pgrep -f "$pattern" >/dev/null || docker exec "$container" pgrep -x gzserver >/dev/null; then
    echo "$container 的旧仿真尚未退出，停止切换。" >&2; exit 1
  fi
done
