# Setup ROS2 Jazzy Container environment

- Clone the jazzy branch on PC host with VScode:
    ````bash
    git clone -b jazzy --single-branch https://github.com/manelpuig/my_rUBot_mecanum.git
    cd my_rUBot_mecanum
    git branch
    git status
    ````
- Open a terminal in the `ros2-jazzy-biorobub` folder
- Verify the `docker-compose_xlaunch.yaml` and `cyclonedds_pc.xml` files configuration in function of Home-simulation (Default) / Lab-rUBot use 
- and run:
    ````bash
    docker compose -f docker-compose_xlaunch.yaml up
    ````
- In VScode `attach` to the `pc_jazzy` container

- Open `.bashrc` file inside the container and verify it contains:
    ````bash
    source /opt/ros/jazzy/setup.bash
    source /root/my_rUBot_mecanum/install/setup.bash
    cd /root/my_rUBot_mecanum
    ````

- To stop the container:
    ````bash
    docker compose -f docker-compose_xlaunch.yaml down
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