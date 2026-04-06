"""
tests/test_handler.py - pytest unit tests for src/handler.py
Author: Abraham Agbolosoo
Run: pytest tests/ --cov=src --cov-report=term-missing
"""

import json
import pytest
from unittest.mock import MagicMock

from src.handler import lambda_handler, process


@pytest.fixture
def context():
    ctx = MagicMock()
    ctx.function_name = "my-python-lambda"
    ctx.aws_request_id = "test-request-id"
    ctx.get_remaining_time_in_millis.return_value = 30000
    return ctx


def test_ping_returns_pong(context):
    response = lambda_handler({"ping": True}, context)
    assert response["statusCode"] == 200
    assert response["body"] == "pong"


def test_default_greeting(context):
    response = lambda_handler({}, context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Hello, World!"


def test_custom_name(context):
    response = lambda_handler({"name": "Abraham"}, context)
    assert response["statusCode"] == 200
    body = json.loads(response["body"])
    assert body["message"] == "Hello, Abraham!"


def test_response_has_correct_headers(context):
    response = lambda_handler({"name": "Test"}, context)
    assert response["headers"]["Content-Type"] == "application/json"


def test_invalid_name_type_returns_400(context):
    response = lambda_handler({"name": 123}, context)
    assert response["statusCode"] == 400
    body = json.loads(response["body"])
    assert "error" in body


def test_process_returns_message():
    result = process({"name": "Abraham"})
    assert result["message"] == "Hello, Abraham!"


def test_process_default_name():
    result = process({})
    assert result["message"] == "Hello, World!"


def test_process_raises_on_non_string():
    with pytest.raises(ValueError, match="'name' must be a string"):
        process({"name": ["not", "a", "string"]})


def test_unhandled_exception_returns_500(context, monkeypatch):
    def boom(event):
        raise RuntimeError("Something exploded")
    monkeypatch.setattr("src.handler.process", boom)
    response = lambda_handler({"name": "Test"}, context)
    assert response["statusCode"] == 500
    body = json.loads(response["body"])
    assert body["error"] == "Internal server error"
