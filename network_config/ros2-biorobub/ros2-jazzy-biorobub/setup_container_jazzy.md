# Setup ROS2 Jazzy Container environment

- Open a terminal in the `ros2-jazzy-biorobub` folder and run:
    ````bash
    docker compose -f docker-compose.win.yaml up -d
    docker exec -it pc_jazzy bash
    code .                     # open VSCode inside the container
    ros2 topic list
    ````
- Open `.bashrc` file inside the container and verify it contains:
    ````bash
    source /opt/ros/humble/setup.bash
    source /usr/share/colcon_argcomplete/hook/colcon-argcomplete.bash
    source ~/Desktop/ROS2_rUBot_mecanum_ws/install/setup.bash
    cd ~/Desktop/ROS2_rUBot_mecanum_ws
    export GAZEBO_MODEL_PATH=~/Desktop/ROS2_rUBot_mecanum_ws/src/my_robot_bringup/models:$GAZEBO_MODEL_PATH
    export QT_QPA_PLATFORM=xcb           # Best for RVIZ2
    export ROS_DOMAIN_ID=1               # group/domain ID
    export ROS_LOCALHOST_ONLY=0          # allow communication with other machines
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export CYCLONEDDS_URI=file:///home/student/Desktop/ROS2_rUBot_mecanum_ws/network_config/cyclonedds_pc.xml
    ````

- To stop the container:
    ````bash
    docker-compose down
    ````
- To see the Images and Containers:
    ````bash
    docker ps -a               # containers
    docker images              # images
    ````

You are ready to work with ROS2 Humble on Docker!