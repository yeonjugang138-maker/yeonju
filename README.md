# my-car-astar

TurtleBot3(waffle_pi)가 **A\*** 알고리즘으로 최단 경로를 계획하고 **Pure Pursuit** 방식으로 따라 주행하는 ROS 2 Humble 패키지입니다.
주행 중 **라이다**로 앞을 막는 장애물을 피하고, **터틀봇 카메라**에 지정한 물체(핸드크림)가 보이면 **비상정지**합니다.
물체 검출에는 직접 학습시킨 YOLOv8 모델(`hand_cream_best.pt`)을 사용합니다.

주행용 노드는 `my_car_astar/astar_estop.py` 하나에 모두 들어 있습니다.

## 동작 개요

```
 /map ──────────────┐
 /amcl_pose ────────┤
 /goal_pose ────────┼─▶ astar_estop ──▶ /cmd_vel ──▶ 로봇
 /scan (라이다) ────┤        │
 /camera/image_raw ─┘        ├──▶ /planned_path   (RViz 확인용 경로)
                             └──▶ /emergency_stop (비상정지 상태)
```

`control_loop`(10Hz)는 아래 우선순위로 동작합니다.

| 순위 | 상황 | 동작 |
|---|---|---|
| 1 | 카메라에 대상 물체 감지 | **비상정지**: 경로를 유지한 채 속도 0, 물체가 사라지면 1초 뒤 재출발 |
| 2 | 라이다 정면 30cm 안에 장애물 | **회피**: 좌우 중 넓은 쪽으로 제자리 회전, 앞이 트이면 A\* 경로 재계산 |
| 3 | 평소 | **Pure Pursuit**로 A\* 경로를 따라 주행, 목적지 15cm 안에 들어오면 정지 |

### 1. 경로 계획 (A\*)
- RViz에서 `2D Goal Pose`를 찍으면 `/goal_pose`를 받아 현재 위치에서 목적지까지 격자 맵 위의 최단 경로를 찾습니다.
- 8방향 이동(대각선 비용 √2), 휴리스틱은 유클리드 거리입니다.
- 벽(100)과 미확인 영역(-1)을 `safety_margin` 칸(기본 6칸 = 30cm)만큼 미리 부풀려 둡니다. 로봇 반지름(약 21cm)보다 넓게 띄워서 벽에 스치지 않게 합니다.
- 시작점이나 목적지가 마진 안에 걸리면 가장 가까운 빈 칸으로 옮겨서 탐색합니다.

### 2. 주행 (Pure Pursuit)
- 경로 위에서 `lookahead_dist` 이상 떨어진 첫 점을 목표로 삼고 `ω = v · 2·sin(α) / L` 공식으로 각속도를 계산합니다.
- 목표점이 뒤쪽(90° 이상)에 있으면 제자리 회전부터 합니다.

### 3. 장애물 회피 (라이다)
- `/scan`을 정면(±30°), 왼쪽, 오른쪽으로 나눠 각 방향의 최소 거리를 구합니다.
- 정면이 `obstacle_dist` 안으로 막히면 더 넓은 쪽으로 회전하고, 앞이 트이면 현재 위치에서 경로를 다시 계산합니다.

### 4. 비상정지 (YOLOv8)
- 카메라 영상을 10Hz로 YOLO에 넣어 대상 물체를 찾습니다.
- 오검출을 줄이기 위해 아래 세 조건을 모두 만족할 때만 정지합니다.
  - 신뢰도가 `confidence` 이상
  - 박스가 화면의 `min_box_ratio` 이상(가까이 있을 때만)
  - 박스 중심이 화면 가운데 `roi_width` 영역 안(진행 방향에 있을 때만, 카메라 창에 노란 선으로 표시)
- 비상정지 상태는 `/emergency_stop`(Bool)으로도 발행합니다.

## 파일 구성

| 파일 | 설명 |
|---|---|
| `my_car_astar/astar_estop.py` | **주행용 노드**: A\* + Pure Pursuit + 라이다 회피 + YOLO 비상정지 |
| `launch/real_robot.launch.py` | 실제 로봇용: 위치 추정(AMCL) + RViz |

## 설치

```bash
cd ~/my_ws/src
git clone https://github.com/<내-아이디>/my-car-astar.git my_car_astar
pip install ultralytics
cp <학습한 가중치>.pt ~/hand_cream_best.pt
cd ~/my_ws
colcon build --symlink-install --packages-select my_car_astar
source install/setup.bash
```

## 실행 (실제 터틀봇)

**로봇 (SSH 터미널 2개)**
```bash
# 터미널 1: 모터와 라이다
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch turtlebot3_bringup robot.launch.py

# 터미널 2: 카메라
ros2 run camera_ros camera_node --ros-args -p width:=320 -p height:=240 -p format:=RGB888
```

**PC (터미널 2개)**
```bash
# 터미널 1: 위치 추정 + RViz (맵: ~/my_ws/src/my_bot/maps/map_tt.yaml)
ros2 launch my_car_astar real_robot.launch.py

# 터미널 2: 주행용 노드
ros2 run my_car_astar astar_estop --ros-args -p use_sim_time:=false -p linear_vel:=0.1
```

**RViz**
1. `2D Pose Estimate`로 로봇의 실제 위치와 방향을 지정합니다.
2. Add → By topic → `/planned_path`를 추가합니다.
3. `2D Goal Pose`로 목적지를 찍으면 경로가 그려지고 출발합니다.
4. 진행 방향에 핸드크림을 놓으면 `!!! 비상정지 !!!` 로그와 함께 멈추고, 치우면 다시 출발합니다.

## 실행 (Gazebo 시뮬레이션)

직접 만든 `class_room` 월드에서 SLAM으로 맵을 만들어 먼저 테스트했습니다.

```bash
export TURTLEBOT3_MODEL=waffle_pi
ros2 launch my_bot tb3_class_room_localization.launch.py
ros2 run my_car_astar astar_estop --ros-args -p use_sim_time:=true
```

## 파라미터

`--ros-args -p 이름:=값`으로 바꿀 수 있습니다.

**주행**

| 이름 | 기본값 | 설명 |
|---|---|---|
| `lookahead_dist` | 0.35 | 전방 주시 거리 [m]. 작을수록 코너를 덜 질러감 |
| `linear_vel` | 0.15 | 직진 속도 [m/s] (실제 로봇은 0.1 권장) |
| `max_angular_vel` | 1.0 | 최대 회전 속도 [rad/s] |
| `stop_tolerance` | 0.15 | 도착 인정 거리 [m] |
| `safety_margin` | 6 | 벽과 띄울 격자 칸 수 (0.05m × 6 = 30cm) |

**장애물 회피**

| 이름 | 기본값 | 설명 |
|---|---|---|
| `obstacle_dist` | 0.30 | 정면 이 거리 안에 장애물이 있으면 회피 [m] |
| `front_angle` | 30.0 | 정면으로 볼 각도 범위 (좌우 각각) [deg] |
| `avoid_turn_vel` | 0.6 | 회피 회전 속도 [rad/s] |

**비상정지**

| 이름 | 기본값 | 설명 |
|---|---|---|
| `model` | `~/hand_cream_best.pt` | YOLO 가중치 경로 |
| `image_topic` | `/camera/image_raw` | 카메라 토픽 |
| `confidence` | 0.75 | 최소 신뢰도 (높을수록 오검출 감소) |
| `min_box_ratio` | 0.06 | 박스가 화면의 이 비율 이상일 때만 정지 (클수록 더 가까이 와야 정지) |
| `roi_width` | 0.4 | 화면 가운데 이 비율 안의 물체만 정지 대상 |
| `clear_time` | 1.0 | 물체가 사라진 뒤 재출발까지 대기 [s] |
| `show_window` | true | 검출 화면 표시 여부 |

## 검출 모델 학습

- **대상**: 데일리콤마 모스트 퍼퓸 핸드크림 (코튼 화이트), 클래스 이름 `hand_cream`
- **데이터**: 휴대폰으로 찍은 사진 7장(앞면, 뒷면, 옆면, 세움, 눕힘)에 박스 라벨을 붙였습니다.
  사진이 적어서, 핸드크림 모양을 오려 다른 배경 위에 크기, 각도, 밝기를 바꿔 붙이는 방식으로 학습 이미지 400장을 합성했습니다.
- **학습**: YOLOv8n, 이미지 크기 416, 12 epoch (검증 mAP50 0.97)

## 수업 예제 코드에서 바꾼 점

- **비상정지**: 카메라 + YOLO로 대상 물체를 보면 경로를 유지한 채 정지, 사라지면 이어서 주행
- **오검출 줄이기**: 신뢰도, 박스 크기, 화면 가운데 검사 영역 세 조건을 모두 만족할 때만 정지
- **라이다 장애물 회피**: 맵에 없는 장애물도 정면이 막히면 피하고 경로 재계산
- **벽 충돌 방지**: 안전 마진 20cm → 30cm, 전방 주시 거리 0.5m → 0.35m
- **A\* 속도 개선**: 매 칸마다 주변을 검사하던 `check_safety` 대신, 맵을 받을 때 numpy로 한 번만 장애물을 부풀림
- **A\* 정확도 개선**: 대각선 이동 비용 √2, `best_g`로 같은 칸에 더 비싼 경로가 중복으로 쌓이지 않게 함
- **`/map` QoS**: map_server의 transient local 설정에 맞춰, 노드를 나중에 켜도 맵을 받을 수 있게 함
- **안전 처리**: 위치를 받기 전 `current_pose`가 `None`일 때 생기던 오류 방지, 목표가 뒤에 있으면 제자리 회전
