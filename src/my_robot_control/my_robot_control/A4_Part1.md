# **PART 1: Differential & holonomic models performance analysis**
For each node, record:

- whether it maintains the desired distance;
- how it reacts to a frontal wall;
- whether the trajectory oscillates;
- whether it stops or loses the wall;
- which Twist components it uses;
- one strength and two limitations.

### **1. DIFFERENTIAL MODEL**

- YES, it maintains the desired distance (0.35 m). This is in part thanks to the frequency at which the robot receives info from the laser. If there was a longer spacing between acquisitions, the distance could be surpassed between acquisitions.
- YES, it reacts correctly to a frontal wall, by turning around itself and following it again
- YES, the trajectory seems to oscillate a little bit. We conclude this because the angular velocity (angular, z) changes it sign in an oscillatory way.
- YES, the robot stops running when the nearest wall is too far away and cannot be detected. When it loses the wall, it stops and due to time out, the simualtion is exited.
- The twist components it uses are (the components that are not 0 when asking the terminal to print the cmd_vel topic): 
    - The forward linear velocity (linear, x)
    - The angular velocity alnog the z axis (angular, z)

Basically this is telling us that the robot is not moving laterally or upwards (it doesn't float). Also, it is not tilting around itself, only rotates about its vertical axis.

- Strength:
    - The security distance is perfectly respected
- Limitation:
    - It stops when it doesn't find a wall in front of it.


### **2. HOLONOMIC MODEL**

-  NO, it does not maintaing the distance at all times. When it tries to surpass the obstacle (the perpendicular wall) it does a motion during which it is far away from the wall for a period of time. Furthermore, when aproximating the right wall, it gets very near instead of maintaining the security distance.
- When detecting the frontal wall, it rotates around itself in order to have the wall at its right. When the wall disappears at its right side, it rotates and reaches the upper wall in a diagonal motion, instead of following the obstacle wall directly.
- No, this model does not oscillate (w value doesn't change sign)
- The twist components it uses are (the components that are not 0 when asking the terminal to print the cmd_vel topic): 
    - The forward linear velocity (linear, x)
    - The lateral linear velocity (linear, y)
    - The angular velocity alnog the z axis (angular, z)

Basically this is telling us that the robot is not upwards (it doesn't float), but it goes frontwards and laterally. Also, it is not tilting around itself, only rotates about its vertical axis.

- Strength:
    - It has the capacity of performing lateral displacement, augmenting the amount of ways it can surpass an obstacle (we assume that this model will be able to surpass more complex obstacles) 
- Limitation:
    - It doesn't always maintaing the security distance with the wall (dangerous for physical simulations)
