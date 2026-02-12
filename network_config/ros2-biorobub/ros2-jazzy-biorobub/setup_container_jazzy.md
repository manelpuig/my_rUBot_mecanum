# Setup ROS2 Jazzy Container environment

- Clone the jazzy branch on PC host with VScode:
    ````bash
    git clone -b jazzy --single-branch https://github.com/manelpuig/my_rUBot_mecanum.git
    cd my_rUBot_mecanum
    git branch
    git status
    ````
- Open a terminal in the `ros2-jazzy-biorobub` folder and run:
    ````bash
    docker compose -f docker-compose.win.yaml up -d
    docker exec -it pc_jazzy bash
    code .                     # open VSCode inside the container
    ros2 topic list
    ````
- Open `.bashrc` file inside the container and verify it contains:
    ````bash
    source /opt/ros/jazzy/setup.bash
    source /root/my_rUBot_mecanum/install/setup.bash
    export RMW_IMPLEMENTATION=rmw_cyclonedds_cpp
    export ROS_DOMAIN_ID=5 # robot number
    export ROS_AUTOMATIC_DISCOVERY_RANGE=LOCALHOST # Mode simulation
    #export ROS_AUTOMATIC_DISCOVERY_RANGE=OFF # Mode robot
    #export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET # Mode Local Development
    #export ROS_STATIC_PEERS="192.168.1.45" # Mode robot with robot IP
    #export CYCLONEDDS_URI=file:///config/cyclonedds_pc.xml # Mode Local Development/robot
    unset CYCLONEDDS_URI # Mode simulation
    unset ROS_STATIC_PEERS # Mode simulation
    ````

- To stop the container:
    ````bash
    docker compose -f docker-compose.win.yaml down
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