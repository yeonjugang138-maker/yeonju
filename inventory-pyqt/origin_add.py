
import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from main__fruit import DB_b

# UI 파일 연결
form_class = uic.loadUiType("9. origin_add.ui")[0]


class OriginAdd(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # DB 연결
        self.main__fruit = DB_b(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        # 저장 버튼
        self.save.clicked.connect(
            self.save_origin
        )

        # [추가] 뒤로가기 버튼 (9. origin_add.ui의 save_2)
        self.save_2.clicked.connect(
            self.close
        )


    # 원산지 추가

    def save_origin(self):

        # 입력값 가져오기 (lineEdit = 원산지 이름, lineEdit_2 = 원산지 코드)
        origin_name = self.lineEdit.text().strip()
        origin_code = self.lineEdit_2.text().strip().lower()


        # 원산지 이름 입력 확인
        if not origin_name:

            QMessageBox.warning(
                self,
                "오류",
                "원산지 이름을 입력하세요."
            )

            return


        # 원산지 코드 입력 확인
        if not origin_code:

            QMessageBox.warning(
                self,
                "오류",
                "원산지 코드를 입력하세요."
            )

            return



        try:
            existing = self.main__fruit.fetch_origin_by_code(origin_code)
        except Exception as e:
            QMessageBox.warning(
                self,
                "오류",
                f"중복 확인 중 오류가 발생했습니다.\n\n{e}"
            )
            return

        if existing:

            existing_code, existing_name = existing

            QMessageBox.warning(
                self,
                "중복",
                f"이미 사용 중인 원산지 코드입니다.\n"
                f"({existing_code} = {existing_name})\n\n"
                f"다른 코드를 입력해주세요."
            )

            return


        # DB에 저장
        result = self.main__fruit.insert_origin(
            origin_name,
            origin_code
        )


        if result:

            QMessageBox.information(
                self,
                "추가 완료",
                f"{origin_name} ({origin_code}) 원산지가 추가되었습니다."
            )

            # 입력창 비우기
            self.lineEdit.clear()
            self.lineEdit_2.clear()

        else:

            QMessageBox.warning(
                self,
                "오류",
                "원산지 추가에 실패했습니다. (이미 사용 중인 코드입니다.)"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = OriginAdd()
    window.show()

    sys.exit(app.exec_())
