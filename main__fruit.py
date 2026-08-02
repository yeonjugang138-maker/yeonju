
import pymysql

class DB_b:

    def __init__(self, **config):
        self.config = config

    def connect(self):
        return pymysql.connect(**self.config)


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

    # 원산지 목록 조회 (콤보박스용)
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

    # [추가] 원산지 코드 자동 생성

    def generate_origin_code(self, prefix, exclude_code=None):

        prefix = prefix.strip().lower()

        sql = """
        SELECT origin_code
        FROM origin
        WHERE origin_code LIKE %s
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (prefix + '%',))
                rows = cur.fetchall()

        if exclude_code:
            rows = [r for r in rows if r[0] != exclude_code]

        if not rows:
            next_num = 1
        else:
            max_num = 0
            found_valid_number = False

            for (code,) in rows:

                suffix = code[len(prefix):]

                if suffix.isdigit():
                    max_num = max(max_num, int(suffix))
                    found_valid_number = True


            if found_valid_number:
                next_num = max_num + 10
            else:

                next_num = 1

        return f"{prefix}{next_num:03d}"

    # 원산지 추가
    def insert_origin(self, origin_name, origin_code):

        sql = """
        INSERT INTO origin
        (origin_name, origin_code)
        VALUES (%s,%s)
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (origin_name, origin_code))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return False

    # [추가] 같은 과일 이름 + 같은 원산지 조합이 이미 있는지 확인.

    def fetch_item_by_name_origin(self, item_name, origin_code):

        sql = """
        SELECT item_id
        FROM items
        WHERE item_name = %s AND origin_code = %s
        """

        with self.connect() as conn:
            with conn.cursor() as cur:
                cur.execute(sql, (item_name, origin_code))
                return cur.fetchone()

    # 과일 추가

    def insert_item(self, item_name, origin_code):

        sql = """
        INSERT INTO items
        (item_name, origin_code, quantity)
        VALUES (%s,%s,0)
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (item_name, origin_code))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return False

    # 과일 이름 수정
    def update_item_name(self, item_id, item_name):

        sql = """
        UPDATE items
        SET item_name=%s
        WHERE item_id=%s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (item_name, item_id))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return False

    # 원산지 이름 수정
    def update_origin_name(self, origin_code, origin_name):

        sql = """
        UPDATE origin
        SET origin_name=%s
        WHERE origin_code=%s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (origin_name, origin_code))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return False

    # 원산지 코드 수정

    def update_origin_code(self, old_code, new_code):

        sql = """
        UPDATE origin
        SET origin_code=%s
        WHERE origin_code=%s
        """

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (new_code, old_code))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()
                return str(e)

    def delete_origin(self, origin_code):

        sql = "DELETE FROM origin WHERE origin_code = %s"

        with self.connect() as conn:
            try:
                with conn.cursor() as cur:
                    cur.execute(sql, (origin_code,))

                conn.commit()
                return True

            except Exception as e:
                print(e)
                conn.rollback()

                message = str(e)

                if "foreign key constraint" in message.lower() or "1451" in message:
                    return "이 원산지를 사용하는 과일이 있어 삭제할 수 없습니다.\n먼저 그 과일들을 삭제하거나 다른 원산지로 옮겨주세요."

                return message


