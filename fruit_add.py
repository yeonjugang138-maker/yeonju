from PyQt5.QtWidgets import QDialog, QMessageBox, QCompleter
from PyQt5.QtCore import Qt
from PyQt5 import uic

from main__fruit import DB_b
from table_format import make_combo_searchable, get_combo_selected_data



form_class = uic.loadUiType("4. fruit_add.ui")[0]


class FruitAdd(QDialog, form_class):

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


        # 원산지 콤보박스 출력
        self.load_origin()

        # 검색(필터링)할 수 있게 한다.
        self.comboBox.setEditable(True)
        self.comboBox.setInsertPolicy(self.comboBox.NoInsert)
        completer = QCompleter(self.comboBox.model(), self.comboBox)
        completer.setCaseSensitivity(Qt.CaseInsensitive)
        completer.setFilterMode(Qt.MatchContains)
        self.comboBox.setCompleter(completer)


        # 저장 버튼
        self.save.clicked.connect(
            self.save_fruit
        )

        self.pushButton.clicked.connect(
            self.close
        )



    # 원산지 불러오기
    def load_origin(self):

        try:

            origins = self.main__fruit.fetch_origin()

            for code, name in origins:

                self.comboBox.addItem(
                    name,   # 화면 표시
                    code    # 실제 저장값
                )

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"원산지 목록을 불러오지 못했습니다.\n\n{e}"
            )



    # 저장

    def save_fruit(self):

        item_name = self.fruit_name.text().strip()


        # 선택된 원산지 코드 (목록에 실제로 있는 걸 선택했을 때만 값이 나옴)
        origin_code = get_combo_selected_data(self.comboBox)


        if item_name == "":
            QMessageBox.warning(
                self,
                "오류",
                "과일 이름을 입력하세요"
            )
            return

        if origin_code is None:
            QMessageBox.warning(
                self,
                "오류",
                "목록에 있는 원산지를 선택하세요.\n"
                "(목록에 없는 글자를 입력하신 것 같습니다)"
            )
            return

        # 중복 확인 (같은 이름 + 같은 원산지)
        try:
            existing = self.main__fruit.fetch_item_by_name_origin(item_name, origin_code)
        except Exception as e:
            QMessageBox.warning(
                self,
                "오류",
                f"중복 확인 중 오류가 발생했습니다.\n\n{e}"
            )
            return

        if existing:
            QMessageBox.warning(
                self,
                "중복",
                "이미 추가된 과일입니다.\n"
                "(같은 과일 이름 + 같은 원산지 조합은 다시 추가할 수 없습니다.\n"
                "과일 이름이나 원산지 중 하나는 달라야 합니다)"
            )
            return


        result = self.main__fruit.insert_item(
            item_name,
            origin_code
        )


        if result:

            QMessageBox.information(
                self,
                "완료",
                "과일 추가 완료"
            )

            self.fruit_name.clear()
            self.fruit_name.setFocus()

        else:

            QMessageBox.warning(
                self,
                "실패",
                "저장 실패"
            )
