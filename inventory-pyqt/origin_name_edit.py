import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox

from main__fruit import DB_b
from table_format import make_combo_searchable, get_combo_selected_data


form_class = uic.loadUiType("8. origin_name_edit.ui")[0]


class OriginNameEdit(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # DB 연결
        self.db = DB_b(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        # 원산지 이름 불러오기
        self.load_origin()


        make_combo_searchable(self.origin_name)

        # 원산지 선택
        self.origin_name.currentIndexChanged.connect(
            self.show_origin_code
        )

        # 저장
        self.save.clicked.connect(
            self.update_origin_name
        )


        self.search_del_2.clicked.connect(
            self.close
        )


    # 원산지 이름 목록
    def load_origin(self):

        try:

            origins = self.db.fetch_origin()

            self.origin_name.clear()


            for origin_code, origin_name in origins:

                self.origin_name.addItem(
                    origin_name
                )

                index = self.origin_name.count() - 1

                self.origin_name.setItemData(
                    index,
                    origin_code
                )

            self.show_origin_code()

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"원산지 목록을 불러오지 못했습니다.\n\n{e}"
            )


    # 선택한 원산지의 코드 표시
    def show_origin_code(self):

        origin_code = get_combo_selected_data(self.origin_name)

        if origin_code is None:
            self.textBrowser.clear()
            return

        self.textBrowser.setText(
            str(origin_code)
        )


    # 원산지 이름 변경
    def update_origin_name(self):


        origin_code = get_combo_selected_data(self.origin_name)
        old_name = self.origin_name.currentText() if origin_code is not None else ""

        # 새 원산지 이름
        new_name = self.fruit_name_adit.text().strip()


        if not old_name:

            QMessageBox.warning(
                self,
                "오류",
                "원산지를 선택하세요."
            )

            return


        if not new_name:

            QMessageBox.warning(
                self,
                "오류",
                "변경할 원산지 이름을 입력하세요."
            )

            return


        if old_name == new_name:

            QMessageBox.warning(
                self,
                "오류",
                "기존 이름과 같은 이름입니다."
            )

            return


        # 이름 변경
        result = self.db.update_origin_name(
            origin_code,
            new_name
        )


        if result:

            QMessageBox.information(
                self,
                "수정 완료",
                f"{old_name} → {new_name}\n\n원산지 이름이 변경되었습니다."
            )


            self.fruit_name_adit.clear()
            self.load_origin()

        else:

            QMessageBox.warning(
                self,
                "수정 실패",
                "원산지 이름 변경에 실패했습니다."
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = OriginNameEdit()
    window.show()

    sys.exit(app.exec_())
