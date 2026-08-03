
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QLineEdit,
    QPushButton,
    QMessageBox
)

from main__fruit import DB_b
from table_format import make_combo_searchable, get_combo_selected_data


class OriginCodeEdit(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("원산지 코드 수정")
        self.resize(360, 200)

        # DB 연결
        self.db = DB_b(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        layout = QVBoxLayout()

        layout.addWidget(QLabel("수정할 원산지를 선택하세요."))

        self.origin_combo = QComboBox()
        layout.addWidget(self.origin_combo)


        self.current_code_label = QLabel("현재 코드: -")
        layout.addWidget(self.current_code_label)

        layout.addWidget(QLabel("새 원산지 코드를 입력하세요."))

        self.new_code_edit = QLineEdit()
        layout.addWidget(self.new_code_edit)


        self.preview_label = QLabel("")
        self.preview_label.setStyleSheet("color: gray;")
        layout.addWidget(self.preview_label)

        button_layout = QHBoxLayout()

        self.back_button = QPushButton("뒤로가기")
        self.save_button = QPushButton("저장")

        button_layout.addWidget(self.back_button)
        button_layout.addStretch()
        button_layout.addWidget(self.save_button)

        layout.addLayout(button_layout)

        self.setLayout(layout)

        # 이벤트 연결
        self.origin_combo.currentIndexChanged.connect(self.show_current_code)
        self.new_code_edit.textChanged.connect(self.update_preview)
        self.back_button.clicked.connect(self.close)
        self.save_button.clicked.connect(self.update_origin_code)

        self.load_origin()


        make_combo_searchable(self.origin_combo)



    def update_preview(self):

        typed = self.new_code_edit.text().strip().lower()

        if not typed:
            self.preview_label.setText("")
            return

        self.preview_label.setText(f"→ 저장될 코드: {typed}")



    def load_origin(self):

        try:

            origins = self.db.fetch_origin()

            self.origin_combo.clear()

            for origin_code, origin_name in origins:
                self.origin_combo.addItem(origin_name, origin_code)

            self.show_current_code()

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"원산지 목록을 불러오지 못했습니다.\n\n{e}"
            )



    def show_current_code(self):

        current_code = get_combo_selected_data(self.origin_combo)

        if current_code is None:
            self.current_code_label.setText("현재 코드: -")
        else:
            self.current_code_label.setText(f"현재 코드: {current_code}")

        self.new_code_edit.clear()


    # 원산지 코드 수정

    def update_origin_code(self):

        old_code = get_combo_selected_data(self.origin_combo)
        new_code = self.new_code_edit.text().strip().lower()

        if old_code is None:

            QMessageBox.warning(
                self,
                "오류",
                "목록에 있는 원산지를 선택하세요."
            )

            return

        if not new_code:

            QMessageBox.warning(
                self,
                "오류",
                "새 원산지 코드를 입력하세요."
            )

            return

        if new_code == old_code:

            QMessageBox.warning(
                self,
                "오류",
                "기존 코드와 같습니다."
            )

            return

        result = self.db.update_origin_code(old_code, new_code)

        if result is True:

            QMessageBox.information(
                self,
                "수정 완료",
                f"{old_code} → {new_code}\n\n원산지 코드가 변경되었습니다.\n"
            )

            self.load_origin()

        else:

            QMessageBox.warning(
                self,
                "수정 실패",
                f"원산지 코드 수정에 실패했습니다.\n\n{result}"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = OriginCodeEdit()
    window.show()

    sys.exit(app.exec_())
