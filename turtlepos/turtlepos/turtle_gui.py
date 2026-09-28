import sys
from datetime import datetime

import pymysql
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose
from std_srvs.srv import Empty

from PyQt5.QtCore import QTimer
from PyQt5.QtWidgets import (
    QApplication, QWidget, QPushButton, QLabel, QGridLayout, QVBoxLayout
)

# ===== MySQL 접속 정보 (Windows MySQL) =====
DB_CONFIG = {
    'host': '192.168.0.141',   # Windows IP (ipconfig로 확인, 바뀔 수 있음)
    'user': 'rosuser',
    'password': 'ros1234',
    'database': 'rosdb',
}

LINEAR_SPEED = 2.0      # 앞/뒤 이동 속도
ANGULAR_SPEED = 1.5708  # 좌/우 회전 속도 (약 90도/초)


class TurtleNode(Node):
    """ROS 2 통신 담당: cmd_vel 발행, pose 구독, reset 서비스 호출"""

    def __init__(self):
        super().__init__('turtle_gui_node')
        self.cmd_pub = self.create_publisher(Twist, '/turtle1/cmd_vel', 10)
        self.pose_sub = self.create_subscription(
            Pose, '/turtle1/pose', self.pose_callback, 10)
        self.reset_client = self.create_client(Empty, '/reset')
        self.pose = None

    def pose_callback(self, msg):
        self.pose = msg

    def move(self, linear, angular):
        msg = Twist()
        msg.linear.x = linear
        msg.angular.z = angular
        self.cmd_pub.publish(msg)

    def reset(self):
        if not self.reset_client.service_is_ready():
            return False
        self.reset_client.call_async(Empty.Request())
        return True


class TurtleGui(QWidget):
    """PyQt GUI: 방향 버튼 4개 + Reset + DB 저장"""

    def __init__(self, node):
        super().__init__()
        self.node = node
        self.init_ui()

        # PyQt 이벤트 루프 안에서 ROS 콜백도 처리되도록 주기적으로 spin
        self.ros_timer = QTimer(self)
        self.ros_timer.timeout.connect(self.spin_ros)
        self.ros_timer.start(10)

    def init_ui(self):
        self.setWindowTitle('Turtle Controller')

        btn_up = QPushButton('▲ 앞으로')
        btn_down = QPushButton('▼ 뒤로')
        btn_left = QPushButton('◀ 왼쪽')
        btn_right = QPushButton('▶ 오른쪽')
        btn_reset = QPushButton('Reset')
        btn_save = QPushButton('위치 저장 (DB)')

        btn_up.clicked.connect(lambda: self.node.move(LINEAR_SPEED, 0.0))
        btn_down.clicked.connect(lambda: self.node.move(-LINEAR_SPEED, 0.0))
        btn_left.clicked.connect(lambda: self.node.move(0.0, ANGULAR_SPEED))
        btn_right.clicked.connect(lambda: self.node.move(0.0, -ANGULAR_SPEED))
        btn_reset.clicked.connect(self.reset_turtle)
        btn_save.clicked.connect(self.save_pose)

        for btn in (btn_up, btn_down, btn_left, btn_right, btn_reset, btn_save):
            btn.setMinimumSize(110, 50)

        grid = QGridLayout()
        grid.addWidget(btn_up, 0, 1)
        grid.addWidget(btn_left, 1, 0)
        grid.addWidget(btn_reset, 1, 1)
        grid.addWidget(btn_right, 1, 2)
        grid.addWidget(btn_down, 2, 1)

        self.pose_label = QLabel('현재 위치: 수신 대기 중...')
        self.status_label = QLabel('')
        self.status_label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(self.pose_label)
        layout.addLayout(grid)
        layout.addWidget(btn_save)
        layout.addWidget(self.status_label)
        self.setLayout(layout)

    def spin_ros(self):
        rclpy.spin_once(self.node, timeout_sec=0)
        pose = self.node.pose
        if pose is not None:
            self.pose_label.setText(
                f'현재 위치: x={pose.x:.3f}, y={pose.y:.3f}, theta={pose.theta:.3f}')

    def reset_turtle(self):
        if self.node.reset():
            self.status_label.setText('거북이를 Reset 했습니다.')
        else:
            self.status_label.setText('/reset 서비스를 찾을 수 없습니다. turtlesim_node가 실행 중인지 확인하세요.')

    def save_pose(self):
        pose = self.node.pose
        if pose is None:
            self.status_label.setText('아직 위치 정보를 받지 못했습니다.')
            return

        now = datetime.fromtimestamp(self.node.get_clock().now().nanoseconds / 1e9)

        try:
            conn = pymysql.connect(**DB_CONFIG)
            with conn:
                with conn.cursor() as cur:
                    cur.execute(
                        'INSERT INTO turtlepos (x, y, theta, `time`) '
                        'VALUES (%s, %s, %s, %s)',
                        (pose.x, pose.y, pose.theta, now))
                conn.commit()
            self.status_label.setText(
                f'저장 완료: x={pose.x:.3f}, y={pose.y:.3f}, '
                f'theta={pose.theta:.3f}, time={now:%H:%M:%S}')
        except Exception as e:
            self.status_label.setText(f'DB 저장 실패: {e}')


def main(args=None):
    rclpy.init(args=args)
    node = TurtleNode()

    app = QApplication(sys.argv)
    gui = TurtleGui(node)
    gui.show()
    exit_code = app.exec_()

    node.destroy_node()
    rclpy.shutdown()
    sys.exit(exit_code)


if __name__ == '__main__':
    main()