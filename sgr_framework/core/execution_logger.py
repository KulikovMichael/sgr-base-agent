from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from pydantic import BaseModel


def _get_executions_dir() -> Path:
    base_dir = Path(os.getenv('SGR_EXECUTIONS_DIR', 'executions')).resolve()
    base_dir.mkdir(parents=True, exist_ok=True)
    return base_dir


_SESSION_LOG_FILES: Dict[str, Path] = {}


def _resolve_log_file(session_id: str) -> Path:
    if session_id not in _SESSION_LOG_FILES:
        timestamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S')
        _SESSION_LOG_FILES[session_id] = _get_executions_dir() / f'{session_id}_{timestamp}.json'
    return _SESSION_LOG_FILES[session_id]


def log_reasoning(session_id: str, phase: str, tool_name: str, payload: BaseModel) -> None:
    record: dict[str, Any] = {
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'session_id': session_id,
        'phase': phase,
        'tool': tool_name,
        'situation_analysis': getattr(payload, 'situation_analysis', ''),
        'trace': getattr(payload, 'trace').model_dump() if hasattr(payload, 'trace') else None,
        'schema': payload.model_dump(),
    }
    log_file = _resolve_log_file(session_id)

    if log_file.exists():
        try:
            with log_file.open('r', encoding='utf-8') as file:
                records: List[dict[str, Any]] = json.load(file)
        except json.JSONDecodeError:
            records = []
    else:
        records = []

    records.append(record)
    with log_file.open('w', encoding='utf-8') as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

