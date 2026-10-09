#!/usr/bin/env bash
# Source only inside the fuel-px4 container.
source /opt/ros/noetic/setup.bash
source /workspace/fuel_ws/devel/setup.bash
px4_root=/workspace/PX4-Autopilot
source "$px4_root/Tools/simulation/gazebo-classic/setup_gazebo.bash" "$px4_root" "$px4_root/build/px4_sitl_default"
export ROS_PACKAGE_PATH="$ROS_PACKAGE_PATH:$px4_root:$px4_root/Tools/simulation/gazebo-classic/sitl_gazebo-classic"
export GAZEBO_MODEL_DATABASE_URI=""
