CREATE DATABASE IF NOT EXISTS fruit DEFAULT CHARACTER SET utf8mb4;
USE fruit;

CREATE TABLE origin (
    origin_code VARCHAR(10) PRIMARY KEY,
    origin_name VARCHAR(50) NOT NULL UNIQUE
);

CREATE TABLE items (
    item_id     INT AUTO_INCREMENT PRIMARY KEY,
    origin_code VARCHAR(10) NOT NULL,
    item_name   VARCHAR(50) NOT NULL,
    quantity    INT NOT NULL DEFAULT 0,      -- 전체 재고 합계 (배치별 remaining_quantity의 합과 항상 같아야 함)

    FOREIGN KEY (origin_code)
        REFERENCES origin(origin_code)
        ON UPDATE CASCADE   -- 원산지 코드가 바뀌면 이 과일들의 origin_code도 자동으로 같이 바뀜
        ON DELETE RESTRICT  -- 이 원산지를 쓰는 과일이 있으면 원산지를 삭제할 수 없음
);

CREATE TABLE purchase (
    purchase_id         INT AUTO_INCREMENT PRIMARY KEY,
    item_id             INT NOT NULL,
    pur_quantity        INT NOT NULL,                                  -- 이 배치에 원래 입고된 수량 (기록용, 변경되지 않음)
    remaining_quantity  INT NOT NULL,                                  -- 이 배치에서 아직 판매되지 않고 남은 수량 (FIFO 판매 시 차감됨)
    purchase_date       DATE NOT NULL,                                 -- 입고일
    created_at          TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,  -- 실제 등록 시각 (같은 날짜 안에서 순서를 가리기 위함)
    is_deleted          TINYINT(1) NOT NULL DEFAULT 0,                 -- 소프트 삭제 여부
    deleted_at          TIMESTAMP NULL DEFAULT NULL,                   -- 소프트 삭제된 시각

    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
        ON DELETE CASCADE   -- 과일 자체가 삭제되면 그 과일의 구매 기록도 같이 삭제됨
);

-- ------------------------------------------------------------
-- sales : 판매 기록
CREATE TABLE sales (
    sales_id    INT AUTO_INCREMENT PRIMARY KEY,
    item_id     INT NOT NULL,
    sal_quantity INT NOT NULL,
    sales_date  DATE NOT NULL,
    created_at  TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (item_id)
        REFERENCES items(item_id)
        ON DELETE CASCADE   -- 과일 자체가 삭제되면 그 과일의 판매 기록도 같이 삭제됨
);

