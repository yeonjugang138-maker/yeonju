
import sys
from datetime import date

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QMessageBox
)
from PyQt5.QtGui import QColor
from PyQt5.QtCore import Qt

from main_fruit import DB_a
from table_format import make_combo_searchable, get_combo_selected_data


# --------------------------------
# UI 파일 연결

form_class = uic.loadUiType("sales_fruit.ui")[0]


# --------------------------------
# 판매 창

class Sales(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        # --------------------------------
        # DB 연결

        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        # --------------------------------
        # 과일 목록 불러오기

        self.load_fruit()

        make_combo_searchable(self.fruit_lisk)



        self.quantuty.setMaximum(1000)

        # --------------------------------
        # 판매 버튼

        self.sales.clicked.connect(
            self.save_sales
        )

        # [추가] 뒤로가기 버튼 (sales_fruit.ui의 sales_2)
        self.sales_2.clicked.connect(
            self.close
        )


    # --------------------------------
    # 과일 목록 불러오기

    def load_fruit(self):

        try:

            fruits = self.db.fetch_items()

            self.fruit_lisk.clear()

            for item_id, item_name, origin_name, stock in fruits:


                if stock == 0:
                    display_text = f"{item_name} (품절)"
                else:
                    display_text = item_name


                self.fruit_lisk.addItem(
                    display_text,
                    item_id
                )

                if stock == 0:
                    index = self.fruit_lisk.count() - 1
                    self.fruit_lisk.setItemData(index, QColor("gray"), Qt.ForegroundRole)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 목록을 불러오지 못했습니다.\n\n{e}"
            )


    # --------------------------------
    # 판매

    def save_sales(self):

        # [수정] 콤보박스 표시 텍스트에 "(품절)"이 붙을 수 있게 되어서,
        # 텍스트 그대로를 과일 이름으로 쓰면 DB의 실제 이름과 안 맞게 됨.
        # item_id(currentData)로 정확히 조회하도록 변경.
        item_id = get_combo_selected_data(self.fruit_lisk)

        # 판매 수량
        quantity = self.quantuty.value()


        # --------------------------------
        # 과일 선택 확인

        if item_id is None:

            QMessageBox.warning(
                self,
                "판매 오류",
                "판매할 과일을 선택하세요."
            )

            return


        # --------------------------------
        # 판매 수량 확인

        if quantity <= 0:

            QMessageBox.warning(
                self,
                "판매 오류",
                "판매 수량을 입력하세요."
            )

            return


        # --------------------------------
        # 현재 재고 확인

        fruits = self.db.fetch_items()

        stock = None
        item_name = None

        for fid, name, origin_name, current_stock in fruits:

            if fid == item_id:

                stock = current_stock
                item_name = name
                break


        # 과일을 찾지 못한 경우
        if stock is None:

            QMessageBox.warning(
                self,
                "판매 오류",
                "선택한 과일을 찾을 수 없습니다."
            )

            return


        # --------------------------------
        # [추가] 품절(재고 0)인 경우 전용 안내

        if stock == 0:

            QMessageBox.warning(
                self,
                "판매 오류",
                f"{item_name}은(는) 품절된 상품입니다."
            )

            return


        # --------------------------------
        # 재고보다 많이 판매하는 경우

        if quantity > stock:

            QMessageBox.warning(
                self,
                "판매 오류",
                f"현재 재고가 {stock}개입니다.\n"
                f"{stock}개 이하로 판매할 수 있습니다."
            )

            return


        # --------------------------------
        # 오늘 날짜

        sales_date = date.today()


        result = self.db.insert_sales(
            item_id,
            quantity,
            sales_date
        )


        # --------------------------------
        # 판매 성공

        if result is True:

            QMessageBox.information(
                self,
                "판매 완료",
                f"{item_name} {quantity}개가 판매되었습니다."
            )

            self.quantuty.setValue(0)
            self.load_fruit()


        # --------------------------------
        # 판매 실패

        else:

            QMessageBox.warning(
                self,
                "판매 실패",
                f"판매 처리에 실패했습니다.\n\n{result}"
            )


# --------------------------------
# 프로그램 실행

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = Sales()
    window.show()

    sys.exit(app.exec_())

