import sys

from PyQt5 import uic
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMessageBox, QTableWidgetItem, QListWidgetItem, QComboBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from main_fruit import DB_a
from table_format import replace_with_table, build_table, pick_monospace_font, configure_table_weighted, enable_drag_scroll, compute_batch_codes


form_class = uic.loadUiType("6. del.ui")[0]


class FruitDelete(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self._orig_size = (self.width(), self.height())
        self._orig_geom = {
            "pushButton": self.pushButton.geometry(),
            "lineEdit": self.lineEdit.geometry(),
            "search_del": self.search_del.geometry(),
        }

        # DB 연결
        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        self.table = replace_with_table(self.list)

        if self.table is not None:
            self.table.setSelectionMode(self.table.MultiSelection)
            enable_drag_scroll(self.table)
        else:
            self.list.setSelectionMode(self.list.MultiSelection)
            self.list.setFont(pick_monospace_font())

        # 삭제 버튼
        self.pushButton.clicked.connect(
            self.delete_fruit
        )

        self.search_del.clicked.connect(
            self.search_fruit
        )

        # [추가] 검색 범위를 고를 수 있는 콤보박스 (전체 / 과일 이름만 / 원산지만)
        self.search_scope_combo = QComboBox(self)
        self.search_scope_combo.addItem("전체", "all")
        self.search_scope_combo.addItem("과일 이름만", "name")
        self.search_scope_combo.addItem("원산지만", "origin")
        self.search_scope_combo.show()

        self.search_del_2.clicked.connect(
            self.close
        )

        self.search_del_3.clicked.connect(
            self.refresh_all
        )

        # 처음 목록 불러오기
        self.load_fruit()

        # 창을 처음 띄운 크기에 맞춰 한 번 배치
        self._reflow()


    # --------------------------------
    # [추가] 창 크기가 바뀔 때마다 표/하단 버튼들을 다시 배치한다.

    def resizeEvent(self, event):

        super().resizeEvent(event)

        self._reflow()


    def _reflow(self):

        if not hasattr(self, "_orig_geom"):
            return

        margin = 10
        orig_w, orig_h = self._orig_size

        w = self.width()
        h = self.height()


        bottom_gap = orig_h - self._orig_geom["lineEdit"].y()
        bottom_y = max(h - bottom_gap, 50)

        target = self.table if self.table is not None else self.list
        table_y = 40
        table_h = bottom_y - table_y - 8
        target.setGeometry(margin, table_y, max(w - margin * 2, 100), max(table_h, 60))

 
        for name in ("pushButton", "search_del"):

            widget = getattr(self, name)
            og = self._orig_geom[name]
            right_gap = orig_w - (og.x() + og.width())
            new_x = w - right_gap - og.width()
            widget.move(new_x, bottom_y)

        combo_width = 90
        combo_x = self.search_del.x() - combo_width - 6
        self.search_scope_combo.setGeometry(
            combo_x, bottom_y, combo_width, self._orig_geom["lineEdit"].height()
        )

        le_og = self._orig_geom["lineEdit"]
        new_width = max(combo_x - le_og.x() - margin, 60)
        self.lineEdit.setGeometry(le_og.x(), bottom_y, new_width, le_og.height())


    def load_fruit(self, keyword=None, scope="all"):

        try:

            batches = self.db.fetch_batches(keyword, scope=scope)

            headers = ["코드", "과일", "입고일", "수량"]

            if not batches:

                self._fill_empty(headers, "표시할 입고 배치가 없습니다.")

                return


            coded = compute_batch_codes(batches)

            rows = []
            row_meta = []   # (purchase_id, remaining) - rows와 순서를 맞춰서 저장

            for item_id, item_name, origin_code, purchase_id, purchase_date, remaining, code, is_depleted in coded:

                rows.append([code, item_name, str(purchase_date), str(remaining)])
                row_meta.append((purchase_id, remaining))

            self._fill_table(headers, rows, row_meta)

        except Exception as e:

            QMessageBox.critical(
                self,
                "오류",
                f"목록을 불러오는 중 오류가 발생했습니다.\n\n{e}"
            )


    # --------------------------------
    # 표(또는 예전 리스트)에 데이터 채우기

    def _fill_table(self, headers, rows, row_meta):

        if self.table is not None:

            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(len(rows))

            for r, row in enumerate(rows):

                purchase_id, remaining = row_meta[r]

                for c, value in enumerate(row):

                    cell = QTableWidgetItem(str(value))

                    if c == 0:
                        # purchase_id / 남은 수량을 첫 칸에 저장해서 삭제할 때 사용
                        cell.setData(Qt.UserRole, purchase_id)
                        cell.setData(Qt.UserRole + 1, remaining)

                    if remaining == 0:
                        cell.setForeground(QColor("gray"))

                    self.table.setItem(r, c, cell)

            self.table.resizeColumnsToContents()
            configure_table_weighted(self.table, [18, 34, 30, 18])

        else:

            # 예전 방식 (QListWidget, 표 교체가 안 된 경우의 대비책)
            self.list.clear()

            header_line, row_lines = build_table(headers, rows)

            header_item = QListWidgetItem(header_line)
            bold_font = header_item.font()
            bold_font.setBold(True)
            header_item.setFont(bold_font)
            header_item.setFlags(header_item.flags() & ~Qt.ItemIsSelectable)
            self.list.addItem(header_item)

            for line, (purchase_id, remaining) in zip(row_lines, row_meta):

                row_item = QListWidgetItem(line)
                row_item.setData(Qt.UserRole, purchase_id)
                row_item.setData(Qt.UserRole + 1, remaining)

                if remaining == 0:
                    row_item.setForeground(QColor("gray"))

                self.list.addItem(row_item)


    def _fill_empty(self, headers, message):

        if self.table is not None:
            self.table.setColumnCount(len(headers))
            self.table.setHorizontalHeaderLabels(headers)
            self.table.setRowCount(1)
            self.table.setItem(0, 0, QTableWidgetItem(message))
        else:
            self.list.clear()
            self.list.addItem(message)


    # --------------------------------
    # 검색

    def search_fruit(self):


        search_text = self.lineEdit.text().strip()

        scope = self.search_scope_combo.currentData()

        self.load_fruit(search_text if search_text else None, scope=scope)


    # --------------------------------
    # [추가] 새로고침 - 검색어를 지우고 전체 배치 목록을 다시 불러온다.

    def refresh_all(self):

        self.lineEdit.clear()
        self.load_fruit()


    # --------------------------------
    # 현재 선택된 행들의 (purchase_id, remaining) 목록을 가져온다
    # --------------------------------
    def _get_selected(self):

        result = []

        if self.table is not None:

            selected_rows = sorted(set(item.row() for item in self.table.selectedItems()))

            for row in selected_rows:

                first_cell = self.table.item(row, 0)

                if first_cell is None:
                    continue

                purchase_id = first_cell.data(Qt.UserRole)
                remaining = first_cell.data(Qt.UserRole + 1)

                if purchase_id is None:
                    continue

                result.append((purchase_id, remaining))

        else:

            for item in self.list.selectedItems():

                purchase_id = item.data(Qt.UserRole)
                remaining = item.data(Qt.UserRole + 1)

                if purchase_id is None:
                    continue

                result.append((purchase_id, remaining))

        return result


    # --------------------------------
    # 삭제
    # --------------------------------
    def delete_fruit(self):

        selected = self._get_selected()

        if not selected:

            QMessageBox.warning(
                self,
                "삭제",
                "삭제할 배치를 선택하세요."
            )

            return


        purchase_ids = [purchase_id for purchase_id, remaining in selected]
        has_remaining = any(remaining for purchase_id, remaining in selected)
        remaining_total = sum(remaining or 0 for purchase_id, remaining in selected)



        if has_remaining:

            answer = QMessageBox.warning(
                self,
                "삭제 확인",
                f"선택한 항목 중 아직 재고가 남아있는 배치가 있습니다 "
                f"(남은 수량 합계 {remaining_total}개).\n"
                f"삭제하면 이 재고 기록도 함께 사라지고, 전체 재고 수량에서도 "
                f"{remaining_total}개가 차감됩니다.\n\n"
                f"정말 삭제하시겠습니까?",
                QMessageBox.Yes | QMessageBox.No
            )

        else:

            answer = QMessageBox.question(
                self,
                "삭제 확인",
                f"품절된 배치 {len(purchase_ids)}건을 삭제하시겠습니까?\n"
                f"(과일 종류 자체는 삭제되지 않습니다)",
                QMessageBox.Yes | QMessageBox.No
            )

        if answer == QMessageBox.No:
            return


        # DB에서 삭제
        try:

            result = self.db.delete_purchase_batches(purchase_ids)

            if result is True:

                QMessageBox.information(
                    self,
                    "삭제 완료",
                    "선택한 배치가 삭제되었습니다."
                )

                # 목록 새로고침
                self.load_fruit()

            else:

                QMessageBox.warning(
                    self,
                    "삭제 실패",
                    f"배치 삭제에 실패했습니다.\n\n{result}"
                )

        except Exception as e:

            QMessageBox.critical(
                self,
                "삭제 오류",
                f"삭제 중 오류가 발생했습니다.\n\n{e}"
            )


# --------------------------------
# 실행
# --------------------------------

if __name__ == "__main__":

    app = QApplication(sys.argv)

    window = FruitDelete()
    window.show()

    sys.exit(app.exec_())
