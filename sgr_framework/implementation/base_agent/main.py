from __future__ import annotations

from typing import Dict, List, Type

from sgr_framework.core.orchestrator import Orchestrator, ToolsRegistry
from sgr_framework.implementation.base_agent.services import SERVICES_REGISTRY
from sgr_framework.implementation.base_agent.state import BaseAgentBusinessState
from sgr_framework.implementation.base_agent.tools.actions import (
    FinalizeConversationTool,
    LookupInfoTool,
    UpdateRecordTool,
)
from sgr_framework.implementation.base_agent.tools.planning import AdaptivePlannerTool


def build_action_schemas() -> Dict[str, Type]:  # type: ignore[type-arg]
    return {
        'LookupInfo': LookupInfoTool,
        'UpdateRecord': UpdateRecordTool,
        'FinalizeConversation': FinalizeConversationTool,
    }


def run_agent(user_messages: List[str]) -> None:
    state = BaseAgentBusinessState(session_id='demo-session')
    registry = ToolsRegistry(SERVICES_REGISTRY)
    orchestrator = Orchestrator(state=state, tools_registry=registry)

    for message in user_messages:
        state.add_user_message(message)
        answer = orchestrator.run_step(AdaptivePlannerTool, build_action_schemas())
        if answer:
            print(f'Agent: {answer}')
            break


if __name__ == '__main__':
    run_agent(['Привет! Что ты знаешь о компании "Рога и копыта"?'])
