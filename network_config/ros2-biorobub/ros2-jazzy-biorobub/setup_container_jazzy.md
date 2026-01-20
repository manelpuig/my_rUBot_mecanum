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
    # --------------------------------------------------
    # ROS 2 Jazzy – base environment
    # --------------------------------------------------
    source /opt/ros/jazzy/setup.bash

    # --------------------------------------------------
    # RMW / DDS (CycloneDDS recommended)
    # --------------------------------------------------
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp

    # --------------------------------------------------
    # ROS Domain (default for local dev)
    # --------------------------------------------------
    export ROS_DOMAIN_ID=0

    # --------------------------------------------------
    # Discovery behavior
    # --------------------------------------------------
    # Default: local development / simulation
    export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET #LOCALHOST

    # --------------------------------------------------
    # Networked robot (ENABLE ONLY WHEN NEEDED)
    # --------------------------------------------------
    # export ROS_AUTOMATIC_DISCOVERY_RANGE=OFF
    # export ROS_STATIC_PEERS="192.168.1.50"
    # export CYCLONEDDS_URI=file:///config/cyclonedds_pc.xml

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

## Migration sequence

- On PC-win
````shell
git clone https://github.com/manelpuig/my_rUBot_mecanum.git
cd my_rUBot_mecanum
git checkout jazzy
git status
git pull
...
git add .
git commit -m "Change"
git push origin jazzy
````
- On ROS2 Jazzy container:
````shell
cd /root
git clone https://github.com/manelpuig/my_rUBot_mecanum.git
cd my_rUBot_mecanum
git checkout jazzy
git status
git pull
````
- To verify the changes:
````shell
source /opt/ros/jazzy/setup.bash
rosdep update
rosdep install --from-paths src --ignore-src -r -y --rosdistro jazzy
````
- Build a single package
````shell
colcon build --packages-select <package_name> --symlink-install
source install/setup.bash
````