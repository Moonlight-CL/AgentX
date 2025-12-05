from pydantic import BaseModel
from typing import Dict, List, Literal, Optional


class EndpointParameters(BaseModel):
    query: Optional[Dict[str, str]] = None
    body: Optional[Dict[str, str]] = None
    headers: Optional[Dict[str, str]] = None


class EndpointConfig(BaseModel):
    path: str
    method: Literal['GET', 'POST', 'PUT', 'DELETE', 'PATCH']
    tool_name: str
    tool_description: str
    parameters: Optional[EndpointParameters] = None
    response_mapping: Optional[Dict] = None


class AuthConfig(BaseModel):
    header: Optional[str] = "Authorization"
    value: str


class RestAPIConfig(BaseModel):
    name: str
    base_url: str
    auth_type: Literal['bearer', 'api_key', 'basic', 'none']
    auth_config: Optional[AuthConfig] = None
    endpoints: List[EndpointConfig]


class RestAPICreate(RestAPIConfig):
    pass


class RestAPIUpdate(RestAPIConfig):
    pass


class RestAPIResponse(RestAPIConfig):
    api_id: str
    user_id: str


class TestEndpointRequest(BaseModel):
    endpoint_path: str
    params: Optional[Dict] = None
