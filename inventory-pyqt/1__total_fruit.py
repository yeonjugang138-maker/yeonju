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
            "search_list_2": self.search_list_2.geometry(),
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
        self.search_list_2.clicked.connect(self.open_registry)

        self.pushButton_3.setText("거래")
        self.pushButton_3.clicked.connect(self.open_trade)

        # 첫 화면: 현재 재고가 있는 과일만 표시
        QTimer.singleShot(0, self.load_list)
        self.pushButton_2.clicked.connect(
            self.open_setting
        )

        # 창을 처음 띄운 크기에 맞춰 한 번 배치
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

        for name in ("pushButton_2", "search_list_2"):

            og = self._orig_geom[name]
            right_gap = orig_w - (og.x() + og.width())
            widget = getattr(self, name)
            widget.move(w - right_gap - og.width(), og.y())


        for name in ("search_list", "pushButton_3"):

            widget = getattr(self, name)
            og = self._orig_geom[name]
            right_gap = orig_w - (og.x() + og.width())
            new_x = w - right_gap - og.width()
            widget.move(new_x, bottom_y)


        le_og = self._orig_geom["lineEdit"]
        new_width = max(self.search_list.x() - le_og.x() - margin, 60)
        self.lineEdit.setGeometry(le_og.x(), bottom_y, new_width, le_og.height())

    # --------------------------------
    # 표에 데이터 채우는 공통 함수

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


    # --------------------------------
    # 과일 전체 목록 (첫 화면)
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

            # _current_items의 각 행: (item_id, item_name, origin_code, origin_name, quantity)
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

    # --------------------------------
    # 검색

    def search_fruit(self):

        keyword = self.lineEdit.text().strip()

        if self._mode == "registry":
            self.load_registry(keyword if keyword else None)
            return

        # 검색어가 없으면 첫 화면(재고 있는 과일 요약)으로 복귀
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

            # 품절(수량 0)인 배치는 검색 결과에서 제외
            if is_depleted:
                continue

            rows.append([code, item_name, str(purchase_date), str(remaining)])

        if not rows:
            rows = [["-", "검색 결과가 없습니다.", "-", "-"]]

        # 검색 결과에는 합계를 보여주지 않음
        self.total_label.hide()
        self._reflow()

        self._fill_table(headers, rows, weights=[18, 34, 30, 18])

    # --------------------------------
    # [추가] 배치 목록(코드/과일/입고일/수량)을 표에 그리는 공통 로직.

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

        # [수정] 폭 지정
        self._fill_table(headers, rows, colors=colors, weights=[18, 34, 30, 18])

    
    def open_registry(self):

        self.lineEdit.clear()
        self.load_registry()


    def load_registry(self, keyword=None):
        try:

            origins = self.db.fetch_origin()   # (origin_code, origin_name)
            items = self.db.fetch_items()      # (item_id, item_name, origin_name, quantity)

            headers = ["구분", "이름", "정보"]

            kw = keyword.strip().lower() if keyword else None

            show_only = None

            if kw in ("과일", "과일이름", "fruit"):
                show_only = "fruit"
                kw = None
            elif kw in ("원산지", "원산지이름", "origin"):
                show_only = "origin"
                kw = None

            rows = []

            if show_only != "fruit":

                for origin_code, origin_name in origins:

                    if kw and kw not in origin_name.lower() and kw not in origin_code.lower():
                        continue

                    rows.append(["원산지", origin_name, origin_code])

            if show_only != "origin":

                for item_id, item_name, origin_name, quantity in items:

                    if kw and kw not in item_name.lower() and kw not in origin_name.lower():
                        continue

                    rows.append(["과일", item_name, origin_name])

            self._mode = "registry"

            self.total_label.hide()
            self._reflow()

            if not rows:
                rows = [["-", "검색 결과가 없습니다.", "-"]]

            self._fill_table(headers, rows, weights=[20, 40, 40])

        except Exception as e:

            QMessageBox.warning(
                self,
                "오류",
                f"조회 목록을 불러오지 못했습니다.\n\n{e}"
            )

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


    # --------------------------------
    # 설정창 열기

    # 조회 화면이 닫히면, 여기서 파생되어 열려있던 다른 창들
    # (설정, 거래, 구매/판매, 이력 화면 등)도 전부 같이 닫히게 한다.
    # --------------------------------

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

    # 처리되지 않은 예외가 나면 조용히 죽는 대신 팝업으로 보여준다
    install_exception_hook()

    window = MainList()
    window.show()

    sys.exit(app.exec_())
