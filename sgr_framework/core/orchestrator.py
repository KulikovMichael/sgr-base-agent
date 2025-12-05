from __future__ import annotations

from typing import Any, Callable, Dict, Type

from loguru import logger
from pydantic import BaseModel

from sgr_framework.core.base_state import BaseAgentState
from sgr_framework.core.exceptions import ServiceExecutionError
from sgr_framework.core.execution_logger import log_reasoning
from sgr_framework.core.llm_gateway import LLMGateway


class ToolsRegistry:
    def __init__(self, services: Dict[str, Callable[..., Any]]):
        self._services = services

    def get_service(self, name: str) -> Callable[..., Any]:
        if name not in self._services:
            raise ServiceExecutionError(f'Unknown service: {name}')
        return self._services[name]


class Orchestrator:
    def __init__(
        self,
        state: BaseAgentState,
        tools_registry: ToolsRegistry,
        gateway: LLMGateway | None = None,
    ) -> None:
        self.state = state
        self.registry = tools_registry
        self.gateway = gateway or LLMGateway()

    def _generate_schema(self, schema_model: Type[BaseModel]) -> BaseModel:
        messages = [
            {
                'role': 'system',
                'content': f'You are an SGR Agent. Current State: {self.state.to_json()}',
            }
        ] + self.state.chat_history
        return self.gateway.generate(schema_model, messages)

    def run_step(
        self,
        planning_model: Type[BaseModel],
        action_models_map: Dict[str, Type[BaseModel]],
    ) -> str | None:
        plan = self._generate_schema(planning_model)
        log_reasoning(self.state.session_id, 'planning', 'Planner', plan)
        trace_payload = {}
        if hasattr(plan, 'trace') and getattr(plan, 'trace') is not None:
            trace_payload = plan.trace.model_dump()
        logger.bind(component='Orchestrator', event='Reasoning').info(
            {'analysis': getattr(plan, 'situation_analysis', ''), 'trace': trace_payload}
        )
        self.state.add_assistant_tool_call(
            tool_name='Planner',
            tool_args=plan.model_dump(),
            raw_reasoning=getattr(plan, 'situation_analysis', ''),
        )

        tool_name = getattr(plan, 'next_step_tool_name', None)
        if tool_name == 'FinalAnswer':
            return getattr(plan, 'answer_to_user', None)

        if tool_name not in action_models_map:
            raise ServiceExecutionError(f'Unknown tool requested: {tool_name}')

        action_schema = action_models_map[tool_name]
        action_data = self._generate_schema(action_schema)
        log_reasoning(self.state.session_id, 'action', tool_name, action_data)

        service_func = self.registry.get_service(tool_name)
        try:
            tool_args = getattr(action_data, 'tool_arguments', {})
            result = service_func(**tool_args)
        except Exception as exc:  # noqa: BLE001
            logger.bind(component='Orchestrator', event='ServiceError').error(
                {'tool': tool_name, 'error': str(exc)}
            )
            result = f'Error: {exc}'
        self.state.add_tool_result(tool_name, str(result))
        return None
