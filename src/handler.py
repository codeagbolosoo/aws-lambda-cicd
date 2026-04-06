"""
src/handler.py - Lambda entry point
Author: Abraham Agbolosoo
"""

import json
import logging
import os

logger = logging.getLogger()
logger.setLevel(logging.INFO)

STAGE = os.environ.get("STAGE", "dev")


def lambda_handler(event: dict, context) -> dict:
    """
    Main Lambda handler.
    Supports:
      - {"ping": true}  smoke test used by CI pipeline staging deploy
      - Any other event  your application logic
    """
    logger.info("Event received on stage=%s: %s", STAGE, json.dumps(event))

    if event.get("ping"):
        logger.info("Ping received - responding pong")
        return {"statusCode": 200, "body": "pong"}

    try:
        result = process(event)
        return {
            "statusCode": 200,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps(result),
        }
    except ValueError as exc:
        logger.warning("Validation error: %s", exc)
        return {"statusCode": 400, "body": json.dumps({"error": str(exc)})}
    except Exception as exc:
        logger.error("Unhandled error: %s", exc, exc_info=True)
        return {"statusCode": 500, "body": json.dumps({"error": "Internal server error"})}


def process(event: dict) -> dict:
    """Core business logic - replace with your own implementation."""
    name = event.get("name", "World")
    if not isinstance(name, str):
        raise ValueError("'name' must be a string")
    return {"message": f"Hello, {name}!", "stage": STAGE}
