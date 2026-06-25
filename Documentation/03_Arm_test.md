# Testing `send_smooth_joint_target_node.py`

## Objective

The purpose of this test is to verify the complete motion chain:

```text
send_smooth_joint_target_node
            ↓
      JointTrajectory
            ↓
serial_trajectory_bridge_node
            ↓
        Arduino ESP32
            ↓
          SG90 Servos
```

The node generates a smooth trajectory consisting of multiple intermediate points between an initial and a target joint configuration.

The `serial_trajectory_bridge_node` receives the trajectory and sends the interpolated positions to the Arduino, resulting in smoother servo motion.

---

# 1. Build the package

```bash
cd ~/my_rUBot_mecanum

colcon build --packages-select my_arm_driver

source install/setup.bash
```

---

# 2. Start the driver node

Open Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Expected output:

```text
Opened serial port /dev/ttyUSB0
Subscribed to /arm_controller/joint_trajectory
```

---

# 3. Verify trajectory topic

Open Terminal 2:

```bash
ros2 topic list
```

You should see:

```text
/arm_controller/joint_trajectory
/joint_states
```

---

# 4. Test a single joint

Move Joint 2 from 0° to +30° in 5 seconds.

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
-p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
-p target_joints_deg:="[0.0,30.0,0.0,0.0,0.0,0.0]" \
-p duration:=5.0 \
-p steps:=50
```

Expected behavior:

* Only Joint 2 moves.
* Motion lasts approximately 5 seconds.
* Motion appears smoother than a direct jump.

---

# 5. Test two joints simultaneously

Move Joint 2 and Joint 3 together.

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
-p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
-p target_joints_deg:="[0.0,45.0,-30.0,0.0,0.0,0.0]" \
-p duration:=5.0 \
-p steps:=50
```

Expected behavior:

* Joint 2 moves from 0° to +45°.
* Joint 3 moves from 0° to -30°.
* Both joints start and finish at the same time.

---

# 6. Test all joints

Move all joints simultaneously.

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
-p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
-p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
-p duration:=6.0 \
-p steps:=60
```

Expected behavior:

* All joints move simultaneously.
* Total motion duration ≈ 6 seconds.
* Motion is continuous and smooth.

---

# 7. Slower movement

Increase the duration.

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
-p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
-p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
-p duration:=10.0 \
-p steps:=100
```

Expected behavior:

* Same final pose.
* Motion duration ≈ 10 seconds.
* Even smoother movement.

---

# 8. Return to home position

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
-p start_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
-p target_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
-p duration:=6.0 \
-p steps:=60
```

Expected behavior:

* Arm returns smoothly to the home position.

---

# 9. Monitor the generated trajectory

Open another terminal:

```bash
ros2 topic echo /arm_controller/joint_trajectory
```

The published message should contain:

```text
joint_names:
- arm_joint1
- arm_joint2
...
points:
- positions: [...]
  time_from_start: ...
- positions: [...]
  time_from_start: ...
...
```

The number of points should equal:

```text
steps + 1
```

For example:

```text
steps = 50
```

generates:

```text
51 trajectory points
```

---

# 10. Monitor joint states

```bash
ros2 topic echo /joint_states
```

Verify that the driver publishes the current joint positions while the arm is moving.

---

# Notes

The SG90 servos do not provide direct velocity control.

Smooth motion is achieved by:

1. Dividing the motion into many small increments.
2. Sending all trajectory points through a `JointTrajectory`.
3. Executing the trajectory over the specified duration.

Increasing:

```text
steps
```

and/or

```text
duration
```

generally produces smoother motion.
