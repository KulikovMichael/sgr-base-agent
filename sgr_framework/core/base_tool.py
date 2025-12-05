from pydantic import BaseModel, Field


class DecisionTrace(BaseModel):
    confidence: float = Field(
        ...,
        description='Число 0.0-1.0, отражающее уверенность в выбранном шаге. Если <0.5, нужен уточняющий вопрос.',
    )
    risks: list[str] = Field(
        default_factory=list,
        description='Список рисков/допущений, которые агент учитывает перед действием.',
    )


class BaseSGRTool(BaseModel):
    situation_analysis: str = Field(
        ...,
        description='Детальное пошаговое рассуждение на основе текущего AgentState перед любым действием.',
    )
    trace: DecisionTrace = Field(
        ...,
        description='Структурированная мета-информация для логирования (confidence + risks).',
    )
