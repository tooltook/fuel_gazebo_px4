#!/usr/bin/env python3
"""Read-only 30-second SITL telemetry probe; run inside fuel-px4 after triggering."""
import json, time, math
import rospy
from nav_msgs.msg import Odometry
from mavros_msgs.msg import State
from quadrotor_msgs.msg import PositionCommand
from sensor_msgs.msg import PointCloud2, Image
rospy.init_node('fuel_px4_verification',anonymous=True)
data={}; counts={}; samples=[]
def cb(m,k):
 data[k]=m; counts[k]=counts.get(k,0)+1
for topic,cls,k in [('/state_ukf/odom',Odometry,'odom'),('/gazebo_fuel/ground_truth',Odometry,'truth'),('/mavros/state',State,'state'),('/planning/pos_cmd',PositionCommand,'cmd'),('/gazebo_fuel/lidar/points_world',PointCloud2,'cloud'),('/gazebo_fuel/camera/depth/image_raw',Image,'depth')]: rospy.Subscriber(topic,cls,cb,k)
start=time.monotonic()
while time.monotonic()-start<30:
 if all(k in data for k in ['odom','truth','cmd','state']):
  p=data['odom'].pose.pose.position; t=data['truth'].pose.pose.position; c=data['cmd'].position; s=data['state']
  samples.append({'pos':[p.x,p.y,p.z],'truth':[t.x,t.y,t.z],'error':math.sqrt((p.x-c.x)**2+(p.y-c.y)**2+(p.z-c.z)**2),'truth_error':math.sqrt((p.x-t.x)**2+(p.y-t.y)**2+(p.z-t.z)**2),'offboard':s.mode=='OFFBOARD','armed':s.armed})
 time.sleep(.1)
if samples:
 print(json.dumps({'samples':len(samples),'start':samples[0],'end':samples[-1],'max_displacement':max(math.dist(x['pos'],samples[0]['pos']) for x in samples),'tracking_mean':sum(x['error'] for x in samples)/len(samples),'tracking_max':max(x['error'] for x in samples),'truth_mean':sum(x['truth_error'] for x in samples)/len(samples),'offboard_all':all(x['offboard'] and x['armed'] for x in samples),'hz':{k:round(v/30,1) for k,v in counts.items()}},indent=2))
else:
 print('Missing data',list(data))
 raise SystemExit(1)
