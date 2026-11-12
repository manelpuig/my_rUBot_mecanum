#!/usr/bin/env python3
import time

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import String
from nav2_simple_commander.robot_navigator import BasicNavigator, TaskResult
from tf_transformations import quaternion_from_euler


class TrafficSignNavigation(Node):

    def __init__(self):
        super().__init__('traffic_sign_navigation')

        # Senyal 1 (igual que a l'A6 original)
        self.declare_parameter('initial_pose', [0.0, 0.0, 0.0])
        self.declare_parameter('inspection_pose', [0.5, -1.0, 1.57])
        self.declare_parameter('left_waypoint', [-0.8, 0.3, 1.57])
        self.declare_parameter('right_waypoint', [0.8, 0.3, 1.57])
        self.declare_parameter('final_pose', [0.0, 1.3, 1.57])
        self.declare_parameter('stop_duration', 3.0)

        # Robot real: anada i tornada llegint 2 senyals
        # (si two_signs es false, el node fa exactament el mateix que abans)
        self.declare_parameter('two_signs', False)
        self.declare_parameter('turn_pose', [0.0, 0.0, 0.0])
        self.declare_parameter('inspection_pose_2', [0.0, 0.0, 0.0])
        self.declare_parameter('left_waypoint_2', [0.0, 0.0, 0.0])
        self.declare_parameter('right_waypoint_2', [0.0, 0.0, 0.0])
        # temps que esperem al punt d'inspeccio abans d'acceptar la senyal
        # (aixi la camera ja esta quieta i mirant la senyal)
        self.declare_parameter('sign_settle_time', 0.0)

        self.initial_pose = self.get_parameter('initial_pose').value
        self.inspection_pose = self.get_parameter('inspection_pose').value
        self.left_waypoint = self.get_parameter('left_waypoint').value
        self.right_waypoint = self.get_parameter('right_waypoint').value
        self.final_pose = self.get_parameter('final_pose').value
        self.stop_duration = self.get_parameter('stop_duration').value

        self.two_signs = self.get_parameter('two_signs').value
        self.turn_pose = self.get_parameter('turn_pose').value
        self.inspection_pose_2 = self.get_parameter('inspection_pose_2').value
        self.left_waypoint_2 = self.get_parameter('left_waypoint_2').value
        self.right_waypoint_2 = self.get_parameter('right_waypoint_2').value
        self.sign_settle_time = self.get_parameter('sign_settle_time').value

        self.navigator = BasicNavigator()
        self.detected_sign = None
        self.accept_sign = False

        # TODO 1: Create a String subscriber for /traffic_sign.
        self.sign_subscriber = self.create_subscription(String,'/traffic_sign', self.sign_callback,10)
        #'/traffic_sign' és el nom del topic on es publica la senyal
        # self.sign_callback és la funció que s'executarà cada cop que arribi un missatge

    def sign_callback(self, msg):
        # TODO 2: While accept_sign is True, store the sign in lower case.
        if self.accept_sign:
            self.detected_sign = msg.data.strip().lower()
            self.get_logger().info(f'Traffic sign received: {self.detected_sign}')

    def create_pose(self, values):
        x, y, yaw = values
        qx, qy, qz, qw = quaternion_from_euler(0.0, 0.0, yaw)

        pose = PoseStamped()
        pose.header.frame_id = 'map'
        pose.header.stamp = self.get_clock().now().to_msg()
        pose.pose.position.x = float(x)
        pose.pose.position.y = float(y)
        pose.pose.orientation.x = qx
        pose.pose.orientation.y = qy
        pose.pose.orientation.z = qz
        pose.pose.orientation.w = qw
        return pose

    def go_to(self, values, name):
        self.get_logger().info(f'Going to {name}')
        self.navigator.goToPose(self.create_pose(values))

        while not self.navigator.isTaskComplete():
            rclpy.spin_once(self, timeout_sec=0.1)

        if self.navigator.getResult() != TaskResult.SUCCEEDED:
            self.get_logger().warn(f'{name} not reached (check that the pose is in free space)')

    def wait_for_sign(self):
        # Esperem una mica quiets perque la camera vegi be la senyal
        start = time.time()
        while time.time() - start < self.sign_settle_time:
            rclpy.spin_once(self, timeout_sec=0.1)

        self.detected_sign = None
        self.accept_sign = True
        self.get_logger().info('Waiting for a traffic sign on /traffic_sign ...')

        # TODO 3: Process callbacks until detected_sign is not None.
        while rclpy.ok() and self.detected_sign is None:
            rclpy.spin_once(self, timeout_sec=0.1)
        self.accept_sign = False
        return self.detected_sign

    def follow_sign(self, sign, left_wp, right_wp, next_pose, next_name, n):
        # TODO 4: Implement left, right, stop and unknown-sign behaviour.
        if sign == 'left':
            self.go_to(left_wp, f'left waypoint {n}')
        elif sign == 'right':
            self.go_to(right_wp, f'right waypoint {n}')
        elif sign == 'stop':
            self.get_logger().info(f'Stop sign: waiting {self.stop_duration} s')
            time.sleep(self.stop_duration)
        else:
            self.get_logger().warn(f'Unknown sign "{sign}". Staying at inspection pose {n}.')
            return False

        self.go_to(next_pose, next_name)
        return True

    def run(self):
        self.navigator.setInitialPose(self.create_pose(self.initial_pose))
        self.navigator.waitUntilNav2Active()

        # Senyal 1
        self.go_to(self.inspection_pose, 'inspection pose 1')
        sign = self.wait_for_sign()

        if not self.two_signs:
            # Comportament original de l'A6 (simulacio)
            self.follow_sign(sign, self.left_waypoint, self.right_waypoint,
                             self.final_pose, 'final pose', 1)
            return

        # Anada: senyal 1 -> punt de gir (al fons)
        if not self.follow_sign(sign, self.left_waypoint, self.right_waypoint,
                                self.turn_pose, 'turn pose', 1):
            return

        # Tornada: senyal 2 -> posicio final
        self.go_to(self.inspection_pose_2, 'inspection pose 2')
        sign = self.wait_for_sign()
        if self.follow_sign(sign, self.left_waypoint_2, self.right_waypoint_2,
                            self.final_pose, 'final pose', 2):
            self.get_logger().info('Route finished')


def main(args=None):
    rclpy.init(args=args)
    node = TrafficSignNavigation()

    try:
        node.run()
    finally:
        node.destroy_node()
        rclpy.shutdown()


if __name__ == '__main__':
    main()


# In part 4 of activity 6 we have proven that the modified files actually make the robot navigate as desired:
# The turn left command causes the robot to take the left path towards the final position.
# The turn right command causes the robot to take the right path towards the final position.
# The stop command causes the robot to wait a few seconds and take the shortest path towards the final positions, which happens to be the same as the left path.

# Real robot (lab): with two_signs: true in traffic_sign_navigation_real.yaml the robot reads
# sign 1 on the way out, turns at turn_pose and reads sign 2 on the way back to the initial pose.





