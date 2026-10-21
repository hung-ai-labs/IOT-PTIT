CREATE TABLE IF NOT EXISTS users (
    id BIGSERIAL PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    email VARCHAR(150) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    role VARCHAR(20) NOT NULL DEFAULT 'USER' CHECK (role IN ('USER','ADMIN')),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS data_sensor (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    sensor_type VARCHAR(20) NOT NULL CHECK (sensor_type IN ('temperature','humidity','light')),
    value NUMERIC(10,2) NOT NULL,
    unit VARCHAR(10) NOT NULL,
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE TABLE IF NOT EXISTS device_actions (
    id BIGSERIAL PRIMARY KEY,
    device_id VARCHAR(50) NOT NULL,
    target VARCHAR(20) NOT NULL CHECK (target IN ('led','fan','ac')),
    action VARCHAR(20) NOT NULL CHECK (action IN ('ON','OFF')),
    issued_by BIGINT REFERENCES users(id) ON DELETE SET NULL,
    result VARCHAR(20) NOT NULL DEFAULT 'Pending' CHECK (result IN ('Pending','Success','Failed','Timeout')),
    timestamp TIMESTAMPTZ NOT NULL DEFAULT now(),
    cmd_id UUID NOT NULL UNIQUE,
    responded_at TIMESTAMPTZ,
    error_msg VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS idx_users_email ON users(email);
CREATE INDEX IF NOT EXISTS idx_sensor_lookup ON data_sensor(device_id,sensor_type,timestamp);
CREATE INDEX IF NOT EXISTS idx_sensor_time ON data_sensor(timestamp);
CREATE INDEX IF NOT EXISTS idx_actions_lookup ON device_actions(device_id,target,result,timestamp);
CREATE INDEX IF NOT EXISTS idx_actions_time ON device_actions(timestamp);
