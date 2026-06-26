# 03 - Test i control del braç robot amb `my_arm_driver`

Aquest document descriu el procediment bàsic per provar el braç robot de 6 graus de llibertat controlat amb servos SG90 i Arduino Nano ESP32 dins del repositori `my_rUBot_mecanum`.

El package principal és:

```text
src/Robot_drivers/my_arm_driver
```

L'objectiu és verificar tota la cadena de control:

```text
Nodes ROS 2 de test o comanda
        ↓
trajectory_msgs/JointTrajectory
        ↓
/arm_controller/joint_trajectory
        ↓
serial_trajectory_bridge_node.py
        ↓
Arduino Nano ESP32
        ↓
Servos SG90
```

---

## 1. Arquitectura general

El braç no utilitza un `joint_trajectory_controller` real de `ros2_control`, sinó un driver Python que escolta trajectòries ROS 2 i les converteix en ordres sèrie cap a l'Arduino.

La interfície ROS principal és:

```text
Topic:
  /arm_controller/joint_trajectory

Message:
  trajectory_msgs/msg/JointTrajectory
```

El node recomanat per executar les ordres al hardware és:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Aquest node rep missatges `JointTrajectory`, converteix cada posició articular de radians a graus de servo i envia una línia de text a l'Arduino amb el format:

```text
servo1,servo2,servo3,servo4,servo5,servo6
```

Per exemple:

```text
90,120,60,90,90,90
```

---

## 2. Nodes disponibles en `my_arm_driver`

Els executables ROS 2 definits al package són:

| Executable | Fitxer Python | Funció principal |
|---|---|---|
| `serial_bridge_node` | `serial_bridge_node.py` | Driver sèrie simple. Llegeix una trajectòria i envia només l'últim punt al robot. |
| `serial_trajectory_bridge_node` | `serial_trajectory_bridge_node.py` | Driver sèrie complet. Executa tots els punts de la trajectòria respectant `time_from_start` i publica `/joint_states`. |
| `test_joint_trajectory_node` | `test_joint_trajectory_node.py` | Genera una trajectòria senzilla de prova per moure un sol joint. |
| `send_joint_target_node` | `send_joint_target_node.py` | Envia una única configuració final del braç. |
| `send_joint_trajectory_node` | `send_joint_trajectory_node.py` | Envia una trajectòria definida per diversos punts manuals. |
| `send_smooth_joint_target_node` | `send_smooth_joint_target_node.py` | Genera una trajectòria interpolada entre una posició inicial i una posició final. És el node recomanat per moviments suaus. |

---

## 3. Compilació del package

Des de l'arrel del workspace:

```bash
cd ~/my_rUBot_mecanum
colcon build --packages-select my_arm_driver
source install/setup.bash
```

Si vols compilar tot el workspace:

```bash
cd ~/my_rUBot_mecanum
colcon build
source install/setup.bash
```

Comprova que els executables estan disponibles:

```bash
ros2 pkg executables my_arm_driver
```

Hauries de veure una sortida similar a:

```text
my_arm_driver serial_bridge_node
my_arm_driver serial_trajectory_bridge_node
my_arm_driver test_joint_trajectory_node
my_arm_driver send_joint_target_node
my_arm_driver send_joint_trajectory_node
my_arm_driver send_smooth_joint_target_node
```

---

## 4. Connexió amb l'Arduino

Abans de llançar el driver, comprova quin port sèrie utilitza l'Arduino:

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

En molts casos serà:

```text
/dev/ttyUSB0
```

o bé:

```text
/dev/ttyACM0
```

Si el port no és accessible, afegeix l'usuari al grup `dialout`:

```bash
sudo usermod -a -G dialout $USER
```

Després cal tancar sessió i tornar-la a obrir.

---

## 5. Node principal: `serial_trajectory_bridge_node`

### 5.1 Funció

Aquest és el node recomanat per controlar el braç real.

Rep trajectòries a:

```text
/arm_controller/joint_trajectory
```

i envia a l'Arduino totes les posicions de la trajectòria. A diferència de `serial_bridge_node`, no es queda només amb l'últim punt, sinó que executa tots els punts respectant el temps indicat en cada `time_from_start`.

També publica l'estat actual estimat dels joints a:

```text
/joint_states
```

Això és útil per visualitzar el braç a RViz2 i per mantenir una interfície ROS més coherent.

### 5.2 Paràmetres principals

| Paràmetre | Valor per defecte | Descripció |
|---|---:|---|
| `serial_port` | `/dev/ttyUSB0` | Port sèrie de l'Arduino. |
| `baudrate` | `115200` | Velocitat de comunicació sèrie. |
| `servo_center_deg` | `[90,90,90,90,90,90]` | Valor de servo corresponent a joint `0 rad`. |
| `servo_sign` | `[1,1,1,1,1,1]` | Signe de conversió de cada joint. Permet invertir un servo. |
| `servo_min_deg` | `[0,0,0,0,0,0]` | Límit mínim de cada servo. |
| `servo_max_deg` | `[180,180,180,180,180,180]` | Límit màxim de cada servo. |
| `joint_names` | `arm_joint1` ... `arm_joint6` | Noms dels joints del braç. |
| `publish_joint_states` | `True` | Activa la publicació de `/joint_states`. |
| `joint_state_rate` | `20.0` | Freqüència de publicació de `/joint_states`. |

### 5.3 Llançament bàsic

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Amb port específic:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyACM0 \
  -p baudrate:=115200
```

Amb inversió d'algun servo:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB0 \
  -p servo_sign:="[1,-1,1,1,1,1]"
```

Amb límits personalitzats:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_min_deg:="[10,10,10,10,10,10]" \
  -p servo_max_deg:="[170,170,170,170,170,170]"
```

---

## 6. Node simple: `serial_bridge_node`

### 6.1 Funció

Aquest node és una primera versió simple del pont sèrie.

Rep un missatge `JointTrajectory`, però només utilitza l'últim punt de la trajectòria:

```python
point = msg.points[-1]
```

Per tant, és útil per proves ràpides de posicions finals, però no és el més adequat per moviments suaus.

### 6.2 Ús

```bash
ros2 run my_arm_driver serial_bridge_node
```

Amb port específic:

```bash
ros2 run my_arm_driver serial_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB0 \
  -p baudrate:=115200
```

### 6.3 Quan utilitzar-lo

Utilitza'l només per:

- Comprovar comunicació sèrie.
- Verificar que l'Arduino rep angles.
- Fer proves molt simples d'una posició final.

Per treball normal amb el braç, és millor utilitzar:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

---

## 7. Node `send_joint_target_node`

### 7.1 Funció

Aquest node publica una única posició objectiu del braç. Genera un `JointTrajectory` amb un sol `JointTrajectoryPoint`.

És útil per moure el braç directament a una configuració concreta.

### 7.2 Paràmetres

| Paràmetre | Valor per defecte | Descripció |
|---|---:|---|
| `topic_name` | `/arm_controller/joint_trajectory` | Topic on es publica la trajectòria. |
| `joint_names` | `joint1` ... `joint6` | Noms dels joints. |
| `target_joints_deg` | `[0,0,0,0,0,0]` | Posició objectiu en graus. |
| `duration` | `2.0` | Temps assignat al punt final. |

> Nota: en aquest node els noms per defecte són `joint1`, `joint2`, etc. Si el model del braç utilitza `arm_joint1`, `arm_joint2`, etc., és recomanable passar els noms correctes per paràmetre.

### 7.3 Exemple amb noms correctes del braç

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_joint_target_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p target_joints_deg:="[0.0,30.0,-30.0,0.0,0.0,0.0]" \
  -p duration:=2.0
```

Comportament esperat:

- Es publica una trajectòria d'un únic punt.
- El driver converteix els angles de radians a graus de servo.
- El braç es mou cap a la configuració final.

Aquest moviment pot ser brusc si el canvi angular és gran.

---

## 8. Node `send_joint_trajectory_node`

### 8.1 Funció

Aquest node publica una trajectòria formada per diversos punts definits manualment.

Cada punt es defineix en graus dins del paràmetre:

```text
trajectory_points_deg
```

i cada instant temporal es defineix a:

```text
point_times_sec
```

El temps és absolut respecte l'inici de la trajectòria, és a dir, s'utilitza com `time_from_start`.

### 8.2 Paràmetres

| Paràmetre | Valor per defecte | Descripció |
|---|---|---|
| `topic_name` | `/arm_controller/joint_trajectory` | Topic de sortida. |
| `joint_names` | `joint1` ... `joint6` | Noms dels joints. |
| `trajectory_points_deg` | Llista de punts | Punts de la trajectòria en graus. |
| `point_times_sec` | `[0,1,2,3,4]` | Temps absolut de cada punt. |

### 8.3 Exemple

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_joint_trajectory_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p trajectory_points_deg:="[
    [0.0,0.0,0.0,0.0,0.0,0.0],
    [0.0,20.0,0.0,0.0,0.0,0.0],
    [0.0,20.0,-20.0,0.0,0.0,0.0],
    [0.0,0.0,0.0,0.0,0.0,0.0]
  ]" \
  -p point_times_sec:="[0.0,2.0,4.0,6.0]"
```

Comportament esperat:

- El braç passa pels punts indicats.
- Els punts s'executen als temps especificats.
- El moviment és més controlat que amb un únic punt final, però la suavitat depèn del nombre de punts.

---

## 9. Node `test_joint_trajectory_node`

### 9.1 Funció

Aquest node genera automàticament una petita trajectòria de test per a un sol joint. És útil per comprovar ràpidament si un servo concret es mou correctament.

La trajectòria generada té cinc punts:

```text
0% → 50% → 100% → 50% → 0%
```

de l'amplitud indicada.

### 9.2 Paràmetres

| Paràmetre | Valor per defecte | Descripció |
|---|---:|---|
| `topic_name` | `/arm_controller/joint_trajectory` | Topic de sortida. |
| `joint_names` | `joint1` ... `joint6` | Noms dels joints. |
| `joint_index` | `0` | Índex del joint que es vol moure. Comença a 0. |
| `amplitude_deg` | `20.0` | Amplitud màxima del moviment en graus. |
| `step_time` | `1.0` | Temps entre punts consecutius. |

### 9.3 Exemple: provar el joint 2

Recorda que `joint_index` comença a zero:

```text
joint_index 0 → arm_joint1
joint_index 1 → arm_joint2
joint_index 2 → arm_joint3
...
```

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver test_joint_trajectory_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p joint_index:=1 \
  -p amplitude_deg:=20.0 \
  -p step_time:=1.0
```

Comportament esperat:

- Només es mou `arm_joint2`.
- El moviment puja progressivament fins a `20°` i torna a `0°`.
- La durada total és aproximadament `4 * step_time`.

---

## 10. Node recomanat per moviment suau: `send_smooth_joint_target_node`

### 10.1 Funció

Aquest node genera automàticament una trajectòria interpolada entre una configuració inicial i una configuració final.

És el node més adequat per als servos SG90, perquè aquests servos no permeten controlar directament la velocitat de forma precisa des de ROS. L'estratègia utilitzada és dividir el moviment global en molts increments petits.

El node genera:

```text
steps + 1
```

punts de trajectòria.

Per exemple:

```text
steps = 50  →  51 punts
steps = 100 → 101 punts
```

Tots els joints tenen el mateix nombre de passos, de manera que comencen i acaben al mateix temps.

### 10.2 Paràmetres

| Paràmetre | Valor per defecte | Descripció |
|---|---:|---|
| `topic_name` | `/arm_controller/joint_trajectory` | Topic de sortida. |
| `joint_names` | `arm_joint1` ... `arm_joint6` | Noms dels joints. |
| `start_joints_deg` | `[0,0,0,0,0,0]` | Configuració inicial en graus. |
| `target_joints_deg` | `[0,30,-30,0,0,0]` | Configuració final en graus. |
| `duration` | `5.0` | Durada total del moviment. |
| `steps` | `50` | Nombre d'increments d'interpolació. |

### 10.3 Exemple: moure un sol joint

Terminal 1:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 2:

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[0.0,30.0,0.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

Comportament esperat:

- Només es mou `arm_joint2`.
- El moviment dura aproximadament 5 segons.
- El moviment és més suau que amb una ordre directa d'un sol punt.

### 10.4 Exemple: moure dos joints

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[0.0,45.0,-30.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

Comportament esperat:

- `arm_joint2` es mou de `0°` a `45°`.
- `arm_joint3` es mou de `0°` a `-30°`.
- Tots dos joints comencen i acaben al mateix temps.

### 10.5 Exemple: moure tots els joints

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p duration:=6.0 \
  -p steps:=60
```

Comportament esperat:

- Es mouen tots els joints.
- La durada total és aproximadament 6 segons.
- El moviment hauria de ser continu i coordinat.

### 10.6 Exemple: moviment més lent

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p duration:=10.0 \
  -p steps:=100
```

Comportament esperat:

- El braç arriba a la mateixa configuració final.
- El moviment és més lent.
- El moviment pot ser més suau perquè hi ha més punts intermedis.

### 10.7 Tornar a home

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[30.0,45.0,-30.0,20.0,-15.0,10.0]" \
  -p target_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=6.0 \
  -p steps:=60
```

---

## 11. Comandes manuals amb `ros2 topic pub`

També es pot publicar directament una trajectòria des de terminal.

### 11.1 Enviar una única posició

```bash
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "
joint_names:
- arm_joint1
- arm_joint2
- arm_joint3
- arm_joint4
- arm_joint5
- arm_joint6
points:
- positions: [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 2
    nanosec: 0
" --once
```

Els valors de `positions` són en radians.

### 11.2 Enviar una trajectòria de dos punts

```bash
ros2 topic pub /arm_controller/joint_trajectory trajectory_msgs/msg/JointTrajectory "
joint_names:
- arm_joint1
- arm_joint2
- arm_joint3
- arm_joint4
- arm_joint5
- arm_joint6
points:
- positions: [0.0, 0.0, 0.0, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 0
    nanosec: 0
- positions: [0.0, 0.5, -0.5, 0.0, 0.0, 0.0]
  time_from_start:
    sec: 4
    nanosec: 0
" --once
```

---

## 12. Monitorització

### 12.1 Veure els topics

```bash
ros2 topic list
```

Hauries de veure:

```text
/arm_controller/joint_trajectory
/joint_states
```

### 12.2 Veure la trajectòria publicada

```bash
ros2 topic echo /arm_controller/joint_trajectory
```

### 12.3 Veure l'estat dels joints

```bash
ros2 topic echo /joint_states
```

### 12.4 Veure la freqüència de publicació de `/joint_states`

```bash
ros2 topic hz /joint_states
```

Si `joint_state_rate` és `20.0`, la freqüència esperada és aproximadament:

```text
20 Hz
```

---

## 13. Visualització a RViz2

Si el robot està carregat amb `robot_state_publisher` i el model URDF/Xacro utilitza els joints:

```text
arm_joint1
arm_joint2
arm_joint3
arm_joint4
arm_joint5
arm_joint6
```

aleshores la publicació de `/joint_states` del `serial_trajectory_bridge_node` permet actualitzar la posició del braç a RViz2.

Procediment recomanat:

Terminal 1:

```bash
ros2 launch my_robot_bringup <launch_del_robot_amb_braç>.launch.py
```

Terminal 2:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

Terminal 3:

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p target_joints_deg:="[0.0,30.0,-30.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

A RViz2 s'hauria de veure el moviment del braç si el model i els noms dels joints coincideixen.

---

## 14. Recomanacions de seguretat

Abans de provar el braç real:

1. Treu qualsevol obstacle de l'espai de treball.
2. Comença amb amplituds petites, per exemple `10°` o `20°`.
3. Comprova que cada servo gira en el sentit correcte.
4. Si un servo gira al revés, modifica `servo_sign`.
5. Si un servo força massa els límits mecànics, redueix `servo_min_deg` i `servo_max_deg`.
6. No passis directament a moviments grans sense haver provat abans cada joint individualment.
7. Mantingues el cable USB accessible per poder desconnectar ràpidament si cal.

---

## 15. Estratègia de moviment suau amb SG90

Els SG90 són servos hobby senzills. Normalment reben una consigna angular i el seu controlador intern decideix com arribar-hi. Per tant, des de ROS no és habitual controlar-ne directament la velocitat real.

L'estratègia pràctica és:

```text
moviment gran
    ↓
dividir en molts increments petits
    ↓
enviar una trajectòria amb molts punts
    ↓
executar-la amb una durada total definida
```

Per això el node més adequat és:

```bash
send_smooth_joint_target_node
```

Els dos paràmetres més importants són:

```text
duration
steps
```

- Augmentar `duration` fa el moviment més lent.
- Augmentar `steps` fa que hi hagi més punts intermedis.
- Una combinació típica inicial és `duration:=5.0` i `steps:=50`.
- Per moviments més lents i suaus es pot provar `duration:=10.0` i `steps:=100`.

---

## 16. Procediment de test recomanat

### Pas 1: compilar

```bash
cd ~/my_rUBot_mecanum
colcon build --packages-select my_arm_driver
source install/setup.bash
```

### Pas 2: llançar el driver

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p serial_port:=/dev/ttyUSB0
```

### Pas 3: comprovar topics

```bash
ros2 topic list | grep joint
```

### Pas 4: provar un joint amb amplitud petita

```bash
ros2 run my_arm_driver test_joint_trajectory_node --ros-args \
  -p joint_names:="[arm_joint1,arm_joint2,arm_joint3,arm_joint4,arm_joint5,arm_joint6]" \
  -p joint_index:=0 \
  -p amplitude_deg:=15.0 \
  -p step_time:=1.0
```

### Pas 5: provar moviment suau d'un joint

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[15.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=4.0 \
  -p steps:=40
```

### Pas 6: provar dos joints

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[15.0,0.0,0.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[15.0,25.0,-20.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

### Pas 7: tornar a home

```bash
ros2 run my_arm_driver send_smooth_joint_target_node --ros-args \
  -p start_joints_deg:="[15.0,25.0,-20.0,0.0,0.0,0.0]" \
  -p target_joints_deg:="[0.0,0.0,0.0,0.0,0.0,0.0]" \
  -p duration:=5.0 \
  -p steps:=50
```

---

## 17. Resolució de problemes

### 17.1 No apareix el port sèrie

Comprova:

```bash
ls /dev/ttyUSB*
ls /dev/ttyACM*
```

Desconnecta i torna a connectar l'Arduino. També pots mirar els últims missatges del kernel:

```bash
dmesg | tail
```

### 17.2 Permís denegat al port sèrie

Solució habitual:

```bash
sudo usermod -a -G dialout $USER
```

Tanca sessió i torna a entrar.

### 17.3 El braç no es mou

Comprova:

```bash
ros2 topic echo /arm_controller/joint_trajectory
```

Si no apareixen missatges, el node de comanda no està publicant o el topic no coincideix.

També comprova que el driver està llançat:

```bash
ros2 node list
```

Hauries de veure:

```text
/serial_trajectory_bridge_node
```

### 17.4 Un servo gira al revés

Canvia el signe del servo corresponent:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_sign:="[1,-1,1,1,1,1]"
```

### 17.5 El servo arriba al límit mecànic

Redueix els límits:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node --ros-args \
  -p servo_min_deg:="[20,20,20,20,20,20]" \
  -p servo_max_deg:="[160,160,160,160,160,160]"
```

### 17.6 RViz2 no mostra moviment

Comprova que `/joint_states` es publica:

```bash
ros2 topic echo /joint_states
```

Comprova també que els noms dels joints coincideixen amb el model URDF/Xacro. Per al braç integrat haurien de ser:

```text
arm_joint1
arm_joint2
arm_joint3
arm_joint4
arm_joint5
arm_joint6
```

---

## 18. Resum final

Per provar el braç real, el procediment recomanat és:

```bash
ros2 run my_arm_driver serial_trajectory_bridge_node
```

i després enviar ordres amb:

```bash
ros2 run my_arm_driver send_smooth_joint_target_node
```

El node `send_smooth_joint_target_node` és el més adequat per als SG90 perquè genera una trajectòria amb molts punts intermedis. Això permet obtenir moviments més progressius encara que els servos no tinguin una interfície directa de control de velocitat.

