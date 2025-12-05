from __future__ import annotations

from typing import List, Optional

from pydantic import Field

from sgr_framework.core.base_state import BaseAgentState


class BaseAgentBusinessState(BaseAgentState):
    client_name: Optional[str] = Field(
        default=None,
        description='Имя клиента, если уже известно из контекста разговора.',
    )
    intent: Optional[str] = Field(
        default=None,
        description='Текущая цель пользователя (например, записаться, узнать статус).',
    )
    pending_questions: List[str] = Field(
        default_factory=list,
        description='Незакрытые вопросы, которые нужно задать клиенту.',
    )
