
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

from main__fruit import DB_b


class OriginDelete(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("원산지 삭제")
        self.resize(320, 150)

        # DB 연결
        self.db = DB_b(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        layout = QVBoxLayout()

        layout.addWidget(QLabel("삭제할 원산지를 선택하세요."))

        self.origin_combo = QComboBox()
        layout.addWidget(self.origin_combo)

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
        self.delete_button.clicked.connect(self.delete_origin)

        self.load_origin()



    def load_origin(self):

        try:

            origins = self.db.fetch_origin()

            self.origin_combo.clear()

            for origin_code, origin_name in origins:
                self.origin_combo.addItem(f"{origin_name} ({origin_code})", origin_code)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"원산지 목록을 불러오지 못했습니다.\n\n{e}"
            )


    def delete_origin(self):

        origin_code = self.origin_combo.currentData()
        display_text = self.origin_combo.currentText()

        if origin_code is None:

            QMessageBox.warning(
                self,
                "오류",
                "삭제할 원산지를 선택하세요."
            )

            return

        answer = QMessageBox.question(
            self,
            "삭제 확인",
            f"{display_text} 원산지를 삭제하시겠습니까?\n"
            f"(이 원산지를 쓰는 과일이 있으면 삭제가 거부됩니다)",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:

            result = self.db.delete_origin(origin_code)

            if result is True:

                QMessageBox.information(
                    self,
                    "삭제 완료",
                    f"{display_text} 원산지가 삭제되었습니다."
                )

                self.load_origin()

            else:

                QMessageBox.warning(
                    self,
                    "삭제 실패",
                    f"{result}"
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"삭제 중 오류가 발생했습니다.\n\n{e}"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = OriginDelete()
    window.show()

    sys.exit(app.exec_())
