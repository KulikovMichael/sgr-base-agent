import pytest
from pydantic import ValidationError

from sgr_framework.implementation.base_agent.tools.actions import LookupInfoTool
from sgr_framework.implementation.base_agent.tools.planning import AdaptivePlannerTool


def test_lookup_tool_arguments_shape():
    tool = LookupInfoTool(
        situation_analysis='Нужно выяснить статус заказа',
        trace={'confidence': 0.9, 'risks': []},
        tool_arguments={'context_key': 'order-42'},
    )
    assert tool.tool_arguments.context_key == 'order-42'


def test_planner_literal_enforcement():
    with pytest.raises(ValidationError):
        AdaptivePlannerTool(
            situation_analysis='Выполним невалидный шаг',
            trace={'confidence': 0.2, 'risks': ['Недостаточно данных']},
            tentative_plan=['1. ???'],
            next_step_tool_name='UnknownTool',
        )
