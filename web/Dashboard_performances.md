# rUBot Web Dashboard

## Main features

The dashboard lets you control and monitor one rUBot from a web browser.

- Connects to ROS 2 through Rosbridge.
- Shows the robot camera.
- Controls forward and backward speed (`Vx`) up to `+/- 0.2 m/s`.
- Controls lateral speed (`Vy`) up to `+/- 0.3 m/s`.
- Controls angular speed from `-45 deg/s` to `+45 deg/s`.
- Returns the angular slider to zero when it is released.
- Shows the robot position, orientation, and velocity direction.
- Shows the current LiDAR scan in yellow.
- Builds a simple local occupancy map from repeated LiDAR scans.
- Shows confirmed walls and obstacles in black.
- Removes old black obstacles when later LiDAR rays see free space there.
- Provides a **Reset map** button to clear the learned occupancy map.

## Map scale

The map uses fixed world limits. Resizing the browser does not change its physical scale.

- X range: `-1.5 m` to `+1.5 m`.
- Y range: `-1.5 m` to `+1.5 m`.
- Each axis has 10 equal intervals.
- Every interval represents `0.30 m` in the real world.
- Red vertical axis: X.
- Green horizontal axis: Y.
- Map resolution: `0.01 m` per occupancy cell.

The map is local to the dashboard and starts at the robot position when the page connects. It depends on wheel odometry. Long runs or wheel slip can make walls look thicker or displaced. For precise mapping, use a ROS 2 SLAM package such as `slam_toolbox`.

## Open the dashboard on a mobile phone

1. Connect the phone and the rUBot to the same Wi-Fi network.
2. Find the robot IP address.
3. Open Chrome, Safari, Firefox, or another modern browser on the phone.
4. Enter this address:

   ```text
   http://ROBOT_IP:8000/
   ```

   Example:

   ```text
   http://192.168.1.14:8000/
   ```

5. Select the robot number and press **Connect**.

Landscape mode gives more space for the camera, joystick, and map. If an old dashboard version appears, refresh the page or clear the browser cache.

## Required robot services

The robot must run:

- the robot bringup;
- Rosbridge WebSocket on port `9090`;
- the web server on port `8000`.

The web server serves this file by default:

```text
/home/ubuntu/ROS2_rUBot_mecanum_ws/web/index.html
```

The dashboard uses these ROS topics:

- `/cmd_vel`
- `/odom`
- `/scan`
- `/image_raw/compressed`

## Map behaviour

One LiDAR hit is not immediately accepted as a wall. Repeated hits increase the confidence of a map cell. When the confidence passes a threshold, the cell becomes black.

LiDAR rays also mark visible space as free. If an old obstacle disappears, later free-space observations reduce its confidence until the black point disappears. This avoids keeping temporary obstacles forever.

The occupancy map is stored only in browser memory. It is cleared when the page is reloaded or when **Reset map** is pressed.
