import importlib
import json

import pytest

from sgr_framework.core.base_tool import BaseSGRTool


class _DummyTool(BaseSGRTool):
    pass


@pytest.mark.usefixtures('monkeypatch')
def test_log_reasoning_writes_json(monkeypatch, tmp_path):
    monkeypatch.setenv('SGR_EXECUTIONS_DIR', str(tmp_path))
    module = importlib.import_module('sgr_framework.core.execution_logger')
    importlib.reload(module)

    payload = _DummyTool(
        situation_analysis='Нужно проверить логирование.',
        trace={'confidence': 0.8, 'risks': ['Нет контекста']},
    )

    module.log_reasoning('session-42', 'planning', 'TestTool', payload)

    log_files = list(tmp_path.glob('session-42_*.json'))
    assert len(log_files) == 1
    raw_content = log_files[0].read_text(encoding='utf-8')
    records = json.loads(raw_content)
    assert isinstance(records, list)
    assert len(records) == 1
    record = records[0]
    assert record['tool'] == 'TestTool'
    assert record['schema']['situation_analysis'] == 'Нужно проверить логирование.'

