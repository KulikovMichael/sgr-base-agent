# Инструкция для разработчика SGR-агента

## 1. Концепция SGR
Schema-Guided Reasoning (SGR) — это подход, в котором LLM никогда не генерирует произвольный текст для принятия решения. Модель **заполняет строго типизированные Pydantic-схемы**, в которых:

- `situation_analysis` вынуждает пошаговое рассуждение перед действием (Forced Reasoning).
- `trace` описывает уверенность и риски, чтобы можно было проводить автоматический аудит качества.
- `next_step_tool_name` выбирается из ограниченного `Literal`, что исключает галлюцинации в выборе инструментов.

Цикл управляется Python-оркестратором, который:
1. Формирует system-промпт из актуального `AgentState`.
2. Валидирует ответ модели схемой (в случае ошибки — автоматический retry).
3. Вызвает сервис (tool) и сохраняет результат в состояние.
4. Повторяет цикл, пока планировщик не вернёт `FinalAnswer`.

## 2. Базовая структура репозитория
```text
sgr_framework/
├── config/settings.py             # Загрузка переменных окружения
├── core/
│   ├── base_state.py              # Общий AgentState
│   ├── base_tool.py               # DecisionTrace + BaseSGRTool
│   ├── execution_logger.py        # JSONL-логи reasoning в `executions/`
│   ├── llm_gateway.py             # Обёртка над LiteLLM + retry + logging
│   ├── orchestrator.py            # Реализация цикла ReAct
│   └── exceptions.py              # Общие ошибки
└── implementation/base_agent/
    ├── state.py                   # Бизнес-стейт конкретного агента
    ├── services.py                # Моковые сервисы (руки)
    ├── tools/
    │   ├── actions.py             # Action-инструменты
    │   └── planning.py            # Adaptive Planner
    └── main.py                    # Точка входа
```

## 3. Как создать нового агента

### Шаг 1. Спроектировать состояние
Расширьте `BaseAgentState`, добавив бизнес-поля, которые должны переживать рестарт процесса.

```12:23:sgr_framework/implementation/base_agent/state.py
class BaseAgentBusinessState(BaseAgentState):
    client_name: Optional[str] = Field(...)
    intent: Optional[str] = Field(...)
    pending_questions: List[str] = Field(...)
```

**Памятка**:
- Все поля должны быть строго типизированы (никаких `dict`/`list` без generic).
- Добавьте методы-хелперы, если требуется предобработка (например, `remember_last_product()`).

### Шаг 2. Реализовать сервисный слой
Сервисы — это чистые функции, которые делают работу (ходят в API, базу, CRM). Они обязаны:
- Возвращать простые типы (`str`, `dict`, `bool`).
- Оборачивать ошибки в пользовательские сообщения.

```1:33:sgr_framework/implementation/base_agent/services.py
def mock_lookup(context_key: str) -> Dict[str, Any]:
    if not context_key:
        raise ValueError('context_key не может быть пустым')
    return {"context_key": context_key, "status": "ok", ...}
```

### Шаг 3. Описать инструменты (actions)
Каждый Action наследуется от `BaseSGRTool` и содержит внутреннюю модель `tool_arguments`.

```8:52:sgr_framework/implementation/base_agent/tools/actions.py
class LookupInfoTool(BaseSGRTool):
    tool_arguments: LookupInfoArguments = Field(
        ..., description='Параметры для запроса информации...'
    )
```

**Правила**:
- Документация пишется в `Field(description=...)` (это прямые инструкции модели).
- Используйте строгие типы (например, `Literal['silver', 'gold']`) там, где выбор ограничен.

### Шаг 4. Сконфигурировать планировщик
Adaptive Planner выбирает **ровно один** инструмент на шаг.

```9:24:sgr_framework/implementation/base_agent/tools/planning.py
AVAILABLE_ACTIONS = Literal['LookupInfo', 'UpdateRecord', 'FinalizeConversation', 'FinalAnswer']
class AdaptivePlannerTool(BaseSGRTool):
    tentative_plan: list[str] = Field(...)
    next_step_tool_name: AVAILABLE_ACTIONS = Field(...)
```

Добавьте все новые action-инструменты в `AVAILABLE_ACTIONS`, иначе модель не сможет их вызвать.

### Шаг 5. Подключить сервисы и оркестратор
В `main.py` зарегистрируйте сервисы и построите карту action-схем.

```16:34:sgr_framework/implementation/base_agent/main.py
def build_action_schemas() -> Dict[str, Type]:
    return {'LookupInfo': LookupInfoTool, ...}

def run_agent(user_messages: List[str]) -> None:
    state = BaseAgentBusinessState(session_id='demo-session')
    registry = ToolsRegistry(SERVICES_REGISTRY)
    orchestrator = Orchestrator(state=state, tools_registry=registry)
    ...
```

Для собственного агента создайте новый пакет `implementation/<your_agent>/...`, но повторите ту же структуру.

### Шаг 6. Настроить окружение
Файл `.env` (см. `.env.example`) должен содержать:

```
LITELLM_API_KEY=sk-...
LITELLM_BASE_URL=https://ваш-прокси (опционально)
MODEL_NAME=gpt-4o-mini
```

- `settings.py` автоматически подтянет переменные и передаст их в `LLMGateway`.
- Для локальных запусков используйте подготовленное окружение `.venv312` (`python3.12 -m venv`).

### Шаг 7. Тесты и чек-лист DoD
Минимально создайте:
- Тест сериализации стейта (`tests/test_state.py`).
- Тесты инструментов/планировщика (`tests/test_tools.py`).
- Тесты вспомогательных модулей (например, `test_execution_logger.py`).

Запуск:
```bash
./.venv312/bin/python -m pytest
```

### Шаг 8. Observability
SGR ведёт наблюдаемость на двух уровнях:
1. **Loguru JSON** — все Reasoning/Service Error события (`loguru` настроен на `serialize=True`).
2. **Execution logger** — каждая схема сохраняется в отдельном `executions/<session_id>_<timestamp>.json` с форматированным JSON.

```18:43:sgr_framework/core/execution_logger.py
log_file = _resolve_log_file(session_id)
...
json.dump(records, file, ensure_ascii=False, indent=2)
```

Используйте переменную `SGR_EXECUTIONS_DIR`, чтобы перенаправить логи, например, в общий каталог мониторинга.

## 4. Расширенные паттерны и развитие

### 4.1 Примеры паттернов Cascade/Routing/Cycle
- Создайте подпакет `implementation/patterns/<pattern_name>/` с теми же подпапками (`state.py`, `services.py`, `tools/`, `main.py`), чтобы демонстрировать готовые схемы рассуждений.
- В `tools/planning.py` каждого примера явно фиксируйте шаги паттерна (например, для Cascade — последовательные стадии фильтрации/валидации, для Routing — Literal с доступными маршрутами, для Cycle — ограничение числа повторов).
- Добавьте README внутри каждого паттерна с кратким описанием сценария и ссылкой на реальные бизнес-кейсы, чтобы команда могла копировать их как шаблон.

### 4.2 Отрицательные сценарии в тестах инструментов
- В `tests/test_tools.py` покрывайте случаи неверных аргументов, отсутствующих ключей и ошибок сервисов (используйте `pytest.raises`), чтобы убедиться, что схема корректно валидирует ввод.
- Для сложных инструментов заводите фикстуры с заведомо некорректными `tool_arguments`, проверяйте, что `ValidationError` и `ServiceExecutionError` логируются, а оркестратор продолжает работу.
- Поддерживайте паритет: для каждого нового инструмента минимум один позитивный и один негативный тест.

### 4.3 Множественные планировщики
- Если сценарий требует разных стратегий (например, быстрый FAQ vs. сложный разбор документов), храните несколько моделей планировщиков. Рекомендуем регистрировать их в `implementation/<agent>/tools/planning.py` как `DEFAULT_PLANNER`, `ROUTING_PLANNER` и т.д.
- В `run_agent` выбирайте планировщик на основе `state.intent` или внешней конфигурации и передавайте соответствующую схему в `orchestrator.run_step`.
- Для каждого планировщика поддерживайте свой набор `AVAILABLE_ACTIONS`, чтобы избежать пересечения инструментов и упрощать тестирование.

## 5. Быстрый чек-лист перед релизом
1. **Reasoning Check** — в логах обязательно есть `analysis` перед каждым действием.
2. **Error Resilience** — оркестратор продолжает работу после ошибок сервисов.
3. **State Persistence** — `state.to_json()` и `from_json()` восстанавливают контекст.
4. **Env Security** — ключи только в `.env`, без хардкода.
5. **Literal Constraints** — Planner и Tools ограничивают выбор действий.
6. **Execution Logs** — в папке `executions/` появляются записи по каждой сессии.

Следуя этим шагам, вы сможете быстро создать нового агента, адаптировать его к своему домену и сохранить соответствие стандартам SGR v3.0.

