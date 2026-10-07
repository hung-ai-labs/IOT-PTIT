"""Tạo 3 bảng gốc: users, data_sensor, device_actions (SRS §4.2)

Revision ID: 056c8b671af8
Revises:
Create Date: 2026-09-09 08:12:07.726481

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '056c8b671af8'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('data_sensor',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.String(length=50), nullable=False),
    sa.Column('sensor_type', sa.String(length=20), nullable=False),
    sa.Column('value', sa.Numeric(precision=10, scale=2), nullable=False),
    sa.Column('unit', sa.String(length=10), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("sensor_type IN ('temperature', 'humidity', 'light')", name='ck_data_sensor_type'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_sensor_lookup', 'data_sensor', ['device_id', 'sensor_type', 'timestamp'], unique=False)
    op.create_index('idx_sensor_time', 'data_sensor', ['timestamp'], unique=False)
    op.create_table('users',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('full_name', sa.String(length=100), nullable=False),
    sa.Column('email', sa.String(length=150), nullable=False),
    sa.Column('password_hash', sa.String(length=255), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("role IN ('USER', 'ADMIN')", name='ck_users_role'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_table('device_actions',
    sa.Column('id', sa.BigInteger(), nullable=False),
    sa.Column('device_id', sa.String(length=50), nullable=False),
    sa.Column('target', sa.String(length=20), nullable=False),
    sa.Column('action', sa.String(length=20), nullable=False),
    sa.Column('issued_by', sa.BigInteger(), nullable=True),
    sa.Column('result', sa.String(length=20), nullable=False),
    sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('cmd_id', sa.Uuid(), nullable=False),
    sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('error_msg', sa.String(length=255), nullable=True),
    sa.CheckConstraint("action IN ('ON', 'OFF')", name='ck_device_actions_action'),
    sa.CheckConstraint("result IN ('Pending', 'Success', 'Failed', 'Timeout')", name='ck_device_actions_result'),
    sa.CheckConstraint("target IN ('led', 'fan', 'ac')", name='ck_device_actions_target'),
    sa.ForeignKeyConstraint(['issued_by'], ['users.id'], ondelete='SET NULL'),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_actions_lookup', 'device_actions', ['device_id', 'target', 'result', 'timestamp'], unique=False)
    op.create_index('idx_actions_time', 'device_actions', ['timestamp'], unique=False)
    op.create_index(op.f('ix_device_actions_cmd_id'), 'device_actions', ['cmd_id'], unique=True)


def downgrade() -> None:
    op.drop_index(op.f('ix_device_actions_cmd_id'), table_name='device_actions')
    op.drop_index('idx_actions_time', table_name='device_actions')
    op.drop_index('idx_actions_lookup', table_name='device_actions')
    op.drop_table('device_actions')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.drop_index('idx_sensor_time', table_name='data_sensor')
    op.drop_index('idx_sensor_lookup', table_name='data_sensor')
    op.drop_table('data_sensor')
