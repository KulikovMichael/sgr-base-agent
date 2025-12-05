SGR Framework Specification: Стандарт разработки автономных агентовВерсия: 3.0 (Enterprise)Статус: FinalЦель: Создание унифицированного ядра (Core), где каждый компонент детерминирован, а поведение LLM строго ограничено схемой.1. Философия и Манифест SGRМы отказываемся от парадигмы "Chatbot" (Text-in -> Text-out) в пользу парадигмы Schema-Guided Reasoning (SGR).1.1 Что такое SGR?SGR — это архитектурный паттерн, где процесс «мышления» LLM жестко структурирован через Pydantic-схемы. Мы не просим модель «ответить пользователю». Мы просим модель заполнить структуру данных, которая отражает мыслительный процесс эксперта.1.2 Ключевые принципы (The Golden Rules)Structure over Free Text: Агент никогда не генерирует свободный текст для принятия решений. Он генерирует JSON.Forced Reasoning (Принудительное мышление): Архитектурный запрет на бездумные действия. В любой схеме поле analysis (рассуждение) идет перед полем action (действие).State as Single Source of Truth: История чата — это не состояние. Состояние (AgentState) — это типизированный объект, хранящий факты (имя клиента, стадия сделки, содержимое корзины).White-Box Loop: Мы управляем циклом, памятью и обработкой ошибок самостоятельно на Python. Никаких закрытых "Run" API (как в OpenAI Assistants).2. Архитектура Ядра (Framework Core)2.1 Стек технологийLanguage: Python 3.10+Validation: pydantic v2.x (Strict typing)LLM Gateway: litellm (Unified Interface)Resilience: tenacity (Retry logic)Logging: loguru (Structured JSON logs)Config: pydantic-settings2.2 Структура проекта (Reference Layout)Разработчик обязан соблюдать эту структуру до последнего файла.sgr_framework/
├── .env.example            # Шаблон переменных окружения
├── config/
│   ├── settings.py         # Загрузка LITELLM_API_KEY, MODEL_NAME
├── core/                   # ЯДРО ФРЕЙМВОРКА (Read-only reference)
│   ├── base_state.py       # BaseAgentState с методами сериализации
│   ├── base_tool.py        # BaseSGRTool с полями analysis/trace
│   ├── orchestrator.py     # Реализация цикла ReAct с коррекцией ошибок
│   ├── llm_gateway.py      # Обертка над LiteLLM с ретраями
│   └── exceptions.py       # Типизированные ошибки (SchemaValidationError)
├── implementation/         # ПРИКЛАДНОЙ СЛОЙ (User Space)
│   ├── salon_agent/
│   │   ├── tools/          # Pydantic Schemas
│   │   │   ├── planning.py # Reasoning Tools
│   │   │   └── actions.py  # Action Tools
│   │   ├── state.py        # Business State
│   │   └── services.py     # YClients API / Database
│   └── main.py             # Точка входа
└── tests/                  # Тесты схем и сервисов
3. Компоненты системы (Specification)3.1. Data Context (Agent State)Требование: AgentState должен уметь сохранять себя в JSON и восстанавливаться (для Stateless серверов).# core/base_state.py
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
import json

class BaseAgentState(BaseModel):
    session_id: str
    chat_history: List[Dict[str, Any]] = Field(default_factory=list)
    is_task_completed: bool = False
    
    def add_user_message(self, content: str):
        self.chat_history.append({"role": "user", "content": content})
        
    def add_assistant_tool_call(self, tool_name: str, tool_args: dict, raw_reasoning: str):
        # Сохраняем не только вызов, но и мыслительный процесс
        self.chat_history.append({
            "role": "assistant",
            "content": raw_reasoning, # Мысли сохраняем как текст
            "tool_call": {"name": tool_name, "arguments": tool_args}
        })

    def add_tool_result(self, tool_name: str, result: str):
        self.chat_history.append({
            "role": "tool",
            "name": tool_name,
            "content": result
        })

    def to_json(self) -> str:
        return self.model_dump_json(indent=2)
3.2. SGR Tools: «Мозг» агентаТребование: Каждый инструмент обязан наследоваться от BaseSGRTool.Запрещено: Использовать docstrings для документации кода. В SGR docstrings — это промпт для LLM.# core/base_tool.py
from pydantic import BaseModel, Field

class DecisionTrace(BaseModel):
    confidence: float = Field(..., description="Уверенность 0.0-1.0. Если < 0.5, рассмотри возможность задать уточняющий вопрос.")
    risks: list[str] = Field(default_factory=list, description="Список потенциальных рисков.")

class BaseSGRTool(BaseModel):
    """
    Base class enforcing SGR compliance.
    """
    # 1. FORCED REASONING
    situation_analysis: str = Field(
        ..., 
        description="CRITICAL: Analyze the current state and user request step-by-step BEFORE making a decision."
    )
    
    # 2. TRACEABILITY
    trace: DecisionTrace = Field(..., description="Meta-data about the decision.")
3.3. Orchestrator (Implementation Reference)Разработчик не должен писать этот код с нуля. Вот эталонная реализация цикла.Ключевые особенности:Injection: Промпт собирается динамически из system_prompt + state.json.Retry Loop: Используется декоратор @retry для обработки ValidationError.# core/orchestrator.py
import json
from tenacity import retry, stop_after_attempt, wait_fixed
from litellm import completion
from pydantic import ValidationError

class Orchestrator:
    def __init__(self, state, tools_registry):
        self.state = state
        self.registry = tools_registry # Dict[str, Type[BaseModel]]

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))
    def _generate_schema(self, schema_model):
        """
        Низкоуровневый вызов LLM с валидацией схемы.
        Если LLM вернет кривой JSON, tenacity сделает повтор.
        """
        messages = [
            {"role": "system", "content": f"You are an SGR Agent. Current State: {self.state.to_json()}"}
        ] + self.state.chat_history

        response = completion(
            model="gpt-4o", # Или из конфига
            messages=messages,
            response_format=schema_model
        )
        
        content = response.choices[0].message.content
        # Валидация Pydantic (вызовет ошибку, если JSON неверен)
        return schema_model.model_validate_json(content)

    def run_step(self, planning_model, action_models_map):
        # PHASE 1: PLANNING
        # LLM решает, какой инструмент вызвать
        plan = self._generate_schema(planning_model)
        
        # Логируем мысли
        print(f"[Reasoning]: {plan.situation_analysis}")
        
        # Обновляем стейт мыслями агента
        self.state.add_assistant_tool_call(
            tool_name="Planner", 
            tool_args=plan.model_dump(), 
            raw_reasoning=plan.situation_analysis
        )

        tool_name = plan.next_step_tool_name
        
        if tool_name == "FinalAnswer":
            return plan.answer_to_user

        # PHASE 2: ACTION EXECUTION
        # Выбираем схему для конкретного действия
        if tool_name not in action_models_map:
            raise ValueError(f"Unknown tool: {tool_name}")
            
        action_schema = action_models_map[tool_name]
        
        # Генерация параметров для действия (Второй вызов LLM, если параметры сложные)
        # В простой версии параметры могут быть уже в Plan. 
        # В SGR v3 рекомендуется генерировать параметры отдельным вызовом для точности.
        action_data = self._generate_schema(action_schema)
        
        # Выполнение сервиса (Service Layer)
        # В registry должны лежать функции-исполнители
        service_func = self.registry.get_service(tool_name)
        try:
            result = service_func(**action_data.tool_arguments)
        except Exception as e:
            result = f"Error: {str(e)}"

        # Обновление стейта результатом
        self.state.add_tool_result(tool_name, str(result))
        
        return None # Продолжаем цикл
4. Паттерны проектирования (SGR Patterns)A. Adaptive Planning (Адаптивный цикл)Суть: План устаревает сразу после выполнения первого шага.Реализация:В начале каждого шага вызывать AdaptivePlannerTool.Он генерирует план на 5 шагов (tentative_plan).Он выбирает ТОЛЬКО ОДИН next_action.Выполняется это действие.На следующем круге план генерируется заново.B. Self-Correction (Авто-коррекция)Если сервис вернул ошибку (например, "Нет свободных слотов"), агент НЕ должен падать.Реализация:Сервис возвращает строку: Error: No slots available for 10:00.Эта строка попадает в AgentState.На следующем шаге AdaptivePlanner читает AgentState, видит ошибку в поле last_tool_result.В поле analysis модель пишет: "Предыдущая попытка не удалась, нужно спросить клиента о другом времени".Выбирается инструмент AskUserTool.5. Инструкция для разработчика: Workflow создания агентаСледуйте этому алгоритму шаг за шагом.Шаг 1: Определить StateСпроектируйте implementation/{project}/state.py.Вопрос: Какие данные нужно помнить, если пользователь замолчит на час?Пример: current_order_id, is_authenticated, found_products_list.Шаг 2: Написать Services ("Руки")В services.py напишите функции. Они должны возвращать простые типы (str, dict, bool).Если функция делает запрос к API, оберните её в try/except и возвращайте понятные сообщения об ошибках.Шаг 3: Написать Tools ("Мозг")Для каждого сервиса создайте Pydantic-схему в tools/actions.py.Prompting Tip: В Field(description=...) пишите так, будто объясняете задачу стажеру.Плохо: description="Client name"Хорошо: description="Extract the client's name from the text. Capitalize the first letter. If not found, return None."Шаг 4: Собрать PlannerВ tools/planning.py создайте Router или AdaptivePlanner. В Literal перечислите имена всех ваших Action Tools.6. Observability & LoggingЛоги — единственный способ отладки "мыслей".Формат лога (JSON):{
  "timestamp": "2023-10-27T10:00:00",
  "level": "INFO",
  "session_id": "123-abc",
  "component": "Orchestrator",
  "event": "ToolCall",
  "payload": {
    "tool": "BookSlot",
    "analysis": "User confirmed 10 AM. Trace shows high confidence.",
    "args": {"time": "10:00"}
  }
}
7. Чек-лист качества (Definition of Done)Перед сдачей задачи разработчик обязан проверить:[ ] Reasoning Check: В логах видно поле analysis перед каждым действием.[ ] Error Resilience: Агент корректно реагирует, если я принудительно сломаю JSON в ответе LLM (симуляция сбоя).[ ] State Persistence: Я могу перезагрузить скрипт, загрузить старый state.json и продолжить диалог.[ ] Env Security: В коде нет хардкода токенов.[ ] No Hallucinations: Параметры Literal ограничивают выбор модели (например, список услуг строго задан).8. Common Pitfalls (Частые ошибки)Ошибка: Использование list или dict без типизации внутри Pydantic.Последствие: Модель сует туда мусор. Используйте List[str] или вложенные модели.Ошибка: Слишком длинный system_prompt.Последствие: Модель "забывает" инструкции. Переносите инструкции в description полей конкретных инструментов.Ошибка: Отсутствие ретраев.Последствие: Падение продакшена при малейшем сбое сети или модели.