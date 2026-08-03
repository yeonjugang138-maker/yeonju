
import unicodedata


def display_width(text):

    width = 0

    for ch in str(text):
        if unicodedata.east_asian_width(ch) in ("F", "W"):
            width += 2
        else:
            width += 1

    return width


def pad(text, width):

    text = str(text)
    current = display_width(text)

    if current >= width:
        return text

    return text + " " * (width - current)


def find_containing_layout(layout, widget):

    if layout is None:
        return None, -1

    index = layout.indexOf(widget)

    if index != -1:
        return layout, index

    for i in range(layout.count()):

        item = layout.itemAt(i)
        sub_layout = item.layout()

        if sub_layout is not None:

            found_layout, found_index = find_containing_layout(sub_layout, widget)

            if found_layout is not None:
                return found_layout, found_index

    return None, -1


def build_table(headers, rows, gap=2):

    col_count = len(headers)
    widths = [display_width(h) for h in headers]

    for row in rows:
        for i in range(col_count):
            widths[i] = max(widths[i], display_width(row[i]))

    def format_row(cells):
        parts = []
        for i, cell in enumerate(cells):
            if i == col_count - 1:

                parts.append(str(cell))
            else:
                parts.append(pad(cell, widths[i] + gap))
        return "".join(parts)

    header_line = format_row(headers)
    row_lines = [format_row(r) for r in rows]

    return header_line, row_lines


def pick_monospace_font():

    from PyQt5.QtGui import QFont, QFontDatabase

    candidates = ["D2Coding", "NanumGothicCoding", "Consolas", "Courier New"]
    families = QFontDatabase().families()

    for name in candidates:
        if name in families:
            return QFont(name, 10)

    fallback = QFontDatabase.systemFont(QFontDatabase.FixedFont)
    fallback.setPointSize(10)

    return fallback


def make_combo_searchable(combo):

    from PyQt5.QtWidgets import QCompleter
    from PyQt5.QtCore import Qt

    combo.setEditable(True)
    combo.setInsertPolicy(combo.NoInsert)

    completer = QCompleter(combo.model(), combo)
    completer.setCaseSensitivity(Qt.CaseInsensitive)
    completer.setFilterMode(Qt.MatchContains)

    combo.setCompleter(completer)


def get_combo_selected_data(combo):

    index = combo.currentIndex()

    if index < 0:
        return None

    if combo.currentText() != combo.itemText(index):
        return None

    return combo.itemData(index)


def install_exception_hook():

    import sys
    import traceback

    def hook(exc_type, exc_value, exc_tb):

        if issubclass(exc_type, (KeyboardInterrupt, SystemExit)):
            sys.__excepthook__(exc_type, exc_value, exc_tb)
            return

        message = "".join(traceback.format_exception(exc_type, exc_value, exc_tb))

        print(message, file=sys.stderr)

        try:
            from PyQt5.QtWidgets import QMessageBox

            QMessageBox.critical(
                None,
                "예상치 못한 오류",
                f"프로그램에서 처리되지 않은 오류가 발생했습니다.\n\n"
                f"{exc_type.__name__}: {exc_value}\n\n"
                f"이 창을 캡처해서 알려주시면 원인을 정확히 찾을 수 있습니다."
            )
        except Exception:

            pass

    sys.excepthook = hook


def compute_batch_codes(batches):

    origin_order = []
    origin_fruit_order = {}   # origin_code -> [item_id, ...] (첫 등장 순서)
    fruit_batches = {}        # (origin_code, item_id) -> {"name": .., "rows": [...]}

    for item_id, item_name, origin_code, purchase_id, purchase_date, remaining in batches:

        if origin_code not in origin_fruit_order:
            origin_fruit_order[origin_code] = []
            origin_order.append(origin_code)

        if item_id not in origin_fruit_order[origin_code]:
            origin_fruit_order[origin_code].append(item_id)

        key = (origin_code, item_id)

        if key not in fruit_batches:
            fruit_batches[key] = {"name": item_name, "rows": []}

        fruit_batches[key]["rows"].append((purchase_id, purchase_date, remaining))

    result = []

    for origin_code in origin_order:

        for fruit_index, item_id in enumerate(origin_fruit_order[origin_code]):


            base = (fruit_index + 1) * 10 + 1

            info = fruit_batches[(origin_code, item_id)]


            rows_sorted = sorted(info["rows"], key=lambda r: (r[1], r[0]))

            seq_offset = 0

            for purchase_id, purchase_date, remaining in rows_sorted:

                if remaining > 0:
                    code = f"{origin_code}-{base + seq_offset:03d}"
                    seq_offset += 1
                    is_depleted = False
                else:
                    code = f"{origin_code}-000"
                    is_depleted = True

                result.append((item_id, info["name"], origin_code, purchase_id, purchase_date, remaining, code, is_depleted))

    return result


def configure_table_resize(table, stretch_index=None):

    from PyQt5.QtWidgets import QHeaderView

    header = table.horizontalHeader()
    col_count = table.columnCount()

    if stretch_index is None:
        stretch_index = col_count - 1

    for i in range(col_count):
        if i == stretch_index:
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(i, QHeaderView.ResizeToContents)


def configure_table_interactive(table, stretch_index=None):

    from PyQt5.QtWidgets import QHeaderView

    header = table.horizontalHeader()
    col_count = table.columnCount()

    if stretch_index is None:
        stretch_index = col_count - 1

    for i in range(col_count):
        if i == stretch_index:
            header.setSectionResizeMode(i, QHeaderView.Stretch)
        else:
            header.setSectionResizeMode(i, QHeaderView.Interactive)


def configure_table_weighted(table, weights):

    from PyQt5.QtWidgets import QHeaderView

    header = table.horizontalHeader()
    col_count = table.columnCount()

    for i in range(col_count):
        header.setSectionResizeMode(i, QHeaderView.Interactive)

    for i, w in enumerate(weights):
        if i < col_count:
            table.setColumnWidth(i, max(int(w * 10), 40))


    for i in range(col_count):
        header.setSectionResizeMode(i, QHeaderView.Stretch)

    # 칸 구분선이 표 전체에 고르게 보이도록 명시적으로 켜준다
    table.setShowGrid(True)


from PyQt5.QtCore import QObject, QEvent, Qt as _Qt


class _DragScrollFilter(QObject):

    def __init__(self, table):
        super().__init__(table)
        self.table = table
        self.dragging = False
        self.moved = False
        self.start_x = 0
        self.start_scroll = 0

    def eventFilter(self, obj, event):

        et = event.type()

        if et == QEvent.MouseButtonPress and event.button() == _Qt.LeftButton:
            self.dragging = True
            self.moved = False
            self.start_x = event.pos().x()
            self.start_scroll = self.table.horizontalScrollBar().value()
            return False

        if et == QEvent.MouseMove and self.dragging:
            dx = event.pos().x() - self.start_x
            if abs(dx) > 4:
                self.moved = True

                self.table.horizontalScrollBar().setValue(self.start_scroll - dx)
                return True

        if et == QEvent.MouseButtonRelease:
            was_moved = self.moved
            self.dragging = False
            if was_moved:

                return True

        return False


def enable_drag_scroll(table):

    filt = _DragScrollFilter(table)
    table.viewport().installEventFilter(filt)

    table._drag_scroll_filter = filt


def add_top_button_row(dialog, buttons, push_down_widget=None):

    from PyQt5.QtWidgets import QHBoxLayout

    layout = dialog.layout()

    if layout is not None:

        row = QHBoxLayout()

        for button in buttons:
            row.addWidget(button)

        layout.insertLayout(0, row)

        return row

 
    x = 10
    y = 5
    max_bottom = y

    for button in buttons:

        button.setParent(dialog)
        button.adjustSize()
        button.move(x, y)
        button.show()
        button.raise_()

        x += button.width() + 6
        max_bottom = max(max_bottom, y + button.height())


    if push_down_widget is not None:

        push_amount = max_bottom + 8
        geom = push_down_widget.geometry()

        new_height = geom.height() - push_amount
        if new_height < 50:
            new_height = 50

        push_down_widget.setGeometry(
            geom.x(),
            geom.y() + push_amount,
            geom.width(),
            new_height
        )

    return None

def replace_with_table(old_widget):

    from PyQt5.QtWidgets import QTableWidget, QAbstractItemView

    parent = old_widget.parentWidget()

    if parent is None:
        return None


    old_geometry = old_widget.geometry()

    table = QTableWidget(parent)
    table.setEditTriggers(QAbstractItemView.NoEditTriggers)
    table.verticalHeader().setVisible(False)
    table.setSelectionBehavior(QAbstractItemView.SelectRows)
    table.setAlternatingRowColors(True)

    top_layout = parent.layout()

    if top_layout is not None:

        layout, index = find_containing_layout(top_layout, old_widget)

        if layout is not None:

            layout.insertWidget(index, table)
        else:

            top_layout.addWidget(table)

        old_widget.hide()
        old_widget.setParent(None)

        return table

    old_widget.hide()

    table.setGeometry(old_geometry)
    table.show()
    table.raise_()

    return table
