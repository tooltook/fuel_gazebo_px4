#!/usr/bin/env python3
"""SITL-only FUEL position/velocity feedforward bridge, with frame calibration."""
import copy
import math
import threading
import time
import numpy as np
import rospy
import tf.transformations as tf
from geometry_msgs.msg import PoseStamped
from nav_msgs.msg import Odometry
from mavros_msgs.msg import State, PositionTarget
from mavros_msgs.srv import CommandBool, SetMode
from quadrotor_msgs.msg import PositionCommand

class Offboard:
    def __init__(self):
        if not rospy.get_param('~sitl_only', False):
            raise RuntimeError('Explicit sitl_only=true required for automatic arming')
        self.lock = threading.RLock()
        self.state = State(); self.local = None; self.truth = None; self.command = None
        self.command_time = 0.; self.rotation = None; self.offset = None; self.yaw_offset = 0.
        self.ready = False; self.hover_since = None
        self.height = rospy.get_param('~takeoff_height', 1.0)
        self.localization = rospy.get_param('~localization', 'gps')
        if self.localization not in ('gps', 'sim_vision'):
            raise ValueError('localization must be gps or sim_vision')
        self.vision_pub = rospy.Publisher('/mavros/vision_pose/pose', PoseStamped, queue_size=10)
        self.last_vision_stamp = None
        self.pub = rospy.Publisher('/mavros/setpoint_raw/local', PositionTarget, queue_size=10)
        self.odom_pub = rospy.Publisher('/state_ukf/odom', Odometry, queue_size=10)
        rospy.Subscriber('/mavros/state', State, self.on_state)
        rospy.Subscriber('/mavros/local_position/odom', Odometry, self.on_local)
        rospy.Subscriber('/gazebo_fuel/ground_truth', Odometry, self.on_truth)
        rospy.Subscriber('/planning/pos_cmd', PositionCommand, self.on_command)
        self.arm = rospy.ServiceProxy('/mavros/cmd/arming', CommandBool)
        self.mode = rospy.ServiceProxy('/mavros/set_mode', SetMode)

    def on_state(self, m):
        with self.lock: self.state = m
    def on_truth(self, m):
        with self.lock:
            self.truth = m
            if self.localization == 'sim_vision':
                if self.last_vision_stamp is None or (m.header.stamp-self.last_vision_stamp).to_sec() >= .019:
                    pose=PoseStamped(); pose.header=copy.deepcopy(m.header); pose.pose=copy.deepcopy(m.pose.pose)
                    self.vision_pub.publish(pose); self.last_vision_stamp=m.header.stamp
    def on_command(self, m):
        with self.lock: self.command=m; self.command_time=time.monotonic()
    def on_local(self, m):
        with self.lock:
            self.local=m
            if self.ready:
                out=copy.deepcopy(m); out.header.frame_id='world'; out.child_frame_id='base_link'
                p=m.pose.pose.position; q=m.pose.pose.orientation; v=m.twist.twist.linear
                pos=self.rotation @ np.array([p.x,p.y,p.z])+self.offset
                quat=tf.quaternion_multiply(tf.quaternion_from_euler(0,0,self.yaw_offset),[q.x,q.y,q.z,q.w])
                out.pose.pose.position.x,out.pose.pose.position.y,out.pose.pose.position.z=pos
                out.pose.pose.orientation.x,out.pose.pose.orientation.y,out.pose.pose.orientation.z,out.pose.pose.orientation.w=quat
                # MAVROS Odometry twist is body-frame; FUEL expects world velocity.
                vel=tf.quaternion_matrix(quat)[:3,:3] @ np.array([v.x,v.y,v.z])
                out.twist.twist.linear.x,out.twist.twist.linear.y,out.twist.twist.linear.z=vel
                self.odom_pub.publish(out)

    def run(self):
        rate=rospy.Rate(50); warmup=time.monotonic(); last_request=0.; held=None
        connected_since = None
        while not rospy.is_shutdown():
            with self.lock:
                state=self.state; local=self.local; truth=self.truth
                if state.connected and local and truth:
                    if connected_since is None: connected_since = time.monotonic()
                else: connected_since = None
                if connected_since is not None and time.monotonic()-connected_since > 8 and self.rotation is None:
                    # One-time world/local alignment while disarmed.
                    # sim_vision additionally feeds truth to the PX4 EKF as a simulated localization sensor.
                    if not state.armed:
                        q=local.pose.pose.orientation; t=truth.pose.pose.orientation
                        self.yaw_offset=tf.euler_from_quaternion([t.x,t.y,t.z,t.w])[2]-tf.euler_from_quaternion([q.x,q.y,q.z,q.w])[2]
                        self.rotation=tf.quaternion_matrix(tf.quaternion_from_euler(0,0,self.yaw_offset))[:3,:3]
                        p=local.pose.pose.position; t=truth.pose.pose.position
                        self.offset=np.array([t.x,t.y,t.z])-self.rotation@np.array([p.x,p.y,p.z])
                        rospy.loginfo('PX4 world/local frame aligned; takeoff target z=%.2f',self.height)
                        warmup=time.monotonic()
                if self.rotation is None:
                    rate.sleep(); continue
                p=local.pose.pose.position; world=self.rotation@np.array([p.x,p.y,p.z])+self.offset
                target=np.array([0.,0.,self.height]); vel=np.zeros(3); yaw=0.
                if state.armed and state.mode=='OFFBOARD' and np.linalg.norm(world-target)<.18:
                    if self.hover_since is None: self.hover_since=time.monotonic()
                    if not self.ready and time.monotonic()-self.hover_since>2:
                        self.ready=True; held=(target.copy(),yaw)
                        rospy.loginfo('PX4_READY: hover reached; use RViz 2D Nav Goal to explore')
                elif not self.ready: self.hover_since=None
                if self.ready:
                    if self.command and time.monotonic()-self.command_time<.5:
                        c=self.command; target=np.array([c.position.x,c.position.y,c.position.z])
                        vel=np.array([c.velocity.x,c.velocity.y,c.velocity.z]); yaw=c.yaw; held=(target.copy(),yaw)
                    elif held: target,yaw=held
                    else: target=world.copy()
                msg=PositionTarget(); msg.header.stamp=rospy.Time.now()
                # MAVROS converts the ROS ENU values to MAVLink LOCAL_NED.
                msg.coordinate_frame=PositionTarget.FRAME_LOCAL_NED
                msg.type_mask=PositionTarget.IGNORE_AFX|PositionTarget.IGNORE_AFY|PositionTarget.IGNORE_AFZ|PositionTarget.IGNORE_YAW_RATE
                goal=self.rotation.T@(target-self.offset); feed=self.rotation.T@vel
                msg.position.x,msg.position.y,msg.position.z=goal
                msg.velocity.x,msg.velocity.y,msg.velocity.z=feed
                msg.yaw=math.atan2(math.sin(yaw-self.yaw_offset),math.cos(yaw-self.yaw_offset))
                self.pub.publish(msg)
            now=time.monotonic()
            if now-warmup>3 and now-last_request>2 and state.connected:
                try:
                    if state.mode!='OFFBOARD': self.mode(custom_mode='OFFBOARD')
                    elif not state.armed: self.arm(True)
                except rospy.ServiceException as e: rospy.logwarn_throttle(5,str(e))
                last_request=now
            rate.sleep()

if __name__=='__main__':
    rospy.init_node('fuel_px4_offboard')
    try:
        Offboard().run()
    except rospy.ROSInterruptException:
        pass
