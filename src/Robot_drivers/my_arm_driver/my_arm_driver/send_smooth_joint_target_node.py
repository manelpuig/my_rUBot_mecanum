#!/usr/bin/env python3

import math
import rclpy
from rclpy.node import Node
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint


class SendSmoothJointTargetNode(Node):
    def __init__(self):
        super().__init__("send_smooth_joint_target_node")

        self.declare_parameter("topic_name", "/arm_controller/joint_trajectory")
        self.declare_parameter(
            "joint_names",
            ["arm_joint1", "arm_joint2", "arm_joint3", "arm_joint4", "arm_joint5", "arm_joint6"],
        )

        # Start and target joint positions in degrees
        self.declare_parameter("start_joints_deg", [0.0, 0.0, 0.0, 0.0, 0.0, 0.0])
        self.declare_parameter("target_joints_deg", [0.0, 30.0, -30.0, 0.0, 0.0, 0.0])

        # Total movement duration
        self.declare_parameter("duration", 5.0)

        # Number of interpolation steps
        self.declare_parameter("steps", 50)

        topic_name = self.get_parameter("topic_name").value
        self.publisher = self.create_publisher(JointTrajectory, topic_name, 10)

        self.timer = self.create_timer(1.0, self.publish_trajectory)
        self.has_published = False

        self.get_logger().info(f"Smooth joint target node ready. Topic: {topic_name}")

    def publish_trajectory(self):
        if self.has_published:
            return

        joint_names = list(self.get_parameter("joint_names").value)
        start_joints_deg = list(self.get_parameter("start_joints_deg").value)
        target_joints_deg = list(self.get_parameter("target_joints_deg").value)
        duration = float(self.get_parameter("duration").value)
        steps = int(self.get_parameter("steps").value)

        n = len(joint_names)

        if len(start_joints_deg) != n or len(target_joints_deg) != n:
            self.get_logger().error(
                "start_joints_deg and target_joints_deg must have the same length as joint_names"
            )
            return

        if steps < 1:
            self.get_logger().error("steps must be >= 1")
            return

        if duration <= 0.0:
            self.get_logger().error("duration must be > 0")
            return

        trajectory = JointTrajectory()
        trajectory.joint_names = joint_names

        for k in range(steps + 1):
            alpha = k / steps
            t = alpha * duration

            point = JointTrajectoryPoint()

            joints_deg = [
                start_joints_deg[i] + alpha * (target_joints_deg[i] - start_joints_deg[i])
                for i in range(n)
            ]

            point.positions = [math.radians(angle_deg) for angle_deg in joints_deg]
            point.time_from_start.sec = int(t)
            point.time_from_start.nanosec = int((t - int(t)) * 1e9)

            trajectory.points.append(point)

        self.publisher.publish(trajectory)

        self.get_logger().info(f"Published smooth trajectory with {steps + 1} points")
        self.get_logger().info(f"Start joints [deg]: {start_joints_deg}")
        self.get_logger().info(f"Target joints [deg]: {target_joints_deg}")
        self.get_logger().info(f"Duration: {duration:.2f} s")

        self.has_published = True


def main(args=None):
    rclpy.init(args=args)
    node = SendSmoothJointTargetNode()

    try:
        rclpy.spin(node)
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == "__main__":
    main()