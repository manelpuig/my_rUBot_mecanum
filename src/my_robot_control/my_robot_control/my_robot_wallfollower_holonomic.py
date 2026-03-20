import math
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, qos_profile_sensor_data
from sensor_msgs.msg import LaserScan
from geometry_msgs.msg import Twist
from rclpy.qos import QoSProfile,QoSReliabilityPolicy,QoSHistoryPolicy,QoSDurabilityPolicy


class WallFollower(Node):
    def __init__(self):
        super().__init__('wall_follower_node')

        # Parameters
        self.declare_parameter('distance_limit', 0.5)    # desired distance to right wall
        self.declare_parameter('forward_speed', 0.20)    # linear speed
        self.declare_parameter('turn_speed', 0.40)       # angular speed
        self.declare_parameter('time_to_stop', 30.0)     # auto-stop
        self.declare_parameter('tolerance', 0.05)        # band around base_distance (RIGHT)
        self.declare_parameter('max_wall_distance', 1)

        self.base_distance = float(self.get_parameter('distance_limit').value)
        self.v_lin = float(self.get_parameter('forward_speed').value)
        self.v_ang = float(self.get_parameter('turn_speed').value)
        self.time_to_stop = float(self.get_parameter('time_to_stop').value)
        self.tol = float(self.get_parameter('tolerance').value)
        self.max_wall_distance = float(self.get_parameter('max_wall_distance').value)

        self.constant_ang = 0
        # Last commanded twist (will be published periodically)
        self.cmd = Twist()
        # ROS 2 entities
        scan_qos = QoSProfile(
            reliability=QoSReliabilityPolicy.BEST_EFFORT,
            history=QoSHistoryPolicy.KEEP_LAST,
            depth=5,
            durability=QoSDurabilityPolicy.VOLATILE
        )
        self.subscription = self.create_subscription(
            LaserScan,
            "/scan",
            self.laser_callback,
            scan_qos,
        )
        self.publisher = self.create_publisher(Twist, '/cmd_vel', 10)

        # Timers
        self.info_timer = self.create_timer(1.0, self.log_info)
        self.stop_timer = self.create_timer(0.05, self.stop_watchdog)

        # Periodic cmd_vel publisher at 10 Hz (0.1 s)
        self.cmd_timer = self.create_timer(0.1, self.cmd_publish_timer_cb)

        self._state_action = "Idle"
        self._last_action_logged = None
        self._shutting_down = False

        self.start_time_s = self.get_clock().now().nanoseconds * 1e-9

        self.get_logger().info(
            "WallFollower (RIGHT tol, BACK_RIGHT when closest) - differential drive."
        )

    #--------------------------------------------------------------------
    def stop_watchdog(self):
        """Stop the robot after time_to_stop seconds."""
        if self._shutting_down:
            return
        now = self.get_clock().now().nanoseconds * 1e-9
        if now - self.start_time_s >= self.time_to_stop:
            self.get_logger().info("Stopping due to timeout.")
            self.stop()

    #--------------------------------------------------------------------
    def stop(self):
        """Safe stop: set cmd to zero Twist, try to publish once, stop timers."""
        self._shutting_down = True

        # Set last command to zero
        self.cmd = Twist()

        # Try a final publish (publisher may still be valid even if shutdown started)
        try:
            self.publisher.publish(self.cmd)
        except Exception:
            # Context/publisher may already be invalid -> ignore
            pass

        # Cancel timers safely
        for t in [self.info_timer, self.stop_timer, self.cmd_timer]:
            try:
                t.cancel()
            except Exception:
                pass

    #--------------------------------------------------------------------
    def cmd_publish_timer_cb(self):
        """Periodic publisher: send the latest cmd_vel at 10 Hz."""
        if self._shutting_down:
            return

        try:
            self.publisher.publish(self.cmd)
        except Exception:
            # If the context or publisher is invalid, ignore
            pass

    #--------------------------------------------------------------------
    def laser_callback(self, scan):
        """Compute control action from LIDAR and update self.cmd."""
        if self._shutting_down:
            return

        angle_min = math.degrees(scan.angle_min)
        angle_inc = math.degrees(scan.angle_increment)

        min_front       = math.inf
        min_left        = math.inf    
        min_fr_right    = math.inf   
        min_right       = math.inf
        min_back_right  = math.inf   
        min_back        = math.inf   
        right_save_ang = 0
        front_save_ang=0
        # el twist.angular.z treballa amb radians: https://robotics.stackexchange.com/questions/94072/units-of-twist-angular-z
        self.K = 0.5 
        self.constant_ang = self.K*math.pi/180 # constant d'aprenentatge + factor conversio

        for i, d in enumerate(scan.ranges):
            if not math.isfinite(d):
                continue
            if d < scan.range_min or d > scan.range_max:
                continue

            ang = angle_min + i * angle_inc

            if  -20  <= ang <=  20:
                if min_front > d:
                    min_front = d
                    front_save_ang = ang
            elif 70  <  ang <= 110:
                min_left = min(min_left, d)
            elif -60  <= ang <  -20:
                min_fr_right = min(min_fr_right, d)
            elif -120 <= ang <  -60:
                if min_right > d:
                    min_right = d
                    right_save_ang = ang #calculem l'angle
                    
            elif -160 <= ang < -120:
                min_back_right = min(min_back_right, d)
            elif ang < -160 or ang > 160:
                min_back = min(min_back, d)
        
        # angle negatiu -> sentit horari -> s'apropa  a paret
        # angle positiu -> sentit antihorari -> s'allunya de la paret
        # -90 graus perquè el right està entre -70 i -110 graus. Per tant -90º   es la meitat
        angle_orig = right_save_ang
        right_save_ang =  right_save_ang - (-90) 
        right_save_ang = right_save_ang * self.constant_ang # convertim a radians
        

        front_save_ang =  front_save_ang - (-90) 
        front_save_ang= front_save_ang * self.constant_ang

        twist = Twist()
        action = ""

        #----------------------------------------------------------
        # RULE 1: FRONT obstacle → turn left
        #----------------------------------------------------------
        if min_front < self.base_distance:
            twist.linear.x = 0.0
            twist.linear.y = self.v_lin
            twist.angular.z = front_save_ang
            action = f"FRONT {min_front:.2f} m → SLIDE LEFT + turn LEFT {front_save_ang:.2f}"

        #----------------------------------------------------------
        # RULE 2: FRONT-RIGHT obstacle → slow + left
        #----------------------------------------------------------
        elif min_fr_right < self.base_distance and min_right > min_fr_right:
            twist.linear.x = self.v_lin*0.5
            twist.linear.y = self.v_lin*0.5
            twist.angular.z = 0.0
            action = f"FRONT-RIGHT {min_fr_right:.2f} m → SLIDE LEFT + stright"

        #----------------------------------------------------------
        # RULE 3: RIGHT visible → control with tolerance band (no vy)
        #----------------------------------------------------------
        elif math.isfinite(min_right) and min_right < self.base_distance:
            # error > 0 → too far; error < 0 → too close
            error = min_right - self.base_distance

            if abs(error) <= self.tol:
                # Inside band: go straight
                twist.linear.x = self.v_lin 
                twist.linear.y = 0.0
                twist.angular.z = right_save_ang
                action = (
                    f"RIGHT ~OK ({min_right:.2f} m, target {self.K}"
                    f"{self.base_distance:.2f}±{self.tol:.2f}) → STRAIGHT {angle_orig:.2f} º -> ang_vel {twist.angular.z:.2f} "
                )

            elif error < 0:
                # Too close to right wall → slow forward + stronger left turn
                #twist.linear.x = self.v_lin
                twist.linear.x = 0.5* self.v_lin 
                twist.linear.y =self.v_lin*0.5
                twist.angular.z =  right_save_ang #velocitat negativa
                action = (
                    f"RIGHT too CLOSE ({min_right:.2f} m < "
                    f"{self.base_distance:.2f}-{self.tol:.2f}) → {angle_orig:.2f} º {twist.angular.z:.2f}"
                    f"forward + strong LEFT turn {self.K}"
                )

            else:
                # Too far from right wall → slow forward + stronger right turn
                twist.linear.x = 0.5*self.v_lin
                twist.linear.y = -self.v_lin*0.5
                twist.angular.z = right_save_ang
                action = (
                    f"RIGHT too FAR ({min_right:.2f} m > "
                    f"{self.base_distance:.2f}+{self.tol:.2f}) → angle {angle_orig:.2f} º {twist.angular.z:.2f}"
                    f"forward + strong RIGHT turn {self.K}"
                )

        #----------------------------------------------------------
        # RULE 4: BACK-RIGHT → only if it is the most relevant wall
        #----------------------------------------------------------
        elif math.isfinite(min_back_right) and (
            not math.isfinite(min_right) or min_back_right <= min_right
        ):
            twist.linear.x = self.v_lin * 0.2
            twist.linear.y = -self.v_lin * 0.5
            twist.angular.z = 0.0
            action = (
                f"BACK-RIGHT {min_back_right:.2f} m → "
                f"Straight + STRONG RIGHT"
            )
        #----------------------------------------------------------
        # RULE 5: BACK → only if it is the most relevant wall
        #----------------------------------------------------------
        elif math.isfinite(min_back) and (
            not math.isfinite(min_right) or min_back <= min_right
        ):
            twist.linear.x = 0.0
            twist.linear.y = -self.v_lin * 0.5
            twist.angular.z = 0.0
            action = (
                f"BACK {min_back:.2f} m → "
                f"Straight + STRONG RIGHT"
            )
        
        else:
            twist.linear.x = self.v_lin 
            twist.linear.y = -self.v_lin
            twist.angular.z = 0.0
            action = (
                f"No wall detected {min_back_right:.2f} m → "
                f"Straight + SLIDE RIGHT"
            )
            
        # if nothing is visible, twist remains zero -> robot stops
        # Update last commanded twist (periodic timer will publish it)
        self.cmd = twist

        # Logging (only on change)
        if action != self._last_action_logged:
            self.get_logger().info(action if action else "No action (stopped).")
            self._last_action_logged = action

        self._state_action = action if action else "Stopped (no wall detected)"

    #--------------------------------------------------------------------
    def log_info(self):
        if not self._shutting_down:
            self.get_logger().info(self._state_action)

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
