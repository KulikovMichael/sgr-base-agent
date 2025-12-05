from __future__ import annotations

from typing import Any, Dict


def mock_lookup(context_key: str) -> Dict[str, Any]:
    if not context_key:
        raise ValueError('context_key не может быть пустым')
    return {
        'context_key': context_key,
        'status': 'ok',
        'payload': {'message': 'Mock lookup result'},
    }


def mock_update(field: str, value: str) -> str:
    if not field:
        raise ValueError('field is required')
    return f'Updated {field} -> {value}'


def mock_finalize(summary: str) -> str:
    if 'error' in summary.lower():
        raise RuntimeError('Cannot finalize: summary contains error keyword')
    return f'Conversation closed with summary: {summary}'


SERVICES_REGISTRY = {
    'LookupInfo': mock_lookup,
    'UpdateRecord': mock_update,
    'FinalizeConversation': mock_finalize,
}
