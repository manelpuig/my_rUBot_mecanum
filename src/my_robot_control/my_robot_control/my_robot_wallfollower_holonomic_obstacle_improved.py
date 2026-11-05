#!/usr/bin/env python3
"""Holonomic obstacle wall follower (A4) - completed from the student template."""

import math

import rclpy
from geometry_msgs.msg import Twist
from nav_msgs.msg import Odometry
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from rclpy.signals import SignalHandlerOptions
from sensor_msgs.msg import LaserScan
from tf_transformations import euler_from_quaternion


def clamp(value, low, high):
    """Limit value to the range"""
    return max(low, min(high, value))


class HolonomicObstacleWallFollower(Node):
    """LiDAR processing, state machine and control laws."""

    def __init__(self):
        super().__init__('holonomic_obstacle_wall_follower')

        # Desired distance between the robot and the right wall (m).
        self.follow_distance = float(
            self.declare_parameter('follow_distance', 0.35).value
        )
        # Maximum lateral distance used to classify a short obstacle (m).
        self.max_front_length = float(
            self.declare_parameter('max_front_length', 0.50).value
        )
        # Forward velocity (m/s).
        self.forward_speed = float(
            self.declare_parameter('forward_speed', 0.20).value
        )
        # Maximum lateral velocity (m/s).
        self.lateral_speed = float(
            self.declare_parameter('lateral_speed', 0.20).value
        )
        # Turn speed and maximum angular correction (rad/s).
        self.turn_speed = float(
            self.declare_parameter('turn_speed', 1.00).value
        )
        # Maximum LiDAR distance considered (m).
        self.detection_limit = float(
            self.declare_parameter('detection_limit', 1.20).value
        )
        # Proportional gain for lateral-distance correction.
        self.lateral_gain = float(
            self.declare_parameter('lateral_gain', 2.0).value
        )
        # Proportional gain for angular alignment.
        self.alignment_gain = float(
            self.declare_parameter('alignment_gain', 2.0).value
        )

        # each LiDAR region is also a state of the state machine
        self.RIGHT = 'RIGHT'
        self.FRONT = 'FRONT'
        self.FRONT_RIGHT = 'FRONT_RIGHT'
        self.BACK_RIGHT = 'BACK_RIGHT'

        self.diagonal_factor = 0.5
        # number of consecutive scans needed to confirm a region change
        self.region_confirmations = 3
        # number of nearest rays averaged per region
        self.robust_rays = 3

        self.state = self.RIGHT
        self.obstacle_is_long = False
        self.passing_short_obstacle = False
        self.command = Twist()
        self.odom_pose = None
        self.front_start_pose = None
        self.right_angle = None

        self.region_candidate = None
        self.region_candidate_count = 0
        self.stable_region = None

        # ROS communication
        self.create_subscription(
            LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data
        )
        self.create_subscription(Odometry, '/odom', self.odom_callback, 10)
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)
        self.timer = self.create_timer(0.05, self.publish_command)

        self.get_logger().info('Holonomic obstacle wall follower started.')

    def publish_command(self):
        self.publisher.publish(self.command)

    def odom_callback(self, msg):
        """Store planar pose (x, y, yaw) from odometry."""
        position = msg.pose.pose.position
        orientation = msg.pose.pose.orientation
        quaternion = [
            orientation.x,
            orientation.y,
            orientation.z,
            orientation.w,
        ]
        _, _, yaw = euler_from_quaternion(quaternion)
        self.odom_pose = (position.x, position.y, yaw)

    # ------------------------------------------------------------------
    # LiDAR processing
    # ------------------------------------------------------------------
    def region_measurements(self, scan):
        """Return robust distances and angles for the four LiDAR regions."""
        # TODO 1: lists of valid rays (distance, angle_deg) per region.
        regions = {
            self.FRONT: [],
            self.FRONT_RIGHT: [],
            self.RIGHT: [],
            self.BACK_RIGHT: [],
        }

        for i, distance in enumerate(scan.ranges):
            # Ignore invalid (inf / nan) and out-of-range measurements.
            if not math.isfinite(distance):
                continue
            if distance < scan.range_min or distance > scan.range_max:
                continue

            # Angle of ray i, normalised to [-pi, pi]
            angle = scan.angle_min + i * scan.angle_increment
            angle = math.atan2(math.sin(angle), math.cos(angle))  # [-pi, pi]
            angle_deg = math.degrees(angle)

            if -20.0 <= angle_deg <= 20.0:
                regions[self.FRONT].append((distance, angle_deg))
            elif -70.0 <= angle_deg < -20.0:
                regions[self.FRONT_RIGHT].append((distance, angle_deg))
            elif -110.0 <= angle_deg < -70.0:
                regions[self.RIGHT].append((distance, angle_deg))
            elif -160.0 <= angle_deg < -110.0:
                regions[self.BACK_RIGHT].append((distance, angle_deg))

        # TODO 2: mean distance and angle of the three nearest valid rays.
        measurements = {}
        for name, rays in regions.items():
            if not rays:
                measurements[name] = (math.inf, None)
                continue
            nearest = sorted(rays)[:self.robust_rays]
            mean_distance = sum(r[0] for r in nearest) / len(nearest)
            mean_angle = sum(r[1] for r in nearest) / len(nearest)
            measurements[name] = (mean_distance, mean_angle)

        self.right_angle = measurements[self.RIGHT][1]
        return measurements

    def closest_region(self, measurements):
        """Return the closest region inside detection_limit."""
        # TODO 3
        valid = {
            name: distance
            for name, (distance, _) in measurements.items()
            if distance < self.detection_limit
        }
        if not valid:
            return None
        return min(valid, key=valid.get)

    def confirmed_region(self, measurements):
        """Confirm a region change over several consecutive scans."""
        # TODO 4
        closest = self.closest_region(measurements)

        if closest == self.region_candidate:
            self.region_candidate_count += 1
        else:
            self.region_candidate = closest
            self.region_candidate_count = 1

        if (self.region_candidate_count >= self.region_confirmations
                and closest != self.stable_region):
            self.get_logger().info(
                f'Closest region: {self.stable_region} -> {closest}'
            )
            self.stable_region = closest

        return self.stable_region

    def lateral_progress(self):
        """Return travel along the robot's initial lateral axis."""
        # TODO 5
        if self.odom_pose is None or self.front_start_pose is None:
            return 0.0
        x, y, _ = self.odom_pose
        x0, y0, yaw0 = self.front_start_pose
        dx = x - x0
        dy = y - y0
        return abs(-math.sin(yaw0) * dx + math.cos(yaw0) * dy)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def change_state(self, new_state):
        if new_state != self.state:
            self.get_logger().info(f'STATE: {self.state} -> {new_state}')
            self.state = new_state

    def enter_front(self):
        """Start a new frontal-obstacle manoeuvre and save the entry pose."""
        self.front_start_pose = self.odom_pose
        self.obstacle_is_long = False
        self.passing_short_obstacle = False
        self.change_state(self.FRONT)

    def lateral_correction(self, measurements):
        """P control of the right distance. Too far -> negative vy (right)."""
        distance, _ = measurements[self.RIGHT]
        if distance >= self.detection_limit:
            return 0.0
        error = self.follow_distance - distance
        return clamp(self.lateral_gain * error,
                     -self.lateral_speed, self.lateral_speed)

    def angular_alignment(self, measurements):
        """P control moving the closest RIGHT angle towards -90 degrees."""
        distance, angle = measurements[self.RIGHT]
        if angle is None or distance >= self.detection_limit:
            return 0.0
        error = math.radians(angle + 90.0)
        return clamp(self.alignment_gain * error,
                     -self.turn_speed, self.turn_speed)

    # ------------------------------------------------------------------
    # State machine
    # ------------------------------------------------------------------
    def follow_right(self, measurements, closest, cmd):
        """Follow the wall using lateral and angular correction."""
        # TODO 6
        if closest == self.FRONT:
            self.enter_front()
            return self.follow_front(measurements, closest, cmd)

        if self.passing_short_obstacle and closest == self.BACK_RIGHT:
            self.change_state(self.BACK_RIGHT)
            return self.follow_back_right(measurements, closest, cmd)

        cmd.linear.x = self.forward_speed
        cmd.linear.y = self.lateral_correction(measurements)
        if self.passing_short_obstacle:
            # The closest point is the obstacle corner: never align with it.
            cmd.angular.z = 0.0
        else:
            cmd.angular.z = self.angular_alignment(measurements)

    def follow_front(self, measurements, closest, cmd):
        """Move laterally and classify the obstacle as short or long."""
        # TODO 7
        if self.front_start_pose is None:
            self.front_start_pose = self.odom_pose

        progress = self.lateral_progress()

        if progress >= self.max_front_length:
            # Long wall: it must become the new right wall.
            self.get_logger().info(
                f'Long wall detected (progress={progress:.2f} m)'
            )
            self.obstacle_is_long = True
            self.change_state(self.FRONT_RIGHT)
            return self.follow_front_right(measurements, closest, cmd)

        if closest != self.FRONT:
            # FRONT cleared before max_front_length: short obstacle.
            self.get_logger().info(
                f'Short obstacle detected (progress={progress:.2f} m)'
            )
            self.passing_short_obstacle = True
            self.change_state(self.FRONT_RIGHT)
            return self.follow_front_right(measurements, closest, cmd)

        cmd.linear.x = 0.0
        cmd.linear.y = self.lateral_speed
        cmd.angular.z = 0.0

    def follow_front_right(self, measurements, closest, cmd):
        """Move diagonally around the front-right side."""
        # TODO 8
        if self.obstacle_is_long:
            # Turn left until the long wall is on the right.
            if closest == self.RIGHT:
                self.obstacle_is_long = False
                self.front_start_pose = None
                self.change_state(self.RIGHT)
                return self.follow_right(measurements, closest, cmd)
            cmd.linear.x = 0.0
            cmd.linear.y = 0.0
            cmd.angular.z = self.turn_speed
            return

        # Short obstacle.
        if closest == self.FRONT:
            # Blocked again: keep the entry pose so progress accumulates.
            self.change_state(self.FRONT)
            return self.follow_front(measurements, closest, cmd)
        if closest == self.RIGHT:
            self.change_state(self.RIGHT)
            return self.follow_right(measurements, closest, cmd)
        if closest == self.BACK_RIGHT:
            self.change_state(self.BACK_RIGHT)
            return self.follow_back_right(measurements, closest, cmd)

        cmd.linear.x = self.forward_speed
        cmd.linear.y = self.diagonal_factor * self.lateral_speed
        cmd.angular.z = 0.0

    def follow_back_right(self, measurements, closest, cmd):
        """Complete the bypass and recover the right wall."""
        # TODO 9
        if closest == self.RIGHT:
            self.passing_short_obstacle = False   # alignment enabled again
            self.front_start_pose = None
            self.change_state(self.RIGHT)
            return self.follow_right(measurements, closest, cmd)

        if closest == self.FRONT:
            self.enter_front()
            return self.follow_front(measurements, closest, cmd)

        cmd.linear.x = self.forward_speed
        cmd.linear.y = -self.diagonal_factor * self.lateral_speed
        cmd.angular.z = 0.0

    def scan_callback(self, scan):
        """Read the LiDAR and calculate the next velocity command."""
        # TODO 10
        measurements = self.region_measurements(scan)
        closest = self.confirmed_region(measurements)
        cmd = Twist()

        handlers = {
            self.RIGHT: self.follow_right,
            self.FRONT: self.follow_front,
            self.FRONT_RIGHT: self.follow_front_right,
            self.BACK_RIGHT: self.follow_back_right,
        }
        handlers[self.state](measurements, closest, cmd)
        self.command = cmd

        right_distance, right_angle = measurements[self.RIGHT]
        angle_txt = f'{right_angle:.1f}' if right_angle is not None else '-'
        self.get_logger().info(
            f'[{self.state}] closest={closest} '
            f'right_d={right_distance:.2f} right_ang={angle_txt} '
            f'short={self.passing_short_obstacle} long={self.obstacle_is_long} '
            f'| vx={cmd.linear.x:.2f} vy={cmd.linear.y:.2f} '
            f'w={cmd.angular.z:.2f}',
            throttle_duration_sec=1.0,
        )

    def stop(self):
        """Publish a final zero command."""
        self.command = Twist()
        self.timer.cancel()
        try:
            self.publisher.publish(self.command)
        except Exception:
            pass


def main(args=None):
    rclpy.init(
        args=args,
        signal_handler_options=SignalHandlerOptions.NO,
    )
    node = HolonomicObstacleWallFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
