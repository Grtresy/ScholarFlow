-- ScholarFlow Database Initialization Script
-- This script sets up the MariaDB database for workflow state persistence

-- Create database if not exists
CREATE DATABASE IF NOT EXISTS scholarflow_state
    CHARACTER SET utf8mb4
    COLLATE utf8mb4_unicode_ci;

-- Use the database
USE scholarflow_state;

-- Create user if not exists and grant privileges
-- Note: Replace 'your_password' with the actual password
CREATE USER IF NOT EXISTS 'scholarflow'@'localhost' IDENTIFIED BY 'your_password';

-- Grant privileges to the user
GRANT ALL PRIVILEGES ON scholarflow_state.* TO 'scholarflow'@'localhost';

-- Flush privileges to ensure changes take effect
FLUSH PRIVILEGES;

-- Create tables for LangGraph checkpointer
-- These tables are required by LangGraph's MySQLSaver

-- Table for storing checkpoints
CREATE TABLE IF NOT EXISTS checkpoints (
    -- Composite primary key: (thread_id, checkpoint_id)
    thread_id VARCHAR(255) NOT NULL,
    checkpoint_id VARCHAR(255) NOT NULL,
    parent_checkpoint_id VARCHAR(255) NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- State data stored as JSON
    state JSON NOT NULL,

    -- Indexes for efficient querying
    PRIMARY KEY (thread_id, checkpoint_id),
    INDEX idx_parent_checkpoint (parent_checkpoint_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Table for storing channel updates
CREATE TABLE IF NOT EXISTS channel_updates (
    -- Composite primary key: (channel, update_id)
    channel VARCHAR(255) NOT NULL,
    update_id VARCHAR(255) NOT NULL,
    channel_ts TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    -- Update data stored as JSON
    update JSON NOT NULL,

    -- Indexes for efficient querying
    PRIMARY KEY (channel, update_id),
    INDEX idx_channel_ts (channel_ts)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Optional: Create indexes for better query performance
-- Index on checkpoints.thread_id for faster thread lookups
CREATE INDEX IF NOT EXISTS idx_checkpoints_thread_id ON checkpoints(thread_id);

-- Index on channel_updates.channel for faster channel lookups
CREATE INDEX IF NOT EXISTS idx_channel_updates_channel ON channel_updates(channel);

-- Optional: Create a view for active checkpoints (most recent per thread)
-- This can be useful for monitoring and debugging
CREATE OR REPLACE VIEW latest_checkpoints AS
SELECT
    c1.thread_id,
    c1.checkpoint_id,
    c1.parent_checkpoint_id,
    c1.created_at,
    c1.state
FROM checkpoints c1
LEFT JOIN checkpoints c2
    ON c1.thread_id = c2.thread_id
    AND c1.created_at < c2.created_at
WHERE c2.checkpoint_id IS NULL;

-- Display confirmation message
SELECT 'Database initialization completed successfully!' AS status;

-- Show created tables
SHOW TABLES;

-- Display database info
SELECT
    SCHEMA_NAME AS database_name,
    DEFAULT_CHARACTER_SET_NAME AS charset,
    DEFAULT_COLLATION_NAME AS collation
FROM information_schema.SCHEMATA
WHERE SCHEMA_NAME = 'scholarflow_state';

-- Instructions for next steps:
-- 1. Update your .env file with the MariaDB credentials:
--    MARIA_DB_HOST=localhost
--    MARIA_DB_PORT=3306
--    MARIA_DB_USER=scholarflow
--    MARIA_DB_PASSWORD=your_password (replace with actual password)
--    MARIA_DB_NAME=scholarflow_state
--
-- 2. Start the ScholarFlow application:
--    python -m app.main --help
--
-- 3. Verify the connection by checking the logs for:
--    "✅ MariaDB checkpointer initialized successfully"
