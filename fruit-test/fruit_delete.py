
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox
)

from main_fruit import DB_a


class FruitDeleteByName(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("과일 이름 삭제")
        self.resize(320, 150)

        # DB 연결
        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        layout = QVBoxLayout()

        layout.addWidget(QLabel("삭제할 과일을 선택하세요."))

        self.fruit_combo = QComboBox()
        layout.addWidget(self.fruit_combo)

        warning_label = QLabel("※ 삭제하면 이 과일의 구매/판매 기록도 전부 같이 삭제되며 되돌릴 수 없습니다.")
        warning_label.setStyleSheet("color: red;")
        warning_label.setWordWrap(True)
        layout.addWidget(warning_label)

        button_layout = QHBoxLayout()

        self.back_button = QPushButton("뒤로가기")
        self.delete_button = QPushButton("삭제")

        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        button_layout.addWidget(self.delete_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 이벤트 연결
        self.back_button.clicked.connect(self.close)
        self.delete_button.clicked.connect(self.delete_fruit)

        self.load_fruit()


    def load_fruit(self):

        try:

            fruits = self.db.fetch_items()

            self.fruit_combo.clear()

            for item_id, item_name, origin_name, quantity in fruits:
                self.fruit_combo.addItem(f"{item_name} ({origin_name})", item_id)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 목록을 불러오지 못했습니다.\n\n{e}"
            )


    def delete_fruit(self):

        item_id = self.fruit_combo.currentData()
        display_text = self.fruit_combo.currentText()

        if item_id is None:

            QMessageBox.warning(
                self,
                "오류",
                "삭제할 과일을 선택하세요."
            )

            return

        answer = QMessageBox.warning(
            self,
            "삭제 확인",
            f"{display_text}을(를) 완전히 삭제하시겠습니까?\n\n"
            f"이 과일의 구매/판매 기록이 전부 같이 삭제되며,\n"
            f"이 작업은 되돌릴 수 없습니다.",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:

            result = self.db.delete_items([item_id])

            if result is True:

                QMessageBox.information(
                    self,
                    "삭제 완료",
                    f"{display_text}이(가) 삭제되었습니다."
                )

                self.load_fruit()

            else:

                QMessageBox.warning(
                    self,
                    "삭제 실패",
                    f"삭제에 실패했습니다.\n\n{result}"
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"삭제 중 오류가 발생했습니다.\n\n{e}"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = FruitDeleteByName()
    window.show()

    sys.exit(app.exec_())
