from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field

class SystemConfig(BaseModel):
    """Model for system configuration."""
    key: str = Field(..., description="配置项的key，例如 host, port, username, password")
    value: str = Field(..., description="配置项的值，使用JSON字符串存储")
    key_display_name: Optional[str] = Field(None, description="配置项的显示名称")
    type: str = Field(..., description="配置项的类型，category 或 item")
    seq_num: int = Field(0, description="配置项的排序序号，用于同一分类下配置项的排序")
    parent: Optional[str] = Field(None, description="父级分类，用于配置分类的层级结构")
    created_at: Optional[str] = Field(None, description="创建时间")
    updated_at: Optional[str] = Field(None, description="更新时间")

class ConfigCategory(BaseModel):
    """Model for configuration category."""
    key: str
    key_display_name: Optional[str] = None
    parent: Optional[str] = None
    children: List['ConfigCategory'] = []
    configs: List[SystemConfig] = []

class CreateConfigRequest(BaseModel):
    """Request model for creating configuration."""
    key: str
    value: str
    key_display_name: Optional[str] = None
    type: str
    seq_num: int = 0
    parent: Optional[str] = None

class UpdateConfigRequest(BaseModel):
    """Request model for updating configuration."""
    value: Optional[str] = None
    key_display_name: Optional[str] = None
    type: Optional[str] = None
    seq_num: Optional[int] = None
    parent: Optional[str] = None

class ConfigResponse(BaseModel):
    """Response model for configuration operations."""
    success: bool
    message: str
    data: Optional[SystemConfig] = None

class ConfigListResponse(BaseModel):
    """Response model for configuration list operations."""
    success: bool
    message: str
    data: List[SystemConfig] = []

class CategoryTreeResponse(BaseModel):
    """Response model for category tree."""
    success: bool
    message: str
    data: List[ConfigCategory] = []

# Model provider specific models
class ModelProviderConfig(BaseModel):
    """Model for model provider configuration."""
    model_id: str
    temperature: float = 0.7
    top_p: float = 1.0
    max_tokens: int = 4096
    api_base_url: Optional[str] = None
    api_key: Optional[str] = None
    
class ModelProviderRequest(BaseModel):
    """Request model for model provider configuration."""
    provider_key: str  # e.g., "bedrock", "openai"
    provider_display_name: str  # e.g., "Amazon Bedrock", "OpenAI"
    config: ModelProviderConfig
