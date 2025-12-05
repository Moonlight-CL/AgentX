import boto3, uuid
import importlib
import json

from boto3.dynamodb.conditions import Attr
from strands import Agent, tool
from strands.models import BedrockModel
from strands.models.bedrock import BotocoreConfig
from strands.tools.mcp.mcp_client import MCPClient
from mcp.client.streamable_http import streamablehttp_client
from strands.session.repository_session_manager import RepositorySessionManager
from ..mcp.mcp import MCPService
from .event_serializer import EventSerializer
from .dynamodb_session_repository import DynamoDBSessionRepository
from ..utils.aws_config import get_aws_region, get_chat_session_table, get_chat_record_table, get_dynamodb_resource

from enum import Enum
from typing import Optional, List
from pydantic import BaseModel

AgentType  = Enum("AgentType", ("plain", "orchestrator"))
ModelProvider = Enum("ModelProvider", ("bedrock", "openai", "anthropic", "litellm", "ollama", "custom"))
AgentToolType = Enum("AgentToolType", ("strands", "mcp", "agent", "python"))

class Tools(Enum):

    retrieve = "RAG & Memory","retrieve", "Retrive data from Amazon Bedrock Knowledge Base for RAG, memory, and other purpose"
    memory = "RAG & Memory", "memory", "Agent memory persistence in Amazon Bedrock Knowledge Bases"
    mem0_memory = "RAG & Memory", "mem0_memory", "Agent memory and personalization built on top of Mem0"

    editor = "FileOps", "editor", "File editing operations like line edits, search, and undo"
    file_read = "FileOps", "file_read", "Read and parse files"
    file_write = "FileOps", "file_write", "Create and modify files"

    http_request = "Web & Network", "http_request", "Make API calls, fetch web data, and call local HTTP servers"
    slack = "Web & Network", "slack", "Slack integration with real-time events, API access, and message sending"

    image_reader = "Multi-modal", "image_reader", "Process and analyze images"
    generate_image = "Multi-modal", "generate_image", "Create AI generated images with Amazon Bedrock"
    nova_reels = "nova_reels", "nova_reels", "Create AI generated videos with Nova Reels on Amazon Bedrock"
    speak = "nova_reels", "speak", "Generate speech from text using macOS say command or Amazon Polly"

    use_aws = "AWS Services", "use_aws","Interact with AWS services"

    calculator = "Utilities", "calculator","Perform calculations and mathematical operations"
    current_time = "Utilities", "current_time", "Get the current time and date"
    
    agentCoreBrowser = "Browser", "browser.AgentCoreBrowser.browser","Interact with web browsers, take screenshots, and perform web automation"
    agentCodeInterpreter = "Code", "code_interpreter.AgentCoreCodeInterpreter.code_interpreter","Perform code execution, data analysis, and file operations using the Code Interpreter tool"


    def __init__(self, category: str, identify:str, desc: str):
        super().__init__()
        self._category = category
        self._desc = desc
        self._identify = identify

    @property
    def desc(self):
        return self._desc

    @property
    def category(self):
        return self._category
    
    @property
    def identify(self):
        return self._identify

    @classmethod
    def getToolByName(cls, name: str) -> Optional:
        for t in Tools:
            if t.name == name:
                return t
        return None

    def __repr__(self):
        return f"Tools(name={self.name}, category={self.category}, identify = {self.identify}, desc={self.desc})"


class HttpMCPSerer(object):
    def __init__(self, name: str, desc: str, url: str):
        self.name = name
        self.desc = desc
        self.url = url

    def __repr__(self):
        return f"HttpMCPSerer(name={self.name}, desc={self.desc}, url={self.url})"

class AgentTool(BaseModel):
    name: str
    display_name: Optional[str] = None
    category: str
    desc:str
    type: AgentToolType = AgentToolType.strands
    mcp_server_url: Optional[str] = None
    agent_id: Optional[str] = None
    extra: Optional[dict] = None

    def __repr__(self):
        return f"AgentTool(name={self.name}, display_name={self.display_name} ,category={self.category},  " \
               f"desc={self.desc}, type={self.type}, mcp_server_url={self.mcp_server_url}, "\
               f"agent_id={self.agent_id}, extra={self.extra})"
    
class AgentPO(BaseModel):
    id: str
    name: str
    display_name: str
    description: str
    agent_type: AgentType = AgentType.plain
    model_provider: ModelProvider = ModelProvider.bedrock
    model_id: str = "us.anthropic.claude-3-7-sonnet-20250219-v1:0"
    sys_prompt: str = "You are a helpful assistant."
    tools: List[AgentTool] = []
    envs: str = ""
    extras: Optional[dict] = None
    shared_users: Optional[List[str]] = None  # List of user IDs this agent is shared with
    shared_groups: Optional[List[str]] = None  # List of group IDs this agent is shared with
    is_public: bool = False  # Whether this agent is public
    creator: Optional[str] = None  # User ID of the agent creator

    def __repr__(self):
        return f"AgentPO(name={self.name}, display_name={self.display_name} description={self.description}, " \
               f"agent_type={self.agent_type}, model_provider={self.model_provider}, " \
               f"model_id={self.model_id}, sys_prompt={self.sys_prompt}, tools={self.tools}, envs={self.envs})"


class AgentPOBuilder:
    def __init__(self):
        self._agent_po = AgentPO(id="", name="", display_name="", description="")

    def set_id(self, id: str):
        self._agent_po.id = id
        return self

    def set_name(self, name: str):
        self._agent_po.name = name
        return self

    def set_display_name(self, display_name: str):
        self._agent_po.display_name = display_name
        return self

    def set_description(self, description: str):
        self._agent_po.description = description
        return self

    def set_agent_type(self, agent_type: AgentType):
        self._agent_po.agent_type = agent_type
        return self

    def set_model_provider(self, model_provider: ModelProvider):
        self._agent_po.model_provider = model_provider
        return self

    def set_model_id(self, model_id: str):
        self._agent_po.model_id = model_id
        return self

    def set_sys_prompt(self, sys_prompt: str):
        self._agent_po.sys_prompt = sys_prompt
        return self

    def set_tools(self, tools: List[AgentTool]):
        self._agent_po.tools = tools
        return self
        
    def set_envs(self, envs: str):
        self._agent_po.envs = envs
        return self

    def build(self) -> AgentPO:
        return self._agent_po



class AgentPOService:
    """
    A service to manage AgentPO objects.It allows adding, retrieving, and listing agents from Amazon DynamoDB.
    """

    dynamodb_table_name = "AgentTable"

    def __init__(self):
        # aws_region = get_aws_region()
        # self.dynamodb = boto3.resource('dynamodb', region_name=aws_region)
        self.dynamodb = get_dynamodb_resource()

    def add_agent(self, agent_po: AgentPO, user_id: str = 'public'):
        """
        Add an AgentPO object to Amazon DynamoDB

        :param agent_po: The AgentPO object to add.
        :param user_id: The user ID for data isolation.
        :raises ValueError: If an agent with the same name already exists.
        :return: None
        """
        if not isinstance(agent_po, AgentPO):
            raise TypeError("agent_po must be an instance of AgentPO")

        # write to DynamoDB
        table = self.dynamodb.Table(self.dynamodb_table_name)
        item = {
            'user_id': user_id,
            'id': agent_po.id,
            'name': agent_po.name,
            'display_name': agent_po.display_name,
            'description': agent_po.description,
            'agent_type': agent_po.agent_type.value,
            'model_provider': agent_po.model_provider.value,
            'model_id': agent_po.model_id,
            'sys_prompt': agent_po.sys_prompt,
            'tools': [tool.model_dump_json() for tool in agent_po.tools],  # Convert tools to JSON string
            'envs': agent_po.envs,
            'is_public': agent_po.is_public
        }
        
        # Add extras if it exists
        if agent_po.extras:
            item['extras'] = agent_po.extras
        
        # Add sharing fields if they exist
        if agent_po.shared_users:
            item['shared_users'] = agent_po.shared_users
        
        if agent_po.shared_groups:
            item['shared_groups'] = agent_po.shared_groups
            
        table.put_item(Item=item)

    def get_agent(self, user_id: str, id: str) -> Optional[AgentPO]:
        """
        Retrieve an AgentPO object by its ID from Amazon DynamoDB.
        Checks both user-specific and public data.

        :param user_id: The user ID for data isolation.
        :param id: The ID of the agent to retrieve.
        :return: An AgentPO object if found, otherwise None.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        keys = [user_id, 'public']
        
        for k in keys:
            response = table.get_item(Key={'user_id': k, 'id': id})
            if 'Item' in response:
                item = response['Item']
                return self._map_agent_item(item)
        return None

    def query_agent_by_name(self, user_id: str, name: str, limit: int = 5) -> Optional[List[AgentPO]]:
        """
        Retrieve AgentPO objects by name from Amazon DynamoDB.
        Checks both user-specific and public data.

        :param user_id: The user ID for data isolation.
        :param name: The name of the agent to retrieve.
        :param limit: Maximum number of results to return.
        :return: A list of AgentPO objects if found, otherwise None.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        keys = [user_id, 'public']
        items = []
        
        for k in keys:
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(k),
                FilterExpression=Attr('name').eq(name),
                Limit=limit
            )
            items.extend(response.get('Items', []))

        if items:
            return [self._map_agent_item(item) for item in items[:limit]]
        return None

    def list_agents(
        self, user_id: str, user_groups: Optional[List[str]] = None
    ) -> List[AgentPO]:
        """
        List AgentPO objects for a specific user from Amazon DynamoDB.
        Includes:
        1. User's own agents
        2. Public agents (is_public=True)
        3. Agents shared with the user directly (shared_users contains user_id)
        4. Agents shared with user's groups (shared_groups contains any of user's groups)

        :param user_id: The user ID for data isolation.
        :param user_groups: List of group IDs the user belongs to.
        :return: A list of AgentPO objects.
        """
        table = self.dynamodb.Table(self.dynamodb_table_name)
        user_groups = user_groups or []

        # Get user's own agents
        # user_agents = []
        # response = table.query(
        #     KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(user_id),
        #     Limit=100,
        # )
        # user_agents.extend(response.get("Items", []))

        # Get public agents
        # public_agents = []
        # response = table.query(
        #     KeyConditionExpression=boto3.dynamodb.conditions.Key("user_id").eq(
        #         "public"
        #     ),
        #     Limit=100,
        # )
        # public_agents.extend(response.get("Items", []))

        # Scan for shared agents (this is expensive but necessary for sharing functionality)
        # In production, you might want to add a GSI for better performance
        all_agents = []
        try:
            # Scan all agents to find those shared with this user or their groups
            scan_response = table.scan()
            all_items = scan_response.get("Items", [])

            # Continue scanning if there are more items
            while "LastEvaluatedKey" in scan_response:
                scan_response = table.scan(
                    ExclusiveStartKey=scan_response["LastEvaluatedKey"]
                )
                all_items.extend(scan_response.get("Items", []))

            for item in all_items:
                # Skip user's own agents and public agents (already included)
                if item.get("user_id") == user_id or item.get("user_id") == "public":
                    all_agents.append(item)
                    continue

                # Check if agent is public
                if item.get("is_public", False):
                    all_agents.append(item)
                    continue

                # Check if shared with user directly
                shared_users = item.get("shared_users", [])
                if user_id in shared_users:
                    all_agents.append(item)
                    continue

                # Check if shared with any of user's groups
                shared_groups = item.get("shared_groups", [])
                if user_groups and any(group in shared_groups for group in user_groups):
                    all_agents.append(item)
                    continue

        except Exception as e:
            print(f"Error scanning for shared agents: {e}")

        # Combine all agents and remove duplicates
        # all_items = user_agents + public_agents + all_agents
        # seen_ids = set()
        # unique_items = []

        # for item in all_items:
        #     agent_id = item["id"]
        #     if agent_id not in seen_ids:
        #         seen_ids.add(agent_id)
        #         unique_items.append(item)

        # if unique_items:
        #     return [self._map_agent_item(item) for item in unique_items]
        if all_agents:
            ret_agents = sorted([self._map_agent_item(item) for item in all_agents], key=lambda a: (a.name or "").lower())
            return ret_agents
        return []

    def delete_agent(self, user_id: str, id: str) -> bool:
        """
        Delete an AgentPO object by its ID from Amazon DynamoDB.

        :param user_id: The user ID for data isolation.
        :param id: The ID of the agent to delete.
        :return: True if deletion was successful, False otherwise.
        """
        print(f"delete agent: {user_id}, {id}")
        table = self.dynamodb.Table(self.dynamodb_table_name)
        response = table.delete_item(Key={'user_id': user_id, 'id': id})

        # Check if the item was deleted successfully
        return response.get('ResponseMetadata', {}).get('HTTPStatusCode') == 200
    
    def update_agent_sharing(
        self,
        user_id: str,
        agent_id: str,
        shared_users: Optional[List[str]] = None,
        shared_groups: Optional[List[str]] = None,
        is_public: Optional[bool] = None,
    ) -> tuple[bool, str]:
        """
        Update agent sharing settings.

        :param user_id: The user ID who owns the agent.
        :param agent_id: The ID of the agent to update.
        :param shared_users: List of user IDs to share with.
        :param shared_groups: List of group IDs to share with.
        :param is_public: Whether the agent should be public.
        :return: Tuple of (success, error_message).
        """
        # Check if user owns the agent
        agent = self.get_agent(user_id, agent_id)
        if not agent:
            return False, "Agent not found or you don't have permission to share it"

        try:
            table = self.dynamodb.Table(self.dynamodb_table_name)

            update_expression = "SET "
            expression_values = {}

            if shared_users is not None:
                update_expression += "shared_users = :shared_users, "
                expression_values[":shared_users"] = shared_users

            if shared_groups is not None:
                update_expression += "shared_groups = :shared_groups, "
                expression_values[":shared_groups"] = shared_groups

            if is_public is not None:
                update_expression += "is_public = :is_public, "
                expression_values[":is_public"] = is_public

            # Remove trailing comma and space
            update_expression = update_expression.rstrip(", ")

            if not expression_values:
                return True, ""  # Nothing to update

            table.update_item(
                Key={"user_id": user_id, "id": agent_id},
                UpdateExpression=update_expression,
                ExpressionAttributeValues=expression_values,
            )

            return True, ""

        except Exception as e:
            error_msg = f"Error updating agent sharing for {agent_id}: {e}"
            print(error_msg)
            return False, error_msg

    def make_agent_public(self, agent_id: str) -> bool:
        """
        Make an agent public by finding it across all users and updating its public status.
        
        :param agent_id: The ID of the agent to make public.
        :return: True if successful, False otherwise.
        """
        try:
            table = self.dynamodb.Table(self.dynamodb_table_name)
            
            # Scan to find the agent across all users
            scan_response = table.scan(
                FilterExpression=Attr('id').eq(agent_id)
            )
            
            items = scan_response.get('Items', [])
            if not items:
                return False  # Agent not found
            
            agent_item = items[0]
            agent_user_id = agent_item['user_id']
            
            # Update agent to be public
            table.update_item(
                Key={'user_id': agent_user_id, 'id': agent_id},
                UpdateExpression="SET is_public = :is_public",
                ExpressionAttributeValues={":is_public": True}
            )
            
            return True
        
        except Exception as e:
            print(f"Error making agent {agent_id} public: {e}")
            return False
    
    def get_agent_sharing_info(self, user_id: str, agent_id: str) -> tuple[Optional[dict], str]:
        """
        Get sharing information for an agent.
        
        :param user_id: The user ID who owns the agent.
        :param agent_id: The ID of the agent.
        :return: Tuple of (sharing_info_dict, error_message).
        """
        agent = self.get_agent(user_id, agent_id)
        if not agent:
            return None, "Agent not found or you don't have permission to view its sharing settings"
        
        sharing_info = {
            "agent_id": agent.id,
            "shared_users": agent.shared_users or [],
            "shared_groups": agent.shared_groups or [],
            "is_public": agent.is_public
        }
        
        return sharing_info, ""
    
    async def stream_chat(self, user_id: str, agent_id: str, user_message: str):
        """
        Stream chat messages from an agent.

        :param user_id: The user ID for data isolation.
        :param agent_id: The ID of the agent to stream chat from.
        :param user_message: The user's message to send to the agent.
        :return: A generator that yields complete event information.
        """
        agent = self.get_agent(user_id, agent_id)
        if not agent:
            raise ValueError(f"Agent with ID {agent_id} not found.")
    
        agent_instance = self.build_strands_agent(agent)

        # Stream the chat response
        async for message in agent_instance.stream_async(user_message):
            # print(f"Received message: {message}")
            msg = EventSerializer.prepare_event_for_serialization(message)
            # print(f"Received message: {msg}")
            # Return the complete event information instead of just the data field
            yield message

    def get_all_available_tools(self, user_id: str) -> List[AgentTool]:
        """
        Get all available tools from the AgentPOService for a specific user.

        :param user_id: The user ID for data isolation.
        :return: A list of AgentTool objects.
        """
        print(f"Getting all available tools for user: {user_id}")
        tools = []
        for tool in Tools:
            tools.append(AgentTool(name=tool.identify, display_name=tool.name, category=tool.category, desc=tool.desc))
        
        # Add Agent tools(Only plain agents)
        for agent in self.list_agents(user_id):
            if agent.agent_type == AgentType.plain:
                tools.append(AgentTool(name=agent.name, display_name=agent.name, category="Agent", desc=agent.description, type=AgentToolType.agent, agent_id=agent.id))

        # Add MCP tools
        mcpService = MCPService()
        for mcp in mcpService.list_mcp_servers(user_id):
            tools.append(AgentTool(name=mcp.name, display_name=mcp.name, category="Mcp", desc=mcp.desc, type=AgentToolType.mcp, mcp_server_url=mcp.host))
        
        # Add REST API tools
        try:
            from ..services.rest_api_registry import RestAPIRegistry
            import asyncio
            
            print(f"Loading REST API tools for user: {user_id}")
            registry = RestAPIRegistry()
            rest_apis = asyncio.run(registry.get_user_apis(user_id))
            print(f"Found {len(rest_apis)} REST APIs")
            
            for api in rest_apis:
                print(f"Processing API: {api['name']}")
                for endpoint in api.get('endpoints', []):
                    tool_name = f"{api['name']}.{endpoint['tool_name']}"
                    print(f"Adding REST API tool: {tool_name}")
                    tools.append(AgentTool(
                        name=tool_name,
                        display_name=endpoint['tool_name'],
                        category="REST API",
                        desc=f"{endpoint['tool_description']} ({api['name']})",
                        type=AgentToolType.mcp,
                        mcp_server_url=""  # Empty string to distinguish from real MCP servers
                    ))
        except Exception as e:
            print(f"Error loading REST API tools: {e}")
            import traceback
            traceback.print_exc()
        
        print(f"Total tools loaded: {len(tools)}")
        return tools

    def build_strands_agent_with_session(self, agent: AgentPO, session_id: str, **kwargs) -> Agent:
        """
        Build a Strands agent from an AgentPO object with session management.

        :param agent: The AgentPO object to build the Strands agent from.
        :param session_id: The session ID to use for session management.
        :param user_id: Optional user_id for loading REST API tools
        :return: A Strands Agent instance with session management.
        """
        # Create DynamoDB session repository
        session_repository = DynamoDBSessionRepository()
        
        # Create session manager
        session_manager = RepositorySessionManager(
            session_id=session_id,
            session_repository=session_repository
        )
        
        agent_id = f"{agent.id}_{session_id}"
        # Build the agent with session manager
        agent_instance = self.build_strands_agent(agent, agent_id = agent_id, session_manager=session_manager, **kwargs)
        
        # Set agent_id for session management
        # agent_instance.agent_id = f"{agent.id}_{session_id}"
        
        return agent_instance

    def build_strands_agent(self, agent: AgentPO, **kwargs) -> Agent:
        """
        Build a Strands agent from an AgentPO object.

        :param agent: The AgentPO object to build the Strands agent from.
        :param user_id: Optional user_id for loading REST API tools
        :return: A Strands Agent instance.
        """
        
        def _get_tool_params(agent_name: str, cls_name: str) -> dict:
            """
            Get tool parameters from environment variables based on agent name and class name.
            Format: AGENT_{agent_name}_{cls_name}_{param_name}=value
            
            :param agent_name: Name of the agent
            :param cls_name: Name of the tool class
            :return: Dictionary of parameters
            """
            import os
            
            params = {}
            agent_name = agent_name.replace(' ', '_')
            prefix = f"{agent_name}_{cls_name}"
            print(f"prefix:{prefix}")

            if cls_name == 'AgentCoreCodeInterpreter' or cls_name == 'AgentCoreBrowser':
                key = f"{prefix}_identifier"
                val = os.environ.get(key)
                print(f"{key}, val: {val}")
                if val:
                    params['identifier'] = val
 
            return params


        # Parse and set environment variables if they exist
        if agent.envs:
            for line in agent.envs.strip().split('\n'):
                if line and '=' in line:
                    key, value = line.split('=', 1)
                    key = key.strip()
                    value = value.strip()
                    if key and value:
                        print(f"Setting environment variable: {key}")
                        import os
                        os.environ[key] = value
        # Load tools based on their type
        tools = []
        for t in agent.tools:
            if t.type == AgentToolType.strands:
                try:
                    print(f"tool.name: {t.name}")
                    name_segs = t.name.split(".")
                    if len(name_segs) ==1:
                        # If the tool name is just a single name, it is a module in strands_tools
                        module = importlib.import_module(f"strands_tools.{t.name}")
                        tools.append(module)
                    elif len(name_segs) >= 3:
                        # module.class.method pattern
                        module_name = f"strands_tools.{'.'.join(name_segs[:-2])}"
                        class_name = name_segs[-2]
                        method_name = name_segs[-1]
                        module = importlib.import_module(module_name)
                        cls = getattr(module, class_name)
                        
                        cls_params = _get_tool_params(agent.name, class_name)
                        obj = cls(**cls_params)
                        method = getattr(obj, method_name)
                        tools.append(method)
                    else:
                        raise AttributeError(f"Invalid tool name format: {t.name}. Expected format: module.class.method or module.")
                except (ImportError, AttributeError) as e:
                    print(f"Error loading tool {t.name}: {e}")
            elif t.type == AgentToolType.agent and t.agent_id:
                # If the tool is another agent, convert it to a Strands tool
                # Note: For agent tools, we use 'public' as user_id to access shared agents
                agent_po = self.get_agent('public', t.agent_id)
                if agent_po:
                    tools.append(self.agent_as_tool(agent_po))
            elif t.type == AgentToolType.mcp:
                # Check if this is a REST API tool (format: "API_Name.tool_name" with empty mcp_server_url)
                if '.' in t.name and not t.mcp_server_url:
                    # This is a REST API tool
                    try:
                        from ..services.rest_api_registry import RestAPIRegistry
                        from ..services.rest_mcp_adapter import RestMCPAdapter
                        
                        api_name, tool_name = t.name.split('.', 1)
                        registry = RestAPIRegistry()
                        
                        # Get user_id from kwargs or use 'public'
                        user_id = kwargs.get('user_id', 'public')
                        
                        # Use synchronous DynamoDB query
                        response = registry.table.query(
                            KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(user_id)
                        )
                        apis = response.get('Items', [])
                        
                        for api in apis:
                            if api['name'] == api_name:
                                for endpoint in api.get('endpoints', []):
                                    if endpoint['tool_name'] == tool_name:
                                        adapter = RestMCPAdapter(registry)
                                        tool_func = adapter._create_tool(api, endpoint)
                                        tools.append(tool_func)
                                        print(f"Loaded REST API tool: {t.name}")
                                        break
                                break
                    except Exception as e:
                        print(f"Error loading REST API tool {t.name}: {e}")
                        import traceback
                        traceback.print_exc()
                elif t.mcp_server_url:
                    # Regular MCP server
                    streamable_http_mcp_client = MCPClient(lambda: streamablehttp_client(t.mcp_server_url))
                    streamable_http_mcp_client = streamable_http_mcp_client.start()
                    tools.extend(streamable_http_mcp_client.list_tools_sync())
            else:
                print(f"Unsupported tool type: {t.type}")
                print(f"Unsupported tool type: {t.type}")
        

        # Choose the appropriate model based on the provider
        if agent.model_provider == ModelProvider.bedrock:
            boto_config = BotocoreConfig(
                retries={"max_attempts": kwargs['max_attempts'] if 'max_attempts' in kwargs else 10, "mode": "standard"},
                connect_timeout=kwargs['connect_timeout'] if 'connect_timeout' in kwargs else 10,
                read_timeout=kwargs['read_timeout'] if 'read_timeout' in kwargs else 900
            )
            max_tokens = int(agent.extras.get('max_tokens')) if agent.extras and 'max_tokens' in agent.extras else None
            temperature = float(agent.extras.get('temperature')) if agent.extras and 'temperature' in agent.extras else None
            top_p = float(agent.extras.get('top_p')) if agent.extras and 'top_p' in agent.extras else None

            print(f"Building Bedrock model: model_id={agent.model_id}, max_tokens={max_tokens}, temperature={temperature}, top_p={top_p}")

            model = BedrockModel(
                model_id=agent.model_id,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                region_name=get_aws_region(),
                boto_client_config=boto_config,
            )
        elif agent.model_provider == ModelProvider.openai:
            # For OpenAI, use the extras field to get base_url and api_key
            from strands.models.openai import OpenAIModel
            
            base_url = None
            api_key = None
            
            if agent.extras:
                base_url = agent.extras.get('base_url')
                api_key = agent.extras.get('api_key')
            
            model = OpenAIModel(
                client_args={
                    "api_key": api_key,
                    "base_url": base_url
                },
                model_id=agent.model_id,
            )
        else:
            # Default to Bedrock for now
            boto_config = BotocoreConfig(
                retries={"max_attempts": kwargs['max_attempts'] if 'max_attempts' in kwargs else 10, "mode": "standard"},
                connect_timeout=kwargs['connect_timeout'] if 'connect_timeout' in kwargs else 10,
                read_timeout=kwargs['read_timeout'] if 'read_timeout' in kwargs else 900
            )

            model = BedrockModel(
                model_id=agent.model_id,
                boto_client_config=boto_config,
            )
        
        # check kwargs has additional tools
        if kwargs and 'additional_tools' in kwargs:
            tools.extend(kwargs['additional_tools'])
            kwargs.pop('additional_tools')
        
        # Remove user_id from kwargs as Agent doesn't accept it
        if 'user_id' in kwargs:
            kwargs.pop('user_id')

        from strands.agent.conversation_manager import SlidingWindowConversationManager
        conversation_Manager = SlidingWindowConversationManager(window_size = 100)

        return Agent(
            system_prompt=agent.sys_prompt,
            model=model,
            tools=tools,
            conversation_manager= conversation_Manager,
            **kwargs
        )
    
    def agent_as_tool(self, agent: AgentPO, **kwargs):
        if agent.agent_type != AgentType.plain:
            return

        @tool(name=agent.name, description=agent.description)
        def agent_tool(query: str) -> str:
            agent_instance = self.build_strands_agent(agent, **kwargs)
            resp = agent_instance(query)
            return str(resp)
        return agent_tool

    def _map_agent_item(self, item: dict) -> AgentPO:
        """
        Map a DynamoDB item to an AgentPO object.

        :param item: The DynamoDB item to map.
        :return: An AgentPO object.
        """
        def json_to_agent_tool(tool_json: dict) -> AgentTool:
            """
            Convert a JSON string to an AgentTool object.
            """
            return AgentTool(
                             name=tool_json['name'],
                             display_name= tool_json.get('display_name', tool_json['name']),
                             category=tool_json['category'],
                             desc=tool_json['desc'],
                             type=AgentToolType(tool_json['type']),
                             mcp_server_url=tool_json.get('mcp_server_url', None),
                             agent_id= tool_json.get('agent_id', None))
        
        # Handle agent_type - convert to int if it's a Decimal
        agent_type_value = item['agent_type']
        if isinstance(agent_type_value, (int, float)):
            agent_type_value = int(agent_type_value)
        
        # Validate agent_type is valid (1 or 2)
        if agent_type_value not in [1, 2]:
            print(f"Warning: Invalid agent_type {agent_type_value} for agent {item.get('id')}, defaulting to plain")
            agent_type_value = 1  # Default to plain
    
        return AgentPO(
            id=item['id'],
            name=item['name'],
            display_name=item['display_name'],
            description=item['description'],
            agent_type=AgentType(agent_type_value),
            model_provider=ModelProvider(item['model_provider']),
            model_id=item['model_id'],
            sys_prompt=item['sys_prompt'],
            tools=[json_to_agent_tool(json.loads(tool)) for tool in item['tools'] ],
            envs=item.get('envs', ''),
            extras=item.get('extras'),
            shared_users=item.get('shared_users'),
            shared_groups=item.get('shared_groups'),
            is_public=item.get('is_public', False),
            creator=item.get('user_id')  # Use user_id as creator
        )

# Agent Chat Records (扩展支持编排记录)
class ChatRecord(BaseModel):
    id: str
    agent_id: str  # 对于编排记录，这里存储"orchestration"
    user_id: str
    user_message: str
    create_time: str  # 对于编排记录，这是start_time
    
    # 编排相关字段
    record_type: str = "agent"  # "agent" 或 "orchestration"
    config: Optional[dict] = None  # 编排配置（当record_type为orchestration时）
    status: Optional[str] = None  # 编排状态：pending, running, completed, failed
    end_time: Optional[str] = None
    results: Optional[dict] = None
    error: Optional[str] = None

# Agent Chat Responses
class ChatResponse(BaseModel):
    chat_id: str
    resp_no: int
    content: str
    create_time: str


class ChatRecordService:
    """
    A service to manage chat records and responses.It allows adding, retrieving, and listing chat records and responses from Amazon DynamoDB.
    """

    chat_record_table_name = "ChatRecordTable"
    chat_response_table_name = "ChatResponseTable"

    def __init__(self):
        self.dynamodb = get_dynamodb_resource()
        self.session_repository = DynamoDBSessionRepository()
        self.session_table = get_chat_session_table()
    
    def _item_to_chat_record(self, item: dict) -> ChatRecord:
        """
        Convert a DynamoDB item to a ChatRecord object.
        
        :param item: The DynamoDB item to convert.
        :return: A ChatRecord object.
        """
        return ChatRecord(
            id=item['id'], 
            agent_id=item['agent_id'], 
            user_id=item.get('user_id', ''),
            user_message=item['user_message'], 
            create_time=item['create_time'],
            record_type=item.get('record_type', 'agent'),
            config=item.get('config'),
            status=item.get('status'),
            end_time=item.get('end_time'),
            results=item.get('results'),
            error=item.get('error')
        )

    def add_chat_record(self, record: ChatRecord):
        """
        Add a chat record to Amazon DynamoDB.

        :param record: The ChatRecord object to add.
        :raises ValueError: If a chat record with the same ID already exists.
        :return: None
        
        """
        if (not record.id):
            record.id = uuid.uuid4().hex
        
        # table = self.dynamodb.Table(self.chat_record_table_name)
        table = get_chat_record_table()
        
        # 构建基本项目
        item = {
            'user_id': record.user_id,
            'id': record.id,
            'agent_id': record.agent_id,
            'user_message': record.user_message,
            'create_time': record.create_time,
            'record_type': record.record_type
        }
        
        # 添加编排相关字段（如果存在）
        if record.config is not None:
            item['config'] = record.config
        if record.status is not None:
            item['status'] = record.status
        if record.end_time is not None:
            item['end_time'] = record.end_time
        if record.results is not None:
            item['results'] = record.results
        if record.error is not None:
            item['error'] = record.error
            
        table.put_item(Item=item)
    
    def get_chat_record(self, user_id: str, id: str) -> ChatRecord:
        """
        Retrieve a chat record by its ID from Amazon DynamoDB.

        :param user_id: The user ID
        :param id: The ID of the chat record to retrieve.
        :return: A ChatRecord object if found, otherwise None.
        
        """
        # table = self.dynamodb.Table(self.chat_record_table_name)
        table = get_chat_record_table()
        keys = [user_id, 'public']
        for k in keys:
            response = table.get_item(Key={'user_id': k, 'id': id})
            if 'Item' in response:
                return self._item_to_chat_record(response['Item'])
        return None
    
    def get_chat_records_by_user(self, user_id: str, record_type: Optional[str] = None) -> List[ChatRecord]:
        """
        Retrieve chat records for a specific user from Amazon DynamoDB.
        This includes records with the matching user_id and legacy records without user_id.

        :param user_id: The user ID to filter by.
        :param record_type: Optional filter by record type ("agent" or "orchestration")
        :return: A list of ChatRecord objects for the user.
        """
        # table = self.dynamodb.Table(self.chat_record_table_name)
        table = get_chat_record_table()
        keys = [user_id, 'public']
        items = []
        
         # 查询两个分区键(user_id和'public')，并合并结果
        for k in keys:
            response = None
            if not record_type:
                response = table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(k),
                    Limit=100
                )
            else:
                filter_expression = Attr('record_type').not_exists() | Attr('record_type').eq(record_type)  if record_type =='agent' else Attr('record_type').eq(record_type)
                response = table.query(
                    KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(k),
                    FilterExpression=filter_expression,
                    Limit=100
                )
            items.extend(response.get('Items', []))

        if items:
            result = [self._item_to_chat_record(item) for item in items]

            # # 按record_type过滤（如果指定）
            # if record_type:
            #     result = [r for r in result if r.record_type == record_type]

            return sorted(result, key=lambda x: x.create_time, reverse=True)
        return []
    
    def get_records_by_agent_id(self, user_id: str, agent_id: str, record_type: Optional[str] = None) -> List[ChatRecord]:
        """
        Retrieve chat records for a specific user and agent_id from Amazon DynamoDB.
        
        :param user_id: The user ID to filter by.
        :param agent_id: The agent ID to filter by.
        :param record_type: Optional filter by record type ("agent" or "orchestration")
        :return: A list of ChatRecord objects for the user and agent.
        """
        # table = self.dynamodb.Table(self.chat_record_table_name)
        table = get_chat_record_table()
        keys = [user_id, 'public']
        items = []
        
        for k in keys:
            # 动态构建FilterExpression
            filter_expression = Attr('agent_id').eq(agent_id)
            if record_type:
                filter_expression = filter_expression & Attr('record_type').eq(record_type)
            
            response = table.query(
                KeyConditionExpression=boto3.dynamodb.conditions.Key('user_id').eq(k),
                FilterExpression=filter_expression,
                Limit=100
            )
            items.extend(response.get('Items', []))

        if items:
            result = [self._item_to_chat_record(item) for item in items]

            return sorted(result, key=lambda x: x.create_time, reverse=True)
        return []
    
    def add_chat_response(self, response: ChatResponse):
        """
        @Deplicated
        Add a chat response to Amazon DynamoDB.

        :param response: The ChatResponse object to add.
        """
        table = self.dynamodb.Table(self.chat_response_table_name)
        table.put_item(
            Item={
                'id': response.chat_id,
                'resp_no': response.resp_no,
                'content': response.content,
                'create_time': response.create_time
            }
        )

    def get_all_chat_responses(self, chat_id: str) -> List[ChatResponse]:
        """
        @Deplicated
        Retrieve all chat responses for a given chat ID from Amazon DynamoDB.

        :param chat_id: The ID of the chat to retrieve responses for.
        :return: A list of ChatResponse objects.
        """
        table = self.dynamodb.Table(self.chat_response_table_name)
        response = table.query(KeyConditionExpression=boto3.dynamodb.conditions.Key('id').eq(chat_id))
        items = response.get('Items', [])
        if items:
            return [ChatResponse(chat_id=item['id'], resp_no=item['resp_no'], content=item['content'], create_time=item['create_time']) for item in items]
        return []
    
    def get_all_chat_responses_from_session(self, chat_id: str, agent_id: str) -> List[ChatResponse]:
        """
        Retrieve all chat responses for a given chat ID from the session repository.
        This method tries to get messages from the session repository first, then falls back to legacy method.

        :param chat_id: The ID of the chat to retrieve responses for (used as session_id).
        :param agent_id: The agent ID to get messages for.
        :return: A list of ChatResponse objects.
        """
        try:
            # Try to get messages from session repository first
            session_agent_id = f"{agent_id}_{chat_id}"
            print(f"Retrieving messages from session repository for chat_id: {chat_id}, session_agent_id: {session_agent_id}")
            
            session_messages = self.session_repository.list_messages(session_id=chat_id, agent_id=session_agent_id, read_attachment=False)
            
            if session_messages:
                # Convert session messages to ChatResponse format
                chat_responses = []
                for i, session_message in enumerate(session_messages):
                    # Convert SessionMessage back to event format for compatibility
                    message_dict = session_message.to_dict()
                    chat_resp = ChatResponse(
                        chat_id=chat_id,
                        resp_no=i,
                        content=json.dumps(message_dict),
                        create_time=session_message.created_at
                    )
                    chat_responses.append(chat_resp)
                return chat_responses
        except Exception as e:
            print(f"Error retrieving messages from session repository: {e}")
        
        # Fall back to legacy method
        return self.get_all_chat_responses(chat_id)

    def del_chat(self, user_id: str, id: str):
        """
        Delete Chat Record and Chat Responses by its ID from Amazon DynamoDB.
        Also attempts to clean up session data if it exists.

        :param user_id: The user ID
        :param id: The ID of the chat to delete.
        """
        table = get_chat_record_table()
        table.delete_item(Key={'user_id': user_id, 'id': id})
        try:
            
            msgs = self.session_table.query(
                KeyConditionExpression = boto3.dynamodb.conditions.Key('PK').eq(id)
            )
            items = msgs['Items']
            deleted_count = 0
            with self.session_table.batch_writer() as batch:
                for item in items:
                    batch.delete_item(
                        Key={
                            'PK': item['PK'],
                            'SK': item['SK']
                        }
                    )
                    deleted_count +=1
            print(f"delete session: {id}, msg count: {deleted_count}")

        except Exception as e:
            print(f"Error checking session data for chat {id}: {e}")
