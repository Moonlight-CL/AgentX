import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from decimal import Decimal
import asyncio
from ..utils.aws_config import get_orchestration_table
from ..agent.agent import AgentPOService, ChatRecordService, ChatRecord, ChatResponse
from .models import (
    OrchestrationConfig,
    OrchestrationExecution,
    ExecutionRequest,
)


def convert_floats_to_decimal(obj):
    """
    Recursively convert float values to Decimal for DynamoDB compatibility.

    Args:
        obj: The object to convert (dict, list, or primitive)

    Returns:
        The object with floats converted to Decimal
    """
    if isinstance(obj, dict):
        return {key: convert_floats_to_decimal(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal(item) for item in obj]
    elif isinstance(obj, float):
        return Decimal(str(obj))
    else:
        return obj


def convert_decimals_to_float(obj):
    """
    Recursively convert Decimal values back to float for frontend compatibility.

    Args:
        obj: The object to convert (dict, list, or primitive)

    Returns:
        The object with Decimals converted to float
    """
    if isinstance(obj, dict):
        return {key: convert_decimals_to_float(value) for key, value in obj.items()}
    elif isinstance(obj, list):
        return [convert_decimals_to_float(item) for item in obj]
    elif isinstance(obj, Decimal):
        return float(obj)
    else:
        return obj


class OrchestrationService:
    """Service class for orchestration business logic."""

    def __init__(self):
        self.orchestration_table = get_orchestration_table()
        self.chat_service = ChatRecordService()
        # Track running tasks for cancellation
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.cancellation_events: Dict[str, asyncio.Event] = {}

    # CRUD operations for orchestrations

    def create_orchestration(
        self, config_data: Dict[str, Any], user_id: str
    ) -> OrchestrationConfig:
        """
        Create a new orchestration configuration.

        Args:
            config_data: The orchestration configuration data
            user_id: The ID of the user creating the orchestration

        Returns:
            OrchestrationConfig: The created orchestration configuration
        """
        # Generate ID and timestamps
        orchestration_id = uuid.uuid4().hex
        current_time = datetime.now().isoformat()

        # Create orchestration config
        orchestration_data = {
            **config_data,
            "id": orchestration_id,
            "userId": user_id,
            "createdAt": current_time,
            "updatedAt": current_time,
        }

        orchestration = OrchestrationConfig(**orchestration_data)

        print("Creating orchestration with data:", orchestration)

        # Convert floats to Decimal for DynamoDB compatibility
        orchestration_data_for_db = convert_floats_to_decimal(
            orchestration.model_dump()
        )

        # Save to DynamoDB
        self.orchestration_table.put_item(Item=orchestration_data_for_db)

        return orchestration

    def get_orchestration(
        self, orchestration_id: str, user_id: str
    ) -> Optional[OrchestrationConfig]:
        """
        Get an orchestration by ID for a specific user.

        Args:
            orchestration_id: The ID of the orchestration
            user_id: The ID of the user

        Returns:
            OrchestrationConfig or None: The orchestration if found and owned by user
        """
        response = self.orchestration_table.get_item(
            Key={"userId": user_id, "id": orchestration_id}
        )

        if "Item" not in response:
            return None

        item = response["Item"]

        # Convert Decimals back to floats for frontend compatibility
        item_with_floats = convert_decimals_to_float(item)

        return OrchestrationConfig(**item_with_floats)

    def list_orchestrations(self, user_id: str) -> List[OrchestrationConfig]:
        """
        List all orchestrations for a specific user.

        Args:
            user_id: The ID of the user

        Returns:
            List[OrchestrationConfig]: List of orchestrations owned by the user
        """
        # Query orchestrations by user_id
        response = self.orchestration_table.query(
            KeyConditionExpression="userId = :user_id",
            ExpressionAttributeValues={":user_id": user_id},
        )

        orchestrations = []
        for item in response.get("Items", []):
            # Convert Decimals back to floats for frontend compatibility
            item_with_floats = convert_decimals_to_float(item)
            orchestrations.append(OrchestrationConfig(**item_with_floats))

        return orchestrations

    def update_orchestration(
        self, orchestration_id: str, config_data: Dict[str, Any], user_id: str
    ) -> Optional[OrchestrationConfig]:
        """
        Update an existing orchestration configuration.

        Args:
            orchestration_id: The ID of the orchestration to update
            config_data: The updated configuration data
            user_id: The ID of the user

        Returns:
            OrchestrationConfig or None: The updated orchestration if successful
        """
        # First, get the existing orchestration to check ownership
        response = self.orchestration_table.get_item(
            Key={"userId": user_id, "id": orchestration_id}
        )

        if "Item" not in response:
            return None

        existing_item = response["Item"]

        # Update the orchestration
        updated_data = {
            **existing_item,
            **config_data,
            "id": orchestration_id,
            "userId": user_id,
            "updatedAt": datetime.now().isoformat(),
        }

        orchestration = OrchestrationConfig(**updated_data)

        # Convert floats to Decimal for DynamoDB compatibility
        orchestration_data_for_db = convert_floats_to_decimal(
            orchestration.model_dump()
        )

        # Save to DynamoDB
        self.orchestration_table.put_item(Item=orchestration_data_for_db)

        return orchestration

    def delete_orchestration(self, orchestration_id: str, user_id: str) -> bool:
        """
        Delete an orchestration configuration.

        Args:
            orchestration_id: The ID of the orchestration to delete
            user_id: The ID of the user

        Returns:
            bool: True if deletion was successful, False otherwise
        """
        self.orchestration_table.delete_item(
            Key={"userId": user_id, "id": orchestration_id}
        )

        return True

    # Execution operations

    def create_execution(
        self, orchestration_id: str, execution_request: ExecutionRequest, user_id: str
    ) -> Optional[OrchestrationExecution]:
        """
        Create a new orchestration execution.

        Args:
            orchestration_id: The ID of the orchestration to execute
            execution_request: The execution request data
            user_id: The ID of the user

        Returns:
            OrchestrationExecution or None: The created execution if successful
        """
        # Verify orchestration exists and user owns it
        orchestration = self.get_orchestration(orchestration_id, user_id)
        if not orchestration:
            return None

        # Create execution record
        execution_id = uuid.uuid4().hex
        current_time = datetime.now().isoformat()

        execution = OrchestrationExecution(
            id=execution_id,
            orchestrationId=orchestration_id,
            userId=user_id,
            status="pending",
            startTime=current_time,
            inputMessage=execution_request.inputMessage,
        )

        # Create ChatRecord for execution
        execution_data = convert_floats_to_decimal(execution.model_dump())

        chat_record = ChatRecord(
            id=execution_id,
            agent_id=orchestration_id,  # 使用编排的id作为agent_id
            user_id=user_id,
            user_message=execution_request.inputMessage,
            create_time=current_time,
            record_type="orchestration",
            config=execution_data,
            status="pending",
        )

        # Save execution record to ChatRecordTable
        self.chat_service.add_chat_record(chat_record)

        return execution

    def get_execution(
        self, execution_id: str, user_id: str
    ) -> Optional[OrchestrationExecution]:
        """
        Get an execution by ID for a specific user.

        Args:
            execution_id: The ID of the execution
            user_id: The ID of the user

        Returns:
            OrchestrationExecution or None: The execution if found and owned by user
        """
        # Get execution from ChatRecordTable
        chat_record = self.chat_service.get_chat_record(user_id, execution_id)

        # Convert ChatRecord to OrchestrationExecution
        return self._chat_record_to_execution(chat_record)

    def update_execution_status(
        self, execution_id: str, status: str, user_id: str, **kwargs
    ) -> bool:
        """
        Update the status of an execution.

        Args:
            execution_id: The ID of the execution
            status: The new status
            user_id: The ID of the user
            **kwargs: Additional fields to update (endTime, results, errorMessage, etc.)

        Returns:
            bool: True if update was successful, False otherwise
        """
        # Get current execution record from ChatRecordTable
        chat_record = self.chat_service.get_chat_record(user_id, execution_id)
        if not chat_record or chat_record.record_type != "orchestration":
            return False

        # Update the ChatRecord with new status and other fields
        updated_record = ChatRecord(
            id=chat_record.id,
            agent_id=chat_record.agent_id,
            user_id=chat_record.user_id,
            user_message=chat_record.user_message,
            create_time=chat_record.create_time,
            record_type=chat_record.record_type,
            config=chat_record.config,
            status=status,
            end_time=kwargs.get("endTime", chat_record.end_time),
            results=kwargs.get("results", chat_record.results),
            error=kwargs.get("errorMessage", chat_record.error),
        )

        # Save updated record
        self.chat_service.add_chat_record(updated_record)

        return True

    def stop_execution(self, execution_id: str, user_id: str) -> bool:
        """
        Stop a running execution by cancelling the actual task.

        Args:
            execution_id: The ID of the execution to stop
            user_id: The ID of the user

        Returns:
            bool: True if stop was successful, False otherwise
        """
        # First verify the execution exists and user owns it
        execution = self.get_execution(execution_id, user_id)
        if not execution:
            return False

        # Set cancellation event if it exists
        if execution_id in self.cancellation_events:
            self.cancellation_events[execution_id].set()
            print(f"Cancellation event set for execution {execution_id}")

        # Cancel the running task if it exists
        if execution_id in self.running_tasks:
            task = self.running_tasks[execution_id]
            if not task.done():
                task.cancel()
                print(f"Task cancelled for execution {execution_id}")

            # Clean up task reference
            del self.running_tasks[execution_id]

        # Clean up cancellation event
        if execution_id in self.cancellation_events:
            del self.cancellation_events[execution_id]

        # Update status in database
        return self.update_execution_status(
            execution_id=execution_id,
            status="failed",
            user_id=user_id,
            endTime=datetime.now().isoformat(),
            errorMessage="Execution stopped by user",
        )

    def list_executions(
        self, user_id: str, orchestration_id: Optional[str] = None
    ) -> List[OrchestrationExecution]:
        """
        List executions for a user, optionally filtered by orchestration ID.

        Args:
            user_id: The ID of the user
            orchestration_id: Optional orchestration ID to filter by

        Returns:
            List[OrchestrationExecution]: List of executions
        """
        if orchestration_id:
            # Get executions for specific orchestration using agent_id (which stores orchestration_id)
            chat_records = self.chat_service.get_records_by_agent_id(
                user_id=user_id, agent_id=orchestration_id, record_type="orchestration"
            )
        else:
            # Get all orchestration executions for user
            chat_records = self.chat_service.get_chat_records_by_user(
                user_id=user_id, record_type="orchestration"
            )

        executions = []
        for chat_record in chat_records:
            # Convert ChatRecord to OrchestrationExecution
            execution = self._chat_record_to_execution(chat_record)
            if execution:
                executions.append(execution)

        return executions

    # Orchestration execution logic

    async def execute_orchestration(
        self, execution: OrchestrationExecution, orchestration: OrchestrationConfig
    ) -> Dict[str, Any]:
        """
        Execute an orchestration based on its type and configuration with cancellation support.

        Args:
            execution: The execution record
            orchestration: The orchestration configuration

        Returns:
            Dict[str, Any]: The execution results
        """
        execution_id = execution.id

        # Create cancellation event for this execution
        self.cancellation_events[execution_id] = asyncio.Event()

        # Update status to running
        self.update_execution_status(
            execution_id=execution_id, status="running", user_id=execution.userId
        )

        try:
            # Create the execution task
            if orchestration.type == "swarm":
                task = asyncio.create_task(self.execute_swarm(execution, orchestration))
            elif orchestration.type == "graph":
                task = asyncio.create_task(self.execute_graph(execution, orchestration))
            elif orchestration.type == "workflow":
                task = asyncio.create_task(
                    self.execute_workflow(execution, orchestration)
                )
            elif orchestration.type == "agents_as_tools":
                task = asyncio.create_task(
                    self.execute_agents_as_tools(execution, orchestration)
                )
            else:
                raise ValueError(
                    f"Unsupported orchestration type: {orchestration.type}"
                )

            # Store the task for potential cancellation
            self.running_tasks[execution_id] = task

            # Wait for either task completion or cancellation
            cancellation_event = self.cancellation_events[execution_id]

            # Use asyncio.wait to handle both task completion and cancellation
            done, pending = await asyncio.wait(
                [task, asyncio.create_task(cancellation_event.wait())],
                return_when=asyncio.FIRST_COMPLETED,
            )

            # Check if cancellation was requested
            if cancellation_event.is_set():
                # Cancel the execution task
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

                # Clean up
                self._cleanup_execution(execution_id)

                # Update status to cancelled
                self.update_execution_status(
                    execution_id=execution_id,
                    status="failed",
                    user_id=execution.userId,
                    endTime=datetime.now().isoformat(),
                    errorMessage="Execution cancelled by user",
                )

                raise asyncio.CancelledError("Execution was cancelled by user")

            # Task completed normally, get the result
            results = await task

            # Clean up
            self._cleanup_execution(execution_id)

            # Update status to completed
            self.update_execution_status(
                execution_id=execution_id,
                status="completed",
                user_id=execution.userId,
                endTime=datetime.now().isoformat(),
                results=results,
            )

            return results

        except asyncio.CancelledError:
            # Handle cancellation
            self._cleanup_execution(execution_id)
            self.update_execution_status(
                execution_id=execution_id,
                status="failed",
                user_id=execution.userId,
                endTime=datetime.now().isoformat(),
                errorMessage="Execution cancelled",
            )
            raise

        except Exception as e:
            # Handle other errors
            self._cleanup_execution(execution_id)
            self.update_execution_status(
                execution_id=execution_id,
                status="failed",
                user_id=execution.userId,
                endTime=datetime.now().isoformat(),
                errorMessage=str(e),
            )
            raise e

    def _cleanup_execution(self, execution_id: str):
        """Clean up execution tracking resources."""
        if execution_id in self.running_tasks:
            del self.running_tasks[execution_id]
        if execution_id in self.cancellation_events:
            del self.cancellation_events[execution_id]

    def _chat_record_to_execution(
        self, chat_record: ChatRecord
    ) -> Optional[OrchestrationExecution]:
        """
        Convert ChatRecord to OrchestrationExecution.

        Args:
            chat_record: The ChatRecord to convert

        Returns:
            OrchestrationExecution or None: The converted execution
        """
        if not chat_record or chat_record.record_type != "orchestration":
            return None

        # Extract execution data from ChatRecord
        execution = OrchestrationExecution(
            id=chat_record.id,
            orchestrationId=chat_record.agent_id,  # agent_id存储的是orchestration_id
            userId=chat_record.user_id,
            status=chat_record.status or "pending",
            startTime=chat_record.create_time,
            inputMessage=chat_record.user_message,
            endTime=chat_record.end_time,
            results=chat_record.results,
            errorMessage=chat_record.error,
        )

        return execution

    def _extract_and_store_multiagent_result(
        self, result, execution_id: str, user_id: str
    ):
        """
        Extract NodeResult messages from MultiAgentResult and store them as ChatResponse records.

        Args:
            result: The MultiAgentResult from orchestration execution
            execution_id: The execution ID to use as chat_id
            user_id: The user ID for the chat record
        """
        try:
            node_results = []

            # Collect all NodeResults from the MultiAgentResult
            for node_id, node_result in result.results.items():
                # Get all AgentResults from this node (handles nested results)
                agent_results = node_result.get_agent_results()

                for agent_result in agent_results:
                    # Extract message content from AgentResult
                    message_content = str(
                        agent_result
                    )  # This uses the __str__ method which extracts text content

                    if message_content.strip():  # Only store non-empty messages
                        node_results.append(
                            {
                                "node_id": node_id,
                                "message": message_content.strip(),
                                "execution_time": getattr(
                                    node_result, "execution_time", 0
                                ),
                                "create_time": datetime.now().isoformat(),
                            }
                        )

            # Sort by execution time to maintain chronological order
            node_results.sort(key=lambda x: x["execution_time"])

            # Store each message as a ChatResponse
            for i, node_result in enumerate(node_results):
                chat_response = ChatResponse(
                    chat_id=execution_id,
                    resp_no=i + 1,  # Start from 1
                    content=node_result["message"],
                    create_time=node_result["create_time"],
                )
                self.chat_service.add_chat_response(chat_response)

            print(f"Stored {len(node_results)} messages for execution {execution_id}")

        except Exception as e:
            print(f"Error extracting and storing MultiAgentResult: {str(e)}")
            # Don't raise the exception to avoid breaking the main execution flow

    async def execute_swarm(
        self, execution: OrchestrationExecution, orchestration: OrchestrationConfig
    ) -> Dict[str, Any]:
        """Execute a Swarm orchestration."""
        from strands.multiagent import Swarm

        agent_service = AgentPOService()

        # Build agents from nodes
        agents = []
        agent_map = {}

        for node in orchestration.nodes:
            if node.type == "agent" and node.agentId:
                agent_po = agent_service.get_agent(node.agentId)
                if agent_po:
                    strands_agent = agent_service.build_strands_agent(
                        agent_po, name=node.name
                    )
                    agents.append(strands_agent)
                    agent_map[node.agentId] = strands_agent

        if not agents:
            raise ValueError("No valid agents found in orchestration")

        # Find entry point agent
        entry_agent = None
        if orchestration.entryPoint:
            entry_agent = agent_map.get(orchestration.entryPoint)

        if not entry_agent:
            entry_agent = agents[0]  # Use first agent as default

        # Create and configure Swarm
        swarm = Swarm(
            nodes=agents,
            entry_point=entry_agent,
            max_handoffs=orchestration.maxHandoffs or 20,
            max_iterations=orchestration.maxIterations or 20,
            node_timeout=orchestration.nodeTimeout or 300,
            repetitive_handoff_detection_window=orchestration.repetitiveHandoffDetectionWindow
            or 0,
            repetitive_handoff_min_unique_agents=orchestration.repetitiveHandoffMinUniqueAgents
            or 0,
        )

        # Execute swarm
        result = await swarm.invoke_async(execution.inputMessage)

        # Extract and store the MultiAgentResult messages
        self._extract_and_store_multiagent_result(
            result, execution.id, execution.userId
        )

        return {
            "type": "swarm",
            "agents_count": len(agents),
            "entry_point": orchestration.entryPoint,
        }

    async def execute_graph(
        self, execution: OrchestrationExecution, orchestration: OrchestrationConfig
    ) -> Dict[str, Any]:
        """Execute a Graph orchestration using GraphBuilder."""
        from strands.multiagent import GraphBuilder

        agent_service = AgentPOService()

        # Build agents from nodes
        agents = {}
        node_id_to_agent_id = {}

        for node in orchestration.nodes:
            if node.type == "agent" and node.agentId:
                agent_po = agent_service.get_agent(node.agentId)
                if agent_po:
                    strands_agent = agent_service.build_strands_agent(
                        agent_po, name=agent_po.name, callback_handler=None
                    )
                    agents[node.id] = strands_agent
                    node_id_to_agent_id[node.id] = node.agentId

        if not agents:
            raise ValueError("No valid agents found in orchestration")

        # Create GraphBuilder
        builder = GraphBuilder()

        # Add nodes to the graph
        for node_id, agent in agents.items():
            builder.add_node(agent, node_id)

        # Add edges (dependencies)
        for edge in orchestration.edges:
            builder.add_edge(edge.source, edge.target)

        # Set entry point
        entry_point = orchestration.entryPoint
        if entry_point:
            # Find the node_id that corresponds to this agent_id
            entry_node_id = None
            for node_id, agent_id in node_id_to_agent_id.items():
                if agent_id == entry_point:
                    entry_node_id = node_id
                    break

            if entry_node_id:
                builder.set_entry_point(entry_node_id)

        # Configure execution limits
        if orchestration.executionTimeout:
            builder.set_execution_timeout(orchestration.executionTimeout)
        if orchestration.maxNodeExecutions:
            builder.set_max_node_executions(orchestration.maxNodeExecutions)
        if orchestration.nodeTimeout:
            builder.set_node_timeout(orchestration.nodeTimeout)
        if orchestration.resetOnRevisit is not None:
            builder.reset_on_revisit(orchestration.resetOnRevisit)

        # Build the graph
        graph = builder.build()

        # Execute graph (wrap in asyncio to make it async)
        result = await graph.invoke_async(execution.inputMessage)

        # Extract and store the MultiAgentResult messages
        self._extract_and_store_multiagent_result(
            result, execution.id, execution.userId
        )

        return {
            "type": "graph",
            "agents_count": len(agents),
            "edges_count": len(orchestration.edges),
            "entry_point": entry_point,
            "status": result.status.name if hasattr(result, "status") else "completed",
            "execution_order": [node.node_id for node in result.execution_order]
            if hasattr(result, "execution_order")
            else [],
        }

    async def execute_workflow(
        self, execution: OrchestrationExecution, orchestration: OrchestrationConfig
    ) -> Dict[str, Any]:
        """Execute a Workflow orchestration with sequential agent execution."""
        import time

        agent_service = AgentPOService()

        # Build agents from nodes
        agents = {}
        node_order = []

        for idx, node in enumerate(orchestration.nodes):
            if node.type == "agent" and node.agentId:
                agent_po = agent_service.get_agent(node.agentId)
                if agent_po:
                    strands_agent = (
                        agent_service.build_strands_agent(
                            agent_po, name=node.name, callback_handler=None
                        )
                        if idx != len(orchestration.nodes) - 1
                        else agent_service.build_strands_agent(agent_po, name=node.name)
                    )

                    agents[node.id] = strands_agent
                    node_order.append(node.id)

        if not agents:
            raise ValueError("No valid agents found in orchestration")

        # Sort nodes by task priorities if provided
        if orchestration.taskPriorities:
            node_order.sort(
                key=lambda node_id: orchestration.taskPriorities.get(node_id, 0),
                reverse=True,
            )

        # Execute agents sequentially
        current_input = execution.inputMessage
        workflow_results = {}
        execution_order = []

        for node_id in node_order:
            if node_id in agents:
                agent = agents[node_id]

                try:
                    # Check for cancellation before each agent execution
                    if (
                        execution.id in self.cancellation_events
                        and self.cancellation_events[execution.id].is_set()
                    ):
                        raise asyncio.CancelledError("Workflow execution cancelled")

                    # Execute agent with current input (synchronous execution)
                    result = await agent.invoke_async(current_input)

                    workflow_results[node_id] = {
                        "result": str(result),
                        "execution_time": str(time.time()),
                        "status": "completed",
                    }
                    execution_order.append(node_id)

                    # Use this agent's output as input for the next agent
                    current_input = str(result)

                except Exception as e:
                    workflow_results[node_id] = {
                        "result": f"Error: {str(e)}",
                        "execution_time": str(time.time()),
                        "status": "failed",
                    }
                    execution_order.append(node_id)

                    # Stop workflow on error unless configured otherwise
                    break

        # Create a mock MultiAgentResult-like structure for message extraction
        class WorkflowResult:
            def __init__(self, results):
                self.results = {}
                for node_id, result_data in results.items():
                    self.results[node_id] = WorkflowNodeResult(
                        result_data["result"], result_data["execution_time"]
                    )

        class WorkflowNodeResult:
            def __init__(self, result_text, execution_time):
                self.result_text = result_text
                self.execution_time = execution_time

            def get_agent_results(self):
                return [WorkflowAgentResult(self.result_text)]

        class WorkflowAgentResult:
            def __init__(self, text):
                self.text = text

            def __str__(self):
                return self.text

        # Create workflow result and extract messages
        workflow_result = WorkflowResult(workflow_results)
        self._extract_and_store_multiagent_result(
            workflow_result, execution.id, execution.userId
        )

        return {
            "type": "workflow",
            "agents_count": len(agents),
            "execution_order": execution_order,
            "results": workflow_results,
        }

    async def execute_agents_as_tools(
        self, execution: OrchestrationExecution, orchestration: OrchestrationConfig
    ) -> Dict[str, Any]:
        """Execute Agents as Tools orchestration with orchestrator and tool agents."""
        from strands import Agent
        import time

        agent_service = AgentPOService()

        # Get orchestrator agent
        orchestrator_agent_id = orchestration.orchestratorAgent
        if not orchestrator_agent_id:
            raise ValueError(
                "No orchestrator agent specified for agents-as-tools orchestration"
            )

        orchestrator_po = agent_service.get_agent(orchestrator_agent_id)
        if not orchestrator_po:
            raise ValueError(f"Orchestrator agent {orchestrator_agent_id} not found")

        # Build tool agents
        tool_functions = []
        tool_names = []

        for node in orchestration.nodes:
            if (
                node.type == "agent"
                and node.agentId
                and node.agentId != orchestrator_agent_id
            ):
                agent_po = agent_service.get_agent(node.agentId)

                if agent_po and node.agentId != orchestrator_agent_id:

                    tool_func = agent_service.agent_as_tool(agent_po)
                    tool_functions.append(tool_func)
                    tool_names.append(agent_po.name)

        if not tool_functions:
            raise ValueError("No valid tool agents found in orchestration")

        orchestrator_agent: Agent = agent_service.build_strands_agent(
            orchestrator_po,
            name=orchestrator_po.name,
            callback_handler=None,
            additional_tools=tool_functions,
        )

        try:
            # Check for cancellation before execution
            if (
                execution.id in self.cancellation_events
                and self.cancellation_events[execution.id].is_set()
            ):
                raise asyncio.CancelledError("Agents-as-tools execution cancelled")

            # Execute orchestrator with the input message
            result = await orchestrator_agent.invoke_async(execution.inputMessage)

            # Create result structure
            agents_as_tools_result = {
                "orchestrator_result": str(result),
                "tool_agents_used": tool_names,
                "execution_time": str(time.time()),
            }

            # Create a mock MultiAgentResult-like structure for message extraction
            class AgentsAsToolsResult:
                def __init__(self, result_text):
                    self.results = {
                        "orchestrator": AgentsAsToolsNodeResult(result_text, 0)
                    }

            class AgentsAsToolsNodeResult:
                def __init__(self, result_text, execution_time):
                    self.result_text = result_text
                    self.execution_time = execution_time

                def get_agent_results(self):
                    return [AgentsAsToolsAgentResult(self.result_text)]

            class AgentsAsToolsAgentResult:
                def __init__(self, text):
                    self.text = text

                def __str__(self):
                    return self.text

            # Create result and extract messages
            orchestration_result = AgentsAsToolsResult(str(result))
            self._extract_and_store_multiagent_result(
                orchestration_result, execution.id, execution.userId
            )

            return {
                "type": "agents_as_tools",
                "orchestrator_agent": orchestrator_agent_id,
                "tool_agents_count": len(tool_functions),
                "result": agents_as_tools_result,
            }

        except Exception as e:
            raise e
