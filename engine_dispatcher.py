"""
ZUKWEND — Multilingual Billing Agent
Engine Dispatcher & Cloud BYOC Strict Authentication Controller (v3.30)
Enforces zero silent fallback when invalid or missing cloud credentials are provided.
"""

import logging
import requests
from typing import Optional

logger = logging.getLogger("zukwend.engine_dispatcher")


class AuthenticationError(Exception):
    """Raised when Cloud BYOC authentication fails (missing key, invalid credentials, HTTP 401/403)."""
    pass


CLOUD_AUTH_ERROR_MSG = (
    "[ERROR] Cloud API Authentication Failed: Invalid or missing API Key. "
    "Please verify credentials in Settings."
)


def validate_cloud_api_key(api_key: Optional[str], provider: str = "anthropic") -> bool:
    """
    Validates that a cloud API key is present and performs an HTTPS authentication check.
    Raises AuthenticationError immediately if key is missing or invalid.
    """
    if not api_key or not str(api_key).strip():
        logger.error("Cloud BYOC authentication failed: API Key is missing or empty.")
        raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)

    key = str(api_key).strip()

    if provider.lower() == "anthropic":
        headers = {
            "x-api-key": key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        }
        try:
            # Probe endpoint with 1 token payload to verify credentials
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json={
                    "model": "claude-3-5-haiku-20241022",
                    "max_tokens": 1,
                    "messages": [{"role": "user", "content": "ping"}],
                },
                timeout=(5, 15),
            )
            if resp.status_code in (401, 403):
                logger.error(f"Cloud API rejected credentials with HTTP {resp.status_code}")
                raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
            # If 200 or 400 (e.g. prompt formatting), auth was accepted
            return True
        except requests.exceptions.HTTPError as e:
            if e.response is not None and e.response.status_code in (401, 403):
                raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
            raise e
        except requests.exceptions.RequestException as e:
            if hasattr(e, "response") and e.response is not None and e.response.status_code in (401, 403):
                raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
            # If network error but not 401/403:
            raise e

    return True


def dispatch_cloud_prompt(
    api_key: Optional[str],
    full_prompt: str,
    model: str = "claude-3-5-haiku-20241022",
    max_tokens: int = 1024,
    timeout: tuple = (5, 60),
) -> str:
    """
    Executes real HTTPS API call to cloud provider endpoint (Anthropic Claude BYOC).
    Strictly raises AuthenticationError if API key is invalid/missing or HTTP 401/403 is received.
    NEVER silently falls back to local engine.
    """
    if not api_key or not str(api_key).strip():
        logger.error("dispatch_cloud_prompt: Missing API Key.")
        raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)

    key = str(api_key).strip()
    headers = {
        "x-api-key": key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }

    try:
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json={
                "model": model,
                "max_tokens": max_tokens,
                "messages": [{"role": "user", "content": full_prompt}],
            },
            timeout=timeout,
        )
        if resp.status_code in (401, 403):
            logger.error(f"Cloud API returned HTTP {resp.status_code}: {resp.text}")
            raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
        resp.raise_for_status()
        data = resp.json()
        return data["content"][0]["text"].strip()
    except requests.exceptions.HTTPError as e:
        if e.response is not None and e.response.status_code in (401, 403):
            logger.error(f"Cloud API Authentication error HTTP {e.response.status_code}")
            raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
        raise e
    except requests.exceptions.RequestException as e:
        if hasattr(e, "response") and e.response is not None and e.response.status_code in (401, 403):
            raise AuthenticationError(CLOUD_AUTH_ERROR_MSG)
        raise e
