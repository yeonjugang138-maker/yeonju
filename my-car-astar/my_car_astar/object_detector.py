"""
YOLOv8 객체 검출 → 비상정지 신호 발행 노드

직접 학습시킨 공(ball) 검출 모델(best.pt)로 터틀봇 카메라 영상을 보고,
공이 일정 크기 이상으로 보이면 /emergency_stop 에 True 를,
사라진 뒤 clear_time 초가 지나면 False 를 발행한다.

영상 입력 (파라미터 source)
  - 'topic'  : 터틀봇 카메라 토픽 구독 (기본 /camera/image_raw)
  - 'webcam' : 노트북 웹캠 직접 사용 (테스트용)
"""
import os
import time

import cv2
import numpy as np
import rclpy
from rclpy.node import Node
from rclpy.qos import qos_profile_sensor_data
from sensor_msgs.msg import Image
from std_msgs.msg import Bool
from ultralytics import YOLO


class ObjectDetector(Node):
    def __init__(self):
        super().__init__('object_detector')

        self.declare_parameter('source', 'topic')                 # 'topic' 또는 'webcam'
        self.declare_parameter('image_topic', '/camera/image_raw')
        self.declare_parameter('webcam_index', 0)
        self.declare_parameter('model', '~/ball_best.pt')         # 수요일에 ball_dataset으로 학습한 가중치
        self.declare_parameter('target_classes', 'all')           # 쉼표로 구분 (예: 'ball'). 'all'이면 모델이 찾는 모든 클래스
        self.declare_parameter('confidence', 0.5)                 # 최소 신뢰도
        self.declare_parameter('min_box_ratio', 0.03)             # 화면 대비 박스 면적 비율 (가까이 있을 때만 정지)
        self.declare_parameter('clear_time', 1.0)                 # 공이 사라진 뒤 재출발까지 대기 [s]
        self.declare_parameter('show_window', True)               # 검출 화면 띄우기

        self.source = self.get_parameter('source').value
        classes = self.get_parameter('target_classes').value
        self.target_classes = {c.strip() for c in classes.split(',') if c.strip() and c.strip() != 'all'}
        self.conf = self.get_parameter('confidence').value
        self.min_box_ratio = self.get_parameter('min_box_ratio').value
        self.clear_time = self.get_parameter('clear_time').value
        self.show_window = self.get_parameter('show_window').value

        model_path = os.path.expanduser(self.get_parameter('model').value)
        if not os.path.exists(model_path):
            self.get_logger().error(f"모델 파일이 없습니다: {model_path}")
            raise FileNotFoundError(model_path)
        self.model = YOLO(model_path)
        self.get_logger().info(f"모델 로드: {model_path} / 클래스: {list(self.model.names.values())}")

        self.pub_stop = self.create_publisher(Bool, '/emergency_stop', 10)

        self.stopped = False
        self.last_seen = 0.0

        if self.source == 'webcam':
            self.cap = cv2.VideoCapture(self.get_parameter('webcam_index').value)
            if not self.cap.isOpened():
                self.get_logger().error("웹캠을 열 수 없습니다.")
            self.create_timer(0.1, self.webcam_loop)
        else:
            topic = self.get_parameter('image_topic').value
            self.create_subscription(Image, topic, self.image_callback, qos_profile_sensor_data)
            self.latest_frame = None
            self.create_timer(0.1, self.topic_loop)   # 최신 프레임만 10Hz로 처리 (밀림 방지)

        # 상태를 주기적으로 다시 보내서, 내비게이션 노드가 늦게 켜져도 상태를 받도록 함
        self.create_timer(0.5, self.publish_state)
        target = sorted(self.target_classes) if self.target_classes else '모든 클래스'
        self.get_logger().info(f"객체 검출 시작 (source={self.source}, 대상={target})")

    # ------------------------------------------------ 영상 입력
    def image_callback(self, msg):
        self.latest_frame = self.imgmsg_to_cv2(msg)

    def topic_loop(self):
        if self.latest_frame is not None:
            frame, self.latest_frame = self.latest_frame, None
            self.process(frame)

    def webcam_loop(self):
        ret, frame = self.cap.read()
        if ret:
            self.process(cv2.flip(frame, 1))

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

    # ------------------------------------------------ 검출
    def process(self, frame):
        h, w = frame.shape[:2]
        detected = False

        for result in self.model(frame, stream=True, conf=self.conf, verbose=False):
            for box in result.boxes:
                x1, y1, x2, y2 = map(int, box.xyxy[0])
                name = self.model.names[int(box.cls[0])]
                conf = float(box.conf[0])
                ratio = (x2 - x1) * (y2 - y1) / float(w * h)

                class_ok = (not self.target_classes) or (name in self.target_classes)
                is_target = class_ok and ratio >= self.min_box_ratio
                detected |= is_target

                color = (0, 0, 255) if is_target else (127, 0, 127)
                cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
                cv2.putText(frame, f"{name} {conf:.2f}", (x1, max(y1 - 10, 10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)

        now = time.monotonic()
        if detected:
            self.last_seen = now
            if not self.stopped:
                self.stopped = True
                self.get_logger().warn("공 감지 → 비상정지 신호 발행")
                self.publish_state()
        elif self.stopped and now - self.last_seen > self.clear_time:
            self.stopped = False
            self.get_logger().info("공 사라짐 → 비상정지 해제")
            self.publish_state()

        if self.show_window:
            label = "EMERGENCY STOP" if self.stopped else "DRIVING"
            cv2.putText(frame, label, (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.9,
                        (0, 0, 255) if self.stopped else (0, 200, 0), 2)
            cv2.imshow('object_detector', frame)
            cv2.waitKey(1)

    def publish_state(self):
        self.pub_stop.publish(Bool(data=self.stopped))

    def destroy_node(self):
        if self.source == 'webcam' and hasattr(self, 'cap'):
            self.cap.release()
        cv2.destroyAllWindows()
        super().destroy_node()


def main(args=None):
    rclpy.init(args=args)
    node = ObjectDetector()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        node.destroy_node()
        rclpy.try_shutdown()


if __name__ == '__main__':
    main()
