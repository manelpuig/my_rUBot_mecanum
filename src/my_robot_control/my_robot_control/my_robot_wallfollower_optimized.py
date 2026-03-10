import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist


class WallFollower(Node):
    def __init__(self):
        super().__init__('wall_follower_node')

        self.declare_parameter('distance_limit', 0.5)   # desired distance to right wall
        self.declare_parameter('forward_speed',  0.20)  # linear x speed
        self.declare_parameter('lateral_speed',  0.20)  # linear y (holonomic) speed
        self.declare_parameter('turn_speed',     0.40)  # angular speed (front avoidance)
        self.declare_parameter('time_to_stop',   30.0)  # auto-stop
        self.declare_parameter('tolerance',      0.05)  # dead-band around target distance

        self.base_distance = float(self.get_parameter('distance_limit').value)
        self.v_lin  = float(self.get_parameter('forward_speed').value)
        self.v_lat  = float(self.get_parameter('lateral_speed').value)
        self.v_ang  = float(self.get_parameter('turn_speed').value)
        self.time_to_stop = float(self.get_parameter('time_to_stop').value)
        self.tol    = float(self.get_parameter('tolerance').value)

        self.cmd = Twist()
        self._state_action      = "Idle"
        self._last_action_logged = None
        self._shutting_down     = False
        self.start_time_s       = self.get_clock().now().nanoseconds * 1e-9

        self.create_subscription(LaserScan, '/scan', self.laser_callback, qos_profile_sensor_data)
        self.publisher  = self.create_publisher(Twist, '/cmd_vel', 10)
        self.cmd_timer  = self.create_timer(0.1,  self.cmd_publish_timer_cb)
        self.stop_timer = self.create_timer(0.05, self.stop_watchdog)

        self.get_logger().info(
            f"WallFollower OPTIMIZED | target={self.base_distance} m tol=±{self.tol} | "
            f"fwd={self.v_lin} lat={self.v_lat} ang={self.v_ang}"
        )

    # ------------------------------------------------------------------
    def _sector_min(self, valid: np.ndarray, lo_deg: float, hi_deg: float,
                    angle_min_rad: float, angle_inc: float, n: int) -> float:
        """Min valid range within an angular sector using direct index slicing."""
        i0 = max(0,     math.ceil( (math.radians(lo_deg) - angle_min_rad) / angle_inc))
        i1 = min(n - 1, math.floor((math.radians(hi_deg) - angle_min_rad) / angle_inc))
        if i0 > i1:
            return float('inf')
        return float(valid[i0:i1 + 1].min())

    # ------------------------------------------------------------------
    def stop_watchdog(self):
        if self._shutting_down:
            return
        if self.get_clock().now().nanoseconds * 1e-9 - self.start_time_s >= self.time_to_stop:
            self.get_logger().info("Timeout — stopping.")
            self.stop()

    def stop(self):
        self._shutting_down = True
        self.cmd = Twist()
        try:
            self.publisher.publish(self.cmd)
        except Exception:
            pass
        for t in [self.cmd_timer, self.stop_timer]:
            try:
                t.cancel()
            except Exception:
                pass

    def cmd_publish_timer_cb(self):
        if not self._shutting_down:
            try:
                self.publisher.publish(self.cmd)
            except Exception:
                pass

    # ------------------------------------------------------------------
    def laser_callback(self, scan: LaserScan):
        if self._shutting_down:
            return

        # Build a masked array: invalid readings replaced with inf (no loops)
        ranges = np.asarray(scan.ranges, dtype=float)
        valid  = np.where(
            np.isfinite(ranges) & (ranges >= scan.range_min) & (ranges <= scan.range_max),
            ranges, np.inf
        )
        n  = len(valid)
        am = scan.angle_min
        ai = scan.angle_increment
        sm = lambda lo, hi: self._sector_min(valid, lo, hi, am, ai, n)

        min_front      = sm(-20,   20)
        min_fr_right   = sm(-70,  -20)
        min_right      = sm(-110, -70)
        min_back_right = sm(-160, -110)

        twist  = Twist()
        action = ""

        # ── RULE 1: FRONT obstacle → turn left (priority avoidance) ──
        if min_front < self.base_distance:
            twist.angular.z = self.v_ang * 2.0
            action = f"FRONT {min_front:.2f} m → turn LEFT"

        # ── RULE 2: FRONT-RIGHT obstacle → turn left ──
        elif min_fr_right < self.base_distance:
            twist.angular.z = self.v_ang * 2.0
            action = f"FRONT-RIGHT {min_fr_right:.2f} m → turn LEFT"

        # ── RULE 3: RIGHT visible → holonomic lateral correction ──
        elif math.isfinite(min_right):
            error = min_right - self.base_distance   # >0 too far, <0 too close

            if abs(error) <= self.tol:
                twist.linear.x = self.v_lin
                action = f"RIGHT OK ({min_right:.2f} m) → STRAIGHT"

            elif error < 0:
                # Too close → slide LEFT (positive y) while moving forward
                scale = min(2.0, abs(error) / self.tol)
                twist.linear.x = self.v_lin
                twist.linear.y = self.v_lat * scale
                action = f"RIGHT CLOSE ({min_right:.2f} m) → forward + slide LEFT"

            else:
                # Too far → slide RIGHT (negative y) while moving forward
                scale = min(2.0, abs(error) / self.tol)
                twist.linear.x = self.v_lin
                twist.linear.y = -self.v_lat * scale
                action = f"RIGHT FAR ({min_right:.2f} m) → forward + slide RIGHT"

        # ── RULE 4: BACK-RIGHT → forward + slide right to reacquire wall ──
        elif math.isfinite(min_back_right):
            twist.linear.x = self.v_lin
            twist.linear.y = -self.v_lat
            action = f"BACK-RIGHT {min_back_right:.2f} m → forward + slide RIGHT"

        # ── No wall detected → go straight ──
        else:
            twist.linear.x = self.v_lin
            action = "No wall → STRAIGHT"

        self.cmd = twist

        # Log only on state change
        if action != self._last_action_logged:
            self.get_logger().info(action)
            self._last_action_logged = action
        self._state_action = action


def main(args=None):
    rclpy.init(args=args)
    node = WallFollower()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        node.stop()
    finally:
        try:
            node.destroy_node()
        except Exception:
            pass
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
