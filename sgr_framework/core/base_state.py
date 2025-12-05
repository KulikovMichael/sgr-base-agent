from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BaseAgentState(BaseModel):
    session_id: str = Field(..., description='Уникальный идентификатор сессии агента')
    chat_history: List[Dict[str, Any]] = Field(
        default_factory=list,
        description='История взаимодействий user/tool/assistant в формате JSON объектов',
    )
    is_task_completed: bool = Field(
        False,
        description='Флаг завершения сценария. True означает, что оркестратор может остановиться.',
    )
    last_tool_result: Optional[str] = Field(
        default=None,
        description='Последний ответ от вызванного инструмента. Используется для само-коррекции.',
    )

    def add_user_message(self, content: str) -> None:
        self.chat_history.append({"role": "user", "content": content})

    def add_assistant_tool_call(self, tool_name: str, tool_args: Dict[str, Any], raw_reasoning: str) -> None:
        self.chat_history.append(
            {
                "role": "assistant",
                "content": raw_reasoning,
                "tool_call": {"name": tool_name, "arguments": tool_args},
            }
        )

    def add_tool_result(self, tool_name: str, result: str) -> None:
        self.chat_history.append({"role": "tool", "name": tool_name, "content": result})
        self.last_tool_result = result

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)

    @classmethod
    def from_json(cls, payload: str) -> 'BaseAgentState':
        return cls.model_validate_json(payload)
