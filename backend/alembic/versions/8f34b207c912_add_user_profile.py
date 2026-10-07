"""Add editable personal profile fields.

Revision ID: 8f34b207c912
Revises: 056c8b671af8
"""
from alembic import op
import sqlalchemy as sa

revision = "8f34b207c912"
down_revision = "056c8b671af8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("users", sa.Column("student_id", sa.String(30), nullable=True))
    op.add_column("users", sa.Column("school", sa.String(200), nullable=True))
    op.add_column("users", sa.Column("contact_email", sa.String(150), nullable=True))
    users = sa.table("users", sa.column("email"), sa.column("full_name"),
                     sa.column("student_id"), sa.column("school"), sa.column("contact_email"))
    op.execute(users.update().where(
        (users.c.email == "admin@ptit.edu.vn") & (users.c.full_name == "Nguyễn Xuân Hùng")
    ).values(student_id="B23DCCN361", school="Học Viện Công Nghệ Bưu Chính Viễn Thông",
             contact_email="Hungmk2005@gmail.com"))


def downgrade() -> None:
    op.drop_column("users", "contact_email")
    op.drop_column("users", "school")
    op.drop_column("users", "student_id")
