
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
    QAbstractItemView
)
from PyQt5.QtGui import QColor

from PyQt5.QtCore import QTimer
from main_fruit import DB_a
from table_format import configure_table_weighted, enable_drag_scroll


class TransactionList(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("전체 거래내역 (구매+판매)")
        self.resize(700, 450)

        # DB 연결
        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        layout = QVBoxLayout()

        # 검색줄
        search_layout = QHBoxLayout()

        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("과일 이름 / 원산지 / 원산지코드 / 날짜로 검색")

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

        layout.addWidget(self.table)

        self.setLayout(layout)

        # 이벤트 연결
        self.search_button.clicked.connect(self.load_data)
        self.search_edit.returnPressed.connect(self.load_data)
        self.refresh_button.clicked.connect(self.load_data)

        QTimer.singleShot(0, self.load_data)


    def load_data(self):

        keyword = self.search_edit.text().strip()

        try:

            ledger = self.db.fetch_stock_ledger(keyword if keyword else None)


            slot_codes = self.db.fetch_fruit_slot_codes()

            combined = []

            for row in ledger["purchase"]:
                purchase_id, item_id, item_name, origin_code, origin_name, qty, date, created_at, before, after = row
                display_code = slot_codes.get(item_id, origin_code)
                combined.append(("구매", item_name, display_code, origin_name, f"+{qty}", after, date, created_at))

            for row in ledger["sale"]:
                sales_id, item_id, item_name, origin_code, origin_name, qty, date, created_at, before, after = row
                display_code = slot_codes.get(item_id, origin_code)
                combined.append(("판매", item_name, display_code, origin_name, f"-{qty}", after, date, created_at))

            combined.sort(key=lambda r: (r[6], r[7]), reverse=True)

            headers = ["번호", "구분", "과일", "원산지코드", "원산지", "수량", "현재수량", "날짜"]

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            if not combined:
                self.table.setRowCount(1)
                self.table.setItem(0, 0, QTableWidgetItem("-"))
                self.table.setItem(0, 1, QTableWidgetItem("거래 기록이 없습니다."))
                return

            self.table.setRowCount(len(combined))

            for r, (kind, item_name, origin_code, origin_name, qty_text, after, date, created_at) in enumerate(combined, start=1):

                values = [r, kind, item_name, origin_code, origin_name, qty_text, after, str(date)]

                for c, value in enumerate(values):

                    cell = QTableWidgetItem(str(value))


                    if c == 1:
                        if kind == "구매":
                            cell.setForeground(QColor("blue"))
                        else:
                            cell.setForeground(QColor("red"))

                    self.table.setItem(r - 1, c, cell)

            self.table.resizeColumnsToContents()
            configure_table_weighted(self.table, [6, 8, 18, 10, 14, 10, 12, 22])

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"거래내역을 불러오지 못했습니다.\n\n{e}"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = TransactionList()
    window.show()

    sys.exit(app.exec_())
