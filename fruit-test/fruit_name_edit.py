import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QDialog, QApplication, QMessageBox

from main__fruit import DB_b
from table_format import make_combo_searchable, get_combo_selected_data


# UI 연결
form_class = uic.loadUiType("7. fruit_name_edit.ui")[0]


class FruitNameEdit(QDialog, form_class):

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

        # 과일 목록 불러오기
        self.load_fruit()

        # [추가] 검색(입력 필터링) 가능
        make_combo_searchable(self.fruit_name)

        # 저장 버튼
        self.save.clicked.connect(
            self.update_fruit_name
        )


        self.search_del_2.clicked.connect(
            self.close
        )


    # 과일 목록 불러오기
    def load_fruit(self):

        try:

            fruits = self.main__fruit.fetch_items()

            self.fruit_name.clear()

            for item_id, item_name, origin_name, stock in fruits:


                self.fruit_name.addItem(
                    item_name,
                    item_id
                )

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 목록을 불러오지 못했습니다.\n\n{e}"
            )


    # 과일 이름 수정
    def update_fruit_name(self):

        item_id = get_combo_selected_data(self.fruit_name)

        # 새 과일 이름
        new_name = self.fruit_name_adit.text().strip()


        # 과일 선택 확인
        if item_id is None:

            QMessageBox.warning(
                self,
                "오류",
                "수정할 과일을 선택하세요."
            )

            return


        # 새 이름 입력 확인
        if not new_name:

            QMessageBox.warning(
                self,
                "오류",
                "변경할 과일 이름을 입력하세요."
            )

            return


        # DB 수정
        result = self.main__fruit.update_item_name(
            item_id,
            new_name
        )


        if result:

            QMessageBox.information(
                self,
                "완료",
                "과일 이름이 수정되었습니다."
            )

            self.fruit_name_adit.clear()
            self.load_fruit()

        else:

            QMessageBox.warning(
                self,
                "오류",
                "과일 이름 수정에 실패했습니다."
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = FruitNameEdit()
    window.show()

    sys.exit(app.exec_())