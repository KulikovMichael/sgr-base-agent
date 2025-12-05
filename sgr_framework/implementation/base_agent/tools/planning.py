from __future__ import annotations

from typing import Literal, Optional

from pydantic import Field

from sgr_framework.core.base_tool import BaseSGRTool

AVAILABLE_ACTIONS = Literal['LookupInfo', 'UpdateRecord', 'FinalizeConversation', 'FinalAnswer']


class AdaptivePlannerTool(BaseSGRTool):
    tentative_plan: list[str] = Field(
        ...,
        description='Список до 5 шагов. Каждый шаг: цель + инструмент. План пересчитывается на каждом цикле.',
    )
    next_step_tool_name: AVAILABLE_ACTIONS = Field(
        ...,
        description='Имя ТОЛЬКО ОДНОГО инструмента из списка AVAILABLE_ACTIONS, который нужно вызвать прямо сейчас.',
    )
    answer_to_user: Optional[str] = Field(
        default=None,
        description='Свободный ответ пользователю, если выбран FinalAnswer. Иначе оставь пустым.',
    )
