from __future__ import annotations

import os
import sys
from typing import Any, List, Type

from loguru import logger
from litellm import completion
from pydantic import BaseModel, ValidationError
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_fixed

from sgr_framework.config.settings import settings
from sgr_framework.core.exceptions import SchemaValidationError


logger.remove()
logger.add(sys.stdout, serialize=True, level='INFO')
os.environ.setdefault('LITELLM_API_KEY', settings.litellm_api_key)
os.environ.setdefault('OPENAI_API_KEY', settings.litellm_api_key)


class LLMGateway:
    def __init__(self, model_name: str | None = None, base_url: str | None = None):
        self.model_name = model_name or settings.model_name
        self.base_url = base_url if base_url is not None else settings.litellm_base_url

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_fixed(1),
        retry=retry_if_exception_type((SchemaValidationError, RuntimeError)),
    )
    def generate(self, schema_model: Type[BaseModel], messages: List[dict[str, Any]]) -> BaseModel:
        request_payload = {
            'model': self.model_name,
            'messages': messages,
            'response_format': schema_model,
        }
        if self.base_url:
            request_payload['base_url'] = self.base_url
        response = completion(**request_payload)
        content = response.choices[0].message.content
        log_payload = {
            'component': 'LLMGateway',
            'event': 'Completion',
            'model': self.model_name,
            'raw_content': content,
        }
        logger.bind(**log_payload).info('LLMResponseCaptured')
        try:
            return schema_model.model_validate_json(content)
        except ValidationError as exc:
            logger.bind(component='LLMGateway', event='SchemaValidationError').error(
                {'schema': schema_model.__name__, 'errors': exc.errors()}
            )
            raise SchemaValidationError(str(exc)) from exc
