-- Database initialization script for Agent Hotline

-- Create agents table
CREATE TABLE IF NOT EXISTS `agents` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `token` VARCHAR(255) NOT NULL,
    `endpoint` VARCHAR(255) NOT NULL,
    `environment` VARCHAR(100) NOT NULL DEFAULT 'local',
    `js_source` VARCHAR(500) NOT NULL,
    `script` VARCHAR(100) NOT NULL,
    `category` VARCHAR(100) NOT NULL,
    `language` VARCHAR(20) NOT NULL,
    `name` VARCHAR(255) NOT NULL,
    `finger_hole` VARCHAR(255) NULL,
    `scrollable_agent_card` VARCHAR(255) NULL,
    `info` TEXT NULL,
    `is_active` BOOLEAN DEFAULT TRUE NOT NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    INDEX `ix_agents_name` (`name`),
    INDEX `ix_agents_category` (`category`),
    INDEX `ix_agents_language` (`language`),
    INDEX `ix_agents_active` (`is_active`),
    INDEX `ix_agents_active_created` (`is_active`, `created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Create settings table (retained for app config)
CREATE TABLE IF NOT EXISTS `settings` (
    `id` INT AUTO_INCREMENT PRIMARY KEY,
    `key` VARCHAR(100) UNIQUE NOT NULL,
    `value` TEXT NOT NULL,
    `description` VARCHAR(255) NULL,
    `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP NOT NULL,
    UNIQUE KEY `uq_settings_key` (`key`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

-- Insert default settings
INSERT IGNORE INTO `settings` (`key`, `value`, `description`) VALUES
('app_name', 'Agent Hotline', 'Application display name'),
('app_version', '2.0.0', 'Application version'),
('webhook_host', '0.0.0.0', 'IP address to bind webhook server'),
('webhook_port', '5687', 'Port for webhook server'),
('webhook_path', '/webhook/agents', 'Webhook endpoint path');
