CREATE TABLE IF NOT EXISTS users (
    user_id VARCHAR(255) PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    password_hash TEXT,
    salt TEXT,
    status VARCHAR(50) DEFAULT 'active',
    is_admin BOOLEAN DEFAULT FALSE,
    user_groups JSONB DEFAULT '[]',
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    last_login VARCHAR(255),
    auth_provider VARCHAR(50) DEFAULT 'local',
    azure_object_id VARCHAR(255),
    azure_tenant_id VARCHAR(255),
    display_name VARCHAR(255),
    given_name VARCHAR(255),
    family_name VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_users_azure_object_id ON users(azure_object_id);

CREATE TABLE IF NOT EXISTS agents (
    user_id VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    display_name VARCHAR(255),
    description TEXT,
    agent_type VARCHAR(50),
    model_provider VARCHAR(50),
    model_id VARCHAR(255),
    sys_prompt TEXT,
    tools JSONB DEFAULT '[]',
    envs TEXT,
    extras JSONB,
    shared_users JSONB DEFAULT '[]',
    shared_groups JSONB DEFAULT '[]',
    is_public BOOLEAN DEFAULT FALSE,
    creator VARCHAR(255),
    runtime VARCHAR(50) DEFAULT 'local',
    PRIMARY KEY (user_id, id)
);
CREATE INDEX IF NOT EXISTS idx_agents_is_public ON agents(is_public);

CREATE TABLE IF NOT EXISTS chat_records (
    user_id VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    user_message TEXT,
    create_time VARCHAR(255),
    record_type VARCHAR(50),
    config JSONB,
    status VARCHAR(50),
    end_time VARCHAR(255),
    results JSONB,
    error TEXT,
    PRIMARY KEY (user_id, id)
);
CREATE INDEX IF NOT EXISTS idx_chat_records_agent_id ON chat_records(agent_id);

CREATE TABLE IF NOT EXISTS chat_sessions (
    session_id VARCHAR(255) PRIMARY KEY,
    session_type VARCHAR(50),
    created_at VARCHAR(255),
    updated_at VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS session_agents (
    session_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    state JSONB DEFAULT '{}',
    conversation_manager_state JSONB DEFAULT '{}',
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    PRIMARY KEY (session_id, agent_id)
);

CREATE TABLE IF NOT EXISTS session_messages (
    session_id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255) NOT NULL,
    message_id INTEGER NOT NULL,
    message_content JSONB NOT NULL,
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    PRIMARY KEY (session_id, agent_id, message_id)
);

CREATE TABLE IF NOT EXISTS http_mcp_servers (
    user_id VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    "desc" TEXT,
    host VARCHAR(255),
    headers JSONB,
    client_id VARCHAR(255),
    client_secret TEXT,
    token_url VARCHAR(255),
    scope VARCHAR(255),
    PRIMARY KEY (user_id, id)
);

CREATE TABLE IF NOT EXISTS agent_schedules (
    user_id VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    agent_id VARCHAR(255),
    agent_user_id VARCHAR(255),
    agent_name VARCHAR(255),
    cron_expression VARCHAR(255),
    status VARCHAR(50) DEFAULT 'ENABLED',
    eventbridge_schedule_name VARCHAR(255),
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    user_message TEXT,
    PRIMARY KEY (user_id, id)
);

CREATE TABLE IF NOT EXISTS orchestrations (
    user_id VARCHAR(255) NOT NULL,
    id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    description TEXT,
    type VARCHAR(50),
    nodes JSONB DEFAULT '[]',
    edges JSONB DEFAULT '[]',
    entry_point VARCHAR(255),
    max_handoffs INTEGER DEFAULT 10,
    max_iterations INTEGER DEFAULT 10,
    node_timeout INTEGER DEFAULT 300,
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    PRIMARY KEY (user_id, id)
);

CREATE TABLE IF NOT EXISTS configurations (
    key VARCHAR(255) PRIMARY KEY,
    value TEXT,
    key_display_name VARCHAR(255),
    type VARCHAR(50),
    parent VARCHAR(255),
    seq_num INTEGER DEFAULT 0,
    created_at VARCHAR(255),
    updated_at VARCHAR(255)
);
CREATE INDEX IF NOT EXISTS idx_configurations_parent ON configurations(parent);

CREATE TABLE IF NOT EXISTS rest_api_registry (
    user_id VARCHAR(255) NOT NULL,
    api_id VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    endpoints JSONB DEFAULT '[]',
    created_at VARCHAR(255),
    updated_at VARCHAR(255),
    PRIMARY KEY (user_id, api_id)
);
