#include <algorithm>
#include <cmath>
#include <memory>
#include <mutex>

#include <gazebo/common/Plugin.hh>
#include <gazebo/gazebo.hh>
#include <gazebo/physics/physics.hh>
#include <nav_msgs/Odometry.h>
#include <quadrotor_msgs/PositionCommand.h>
#include <ros/ros.h>

namespace gazebo {

// Ideal force actuator: Gazebo supplies rigid-body physics, collision and sensing.
// This is deliberately simpler than a rotor/motor model.
class FuelGazeboController : public ModelPlugin {
 public:
  void Load(physics::ModelPtr model, sdf::ElementPtr sdf) override {
    model_ = model;
    link_ = model_->GetLink("body");
    if (!link_) {
      gzerr << "fuel_gazebo_controller: body link missing\n";
      return;
    }
    if (!ros::isInitialized()) {
      gzerr << "fuel_gazebo_controller: load Gazebo through gazebo_ros\n";
      return;
    }

    mass_ = link_->GetInertial()->Mass();
    target_position_ = ignition::math::Vector3d(0, 0, 1);
    nh_.reset(new ros::NodeHandle);
    odom_pub_ = nh_->advertise<nav_msgs::Odometry>("/state_ukf/odom", 10);
    cmd_sub_ = nh_->subscribe("/planning/pos_cmd", 10,
                              &FuelGazeboController::CommandCallback, this);
    spinner_.reset(new ros::AsyncSpinner(1));
    spinner_->start();
    update_connection_ = event::Events::ConnectWorldUpdateBegin(
        std::bind(&FuelGazeboController::Update, this));
    ROS_INFO("FUEL Gazebo controller loaded for %s", model_->GetName().c_str());
  }

 private:
  static double WrapAngle(double angle) {
    return std::atan2(std::sin(angle), std::cos(angle));
  }

  void CommandCallback(const quadrotor_msgs::PositionCommand::ConstPtr& msg) {
    std::lock_guard<std::mutex> lock(command_mutex_);
    target_position_.Set(msg->position.x, msg->position.y, msg->position.z);
    target_velocity_.Set(msg->velocity.x, msg->velocity.y, msg->velocity.z);
    target_acceleration_.Set(msg->acceleration.x, msg->acceleration.y, msg->acceleration.z);
    target_yaw_ = msg->yaw;
  }

  void Update() {
    if (!link_ || !ros::ok()) return;
    const auto now = model_->GetWorld()->SimTime();
    const double dt = (now - last_time_).Double();
    if (dt <= 0) return;
    last_time_ = now;

    const auto pose = link_->WorldPose();
    const auto velocity = link_->WorldLinearVel();
    const auto angular_velocity = link_->WorldAngularVel();
    ignition::math::Vector3d target_position, target_velocity, target_acceleration;
    double target_yaw;
    {
      std::lock_guard<std::mutex> lock(command_mutex_);
      target_position = target_position_;
      target_velocity = target_velocity_;
      target_acceleration = target_acceleration_;
      target_yaw = target_yaw_;
    }

    const auto position_error = target_position - pose.Pos();
    const auto velocity_error = target_velocity - velocity;
    auto acceleration = target_acceleration + 7.0 * position_error + 5.0 * velocity_error;
    acceleration.X(std::max(-5.0, std::min(5.0, acceleration.X())));
    acceleration.Y(std::max(-5.0, std::min(5.0, acceleration.Y())));
    acceleration.Z(std::max(-5.0, std::min(5.0, acceleration.Z())));
    link_->AddForce(mass_ * (acceleration + ignition::math::Vector3d(0, 0, 9.81)));

    const auto rpy = pose.Rot().Euler();
    const double yaw_error = WrapAngle(target_yaw - rpy.Z());
    link_->AddTorque(ignition::math::Vector3d(
        -0.5 * rpy.X() - 0.12 * angular_velocity.X(),
        -0.5 * rpy.Y() - 0.12 * angular_velocity.Y(),
        0.6 * yaw_error - 0.15 * angular_velocity.Z()));

    if ((now - last_odom_time_).Double() < 0.01) return;
    last_odom_time_ = now;
    nav_msgs::Odometry odom;
    odom.header.stamp = ros::Time(now.sec, now.nsec);
    odom.header.frame_id = "world";
    odom.child_frame_id = "base_link";
    odom.pose.pose.position.x = pose.Pos().X();
    odom.pose.pose.position.y = pose.Pos().Y();
    odom.pose.pose.position.z = pose.Pos().Z();
    odom.pose.pose.orientation.x = pose.Rot().X();
    odom.pose.pose.orientation.y = pose.Rot().Y();
    odom.pose.pose.orientation.z = pose.Rot().Z();
    odom.pose.pose.orientation.w = pose.Rot().W();
    odom.twist.twist.linear.x = velocity.X();
    odom.twist.twist.linear.y = velocity.Y();
    odom.twist.twist.linear.z = velocity.Z();
    odom.twist.twist.angular.x = angular_velocity.X();
    odom.twist.twist.angular.y = angular_velocity.Y();
    odom.twist.twist.angular.z = angular_velocity.Z();
    odom_pub_.publish(odom);
  }

  physics::ModelPtr model_;
  physics::LinkPtr link_;
  event::ConnectionPtr update_connection_;
  std::unique_ptr<ros::NodeHandle> nh_;
  std::unique_ptr<ros::AsyncSpinner> spinner_;
  ros::Subscriber cmd_sub_;
  ros::Publisher odom_pub_;
  std::mutex command_mutex_;
  ignition::math::Vector3d target_position_, target_velocity_, target_acceleration_;
  double target_yaw_ = 0.0;
  double mass_ = 0.98;
  common::Time last_time_, last_odom_time_;
};

GZ_REGISTER_MODEL_PLUGIN(FuelGazeboController)
}  // namespace gazebo
