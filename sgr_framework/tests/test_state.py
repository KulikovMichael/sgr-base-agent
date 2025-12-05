from sgr_framework.implementation.base_agent.state import BaseAgentBusinessState


def test_state_persistence_roundtrip():
    state = BaseAgentBusinessState(session_id='test', client_name='Alice')
    state.add_user_message('hello')
    payload = state.to_json()

    restored = BaseAgentBusinessState.from_json(payload)

    assert restored.session_id == 'test'
    assert restored.chat_history[-1]['content'] == 'hello'
    assert restored.client_name == 'Alice'
