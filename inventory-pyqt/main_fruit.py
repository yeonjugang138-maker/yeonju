# main_fruit.py
# 정보 조회, 구매, 판매

import pymysql


# 전체 조회 / 원산지 조회 / 과일 조회 / 과일추가(구매) / 판매
class DB_a:

    def __init__(self, **config):
        self.config = config

    def connect(self):
        return pymysql.connect(**self.config)

    # 전체 조회 (재고 0인 것도 포함, 수정/삭제 화면 등에서 사용)
    def fetch_items(self):

        sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_name,
            i.quantity
        FROM items i
        JOIN origin o
        ON i.origin_code = o.origin_code
        ORDER BY i.item_id ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()


    def fetch_items_in_stock(self):

        sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_code,
            o.origin_name,
            i.quantity
        FROM items i
        JOIN origin o
        ON i.origin_code = o.origin_code
        WHERE i.quantity > 0
        ORDER BY i.item_name ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()


    def fetch_batches(self, keyword=None, scope="all"):

        base_sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_code,
            p.purchase_id,
            p.purchase_date,
            p.remaining_quantity
        FROM items i
        JOIN origin o ON i.origin_code = o.origin_code
        JOIN purchase p ON p.item_id = i.item_id
        WHERE p.is_deleted = 0
        """

        with self.connect() as conn:
            with conn.cursor() as cur:

                if keyword:

                    like = f"%{keyword}%"

                    if scope == "name":
                        sql = base_sql + """
                            AND i.item_name LIKE %s
                            ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
                        """
                        cur.execute(sql, (like,))

                    elif scope == "origin":
                        sql = base_sql + """
                            AND (o.origin_name LIKE %s OR o.origin_code LIKE %s)
                            ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
                        """
                        cur.execute(sql, (like, like))

                    else:
                        sql = base_sql + """
                            AND (
                                i.item_name LIKE %s
                                OR o.origin_name LIKE %s
                                OR o.origin_code LIKE %s
                                OR p.purchase_date LIKE %s
                            )
                            ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
                        """
                        cur.execute(sql, (like, like, like, like))

                else:
                    sql = base_sql + """
                        ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
                    """
                    cur.execute(sql)

                return cur.fetchall()


    def fetch_batches_by_item(self, item_id):

        sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_code,
            p.purchase_id,
            p.purchase_date,
            p.remaining_quantity
        FROM items i
        JOIN origin o ON i.origin_code = o.origin_code
        JOIN purchase p ON p.item_id = i.item_id
        WHERE i.item_id = %s AND p.is_deleted = 0
        ORDER BY p.purchase_date ASC, p.purchase_id ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (item_id,))
                return cur.fetchall()

    def fetch_all_batches_for_codes(self):

        sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_code,
            p.purchase_id,
            p.purchase_date,
            p.remaining_quantity
        FROM purchase p
        JOIN items i ON i.item_id = p.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        WHERE p.is_deleted = 0
        ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()

 
    def delete_purchase_record_only(self, purchase_id):

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute("""
                        UPDATE purchase
                        SET is_deleted = 1, deleted_at = NOW()
                        WHERE purchase_id = %s
                    """, (purchase_id,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)


    def delete_sales_record(self, sales_id):

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:

                    cur.execute(
                        "SELECT item_id, sal_quantity FROM sales WHERE sales_id = %s",
                        (sales_id,)
                    )
                    row = cur.fetchone()

                    if row is None:
                        return "해당 판매 기록을 찾을 수 없습니다."

                    item_id, sal_quantity = row

                    cur.execute(
                        "UPDATE items SET quantity = quantity + %s WHERE item_id = %s",
                        (sal_quantity, item_id)
                    )

                    cur.execute(
                        "DELETE FROM sales WHERE sales_id = %s",
                        (sales_id,)
                    )

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)

    def fetch_fruit_slot_codes(self):

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT item_id, origin_code
                    FROM items
                    ORDER BY item_name ASC
                """)
                rows = cur.fetchall()

        origin_fruit_index = {}
        slot_codes = {}

        for item_id, origin_code in rows:

            idx = origin_fruit_index.get(origin_code, 0)
            origin_fruit_index[origin_code] = idx + 1

            base = (idx + 1) * 10 + 1
            slot_codes[item_id] = f"{origin_code}-{base:03d}"

        return slot_codes

    def fetch_batches_by_origin(self, origin_code):

        sql = """
        SELECT
            i.item_id,
            i.item_name,
            o.origin_code,
            p.purchase_id,
            p.purchase_date,
            p.remaining_quantity
        FROM items i
        JOIN origin o ON i.origin_code = o.origin_code
        JOIN purchase p ON p.item_id = i.item_id
        WHERE o.origin_code = %s AND p.is_deleted = 0
        ORDER BY i.item_name ASC, p.purchase_date ASC, p.purchase_id ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (origin_code,))
                return cur.fetchall()

    # 원산지 조회 (콤보박스용)
    def fetch_origin(self):

        sql = """
        SELECT
            origin_code,
            origin_name
        FROM origin
        ORDER BY origin_name ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql)
                return cur.fetchall()

    # 과일 이름 조회
    def fetch_item_name(self, item_name):

        sql = """
        SELECT
            i.item_id,
            i.item_name
        FROM items i
        WHERE item_name LIKE %s
        ORDER BY i.item_name ASC
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, ('%' + item_name + '%',))
                return cur.fetchall()

    # 선택한 과일의 원산지 이름 조회 (구매 화면에서 사용)
    def fetch_origin_by_item(self, item_id):

        sql = """
        SELECT o.origin_name
        FROM items i
        JOIN origin o
        ON i.origin_code = o.origin_code
        WHERE i.item_id = %s
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (item_id,))
                row = cur.fetchone()
                return row[0] if row else ""

    # 과일 추가 (구매)

    def insert_purchase(self, item_id, pur_quantity, purchase_date):

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:

                    cur.execute(
                        "SELECT item_id FROM items WHERE item_id = %s",
                        (item_id,)
                    )
                    row = cur.fetchone()

                    if row is None:
                        return "해당 과일을 찾을 수 없습니다. 먼저 과일을 추가하세요."


                    cur.execute("""
                        SELECT purchase_id
                        FROM purchase
                        WHERE item_id = %s AND purchase_date = %s AND is_deleted = 0
                    """, (item_id, purchase_date))

                    existing = cur.fetchone()

                    if existing:
                        purchase_id = existing[0]

                        cur.execute("""
                            UPDATE purchase
                            SET pur_quantity = pur_quantity + %s,
                                remaining_quantity = remaining_quantity + %s
                            WHERE purchase_id = %s
                        """, (pur_quantity, pur_quantity, purchase_id))

                    else:
                        cur.execute("""
                            INSERT INTO purchase
                                (item_id, pur_quantity, remaining_quantity, purchase_date)
                            VALUES (%s, %s, %s, %s)
                        """, (item_id, pur_quantity, pur_quantity, purchase_date))

                    # 총 재고 수량 증가
                    cur.execute("""
                        UPDATE items
                        SET quantity = quantity + %s
                        WHERE item_id = %s
                    """, (pur_quantity, item_id))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()

                return str(e)

    # 구매 목록 조회
    def fetch_purchase_dt(self, item_id=None):

        base_sql = """
        SELECT
            p.purchase_id,
            i.item_id,
            i.item_name,
            o.origin_name,
            p.pur_quantity,
            p.remaining_quantity,
            p.purchase_date
        FROM purchase p
        JOIN items i ON i.item_id = p.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        WHERE p.is_deleted = 0
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if item_id:
                    cur.execute(base_sql + " AND i.item_id = %s ORDER BY p.purchase_id ASC", (item_id,))
                else:
                    cur.execute(base_sql + " ORDER BY p.purchase_id ASC")
                return cur.fetchall()

    # 과일 판매

    def insert_sales(self, item_id, sal_quantity, sales_date):

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:

                    # 현재 총 재고 확인
                    cur.execute("""
                        SELECT item_id, quantity
                        FROM items
                        WHERE item_id = %s
                    """, (item_id,))

                    result = cur.fetchone()

                    # 해당 과일이 없는 경우
                    if result is None:
                        return "해당 과일을 찾을 수 없습니다."

                    item_id, quantity = result

                    # 재고보다 많이 판매하는 경우
                    if sal_quantity > quantity:
                        return f"현재 재고({quantity}개)보다 많이 판매할 수 없습니다."

                    # 판매 기록
                    cur.execute("""
                        INSERT INTO sales (item_id, sal_quantity, sales_date)
                        VALUES (%s, %s, %s)
                    """, (item_id, sal_quantity, sales_date))

                    # 먼저 입고된 배치부터 순서대로 remaining_quantity 차감 (FIFO)
                    cur.execute("""
                        SELECT purchase_id, remaining_quantity
                        FROM purchase
                        WHERE item_id = %s AND remaining_quantity > 0 AND is_deleted = 0
                        ORDER BY purchase_date ASC, purchase_id ASC
                    """, (item_id,))

                    batches = cur.fetchall()

                    left = sal_quantity

                    for purchase_id, remaining in batches:

                        if left <= 0:
                            break

                        deduct = remaining if remaining < left else left

                        cur.execute("""
                            UPDATE purchase
                            SET remaining_quantity = remaining_quantity - %s
                            WHERE purchase_id = %s
                        """, (deduct, purchase_id))

                        left -= deduct

                    # 총 재고 수량 감소
                    cur.execute("""
                        UPDATE items
                        SET quantity = quantity - %s
                        WHERE item_id = %s
                    """, (sal_quantity, item_id))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)

    # 판매 목록 조회
    def fetch_sales_dt(self, item_id=None):

        base_sql = """
        SELECT
            s.sales_id,
            i.item_id,
            i.item_name,
            o.origin_name,
            s.sal_quantity,
            s.sales_date
        FROM sales s
        JOIN items i ON i.item_id = s.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if item_id:
                    cur.execute(base_sql + " WHERE i.item_id = %s ORDER BY s.sales_id ASC", (item_id,))
                else:
                    cur.execute(base_sql + " ORDER BY s.sales_id ASC")
                return cur.fetchall()

    # [추가] 다 팔려서 남은 수량이 0인 입고 배치 목록
    # (삭제 화면에서 사용 - 과일 자체가 아니라 이 배치 기록만 지우는 용도)
    def fetch_depleted_batches(self, keyword=None):

        base_sql = """
        SELECT
            p.purchase_id,
            i.item_name,
            o.origin_code,
            p.purchase_date
        FROM purchase p
        JOIN items i ON i.item_id = p.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        WHERE p.remaining_quantity = 0 AND p.is_deleted = 0
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if keyword:
                    cur.execute(
                        base_sql + " AND i.item_name LIKE %s ORDER BY i.item_name ASC, p.purchase_date ASC",
                        (f"%{keyword}%",)
                    )
                else:
                    cur.execute(base_sql + " ORDER BY i.item_name ASC, p.purchase_date ASC")
                return cur.fetchall()


    def delete_purchase_batches(self, purchase_ids):

        select_sql = "SELECT item_id, remaining_quantity FROM purchase WHERE purchase_id = %s"
        update_items_sql = "UPDATE items SET quantity = quantity - %s WHERE item_id = %s"
        soft_delete_sql = """
            UPDATE purchase
            SET is_deleted = 1, deleted_at = NOW()
            WHERE purchase_id = %s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    for purchase_id in purchase_ids:

                        cur.execute(select_sql, (purchase_id,))
                        row = cur.fetchone()

                        if row is None:
                            continue

                        item_id, remaining = row

                        if remaining:
                            cur.execute(update_items_sql, (remaining, item_id))

                        cur.execute(soft_delete_sql, (purchase_id,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)


    def restore_purchase_batches(self, purchase_ids):

        select_sql = "SELECT item_id, remaining_quantity FROM purchase WHERE purchase_id = %s"
        update_items_sql = "UPDATE items SET quantity = quantity + %s WHERE item_id = %s"
        restore_sql = """
            UPDATE purchase
            SET is_deleted = 0, deleted_at = NULL
            WHERE purchase_id = %s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    for purchase_id in purchase_ids:

                        cur.execute(select_sql, (purchase_id,))
                        row = cur.fetchone()

                        if row is None:
                            continue

                        item_id, remaining = row

                        if remaining:
                            cur.execute(update_items_sql, (remaining, item_id))

                        cur.execute(restore_sql, (purchase_id,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)


    def fetch_deleted_records(self, keyword=None):

        base_sql = """
        SELECT
            p.purchase_id,
            i.item_name,
            o.origin_code,
            o.origin_name,
            p.pur_quantity,
            p.remaining_quantity,
            p.purchase_date,
            p.deleted_at
        FROM purchase p
        JOIN items i ON i.item_id = p.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        WHERE p.is_deleted = 1
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if keyword:
                    like = f"%{keyword}%"
                    cur.execute(base_sql + """
                        AND (
                            i.item_name LIKE %s
                            OR o.origin_name LIKE %s
                            OR o.origin_code LIKE %s
                            OR p.purchase_date LIKE %s
                        )
                        ORDER BY p.deleted_at DESC
                    """, (like, like, like, like))
                else:
                    cur.execute(base_sql + " ORDER BY p.deleted_at DESC")
                return cur.fetchall()


    def fetch_stock_ledger(self, keyword=None):

        with self.connect() as conn:
            with conn.cursor() as cur:

                cur.execute("SELECT item_id, quantity FROM items")
                current_qty = dict(cur.fetchall())

                cur.execute("""
                    SELECT p.purchase_id, p.item_id, i.item_name, o.origin_code, o.origin_name,
                           p.pur_quantity, p.purchase_date, p.created_at
                    FROM purchase p
                    JOIN items i ON i.item_id = p.item_id
                    JOIN origin o ON i.origin_code = o.origin_code
                    WHERE p.is_deleted = 0
                """)
                purchases = cur.fetchall()

                cur.execute("""
                    SELECT s.sales_id, s.item_id, i.item_name, o.origin_code, o.origin_name,
                           s.sal_quantity, s.sales_date, s.created_at
                    FROM sales s
                    JOIN items i ON i.item_id = s.item_id
                    JOIN origin o ON i.origin_code = o.origin_code
                """)
                sales = cur.fetchall()

        events_by_item = {}

        for purchase_id, item_id, item_name, origin_code, origin_name, qty, date, created_at in purchases:
            events_by_item.setdefault(item_id, []).append({
                "type": "purchase",
                "id": purchase_id,
                "item_name": item_name,
                "origin_code": origin_code,
                "origin_name": origin_name,
                "qty": qty,
                "date": date,
                "created_at": created_at,
            })

        for sales_id, item_id, item_name, origin_code, origin_name, qty, date, created_at in sales:
            events_by_item.setdefault(item_id, []).append({
                "type": "sale",
                "id": sales_id,
                "item_name": item_name,
                "origin_code": origin_code,
                "origin_name": origin_name,
                "qty": qty,
                "date": date,
                "created_at": created_at,
            })

        result = {"purchase": [], "sale": []}

        for item_id, events in events_by_item.items():


            events.sort(key=lambda e: (e["date"], e["created_at"], e["id"]))


            balance = current_qty.get(item_id, 0)

            for e in reversed(events):

                after = balance

                if e["type"] == "purchase":
                    before = balance - e["qty"]
                else:
                    before = balance + e["qty"]

                e["before"] = before
                e["after"] = after

                balance = before

            for e in events:

                before = e["before"]
                after = e["after"]

                if keyword:
                    like = keyword.lower()

                    origin_code = e.get("origin_code", "") or ""
                    if (like not in e["item_name"].lower()
                            and like not in e["origin_name"].lower()
                            and like not in origin_code.lower()
                            and like not in str(e["date"])):
                        continue

                result[e["type"]].append((
                    e["id"], item_id, e["item_name"], e["origin_code"], e["origin_name"],
                    e["qty"], e["date"], e["created_at"], before, after
                ))

        return result

    # [추가] 구매 목록 화면에서 사용 (과일이름/원산지/입고일로 검색 가능)
    def fetch_purchase_history(self, keyword=None):

        base_sql = """
        SELECT
            p.purchase_id,
            i.item_name,
            o.origin_name,
            p.pur_quantity,
            p.remaining_quantity,
            p.purchase_date
        FROM purchase p
        JOIN items i ON i.item_id = p.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        WHERE p.is_deleted = 0
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if keyword:
                    like = f"%{keyword}%"
                    cur.execute(base_sql + """
                        AND (i.item_name LIKE %s OR o.origin_name LIKE %s OR p.purchase_date LIKE %s)
                        ORDER BY p.purchase_date DESC, p.purchase_id DESC
                    """, (like, like, like))
                else:
                    cur.execute(base_sql + " ORDER BY p.purchase_date DESC, p.purchase_id DESC")
                return cur.fetchall()

    # [추가] 판매 목록 화면에서 사용 (과일이름/원산지/판매일로 검색 가능)
    def fetch_sales_history(self, keyword=None):

        base_sql = """
        SELECT
            s.sales_id,
            i.item_name,
            o.origin_name,
            s.sal_quantity,
            s.sales_date
        FROM sales s
        JOIN items i ON i.item_id = s.item_id
        JOIN origin o ON i.origin_code = o.origin_code
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                if keyword:
                    like = f"%{keyword}%"
                    cur.execute(base_sql + """
                        WHERE i.item_name LIKE %s OR o.origin_name LIKE %s OR s.sales_date LIKE %s
                        ORDER BY s.sales_date DESC, s.sales_id DESC
                    """, (like, like, like))
                else:
                    cur.execute(base_sql + " ORDER BY s.sales_date DESC, s.sales_id DESC")
                return cur.fetchall()

    def permanently_delete_batches(self, purchase_ids):

        sql = "DELETE FROM purchase WHERE purchase_id = %s"

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    for purchase_id in purchase_ids:
                        cur.execute(sql, (purchase_id,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)

    # 과일 삭제

    def delete_items(self, item_ids):

        sql = """
        DELETE FROM items
        WHERE item_id = %s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    for item_id in item_ids:
                        cur.execute(sql, (item_id,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)
