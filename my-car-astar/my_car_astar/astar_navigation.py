"""
A* 경로 계획 + Pure Pursuit 주행 + 객체 검출 비상정지 통합 노드

구독
  /map          (nav_msgs/OccupancyGrid)              : 주행할 맵
  /amcl_pose    (geometry_msgs/PoseWithCovarianceStamped) : 현재 위치 추정값
  /goal_pose    (geometry_msgs/PoseStamped)           : RViz [2D Goal Pose]로 찍은 목적지
  /emergency_stop (std_msgs/Bool)                     : 객체 검출 노드가 보내는 비상정지 신호

발행
  /cmd_vel       (geometry_msgs/Twist) : 주행 명령
  /planned_path  (nav_msgs/Path)       : RViz 확인용 계획 경로
"""
import heapq
from math import atan2, sqrt, sin, pi

import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import QoSProfile, DurabilityPolicy, ReliabilityPolicy
from geometry_msgs.msg import Twist, PoseStamped, PoseWithCovarianceStamped
from nav_msgs.msg import OccupancyGrid, Path
from std_msgs.msg import Bool


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


class AStarNavigation(Node):
    def __init__(self):
        super().__init__('astar_navigation')

        # ---------------- 튜닝 파라미터 (ros2 run ... --ros-args -p 이름:=값 으로 변경 가능)
        self.declare_parameter('lookahead_dist', 0.5)   # 전방 주시 거리 [m]
        self.declare_parameter('linear_vel', 0.2)       # 직진 속도 [m/s]
        self.declare_parameter('max_angular_vel', 1.0)  # 최대 회전 속도 [rad/s]
        self.declare_parameter('stop_tolerance', 0.15)  # 도착 인정 거리 [m]
        self.declare_parameter('safety_margin', 4)      # 장애물과 띄울 격자 칸 수

        self.lookahead_dist = self.get_parameter('lookahead_dist').value
        self.linear_vel = self.get_parameter('linear_vel').value
        self.max_angular_vel = self.get_parameter('max_angular_vel').value
        self.stop_tolerance = self.get_parameter('stop_tolerance').value
        self.safety_margin = int(self.get_parameter('safety_margin').value)

        # ---------------- 맵 정보
        self.map_data = None       # 원본 점유 격자 (2차원)
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

        # ---------------- 비상정지 상태
        self.emergency = False

        # ---------------- 통신
        self.pub_cmd = self.create_publisher(Twist, '/cmd_vel', 10)
        self.pub_path = self.create_publisher(Path, '/planned_path', 10)

        # map_server는 /map을 한 번만(transient local) 발행하므로 QoS를 맞춰야 늦게 켜도 맵을 받음
        map_qos = QoSProfile(
            depth=1,
            durability=DurabilityPolicy.TRANSIENT_LOCAL,
            reliability=ReliabilityPolicy.RELIABLE,
        )
        self.create_subscription(OccupancyGrid, '/map', self.map_callback, map_qos)
        self.create_subscription(PoseWithCovarianceStamped, '/amcl_pose', self.pose_callback, 10)
        self.create_subscription(PoseStamped, '/goal_pose', self.goal_callback, 10)
        self.create_subscription(Bool, '/emergency_stop', self.emergency_callback, 10)

        self.timer = self.create_timer(0.1, self.control_loop)
        self.get_logger().info("A* Navigation 시작! 맵/위치/목적지를 기다리는 중...")

    # ============================================================ 콜백
    def map_callback(self, msg):
        self.map_resolution = msg.info.resolution
        self.map_width = msg.info.width
        self.map_height = msg.info.height
        self.map_origin = [msg.info.origin.position.x, msg.info.origin.position.y]
        self.map_data = np.array(msg.data, dtype=np.int16).reshape((self.map_height, self.map_width))

        # 0이 아닌 칸(벽 100, 미확인 -1)을 장애물로 보고, safety_margin 만큼 미리 부풀려 둔다.
        # (원래 코드처럼 매 칸마다 주변을 검사하면 A*가 매우 느려지므로 한 번만 계산)
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

        goal = [msg.pose.position.x, msg.pose.position.y]
        start_grid = self.world_to_grid(self.current_pose)
        goal_grid = self.world_to_grid(goal)

        self.get_logger().info(f"경로 계산 중... 목적지 ({goal[0]:.2f}, {goal[1]:.2f})")
        path_grid = self.run_astar(start_grid, goal_grid)

        if path_grid:
            self.global_path = [self.grid_to_world(p) for p in path_grid]
            self.path_index = 0
            self.publish_path_viz()
            self.get_logger().info(f"경로 발견! ({len(path_grid)}칸) 출발합니다.")
        else:
            self.global_path = []
            self.stop_robot()
            self.get_logger().warn("경로를 찾지 못했습니다. 목적지가 벽에 너무 가깝지 않은지 확인하세요.")

    def emergency_callback(self, msg):
        if msg.data and not self.emergency:
            self.get_logger().warn("!!! 비상정지 !!! 객체가 감지되어 정지합니다.")
            self.stop_robot()
        elif not msg.data and self.emergency:
            self.get_logger().info("객체가 사라졌습니다. 주행을 재개합니다.")
        self.emergency = msg.data

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

        # 비상정지 중에는 경로는 유지한 채 계속 0 속도만 보낸다
        if self.emergency:
            self.stop_robot()
            return

        final_goal = self.global_path[-1]
        dist_to_final = sqrt((final_goal[0] - self.current_pose[0]) ** 2 +
                             (final_goal[1] - self.current_pose[1]) ** 2)

        if dist_to_final < self.stop_tolerance:
            self.global_path = []
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
        # 목표점이 뒤쪽(90도 이상)에 있으면 제자리 회전부터
        if abs(alpha) > pi / 2:
            cmd.linear.x = 0.0
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
        # 칸의 중심 좌표로 변환
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


def main(args=None):
    rclpy.init(args=args)
    node = AStarNavigation()
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
