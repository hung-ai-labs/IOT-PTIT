"""Khởi tạo tài khoản. Không sinh dữ liệu cảm biến hoặc lịch sử điều khiển.

    cd backend && .venv/bin/python ../scripts/seed.py
    cd backend && .venv/bin/python ../scripts/seed.py --reset   # xoá dữ liệu cũ trước

Tạo:
  • 1 tài khoản ADMIN + 1 tài khoản USER
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1] / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.security import hash_password  # noqa: E402
from app.db.base import DataSensor, DeviceAction, User  # noqa: E402
from app.db.session import SessionLocal  # noqa: E402

ACCOUNTS = [
    {
        "full_name": "Nguyễn Xuân Hùng",
        "email": "admin@ptit.edu.vn",
        "password": "123456",
        "role": "ADMIN",
    },
    {
        "full_name": "Người dùng thử nghiệm",
        "email": "user@ptit.edu.vn",
        "password": "123456",
        "role": "USER",
    },
]


def seed_users(db) -> list[User]:
    users: list[User] = []
    for account in ACCOUNTS:
        existing = db.query(User).filter(User.email == account["email"]).one_or_none()
        if existing:
            print(f"  · Bỏ qua {account['email']} (đã tồn tại)")
            users.append(existing)
            continue

        user = User(
            full_name=account["full_name"],
            email=account["email"],
            password_hash=hash_password(account["password"]),
            role=account["role"],
        )
        if account["email"] == "admin@ptit.edu.vn":
            user.student_id = "B23DCCN361"
            user.school = "Học Viện Công Nghệ Bưu Chính Viễn Thông"
            user.contact_email = "Hungmk2005@gmail.com"
        db.add(user)
        users.append(user)
        print(f"  · Tạo {account['role']:<5} {account['email']}  (mật khẩu: {account['password']})")

    db.flush()
    return users


def reset(db) -> None:
    print("Xoá dữ liệu cũ...")
    db.query(DeviceAction).delete()
    db.query(DataSensor).delete()
    db.query(User).delete()
    db.commit()


def main() -> None:
    parser = argparse.ArgumentParser(description="Khởi tạo tài khoản cho hệ thống IoT.")
    parser.add_argument("--reset", action="store_true", help="Xoá toàn bộ dữ liệu trước khi nạp")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.reset:
            reset(db)

        print("Tài khoản:")
        seed_users(db)

        db.commit()
        print("Không tạo dữ liệu cảm biến hoặc lịch sử mẫu.")
        print("Hoàn tất.")
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
