import os
import sys
from pathlib import Path

qt_platforms = (
    Path(sys.executable).resolve().parent.parent
    / "Lib" / "site-packages" / "PyQt5" / "Qt5" / "plugins" / "platforms"
)
os.environ.setdefault("QT_QPA_PLATFORM_PLUGIN_PATH", str(qt_platforms))

from PyQt5 import uic
from PyQt5.QtWidgets import QApplication, QDialog, QMessageBox, QTableWidgetItem, QLabel
from PyQt5.QtGui import QColor, QStandardItemModel, QStandardItem
from PyQt5.QtCore import Qt, QTimer

from main_fruit import DB_a
from table_format import (
    replace_with_table, pick_monospace_font, configure_table_resize,
    configure_table_weighted, enable_drag_scroll, compute_batch_codes
)


# --------------------------------
# UI 연결
form_class = uic.loadUiType("fruit_list.ui")[0]


# --------------------------------
# 메인 화면
class MainList(QDialog, form_class):

    def __init__(self):
        super().__init__()

        self.setupUi(self)

        self._orig_size = (self.width(), self.height())
        self._orig_geom = {
            "search_list": self.search_list.geometry(),
            "pushButton_2": self.pushButton_2.geometry(),
            "pushButton_3": self.pushButton_3.geometry(),
            "lineEdit": self.lineEdit.geometry(),
        }

        # DB 연결
        self.db = DB_a(
            host="localhost",
            user="root",
            password="8520",
            database="fruit",
            charset="utf8"
        )

        self.table = replace_with_table(self.list_main)

        if self.table is None:

            self.model = QStandardItemModel()
            self.list_main.setModel(self.model)
            self.list_main.setFont(pick_monospace_font())
            self.list_main.clicked.connect(self.on_row_clicked_fallback)
        else:

            self.table.cellClicked.connect(self.on_row_clicked)

            enable_drag_scroll(self.table)

        self.total_label = QLabel(self)
        self.total_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        self.total_label.setStyleSheet("font-weight: bold; padding-right: 6px;")
        self.total_label.hide()

        self._mode = "summary"
        self._current_items = []

        # 검색 버튼
        self.search_list.clicked.connect(
            self.search_fruit
        )

        self.search_list_3.clicked.connect(self.go_back_to_summary)

        self.pushButton_3.setText("거래")
        self.pushButton_3.clicked.connect(self.open_trade)

   
        QTimer.singleShot(0, self.load_list)


        self.pushButton_2.setText("설정")
        self.pushButton_2.clicked.connect(
            self.open_setting
        )

        self._reflow()


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

        total_h = 24 if self.total_label.isVisible() else 0


        target = self.table if self.table is not None else self.list_main
        table_y = 40
        table_h = bottom_y - table_y - 8 - total_h
        target.setGeometry(margin, table_y, max(w - margin * 2, 100), max(table_h, 60))

        if self.total_label.isVisible():
            self.total_label.setGeometry(
                margin, table_y + target.height() + 4, max(w - margin * 2, 100), total_h - 2
            )

        for name in ("search_list", "pushButton_2", "pushButton_3"):

            widget = getattr(self, name)
            og = self._orig_geom[name]
            right_gap = orig_w - (og.x() + og.width())
            new_x = w - right_gap - og.width()
            widget.move(new_x, bottom_y)


        le_og = self._orig_geom["lineEdit"]
        new_width = max(self.search_list.x() - le_og.x() - margin, 60)
        self.lineEdit.setGeometry(le_og.x(), bottom_y, new_width, le_og.height())


    def _fill_table(self, headers, rows, colors=None, bold_rows=None, italic_rows=None, stretch_index=None, weights=None):

        if self.table is None:
            self._fill_list_fallback(headers, rows)
            return

        self.table.setColumnCount(len(headers))
        self.table.setHorizontalHeaderLabels(headers)
        self.table.setRowCount(len(rows))

        for r, row in enumerate(rows):
            for c, value in enumerate(row):

                cell = QTableWidgetItem(str(value))

                if colors and colors[r]:
                    cell.setForeground(colors[r])

                if bold_rows and bold_rows[r]:
                    font = cell.font()
                    font.setBold(True)
                    cell.setFont(font)

                if italic_rows and italic_rows[r]:
                    font = cell.font()
                    font.setItalic(True)
                    cell.setFont(font)

                self.table.setItem(r, c, cell)

        if weights:
            configure_table_weighted(self.table, weights)
        else:
            self.table.resizeColumnsToContents()
            configure_table_resize(self.table, stretch_index=stretch_index)


    def _fill_list_fallback(self, headers, rows):

        from table_format import build_table

        self.model.clear()

        header_line, row_lines = build_table(headers, rows)

        header_item = QStandardItem(header_line)
        header_item.setEditable(False)
        bold_font = header_item.font()
        bold_font.setBold(True)
        header_item.setFont(bold_font)
        self.model.appendRow(header_item)

        for line in row_lines:
            row_item = QStandardItem(line)
            row_item.setEditable(False)
            self.model.appendRow(row_item)


    def load_list(self):

        try:

            items = self.db.fetch_items_in_stock()

            headers = ["번호", "원산지코드", "과일", "원산지", "재고"]

            weights = [7, 18, 30, 25, 20]

            self._mode = "summary"
            self._current_items = list(items)


            self.total_label.hide()
            self._reflow()

            if not items:

                self._fill_table(headers, [["-", "-", "현재 판매 중인 과일이 없습니다.", "-", "-"]], weights=weights)

                return

            rows = []


            origin_fruit_index = {}
            fruit_display_code = {}

            for item_id, item_name, origin_code, origin_name, quantity in items:

                idx = origin_fruit_index.get(origin_code, 0)
                origin_fruit_index[origin_code] = idx + 1

                base = (idx + 1) * 10 + 1
                fruit_display_code[item_id] = f"{origin_code}-{base:03d}"

            for row_no, (item_id, item_name, origin_code, origin_name, quantity) in enumerate(items, start=1):

                rows.append([row_no, fruit_display_code[item_id], item_name, origin_name, quantity])

            self._fill_table(headers, rows, weights=weights)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"목록을 불러오지 못했습니다.\n\n{e}"
            )



    def on_row_clicked(self, row, column):

        try:

            if self._mode != "summary":
                return

            if row >= len(self._current_items):
                return


            item_id = self._current_items[row][0]
            item_name = self._current_items[row][1]
            origin_code = self._current_items[row][2]

            if not item_name:
                return

            self.lineEdit.setText(item_name)


            batches = self.db.fetch_batches_by_origin(origin_code)

            self._mode = "batch"

            self._render_batches(batches, only_item_id=item_id)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 정보를 불러오지 못했습니다.\n\n{e}"
            )



    def on_row_clicked_fallback(self, index):

        try:

            if self._mode != "summary":
                return

            row = index.row() - 1

            if row < 0 or row >= len(self._current_items):
                return

            item_id = self._current_items[row][0]
            item_name = self._current_items[row][1]
            origin_code = self._current_items[row][2]

            if not item_name:
                return

            self.lineEdit.setText(item_name)

            batches = self.db.fetch_batches_by_origin(origin_code)

            self._mode = "batch"

            self._render_batches(batches, only_item_id=item_id)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"과일 정보를 불러오지 못했습니다.\n\n{e}"
            )



    def search_fruit(self):

        keyword = self.lineEdit.text().strip()


        if not keyword:

            self.load_list()

            return


        try:

            batches = self.db.fetch_batches(keyword)

            self._mode = "batch"

            if not batches:

                headers = ["코드", "과일", "입고일", "수량"]
                self._fill_table(headers, [["-", "검색 결과가 없습니다.", "-", "-"]], weights=[18, 34, 30, 18])

                QMessageBox.information(
                    self,
                    "검색",
                    "검색 결과가 없습니다."
                )

                return


            self._render_batches_plain(batches)

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"검색 중 오류가 발생했습니다.\n\n{e}"
            )




    def _render_batches_plain(self, batches):

        headers = ["코드", "과일", "입고일", "수량"]


        coded = compute_batch_codes(batches)

        rows = []

        for item_id, item_name, origin_code, purchase_id, purchase_date, remaining, code, is_depleted in coded:


            if is_depleted:
                continue

            rows.append([code, item_name, str(purchase_date), str(remaining)])

        if not rows:
            rows = [["-", "검색 결과가 없습니다.", "-", "-"]]


        self.total_label.hide()
        self._reflow()


        self._fill_table(headers, rows, weights=[18, 34, 30, 18])




    def _render_batches(self, batches, only_item_id=None):

        headers = ["코드", "과일", "입고일", "수량"]


        coded = compute_batch_codes(batches)

        if only_item_id is not None:
            coded = [c for c in coded if c[0] == only_item_id]

        rows = []
        colors = []

        grand_total = 0
        fruit_names_seen = []

        for item_id, item_name, origin_code, purchase_id, purchase_date, remaining, code, is_depleted in coded:

            grand_total += remaining

            if item_name not in fruit_names_seen:
                fruit_names_seen.append(item_name)

            if is_depleted:
                qty_text = "0 (품절)"
                color = QColor("gray")
            else:
                qty_text = str(remaining)
                color = None

            rows.append([code, item_name, str(purchase_date), qty_text])
            colors.append(color)


        if len(fruit_names_seen) == 1:
            self.total_label.setText(f"{fruit_names_seen[0]} 합계: {grand_total}개")
        else:
            self.total_label.setText(f"전체 합계: {grand_total}개")

        self.total_label.show()
        self._reflow()


        self._fill_table(headers, rows, colors=colors, weights=[18, 34, 30, 18])




    def go_back_to_summary(self):

        self.lineEdit.clear()
        self.load_list()




    def open_trade(self):

        try:

            from button_start import TradeWindow

            self.trade_window = TradeWindow()

            self.trade_window.show()

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"거래 창을 열 수 없습니다.\n\n{e}"
            )




    def closeEvent(self, event):

        QApplication.instance().closeAllWindows()

        super().closeEvent(event)


    def open_setting(self):

        try:

            from button_start import Window

            self.setting_window = Window()

            self.setting_window.show()

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"설정창을 열 수 없습니다.\n\n{e}"
            )


# --------------------------------
# 프로그램 실행


if __name__ == "__main__":

    from table_format import install_exception_hook

    app = QApplication(sys.argv)


    install_exception_hook()

    window = MainList()
    window.show()

    sys.exit(app.exec_())