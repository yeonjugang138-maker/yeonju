
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
from table_format import configure_table_weighted, enable_drag_scroll, compute_batch_codes


class PurchaseList(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("구매 목록")
        self.resize(650, 420)

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
        self.search_edit.setPlaceholderText("과일 이름 / 원산지 / 구매일로 검색")

        self.search_button = QPushButton("검색")

        # [추가] 새로고침 버튼
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

        # 이벤트 연결
        self.search_button.clicked.connect(self.load_data)
        self.search_edit.returnPressed.connect(self.load_data)
        self.refresh_button.clicked.connect(self.load_data)


        QTimer.singleShot(0, self.load_data)


    def load_data(self):

        keyword = self.search_edit.text().strip()

        try:

            ledger = self.db.fetch_stock_ledger(keyword if keyword else None)

            rows = ledger["purchase"]


            rows = sorted(rows, key=lambda r: (r[6], r[7]), reverse=True)


            all_batches = self.db.fetch_all_batches_for_codes()
            coded = compute_batch_codes(all_batches)
            batch_codes = {c[3]: c[6] for c in coded}   # purchase_id -> code

            headers = ["번호", "과일", "원산지코드", "원산지", "입고수량", "현재수량", "입고일"]

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            if not rows:
                self.table.clearContents()
                self.table.setRowCount(1)
                self.table.setItem(0, 0, QTableWidgetItem("-"))
                self.table.setItem(0, 1, QTableWidgetItem("구매 기록이 없습니다."))
                return

            self.table.setRowCount(len(rows))

            for r, (purchase_id, item_id, item_name, origin_code, origin_name, qty, date, created_at, before, after) in enumerate(rows, start=1):

                display_code = batch_codes.get(purchase_id, origin_code)

                values = [r, item_name, display_code, origin_name, qty, after, str(date)]

                for c, value in enumerate(values):

                    cell = QTableWidgetItem(str(value))

                    if c == 0:
                        # [추가] purchase_id를 저장해서 우클릭 삭제에 사용
                        cell.setData(Qt.UserRole, purchase_id)

                    self.table.setItem(r - 1, c, cell)

            self.table.resizeColumnsToContents()
            configure_table_weighted(self.table, [7, 20, 12, 16, 13, 13, 19])

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"구매 목록을 불러오지 못했습니다.\n\n{e}"
            )


    def show_context_menu(self, pos):

        row = self.table.rowAt(pos.y())

        if row < 0:
            return

        first_cell = self.table.item(row, 0)

        if first_cell is None:
            return

        purchase_id = first_cell.data(Qt.UserRole)

        if purchase_id is None:
            return

        menu = QMenu(self)
        delete_action = menu.addAction("삭제")

        action = menu.exec_(self.table.viewport().mapToGlobal(pos))

        if action == delete_action:
            self.delete_purchase(purchase_id)


    def delete_purchase(self, purchase_id):

        answer = QMessageBox.question(
            self,
            "삭제 확인",
            "구매 기록을 삭제하시겠습니까?\n"
            "(재고가 남아있었다면 그만큼 전체 재고 수량에서도 함께 차감됩니다.\n"
            "삭제된 기록은 '이전 기록'에서 다시 볼 수 있습니다",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:


            result = self.db.delete_purchase_batches([purchase_id])

            if result is True:

                QMessageBox.information(
                    self,
                    "삭제 완료",
                    "구매 기록이 삭제되었습니다."
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

    window = PurchaseList()
    window.show()

    sys.exit(app.exec_())
