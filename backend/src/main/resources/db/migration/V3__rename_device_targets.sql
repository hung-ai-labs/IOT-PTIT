-- Đổi khoá thiết bị cho khớp tên hiển thị (đèn giao thông):
--   led -> red (Đèn đỏ) · fan -> green (Đèn xanh) · ac -> yellow (Đèn vàng)
-- Khoá cũ là tên thiết bị theo SRS gốc (Đèn LED / Quạt / Điều hòa); dự án đã
-- chuyển sang mô hình 3 đèn nên giữ khoá cũ gây hiểu nhầm khi đọc DB và log MQTT.

ALTER TABLE device_actions DROP CONSTRAINT ck_device_actions_target;

UPDATE device_actions
SET target = CASE target
    WHEN 'led' THEN 'red'
    WHEN 'fan' THEN 'green'
    WHEN 'ac'  THEN 'yellow'
    ELSE target
END
WHERE target IN ('led', 'fan', 'ac');

ALTER TABLE device_actions
    ADD CONSTRAINT ck_device_actions_target
    CHECK (target IN ('red', 'green', 'yellow'));
