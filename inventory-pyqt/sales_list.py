
import sys

from PyQt5.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QMessageBox,
    QAbstractItemView,
    QMenu
)

from PyQt5.QtCore import QTimer, Qt
from main_fruit import DB_a
from table_format import configure_table_weighted, enable_drag_scroll


class SalesList(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("판매 목록")
        self.resize(600, 420)

        # DB 연결
        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        layout = QVBoxLayout()

        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("과일 이름 / 원산지 / 판매일로 검색")

        self.search_button = QPushButton("검색")

        self.refresh_button = QPushButton("새로고침")

        search_layout.addWidget(self.search_edit)
        search_layout.addWidget(self.search_button)
        search_layout.addWidget(self.refresh_button)

        layout.addLayout(search_layout)

        # 표
        self.table = QTableWidget()
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        enable_drag_scroll(self.table)
        self.table.setAlternatingRowColors(True)


        self.table.setContextMenuPolicy(Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)

        layout.addWidget(self.table)

        self.setLayout(layout)


        self.search_button.clicked.connect(self.load_data)
        self.search_edit.returnPressed.connect(self.load_data)
        self.refresh_button.clicked.connect(self.load_data)


        QTimer.singleShot(0, self.load_data)


    def load_data(self):

        keyword = self.search_edit.text().strip()

        try:

            ledger = self.db.fetch_stock_ledger(keyword if keyword else None)

            rows = ledger["sale"]


            rows = sorted(rows, key=lambda r: (r[6], r[7]), reverse=True)

            slot_codes = self.db.fetch_fruit_slot_codes()

            headers = ["번호", "과일", "원산지코드", "원산지", "판매수량", "현재수량", "판매일"]

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            if not rows:
                self.table.clearContents()
                self.table.setRowCount(1)
                self.table.setItem(0, 0, QTableWidgetItem("-"))
                self.table.setItem(0, 1, QTableWidgetItem("판매 기록이 없습니다."))
                return

            self.table.setRowCount(len(rows))

            for r, (sales_id, item_id, item_name, origin_code, origin_name, qty, date, created_at, before, after) in enumerate(rows, start=1):

                display_code = slot_codes.get(item_id, origin_code)

                values = [r, item_name, display_code, origin_name, qty, after, str(date)]

                for c, value in enumerate(values):

                    cell = QTableWidgetItem(str(value))

                    if c == 0:

                        cell.setData(Qt.UserRole, sales_id)

                    self.table.setItem(r - 1, c, cell)

            self.table.resizeColumnsToContents()
            configure_table_weighted(self.table, [7, 20, 12, 16, 13, 13, 19])

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"판매 목록을 불러오지 못했습니다.\n\n{e}"
            )



    def show_context_menu(self, pos):

        row = self.table.rowAt(pos.y())

        if row < 0:
            return

        first_cell = self.table.item(row, 0)

        if first_cell is None:
            return

        sales_id = first_cell.data(Qt.UserRole)

        if sales_id is None:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("삭제")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))

        if action == delete_action:
            self.delete_sales(sales_id)


    def delete_sales(self, sales_id):

        answer = QMessageBox.question(
            self,
            "삭제 확인",
            "이 판매 기록을 삭제하시겠습니까?\n"
            "(팔렸던 수량만큼 전체 재고 수량에 다시 더해집니다)",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:

            result = self.db.delete_sales_record(sales_id)

            if result is True:

                QMessageBox.information(
                    self,
                    "삭제 완료",
                    "판매 기록이 삭제되었습니다."
                )

                self.load_data()

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

    window = SalesList()
    window.show()

    sys.exit(app.exec_())
