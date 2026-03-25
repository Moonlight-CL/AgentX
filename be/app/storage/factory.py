import os


def _backend():
    return os.environ.get("STORAGE_BACKEND", "dynamodb").lower()


def get_user_service():
    if _backend() == "postgresql":
        from ..user.pg_user_service import PGUserService
        return PGUserService()
    from ..user.models import UserService
    return UserService()


def get_agent_service():
    if _backend() == "postgresql":
        from ..agent.pg_agent_service import PGAgentPOService
        return PGAgentPOService()
    from ..agent.agent import AgentPOService
    return AgentPOService()


def get_chat_record_service():
    if _backend() == "postgresql":
        from ..agent.pg_agent_service import PGChatRecordService
        return PGChatRecordService()
    from ..agent.agent import ChatRecordService
    return ChatRecordService()


def get_mcp_service():
    if _backend() == "postgresql":
        from ..mcp.pg_mcp_service import PGMCPService
        return PGMCPService()
    from ..mcp.mcp import MCPService
    return MCPService()


def get_schedule_service():
    if _backend() == "postgresql":
        from ..schedule.pg_schedule_service import PGScheduleService
        return PGScheduleService()
    from ..schedule.dynamo_schedule_service import DynamoDBScheduleService
    return DynamoDBScheduleService()


def get_config_service():
    if _backend() == "postgresql":
        from ..config.pg_config_service import PGConfigService
        return PGConfigService()
    from ..config.config import ConfigService
    return ConfigService()


def get_orchestration_service():
    if _backend() == "postgresql":
        from ..orchestration.pg_orchestration_service import PGOrchestrationService
        return PGOrchestrationService()
    from ..orchestration.service import OrchestrationService
    return OrchestrationService()


def get_rest_api_registry():
    if _backend() == "postgresql":
        from ..services.pg_rest_api_registry import PGRestAPIRegistry
        return PGRestAPIRegistry()
    from ..services.rest_api_registry import RestAPIRegistry
    return RestAPIRegistry()


def get_session_repository():
    if _backend() == "postgresql":
        from ..agent.pg_session_repository import PostgreSQLSessionRepository
        return PostgreSQLSessionRepository()
    from ..agent.dynamodb_session_repository import DynamoDBSessionRepository
    return DynamoDBSessionRepository()
