from __future__ import annotations

from pydantic import BaseModel, Field

from sgr_framework.core.base_tool import BaseSGRTool


class LookupInfoArguments(BaseModel):
    context_key: str = Field(
        ...,
        description='Ключ для обращения к внешнему источнику данных. Используй точное значение из запроса клиента.',
    )


class LookupInfoTool(BaseSGRTool):
    tool_arguments: LookupInfoArguments = Field(
        ...,
        description='Параметры для запроса информации. Включай только проверенные значения.',
    )


class UpdateRecordArguments(BaseModel):
    field: str = Field(
        ...,
        description='Имя параметра, который нужно обновить (например, phone, status).',
    )
    value: str = Field(
        ...,
        description='Новое значение параметра. Обязательно подтвержденное пользователем.',
    )


class UpdateRecordTool(BaseSGRTool):
    tool_arguments: UpdateRecordArguments = Field(
        ...,
        description='Структура с подтвержденными пользователем данными для обновления записи.',
    )


class FinalizeConversationArguments(BaseModel):
    summary: str = Field(
        ...,
        description='Краткое резюме разговора с ключевыми решениями. Используется для записи в CRM.',
    )


class FinalizeConversationTool(BaseSGRTool):
    tool_arguments: FinalizeConversationArguments = Field(
        ...,
        description='Итоговые данные для закрытия сценария и фиксации прогресса.',
    )
