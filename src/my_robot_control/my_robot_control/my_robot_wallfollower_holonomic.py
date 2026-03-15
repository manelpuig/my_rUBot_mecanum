from dbm import error
import logging
import math
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile,QoSReliabilityPolicy,QoSHistoryPolicy,QoSDurabilityPolicy


class WallFollower(Node):
    def __init__(self):
        super().__init__('wall_follower_node')

        self.declare_parameter('distance_limit', 0.2)   # desired distance to right wall
        self.declare_parameter('forward_speed',  0.1)  # linear x speed
        self.declare_parameter('lateral_speed',  0.1)  # linear y (holonomic) speed
        self.declare_parameter('turn_speed',     0.4)  # angular speed (front avoidance)
        self.declare_parameter('time_to_stop',   30.0)  # auto-stop
        self.declare_parameter('tolerance',      0.03)  # dead-band around target distance
        self.declare_parameter('limit_wall',    0.15)   # max valid distance to consider a wall 

        self.base_distance = float(self.get_parameter('distance_limit').value)
        self.v_lin  = float(self.get_parameter('forward_speed').value)
        self.v_lat  = float(self.get_parameter('lateral_speed').value)
        self.v_ang  = float(self.get_parameter('turn_speed').value)
        self.time_to_stop = float(self.get_parameter('time_to_stop').value)
        self.tol    = float(self.get_parameter('tolerance').value)
        self.limit_wall = float(self.get_parameter('limit_wall').value)
        self.cmd = Twist()
        self._state_action      = "Idle"
        self._last_action_logged = None
        self._shutting_down     = False
        self.start_time_s       = self.get_clock().now().nanoseconds * 1e-9

        scan_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        self.subscription = self.create_subscription(
            LaserScan,
            "/scan" ,
            self.laser_callback,
            scan_qos,
        )
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
        min_dist = np.min(valid)
        min_idx  = np.argmin(valid)
        
        n  = len(valid)
        am = scan.angle_min
        ai = scan.angle_increment
        sm = lambda lo, hi: self._sector_min(valid, lo, hi, am, ai, n)
        
        min_front      = sm(-20,   20)
        min_fr_right   = sm(-70,  -20)
        min_right      = sm(-110, -70)
        min_back_right = sm(-160, -110)
        min_fr_left    = sm(20, 70)
        min_left = sm(70,110)
        min_back_left = sm(110,160)
        min_back = min(min_back_left, min_back_right)  # ja no infinit
        min_distance = min(min_front, min_fr_right, min_right, min_back_right, min_fr_left)

        twist  = Twist()
        action = ""
        reaction = self.base_distance + self.tol

        # ── RULE 0: LEFT & RIGHT  GO BACK ──
        if min_back < self.base_distance and (
            math.isfinite(min_fr_left) and min_fr_left < self.base_distance and math.isfinite(min_fr_right) and min_fr_right < self.base_distance
            ):
            if min_back < self.limit_wall:
                #girem si anem a xocar de cul
                twist.linear.x = 0.0
                twist.linear.y = 0.0
                twist.angular.z = -self.v_ang
                action = f"LEFT {min_fr_left:.2f} m & RIGHT {min_fr_right:.2f} m  BACK {min_back:.2f} m → TURN RIGHT"
            else:
                #anem endarrere si tenim espai
                twist.linear.x = -0.3*self.v_lin
                twist.linear.y = 0.0
                twist.angular.z = 0.0                
                action = f"LEFT {min_fr_left:.2f} m & RIGHT {min_fr_right:.2f} m → BACKWARD"

        # ── RULE 1: FRONT left → Avoid front left obstacle ──
        elif min_distance == min_fr_left:
            
            if min_front < self.base_distance and min_fr_left < self.base_distance:
                # demasiado cerca
                twist.linear.x = 0.0
                twist.linear.y = 0.0
                twist.angular.z = self.v_ang * 2.0
                action = f"FRONT-LEFT {min_fr_left:.2f} m → turn LEFT"
            else:
                # demasiado lejos
                twist.linear.x = self.v_lin
                twist.linear.y = -self.v_lin
                twist.angular.z = 0.0
                action = f"FRONT-LEFT too far {min_fr_left:.2f} m → STRAIGHT + SLIDE RIGHT"
        
        # ── RULE 2: FRONT obstacle → turn left (priority avoidance) ──
        elif min_distance == min_front:
            if min_front < self.limit_wall:
                # Massa aprop de la paret reculem
                twist.linear.x = -self.v_lin
                if math.isfinite(min_left) and min_left > self.limit_wall:
                    # no xoquem amb paret esquerra
                    twist.linear.y = self.v_lin
                else:
                    # no xoquem amb paret dreta
                    twist.linear.y = -self.v_lin

                twist.angular.z = 0.0
                action = f"FRONT {min_front:.2f} m → BACKWARD RIGHT {min_right:.2f} m"

            elif min_front < self.base_distance:
                # girem per posar-nos paral·lels a la paret
                twist.linear.x = 0.0
                twist.linear.y = 0.0
                twist.angular.z = self.v_ang * 2.0
                action = f"FRONT {min_front:.2f} m → turn LEFT"

            else:
                # Busquem la paret detectada al front per acostar-nos-hi
                twist.linear.x = self.v_lin
                twist.linear.y = -self.v_lat
                twist.angular.z = 0.0
                action = f"FRONT {min_front:.2f} m → STRAIGHT {min_right:.2f} m"

        # ── RULE 3: FRONT-RIGHT obstacle → turn left ──
        elif min_distance == min_fr_right:
            if min_front < self.base_distance and min_fr_right < self.limit_wall:
                twist.linear.x = -self.v_lin
                twist.linear.y = self.v_lat
                twist.angular.z = 0.0
                action = f"FRONT-RIGHT too far {min_fr_right:.2f} m → BACKWARD + SLIDE LEFT"
            elif min_fr_right < self.base_distance:
                # demasiado cerca
                twist.angular.z = self.v_ang * 2.0
                action = f"FRONT-RIGHT {min_fr_right:.2f} m → turn LEFT"

        elif min_distance == min_right:
            # ── RULE 4: RIGHT visible → holonomic lateral correction ──
            if math.isfinite(min_right):
                error = min_right - self.base_distance   # >0 too far, <0 too close
                scale = min(2.0, abs(error) / self.tol)
                if abs(error) <= self.tol:
                    twist.linear.x = self.v_lin
                    twist.linear.y = -self.v_lat * scale * 1.5
                    twist.angular.z = 0.0
                    action = f"RIGHT OK ({min_right:.2f} m) → STRAIGHT"

                elif error < 0:
                    # Too close → slide LEFT (positive y) while moving forward
                    twist.linear.x = self.v_lin
                    twist.linear.y = self.v_lat * scale
                    twist.angular.z = self.v_ang
                    action = f"RIGHT CLOSE ({min_right:.2f} m) → forward + slide LEFT"

                else:
                    # Too far → slide RIGHT (negative y) while moving forward
                    twist.linear.x = self.v_lin
                    twist.linear.y = -self.v_lat * scale
                    twist.angular.z = -4.0*self.v_ang
                    action = f"RIGHT FAR ({min_right:.2f} m) → forward + slide RIGHT"
        
        # ── RULE 5: BACK-RIGHT → forward + slide right to reacquire wall ──
        elif math.isfinite(min_back_right):
            #twist.linear.x = self.v_lin
            twist.linear.x=0.0
            twist.linear.y = -self.v_lat
            twist.angular.z = -4.0*self.v_ang
            action = f"BACK-RIGHT {min_back_right:.2f} m → slide RIGHT + turn slightly RIGHT"

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
