cmake_minimum_required(VERSION 3.0.2)
project(fuel_gazebo)
set(CMAKE_CXX_STANDARD 14)

find_package(catkin REQUIRED COMPONENTS roscpp nav_msgs quadrotor_msgs)
find_package(gazebo REQUIRED)

catkin_package(LIBRARIES fuel_gazebo_controller)
include_directories(${catkin_INCLUDE_DIRS} ${GAZEBO_INCLUDE_DIRS})
link_directories(${GAZEBO_LIBRARY_DIRS})
add_library(fuel_gazebo_controller SHARED src/fuel_gazebo_controller.cpp)
add_dependencies(fuel_gazebo_controller ${catkin_EXPORTED_TARGETS})
target_link_libraries(fuel_gazebo_controller ${catkin_LIBRARIES} ${GAZEBO_LIBRARIES})

catkin_install_python(PROGRAMS scripts/camera_pose.py scripts/px4_offboard.py DESTINATION ${CATKIN_PACKAGE_BIN_DESTINATION})
