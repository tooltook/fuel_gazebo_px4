#!/usr/bin/env python3
"""Adapt Gazebo depth images or laser point clouds for FUEL mapping."""
import threading
import numpy as np

import rospy
import tf.transformations as tf
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from sensor_msgs.msg import Image, PointCloud, PointCloud2, PointField


class CameraPose:
    def __init__(self):
        self.lock = threading.Lock()
        self.odom = None
        self.sensor_x = rospy.get_param('~sensor_x', 0.0)
        self.depth_z = rospy.get_param('~depth_z', 0.0)
        self.lidar_z = rospy.get_param('~lidar_z', 0.15)
        self.mask_cylinder = rospy.get_param('~mask_cylinder', True)
        self.publisher = rospy.Publisher('/gazebo_fuel/sensor_pose', PoseStamped, queue_size=10)
        rospy.Subscriber('/state_ukf/odom', Odometry, self.on_odom, queue_size=10)
        mode = rospy.get_param('~sensor_mode', 'depth')
        if mode == 'depth':
            rospy.Subscriber('/gazebo_fuel/camera/depth/image_raw', Image,
                             self.on_depth, queue_size=2)
        elif mode == 'lidar':
            self.cloud_publisher = rospy.Publisher('/gazebo_fuel/lidar/points_world', PointCloud2,
                                                   queue_size=2)
            rospy.Subscriber('/gazebo_fuel/lidar/points_raw', PointCloud,
                             self.on_lidar, queue_size=1, buff_size=2 * 1024 * 1024)
        else:
            raise ValueError('sensor_mode must be depth or lidar')

    def on_odom(self, message):
        with self.lock:
            self.odom = message

    def sensor_transform(self, lidar=False):
        with self.lock:
            odom = self.odom
        if odom is None:
            return
        position = odom.pose.pose.position
        orientation = odom.pose.pose.orientation
        body = tf.quaternion_matrix((orientation.x, orientation.y,
                                     orientation.z, orientation.w))
        body[:3, 3] = (position.x, position.y, position.z)
        optical_to_body = [[0, 0, 1, 0], [-1, 0, 0, 0],
                           [0, -1, 0, 0], [0, 0, 0, 1]]
        if lidar:
            lidar_to_body = np.eye(4)
            lidar_to_body[0, 3] = self.sensor_x
            lidar_to_body[2, 3] = self.lidar_z
            camera = tf.concatenate_matrices(body, lidar_to_body)
        else:
            optical_to_body[0][3] = self.sensor_x
            optical_to_body[2][3] = self.depth_z
            camera = tf.concatenate_matrices(body, optical_to_body)
        return camera

    def make_pose(self, stamp, camera):
        quaternion = tf.quaternion_from_matrix(camera)
        pose = PoseStamped()
        pose.header.stamp = stamp
        pose.header.frame_id = 'world'
        pose.pose.position.x, pose.pose.position.y, pose.pose.position.z = camera[:3, 3]
        pose.pose.orientation.x, pose.pose.orientation.y, pose.pose.orientation.z, \
            pose.pose.orientation.w = quaternion
        return pose

    def on_depth(self, image):
        camera = self.sensor_transform()
        if camera is not None:
            self.publisher.publish(self.make_pose(image.header.stamp, camera))

    def on_lidar(self, message):
        sensor = self.sensor_transform(lidar=True)
        if sensor is None:
            return
        xyz = np.array([(p.x, p.y, p.z) for p in message.points], dtype=np.float32).reshape(-1, 3)
        # Exclude invalid/no-return points and the plugin's range-limit endpoints.
        distance = np.linalg.norm(xyz, axis=1)
        valid = np.isfinite(xyz).all(axis=1) & (distance >= 0.2) & (distance < 7.999)
        # The ray sensor can see its own cylinder body at the bottom scan angles.
        # Mask only the modeled body (radius .18 m, half-height .05 m), with
        # 2.5 cm tolerance for the block-laser angle interpolation.
        self_hit = ((xyz[:, 0] ** 2 + xyz[:, 1] ** 2) <= 0.205 ** 2) & \
                   (np.abs(xyz[:, 2] + 0.15) <= 0.075)
        xyz = xyz[valid & ~self_hit] if self.mask_cylinder else xyz[valid]
        xyz = np.ascontiguousarray(xyz @ sensor[:3, :3].T + sensor[:3, 3], dtype='<f4')
        output = PointCloud2()
        output.header.stamp = message.header.stamp
        output.header.frame_id = 'world'
        output.height = 1
        output.width = len(xyz)
        output.fields = [PointField(n, i * 4, PointField.FLOAT32, 1)
                         for i, n in enumerate(('x', 'y', 'z'))]
        output.is_bigendian = False
        output.point_step = 12
        output.row_step = output.width * 12
        output.is_dense = True
        output.data = xyz.tobytes()
        self.cloud_publisher.publish(output)
        self.publisher.publish(self.make_pose(message.header.stamp, sensor))


if __name__ == '__main__':
    rospy.init_node('fuel_gazebo_camera_pose')
    CameraPose()
    rospy.spin()
