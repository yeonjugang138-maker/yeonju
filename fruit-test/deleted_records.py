
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
from PyQt5.QtCore import Qt, QTimer

from main_fruit import DB_a
from table_format import configure_table_weighted, enable_drag_scroll


class DeletedRecords(QDialog):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("이전 기록")
        self.resize(1100, 500)

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
        self.search_edit.setPlaceholderText("과일 이름 / 원산지 / 원산지코드 / 입고일로 검색")

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
        self.table.setSelectionMode(QAbstractItemView.MultiSelection)
        self.table.setAlternatingRowColors(True)
        enable_drag_scroll(self.table)

        layout.addWidget(self.table)

        # [추가] 되돌리기 / 영구 삭제 버튼
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()

        self.restore_button = QPushButton("되돌리기")
        self.permanent_delete_button = QPushButton("영구 삭제")

        bottom_layout.addWidget(self.restore_button)
        bottom_layout.addWidget(self.permanent_delete_button)

        layout.addLayout(bottom_layout)

        self.setLayout(layout)

        # 이벤트 연결
        self.search_button.clicked.connect(self.load_data)
        self.search_edit.returnPressed.connect(self.load_data)
        self.refresh_button.clicked.connect(self.load_data)
        self.restore_button.clicked.connect(self.restore_selected)
        self.permanent_delete_button.clicked.connect(self.permanent_delete)


        QTimer.singleShot(0, self.load_data)


    def load_data(self):

        keyword = self.search_edit.text().strip()

        try:

            rows = self.db.fetch_deleted_records(keyword if keyword else None)


            headers = ["번호", "과일", "원산지코드", "원산지", "입고수량", "당시수량", "입고일", "삭제일시"]


            self.table.clearContents()

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)

            if not rows:
                self.table.setRowCount(1)
                self.table.setItem(0, 0, QTableWidgetItem("-"))
                self.table.setItem(0, 1, QTableWidgetItem("삭제된 기록이 없습니다."))
                return

            self.table.setRowCount(len(rows))

            for r, (purchase_id, item_name, origin_code, origin_name, pur_quantity, remaining_quantity, purchase_date, deleted_at) in enumerate(rows, start=1):

                values = [r, item_name, origin_code, origin_name, pur_quantity, remaining_quantity, str(purchase_date), str(deleted_at)]

                for c, value in enumerate(values):

                    cell = QTableWidgetItem(str(value))

                    if c == 0:
                        # purchase_id를 첫 칸에 저장해서 영구 삭제할 때 사용
                        cell.setData(Qt.UserRole, purchase_id)

                    self.table.setItem(r - 1, c, cell)


            configure_table_weighted(self.table, [5, 14, 10, 12, 10, 10, 15, 24])

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"이전 기록을 불러오지 못했습니다.\n\n{e}"
            )


    # --------------------------------

    def restore_selected(self):

        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))

        purchase_ids = []

        for row in selected_rows:

            first_cell = self.table.item(row, 0)

            if first_cell is None:
                continue

            purchase_id = first_cell.data(Qt.UserRole)

            if purchase_id is not None:
                purchase_ids.append(purchase_id)

        if not purchase_ids:

            QMessageBox.warning(
                self,
                "되돌리기",
                "되돌릴 항목을 선택하세요."
            )

            return

        answer = QMessageBox.question(
            self,
            "되돌리기 확인",
            f"선택한 {len(purchase_ids)}건을 다시 활성 상태로 되돌리시겠습니까?\n"
            f"(삭제 당시 남아있던 수량만큼 전체 재고에도 다시 더해집니다)",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:

            result = self.db.restore_purchase_batches(purchase_ids)

            if result is True:

                QMessageBox.information(
                    self,
                    "되돌리기 완료",
                    "선택한 기록이 복원되었습니다."
                )

                self.load_data()

            else:

                QMessageBox.warning(
                    self,
                    "되돌리기 실패",
                    f"되돌리기에 실패했습니다.\n\n{result}"
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"되돌리기 중 오류가 발생했습니다.\n\n{e}"
            )


    # --------------------------------
    #  영구 삭제 - 선택한 기록을 DB에서 완전히 지운다

    def permanent_delete(self):

        selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))

        purchase_ids = []

        for row in selected_rows:

            first_cell = self.table.item(row, 0)

            if first_cell is None:
                continue

            purchase_id = first_cell.data(Qt.UserRole)

            if purchase_id is not None:
                purchase_ids.append(purchase_id)

        if not purchase_ids:

            QMessageBox.warning(
                self,
                "영구 삭제",
                "영구 삭제할 항목을 선택하세요."
            )

            return

        answer = QMessageBox.warning(
            self,
            "영구 삭제 확인",
            f"선택한 {len(purchase_ids)}건을 DB에서 완전히 삭제합니다.\n"
            f"이 작업은 되돌릴 수 없습니다.\n\n"
            f"정말 영구 삭제하시겠습니까?",
            QMessageBox.Yes | QMessageBox.No
        )

        if answer == QMessageBox.No:
            return

        try:

            result = self.db.permanently_delete_batches(purchase_ids)

            if result is True:

                QMessageBox.information(
                    self,
                    "영구 삭제 완료",
                    "선택한 기록이 완전히 삭제되었습니다."
                )

                self.load_data()

            else:

                QMessageBox.warning(
                    self,
                    "영구 삭제 실패",
                    f"영구 삭제에 실패했습니다.\n\n{result}"
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"영구 삭제 중 오류가 발생했습니다.\n\n{e}"
            )


if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = DeletedRecords()
    window.show()

    sys.exit(app.exec_())
