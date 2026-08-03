
import sys
import importlib

from PyQt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QPushButton,
    QMessageBox
)

from fruit_add import FruitAdd
from origin_add import OriginAdd

from fruit_name_edit import FruitNameEdit
from origin_name_edit import OriginNameEdit
from origin_code_edit import OriginCodeEdit

from del_fruit import FruitDelete
from origin_delete import OriginDelete
from fruit_delete import FruitDeleteByName
from purchase import Purchase
from sales_fruit import Sales
from purchase_list import PurchaseList
from sales_list import SalesList
from transaction_list import TransactionList
from deleted_records import DeletedRecords


class EditWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("수정")
        self.setFixedSize(250, 270)

        layout = QVBoxLayout()


        self.fruit_add_button = QPushButton("과일 추가")
        self.origin_add_button = QPushButton("원산지 추가")

        # 과일 이름 수정
        self.fruit_name_button = QPushButton("과일 이름 수정")

        # 원산지 이름 수정
        self.origin_name_button = QPushButton("원산지 이름 수정")

        # 원산지 코드 수정
        self.origin_code_button = QPushButton("원산지 코드 수정")

        layout.addWidget(self.fruit_add_button)
        layout.addWidget(self.origin_add_button)
        layout.addWidget(self.fruit_name_button)
        layout.addWidget(self.origin_name_button)
        layout.addWidget(self.origin_code_button)

        self.setLayout(layout)

        # 버튼 연결
        self.fruit_add_button.clicked.connect(self.open_fruit_add)
        self.origin_add_button.clicked.connect(self.open_origin_add)
        self.fruit_name_button.clicked.connect(self.open_fruit_name_edit)
        self.origin_name_button.clicked.connect(self.open_origin_name_edit)
        self.origin_code_button.clicked.connect(self.open_origin_code_edit)


    # --------------------------------------
    # [추가] 과일 추가

    def open_fruit_add(self):

        self.fruit_add_window = FruitAdd()

        self.fruit_add_window.exec_()


    # --------------------------------------
    # [추가] 원산지 추가

    def open_origin_add(self):

        self.origin_add_window = OriginAdd()

        self.origin_add_window.exec_()


    # --------------------------------------
    # 과일 이름 수정

    def open_fruit_name_edit(self):

        self.fruit_edit_window = FruitNameEdit()

        self.fruit_edit_window.exec_()


    # --------------------------------------
    # 원산지 이름 수정

    def open_origin_name_edit(self):

        self.origin_name_edit_window = OriginNameEdit()

        self.origin_name_edit_window.exec_()


    # --------------------------------------
    # 원산지 코드 수정

    def open_origin_code_edit(self):

        self.origin_code_edit_window = OriginCodeEdit()

        self.origin_code_edit_window.exec_()


# ==========================================
# [추가] 삭제 선택 창 (원산지 삭제 / 과일 이름 삭제 / 목록 삭제)

class DeleteWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("삭제")
        self.setFixedSize(250, 150)

        layout = QVBoxLayout()

        self.origin_delete_button = QPushButton("원산지 삭제")
        self.fruit_delete_button = QPushButton("과일 이름 삭제")
        self.batch_delete_button = QPushButton("목록 삭제")

        layout.addWidget(self.origin_delete_button)
        layout.addWidget(self.fruit_delete_button)
        layout.addWidget(self.batch_delete_button)

        self.setLayout(layout)

        self.origin_delete_button.clicked.connect(self.open_origin_delete)
        self.fruit_delete_button.clicked.connect(self.open_fruit_delete)
        self.batch_delete_button.clicked.connect(self.open_batch_delete)


    # 원산지 삭제 - 그 원산지를 쓰는 과일이 있으면 DB가 막아줌
    def open_origin_delete(self):

        self.origin_delete_window = OriginDelete()
        self.origin_delete_window.exec_()


    # 과일 이름 삭제 - 과일 종류 자체(구매/판매 기록까지 전부) 삭제
    def open_fruit_delete(self):

        self.fruit_delete_window = FruitDeleteByName()
        self.fruit_delete_window.exec_()


    # 목록 삭제 - 입고 배치만 소프트 삭제 (기존 del_fruit.py)
    def open_batch_delete(self):

        self.batch_delete_window = FruitDelete()
        self.batch_delete_window.exec_()


# ==========================================
# 거래 선택 창 (구매 / 판매)

class TradeWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("거래")
        self.setFixedSize(250, 120)

        layout = QVBoxLayout()

        self.purchase_button = QPushButton("구매")
        self.sales_button = QPushButton("판매")

        layout.addWidget(self.purchase_button)
        layout.addWidget(self.sales_button)

        self.setLayout(layout)

        self.purchase_button.clicked.connect(self.open_purchase)
        self.sales_button.clicked.connect(self.open_sales)


    def open_purchase(self):

        self.purchase_window = Purchase()
        self.purchase_window.exec_()


    def open_sales(self):

        self.sales_window = Sales()
        self.sales_window.exec_()


# ==========================================
# 이력 선택 창 (구매 목록 / 판매 목록 / 전체 거래내역 / 이전 기록)

class HistoryWindow(QWidget):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("이력")
        self.setFixedSize(250, 190)

        layout = QVBoxLayout()

        self.purchase_list_button = QPushButton("구매 목록")
        self.sales_list_button = QPushButton("판매 목록")
        self.transaction_list_button = QPushButton("전체 거래내역")
        self.deleted_records_button = QPushButton("이전 기록")

        layout.addWidget(self.purchase_list_button)
        layout.addWidget(self.sales_list_button)
        layout.addWidget(self.transaction_list_button)
        layout.addWidget(self.deleted_records_button)

        self.setLayout(layout)

        self.purchase_list_button.clicked.connect(self.open_purchase_list)
        self.sales_list_button.clicked.connect(self.open_sales_list)
        self.transaction_list_button.clicked.connect(self.open_transaction_list)
        self.deleted_records_button.clicked.connect(self.open_deleted_records)


    def open_purchase_list(self):

        self.purchase_list_window = PurchaseList()
        self.purchase_list_window.show()


    def open_sales_list(self):

        self.sales_list_window = SalesList()
        self.sales_list_window.show()


    def open_transaction_list(self):

        self.transaction_list_window = TransactionList()
        self.transaction_list_window.show()


    def open_deleted_records(self):

        self.deleted_records_window = DeletedRecords()
        self.deleted_records_window.show()


# ==========================================
# 메인 설정 창

class Window(QMainWindow):

    def __init__(self):

        super().__init__()

        self.setWindowTitle("설정")
        self.setFixedSize(250, 170)

        window = QWidget()

        layout = QVBoxLayout()


        self.delete_button = QPushButton("삭제")


        self.edit_button = QPushButton("수정")


        self.history_button = QPushButton("이력")

        # 버튼 배치
        layout.addWidget(self.delete_button)
        layout.addWidget(self.edit_button)
        layout.addWidget(self.history_button)

        window.setLayout(layout)

        self.setCentralWidget(window)

        # ----------------------------------
        # 버튼 연결

        self.delete_button.clicked.connect(
            self.open_delete
        )

        self.edit_button.clicked.connect(
            self.open_edit
        )

        self.history_button.clicked.connect(
            self.open_history
        )


    # ======================================
    # 삭제 선택 창 (원산지 삭제 / 과일 이름 삭제 / 목록 삭제)


    def open_delete(self):

        self.delete_window = DeleteWindow()
        self.delete_window.show()


    # ======================================
    # 수정 선택 창 (추가 + 과일이름/원산지이름/원산지코드 수정)

    def open_edit(self):

        self.edit_window = EditWindow()
        self.edit_window.show()


    # ======================================
    # 이력 선택 창

    def open_history(self):

        self.history_window = HistoryWindow()
        self.history_window.show()


# ==========================================
# 프로그램 실행

if __name__ == "__main__":

    from table_format import install_exception_hook

    app = QApplication(sys.argv)

    install_exception_hook()

    myWindow = Window()

    myWindow.show()

    sys.exit(app.exec_())
