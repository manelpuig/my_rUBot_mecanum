#!/bin/bash
set -e

# Source ROS 2 Humble
source /opt/ros/humble/setup.bash

# Source local workspace inside the container (if it exists)
if [ -f /root/pc_ws/install/setup.bash ]; then
  source /root/pc_ws/install/setup.bash
fi

exec "$@"
