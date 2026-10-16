"""
A* 경로 계획 + Pure Pursuit 주행 + 라이다 장애물 회피 + YOLOv8 객체 검출 비상정지 (단일 노드)

구독
  /map              (nav_msgs/OccupancyGrid)                  : 주행할 맵
  /amcl_pose        (geometry_msgs/PoseWithCovarianceStamped) : 현재 위치 추정값
  /goal_pose        (geometry_msgs/PoseStamped)               : RViz [2D Goal Pose]로 찍은 목적지
  /camera/image_raw (sensor_msgs/Image)                       : 터틀봇 카메라 영상
  /scan             (sensor_msgs/LaserScan)                   : 라이다 (장애물 회피)

발행
  /cmd_vel          (geometry_msgs/Twist) : 주행 명령
  /planned_path     (nav_msgs/Path)       : RViz 확인용 계획 경로
  /emergency_stop   (std_msgs/Bool)       : 비상정지 상태 (대상 물체 감지 시 True)
"""
import heapq
import os
import time
from math import atan2, sqrt, sin, cos, pi, isfinite

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy, qos_profile_sensor_data
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Path
from sensor_msgs.msg import Image, LaserScan
from std_msgs.msg import Bool
from ultralytics import YOLO


class NodeAStar:
    """A* 탐색에 쓰는 격자 한 칸"""

    def __init__(self, parent=None, position=None):
        self.parent = parent
        self.position = position
        self.g = 0.0
        self.h = 0.0
        self.f = 0.0

    def __eq__(self, other):
        return self.position == other.position

    def __lt__(self, other):
        return self.f < other.f


class AStarEStop(Node):
    def __init__(self):
        super().__init__('astar_estop')

        # ---------------- 주행 파라미터
        self.declare_parameter('lookahead_dist', 0.35)  # 전방 주시 거리 [m] (작을수록 코너를 덜 질러감)
        self.declare_parameter('linear_vel', 0.15)      # 직진 속도 [m/s]
        self.declare_parameter('max_angular_vel', 1.0)  # 최대 회전 속도 [rad/s]
        self.declare_parameter('stop_tolerance', 0.15)  # 도착 인정 거리 [m]
        self.declare_parameter('safety_margin', 6)      # 벽과 띄울 격자 칸 수 (0.05m x 6 = 30cm, 로봇 반지름 약 21cm)

        # ---------------- 라이다 장애물 회피 파라미터
        self.declare_parameter('obstacle_dist', 0.30)   # 정면 이 거리 안에 장애물이 있으면 회피 [m]
        self.declare_parameter('front_angle', 30.0)     # 정면으로 볼 각도 범위 (좌우 각각) [deg]
        self.declare_parameter('avoid_turn_vel', 0.6)   # 회피 회전 속도 [rad/s]

        # ---------------- 객체 검출(비상정지) 파라미터
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('model', '~/hand_cream_best.pt')  # 직접 학습한 YOLO 가중치 (핸드크림)
        self.declare_parameter('confidence', 0.75)           # 최소 신뢰도 (높을수록 오검출 감소)
        self.declare_parameter('min_box_ratio', 0.06)        # 화면 대비 박스 면적 비율 (가까운 물체만)
        self.declare_parameter('clear_time', 1.0)            # 물체가 사라진 뒤 재출발까지 대기 [s]
        self.declare_parameter('show_window', True)          # 검출 화면 띄우기
        self.declare_parameter('roi_width', 0.4)             # 화면 가운데 이 비율 안의 물체만 비상정지 대상

        self.lookahead_dist = self.get_parameter('lookahead_dist').value
        self.linear_vel = self.get_parameter('linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        self.stop_tolerance = self.get_parameter('stop_tolerance').value
        self.safety_margin = int(self.get_parameter('safety_margin').value)
        self.obstacle_dist = self.get_parameter('obstacle_dist').value
        self.front_angle = self.get_parameter('front_angle').value * pi / 180.0
        self.avoid_turn_vel = self.get_parameter('avoid_turn_vel').value

        self.conf = self.get_parameter('confidence').value
        self.min_box_ratio = self.get_parameter('min_box_ratio').value
        self.clear_time = self.get_parameter('clear_time').value
        self.show_window = self.get_parameter('show_window').value
        self.roi_width = self.get_parameter('roi_width').value

        # ---------------- YOLO 모델
        model_path = os.path.expanduser(self.get_parameter('model').value)
        if not os.path.exists(model_path):
            self.get_logger().error(f"모델 파일이 없습니다: {model_path}")
            raise FileNotFoundError(model_path)
        self.model = YOLO(model_path)
        self.get_logger().info(f"모델 로드: {model_path} / 클래스: {list(self.model.names.values())}")

        # ---------------- 맵 정보
        self.map_data = None
        self.cost_map = None       # 안전 마진을 반영한 "갈 수 없는 칸" 격자 (bool)
        self.map_resolution = 0.05
        self.map_origin = [0.0, 0.0]
        self.map_width = 0
        self.map_height = 0

        # ---------------- 로봇 상태
        self.current_pose = None
        self.current_yaw = 0.0
        self.global_path = []
        self.path_index = 0
        self.goal = None            # 최종 목적지 (회피 후 다시 경로를 짤 때 사용)

        # ---------------- 라이다 상태
        self.front_dist = float('inf')
        self.left_dist = float('inf')
        self.right_dist = float('inf')
        self.avoiding = False

        # ---------------- 비상정지 상태
        self.emergency = False
        self.last_seen = 0.0
        self.latest_frame = None

        # ---------------- 통신
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_path = self.create_publisher(Path, '/planned_path', 10)
        self.pub_stop = self.create_publisher(Bool, '/emergency_stop', 10)

        map_qos = QoSProfile(depth=1,
                             durability=DurabilityPolicy.TRANSIENT_LOCAL,
                             reliability=ReliabilityPolicy.RELIABLE)
        self.create_subscription(OccupancyGrid, '/map', self.map_callback, map_qos)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.pose_callback, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.create_subscription(Image, self.get_parameter('image_topic').value,
                                 self.image_callback, qos_profile_sensor_data)
        self.create_subscription(LaserScan, '/scan', self.scan_callback, qos_profile_sensor_data)

        self.create_timer(0.1, self.control_loop)   # 주행 10Hz
        self.create_timer(0.1, self.detect_loop)    # 객체 검출 10Hz (최신 프레임만)
        self.get_logger().info("A* + 비상정지 노드 시작! 맵/위치/목적지를 기다리는 중...")

    # ============================================================ 콜백
    def map_callback(self, msg):
        self.map_resolution = msg.info.resolution
        self.map_width = msg.info.width
        self.map_height = msg.info.height
        self.map_origin = [msg.info.origin.position.x, msg.info.origin.position.y]
        self.map_data = np.array(msg.data, dtype=np.int16).reshape((self.map_height, self.map_width))
        # 벽(100)·미확인(-1)을 safety_margin 칸만큼 한 번에 부풀려 둔다
        self.cost_map = self.inflate(self.map_data != 0, self.safety_margin)
        self.get_logger().info(f"맵 수신: {self.map_width} x {self.map_height}")

    def pose_callback(self, msg):
        self.current_pose = [msg.pose.pose.position.x, msg.pose.pose.position.y]
        q = msg.pose.pose.orientation
        self.current_yaw = atan2(2.0 * (q.w * q.z + q.x * q.y),
                                 1.0 - 2.0 * (q.y * q.y + q.z * q.z))

    def goal_callback(self, msg):
        if self.map_data is None:
            self.get_logger().warn("아직 맵을 받지 못했습니다.")
            return
        if self.current_pose is None:
            self.get_logger().warn("아직 위치를 모릅니다. RViz에서 [2D Pose Estimate]를 먼저 해주세요.")
            return

        self.goal = [msg.pose.position.x, msg.pose.position.y]
        self.avoiding = False
        self.get_logger().info(f"경로 계산 중... 목적지 ({self.goal[0]:.2f}, {self.goal[1]:.2f})")
        self.plan_path()

    def plan_path(self):
        """현재 위치 → self.goal 까지 A* 경로를 새로 계산한다."""
        path_grid = self.run_astar(self.world_to_grid(self.current_pose), self.world_to_grid(self.goal))

        if path_grid:
            self.global_path = [self.grid_to_world(p) for p in path_grid]
            self.path_index = 0
            self.publish_path_viz()
            self.get_logger().info(f"경로 발견! ({len(path_grid)}칸) 출발합니다.")
        else:
            self.global_path = []
            self.stop_robot()
            self.get_logger().warn("경로를 찾지 못했습니다. 목적지가 벽에 너무 가깝지 않은지 확인하세요.")

    def image_callback(self, msg):
        self.latest_frame = self.imgmsg_to_cv2(msg)

    def scan_callback(self, msg):
        """라이다에서 정면/왼쪽/오른쪽 최소 거리를 구한다 (0rad = 정면, 반시계 방향이 +)."""
        front, left, right = float('inf'), float('inf'), float('inf')
        for i, r in enumerate(msg.ranges):
            if not isfinite(r) or r < msg.range_min or r > msg.range_max:
                continue
            a = msg.angle_min + i * msg.angle_increment
            a = atan2(sin(a), cos(a))   # -pi ~ pi 로 정규화
            if abs(a) <= self.front_angle:
                front = min(front, r)
            elif self.front_angle < a <= pi / 2:
                left = min(left, r)
            elif -pi / 2 <= a < -self.front_angle:
                right = min(right, r)
        self.front_dist, self.left_dist, self.right_dist = front, left, right

    # ============================================================ 객체 검출 → 비상정지
    @staticmethod
    def imgmsg_to_cv2(msg):
        """cv_bridge 없이 sensor_msgs/Image → OpenCV BGR 변환 (rgb8/bgr8/mono8)"""
        channels = 1 if msg.encoding == 'mono8' else 3
        img = np.frombuffer(msg.data, dtype=np.uint8).reshape(msg.height, msg.step)
        img = img[:, :msg.width * channels].reshape(msg.height, msg.width, channels)
        if msg.encoding == 'rgb8':
            img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
        elif msg.encoding == 'mono8':
            img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
        return img.copy()

    def detect_loop(self):
        if self.latest_frame is None:
            return
        frame, self.latest_frame = self.latest_frame, None
        h, w = frame.shape[:2]
        detected = False

        for result in self.model(frame, stream=True, conf=self.conf, verbose=False):
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                name = self.model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                # 화면 가운데(진행 방향) 영역 안에 있고, 충분히 크게(가까이) 보일 때만 정지 대상
                in_roi = abs((x1 + x2) / 2 - w / 2) <= self.roi_width * w / 2
                is_target = in_roi and (x2 - x1) * (y2 - y1) / float(w * h) >= self.min_box_ratio
                detected |= is_target

                color = (0, 0, 255) if is_target else (127, 0, 127)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(y1 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        now = time.monotonic()
        if detected:
            self.last_seen = now
            if not self.emergency:
                self.emergency = True
                self.stop_robot()
                self.get_logger().warn("!!! 비상정지 !!! 대상 물체가 감지되어 정지합니다.")
        elif self.emergency and now - self.last_seen > self.clear_time:
            self.emergency = False
            self.get_logger().info("대상 물체가 사라졌습니다. 주행을 재개합니다.")
        self.pub_stop.publish(Bool(data=self.emergency))

        if self.show_window:
            rx = int(w * (1 - self.roi_width) / 2)
            cv2.rectangle(frame, (rx, 0), (w - rx, h - 1), (0, 255, 255), 1)   # 검사 영역 표시
            label = "EMERGENCY STOP" if self.emergency else "DRIVING"
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                        (0, 0, 255) if self.emergency else (0, 200, 0), 2)
            cv2.imshow('astar_estop camera', frame)
            cv2.waitKey(1)

    # ============================================================ A*
    @staticmethod
    def inflate(obstacle, margin):
        """장애물 격자를 margin 칸만큼 사방으로 넓힌다 (numpy 시프트 연산)."""
        if margin <= 0:
            return obstacle.copy()
        h, w = obstacle.shape
        padded = np.pad(obstacle, margin, mode='constant', constant_values=False)
        result = np.zeros_like(obstacle)
        for dy in range(-margin, margin + 1):
            for dx in range(-margin, margin + 1):
                result |= padded[margin + dy: margin + dy + h, margin + dx: margin + dx + w]
        return result

    def nearest_free(self, cell, max_radius=20):
        """시작/목표점이 마진 안쪽에 걸려 있으면 가장 가까운 빈 칸으로 옮긴다."""
        y, x = cell
        if not self.cost_map[y][x]:
            return cell
        for r in range(1, max_radius + 1):
            for dy in range(-r, r + 1):
                for dx in range(-r, r + 1):
                    ny, nx = y + dy, x + dx
                    if 0 <= ny < self.map_height and 0 <= nx < self.map_width and not self.cost_map[ny][nx]:
                        return (ny, nx)
        return None

    def in_map(self, cell):
        return 0 <= cell[0] < self.map_height and 0 <= cell[1] < self.map_width

    def run_astar(self, start, end):
        if not (self.in_map(start) and self.in_map(end)):
            return None
        start = self.nearest_free(start)
        end = self.nearest_free(end)
        if start is None or end is None:
            return None

        open_list = []
        heapq.heappush(open_list, NodeAStar(None, start))
        visited = set()
        best_g = {start: 0.0}
        # 8방향 이동, 대각선은 비용 √2
        moves = [(0, 1, 1.0), (0, -1, 1.0), (1, 0, 1.0), (-1, 0, 1.0),
                 (1, 1, 1.414), (1, -1, 1.414), (-1, 1, 1.414), (-1, -1, 1.414)]

        while open_list:
            current = heapq.heappop(open_list)
            if current.position in visited:
                continue
            visited.add(current.position)

            if current.position == end:
                path = []
                while current:
                    path.append(current.position)
                    current = current.parent
                return path[::-1]

            cy, cx = current.position
            for my, mx, cost in moves:
                ny, nx = cy + my, cx + mx
                if not (0 <= ny < self.map_height and 0 <= nx < self.map_width):
                    continue
                if self.cost_map[ny][nx] or (ny, nx) in visited:
                    continue
                g = current.g + cost
                if g >= best_g.get((ny, nx), float('inf')):
                    continue
                best_g[(ny, nx)] = g

                node = NodeAStar(current, (ny, nx))
                node.g = g
                node.h = sqrt((ny - end[0]) ** 2 + (nx - end[1]) ** 2)
                node.f = node.g + node.h
                heapq.heappush(open_list, node)
        return None

    # ============================================================ Pure Pursuit 주행
    def control_loop(self):
        if not self.global_path or self.current_pose is None:
            return

        # 비상정지 중에는 경로는 유지한 채 속도 0만 보낸다
        if self.emergency:
            self.stop_robot()
            return

        # 라이다 장애물 회피: 정면이 막히면 멈춰서 넓은 쪽으로 회전
        if self.front_dist < self.obstacle_dist:
            if not self.avoiding:
                self.get_logger().warn(f"장애물 감지 ({self.front_dist:.2f}m) → 회피 회전")
            self.avoiding = True
            cmd = Twist()
            cmd.angular.z = self.avoid_turn_vel if self.left_dist > self.right_dist else -self.avoid_turn_vel
            self.pub_cmd.publish(cmd)
            return
        if self.avoiding:
            # 정면이 트이면 현재 위치에서 경로를 다시 계산
            self.avoiding = False
            self.get_logger().info("정면 확보 → 경로 재계산")
            self.plan_path()
            if not self.global_path:
                return

        final_goal = self.global_path[-1]
        dist_to_final = sqrt((final_goal[0] - self.current_pose[0]) ** 2 +
                             (final_goal[1] - self.current_pose[1]) ** 2)
        if dist_to_final < self.stop_tolerance:
            self.global_path = []
            self.goal = None
            self.stop_robot()
            self.get_logger().info("목적지 도착!")
            return

        # 경로 위에서 lookahead_dist 이상 떨어진 첫 점을 목표점으로 선택
        target_x, target_y = final_goal
        for i in range(self.path_index, len(self.global_path)):
            px, py = self.global_path[i]
            if sqrt((px - self.current_pose[0]) ** 2 + (py - self.current_pose[1]) ** 2) >= self.lookahead_dist:
                target_x, target_y = px, py
                self.path_index = i
                break

        alpha = atan2(target_y - self.current_pose[1], target_x - self.current_pose[0]) - self.current_yaw
        while alpha > pi:
            alpha -= 2 * pi
        while alpha < -pi:
            alpha += 2 * pi

        cmd = Twist()
        if abs(alpha) > pi / 2:   # 목표점이 뒤쪽이면 제자리 회전부터
            cmd.angular.z = self.max_angular_vel if alpha > 0 else -self.max_angular_vel
        else:
            cmd.linear.x = self.linear_vel
            cmd.angular.z = self.linear_vel * (2.0 * sin(alpha)) / self.lookahead_dist
        cmd.angular.z = max(-self.max_angular_vel, min(self.max_angular_vel, cmd.angular.z))
        self.pub_cmd.publish(cmd)

    # ============================================================ 유틸
    def world_to_grid(self, world):
        return (int((world[1] - self.map_origin[1]) / self.map_resolution),
                int((world[0] - self.map_origin[0]) / self.map_resolution))

    def grid_to_world(self, grid):
        return [(grid[1] + 0.5) * self.map_resolution + self.map_origin[0],
                (grid[0] + 0.5) * self.map_resolution + self.map_origin[1]]

    def publish_path_viz(self):
        msg = Path()
        msg.header.frame_id = 'map'
        msg.header.stamp = self.get_clock().now().to_msg()
        for p in self.global_path:
            ps = PoseStamped()
            ps.header = msg.header
            ps.pose.position.x, ps.pose.position.y = p[0], p[1]
            ps.pose.orientation.w = 1.0
            msg.poses.append(ps)
        self.pub_path.publish(msg)

    def stop_robot(self):
        self.pub_cmd.publish(Twist())

    def destroy_node(self):
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = AStarEStop()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.stop_robot()
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
