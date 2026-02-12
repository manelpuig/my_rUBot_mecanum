#!/bin/bash
set -e

# Source ROS 2 Jazzy
source /opt/ros/jazzy/setup.bash

# Source workspace if present
if [ -f /root/my_rUBot_mecanum/install/setup.bash ]; then
  source /root/my_rUBot_mecanum/install/setup.bash
fi

# DDS / ROS 2 networking (clear & explicit)
export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
export ROS_LOCALHOST_ONLY=0

# Teaching banner
echo "=============================================="
echo " ROS 2 Jazzy - Docker PC"
echo "----------------------------------------------"
echo " ROS_DOMAIN_ID                 = ${ROS_DOMAIN_ID:-<unset>}"
echo " ROS_AUTOMATIC_DISCOVERY_RANGE = ${ROS_AUTOMATIC_DISCOVERY_RANGE:-<unset>}"
echo " ROS_STATIC_PEERS              = ${ROS_STATIC_PEERS:-<unset>}"
echo " CYCLONEDDS_URI                = ${CYCLONEDDS_URI:-<unset>}"
echo "=============================================="

exec "$@"