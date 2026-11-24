
import hashlib
import json
import logging
import time
from dataclasses import dataclass

import litellm
from litellm import Cache, completion

from .config import settings


# --------------------------------------------------
# Model configuration
# --------------------------------------------------

PRIMARY_MODEL = settings.model
BACKUP_MODEL = "gemini/gemini-3.5-flash-lite"

# Primary model is always attempted before backup.
MODELS = [
    PRIMARY_MODEL,
    BACKUP_MODEL,
]


# --------------------------------------------------
# Logging configuration
# --------------------------------------------------

logger = logging.getLogger("nexora.llm")

if not logger.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s [%(levelname)s] %(message)s"
        )
    )
    logger.addHandler(handler)

logger.setLevel(logging.INFO)


# --------------------------------------------------
# LiteLLM cache configuration
# --------------------------------------------------

litellm.cache = Cache(type="local")

_RESPONSE_CACHE = {}


# --------------------------------------------------
# Custom exception and result
# --------------------------------------------------

class ProvidersUnavailable(Exception):
    pass


@dataclass
class Result:
    reply: str
    metadata: dict


# --------------------------------------------------
# Cache helpers
# --------------------------------------------------

def _cache_key(messages):
    raw = json.dumps(
        {
            "models": MODELS,
            "messages": messages
        },
        sort_keys=True,
        ensure_ascii=False
    )

    return hashlib.sha256(
        raw.encode("utf-8")
    ).hexdigest()


def _usage(response):
    usage = getattr(response, "usage", None)

    input_tokens = int(
        getattr(usage, "prompt_tokens", 0) or 0
    )

    output_tokens = int(
        getattr(usage, "completion_tokens", 0) or 0
    )

    return input_tokens, output_tokens


# --------------------------------------------------
# Safe error logging
# --------------------------------------------------

def _safe_error_message(exc, api_keys):
    message = str(exc)

    for api_key in api_keys:
        if api_key:
            message = message.replace(
                api_key,
                "[REDACTED]"
            )

    return message


# --------------------------------------------------
# Failure simulation
# --------------------------------------------------

def _simulation_map(header):
    result = {}

    if not header:
        return result

    for pair in header.split(","):
        if "=" not in pair:
            continue

        key, status = pair.strip().split("=", 1)

        if status.strip() in {
            "429", "500", "502", "503"
        }:
            result[key.strip()] = int(status.strip())

    return result


# --------------------------------------------------
# Main LLM inference function
# --------------------------------------------------

def ask(messages, failure_header=None):

    started = time.perf_counter()

    cache_key = _cache_key(messages)

    api_keys = settings.llm_api_keys or []

    # ----------------------------------------------
    # Check response cache
    # ----------------------------------------------

    if cache_key in _RESPONSE_CACHE:

        cached = _RESPONSE_CACHE[cache_key]

        logger.info("LLM cache hit")

        return Result(
            cached["reply"],
            {
                **cached["metadata"],
                "resolution_source": "LLM_CACHE",
                "latency_ms": max(
                    0,
                    int(
                        (time.perf_counter() - started) * 1000
                    )
                ),
                "key_id": None,
                "fallback_attempts": 0,
            }
        )

    # ----------------------------------------------
    # Check API keys
    # ----------------------------------------------

    if not api_keys:
        logger.error("No LLM API keys configured.")

        raise ProvidersUnavailable(
            "No LLM API keys configured."
        )

    logger.info(
        "Starting inference | primary=%s | backup=%s | configured_keys=%s",
        PRIMARY_MODEL,
        BACKUP_MODEL,
        len(api_keys)
    )

    # ----------------------------------------------
    # Failure simulation
    # ----------------------------------------------

    simulated = {}

    if settings.enable_failure_simulation:
        simulated = _simulation_map(failure_header)

    failures = 0
    errors = []

    # ----------------------------------------------
    # Try primary model, then backup model
    # ----------------------------------------------

    for model_index, model in enumerate(MODELS):

        is_fallback = model_index > 0

        if is_fallback:
            logger.warning(
                "PRIMARY MODEL FAILED | switching to backup=%s",
                model
            )

        # ------------------------------------------
        # Try every configured API key for this model
        # ------------------------------------------

        for index, api_key in enumerate(api_keys, start=1):

            key_id = f"key_{index}"

            if not api_key or not api_key.strip():

                failures += 1

                logger.error(
                    "Skipping %s: API key is empty.",
                    key_id
                )

                continue

            # --------------------------------------
            # Failure simulation
            # --------------------------------------

            if "*" in simulated or key_id in simulated:

                simulated_status = simulated.get(
                    key_id,
                    simulated.get("*")
                )

                failures += 1

                logger.warning(
                    "Failure simulation triggered | model=%s | key=%s | status=%s",
                    model,
                    key_id,
                    simulated_status
                )

                continue

            # --------------------------------------
            # Call Gemini through LiteLLM
            # --------------------------------------

            try:

                logger.info(
                    "Attempting inference | model=%s | key=%s",
                    model,
                    key_id
                )

                response = completion(
                    model=model,
                    messages=messages,
                    api_key=api_key,
                    caching=True,
                    timeout=45,
                )

                # ----------------------------------
                # Extract response
                # ----------------------------------

                content = response.choices[0].message.content

                if not content:
                    content = (
                        "I couldn't generate a response. "
                        "Please try again."
                    )

                # ----------------------------------
                # Extract token usage
                # ----------------------------------

                input_tokens, output_tokens = _usage(
                    response
                )

                latency = max(
                    0,
                    int(
                        (time.perf_counter() - started) * 1000
                    )
                )

                metadata = {
                    "resolution_source": (
                        "MODEL_FALLBACK"
                        if is_fallback
                        else "LIVE_INFERENCE"
                    ),
                    "model": model,
                    "latency_ms": latency,
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "key_id": key_id,
                    "fallback_attempts": failures,
                }

                # ----------------------------------
                # Save successful response in cache
                # ----------------------------------

                _RESPONSE_CACHE[cache_key] = {
                    "reply": content,
                    "metadata": metadata
                }

                logger.info(
                    "Inference successful | model=%s | key=%s | fallback=%s | latency_ms=%s",
                    model,
                    key_id,
                    is_fallback,
                    latency
                )

                return Result(
                    content,
                    metadata
                )

            # --------------------------------------
            # Capture provider errors
            # --------------------------------------

            except Exception as exc:

                status = getattr(
                    exc,
                    "status_code",
                    None
                )

                error_type = type(exc).__name__

                error_message = _safe_error_message(
                    exc,
                    api_keys
                )

                errors.append(
                    {
                        "model": model,
                        "key_id": key_id,
                        "type": error_type,
                        "status": status,
                        "message": error_message
                    }
                )

                logger.error(
                    "PROVIDER FAILURE | model=%s | key=%s | "
                    "type=%s | status=%s | message=%s",
                    model,
                    key_id,
                    error_type,
                    status,
                    error_message
                )

                failures += 1

                # Continue to the next API key.
                continue

    # ----------------------------------------------
    # All models and keys failed
    # ----------------------------------------------

    logger.error(
        "ALL MODELS UNAVAILABLE | models=%s | attempted=%s | failures=%s",
        len(MODELS),
        len(MODELS) * len(api_keys),
        failures
    )

    raise ProvidersUnavailable(
        "All configured Gemini models are unavailable. "
        f"Failed attempts: {failures}"
    )
