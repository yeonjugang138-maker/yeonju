import sys

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox
from PyQt5.QtCore import QDate, Qt
from PyQt5.QtGui import QColor, QFont

from main_fruit import DB_a
from fruit_add import FruitAdd
from table_format import make_combo_searchable, get_combo_selected_data

# UI 파일 연결

form_class = uic.loadUiType("5. purchase.ui")[0]


class Purchase(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # DB 연결
        self.main_fruit = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        # 과일 목록 불러오기
        self.load_fruit()


        make_combo_searchable(self.fruit_name)


        self.quantity.setMaximum(1000)

        # 오늘 날짜
        self.dateEdit.setDate(QDate.currentDate())

        # 과일 선택 시 원산지 표시
        self.fruit_name.currentIndexChanged.connect(
            self.show_origin
        )

        # 구매 버튼
        self.purchase.clicked.connect(
            self.save_purchase
        )

        # add 버튼 → 과일 추가 창
        self.add.clicked.connect(
            self.open_fruit_add
        )


        self.add_2.clicked.connect(
            self.close
        )

    # --------------------------------
    # 과일 목록 불러오기

    def load_fruit(self):

        try:

            fruits = self.main_fruit.fetch_items()

            self.fruit_name.clear()

            for item_id, item_name, origin_name, stock in fruits:


                if stock == 0:
                    display_text = f"{item_name} (재고없음)"
                else:
                    display_text = item_name

                # 화면에는 과일 이름
                # 내부 데이터에는 item_id 저장
                self.fruit_name.addItem(
                    display_text,
                    item_id
                )

                if stock == 0:

                    index = self.fruit_name.count() - 1

                    bold_font = QFont()
                    bold_font.setBold(True)

                    self.fruit_name.setItemData(index, bold_font, Qt.FontRole)
                    self.fruit_name.setItemData(index, QColor("darkorange"), Qt.ForegroundRole)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 목록을 불러오지 못했습니다.\n\n{e}"
            )

            return

        # 첫 번째 과일의 원산지 표시
        self.show_origin()

    # --------------------------------
    # 선택한 과일의 원산지 표시
    # --------------------------------
    def show_origin(self):

        item_id = get_combo_selected_data(self.fruit_name)

        if item_id is None:
            self.textBrowser.clear()
            return


        origin_name = self.main_fruit.fetch_origin_by_item(
            item_id
        )


        self.textBrowser.setHtml(
            f"<table width='100%' height='100%'>"
            f"<tr><td align='center' valign='middle' style='font-size:14pt;'>"
            f"{origin_name}"
            f"</td></tr></table>"
        )

    # --------------------------------
    # 구매 저장
  
    def save_purchase(self):


        item_id = get_combo_selected_data(self.fruit_name)

        item_name = None

        if item_id is not None:
            for fid, name, origin_name, stock in self.main_fruit.fetch_items():
                if fid == item_id:
                    item_name = name
                    break

        # 수량
        quantity = self.quantity.value()

        # 날짜
        purchase_date = self.dateEdit.date().toString(
            "yyyy-MM-dd"
        )

        # 과일 선택 확인
        if item_id is None:

            QMessageBox.warning(
                self,
                "오류",
                "과일을 선택하세요."
            )

            return

        # 수량 확인
        if quantity <= 0:

            QMessageBox.warning(
                self,
                "오류",
                "구매 수량을 입력하세요."
            )

            return


        result = self.main_fruit.insert_purchase(
            item_id,
            quantity,
            purchase_date
        )

        if result is True:

            QMessageBox.information(
                self,
                "구매 완료",
                f"{item_name} {quantity}개 구매되었습니다."
            )


            self.quantity.setValue(0)
            self.load_fruit()

        else:

            QMessageBox.warning(
                self,
                "오류",
                f"구매 처리에 실패했습니다.\n\n{result}"
            )

    def open_fruit_add(self):

        self.fruit_add_window = FruitAdd()

        self.fruit_add_window.exec_()

        # 과일 추가 창을 닫으면 목록 다시 불러오기
        self.load_fruit()


# --------------------------------
# 실행

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = Purchase()
    window.show()

    sys.exit(app.exec_())
