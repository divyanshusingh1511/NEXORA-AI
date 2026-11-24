import hashlib, json, time
from dataclasses import dataclass
from litellm import completion
import litellm
from litellm import Cache
from .config import settings

# LiteLLM's built-in local cache is enabled. A small in-process response index
# is also used to reliably label cache hits and retain the original usage metadata.
litellm.cache = Cache(type="local")
_RESPONSE_CACHE = {}

class ProvidersUnavailable(Exception):
    pass

@dataclass
class Result:
    reply: str
    metadata: dict

def _cache_key(messages):
    raw = json.dumps({"model": settings.model, "messages": messages}, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def _usage(response):
    usage = getattr(response, "usage", None)
    return int(getattr(usage, "prompt_tokens", 0) or 0), int(getattr(usage, "completion_tokens", 0) or 0)

def _simulation_map(header):
    result = {}
    if not header:
        return result
    for pair in header.split(","):
        if "=" not in pair:
            continue
        key, status = pair.strip().split("=", 1)
        if status.strip() in {"429", "500", "502", "503"}:
            result[key.strip()] = int(status.strip())
    return result

def ask(messages, failure_header=None):
    key = _cache_key(messages)
    started = time.perf_counter()
    if key in _RESPONSE_CACHE:
        cached = _RESPONSE_CACHE[key]
        return Result(cached["reply"], {
            **cached["metadata"],
            "resolution_source": "LLM_CACHE",
            "latency_ms": max(0, int((time.perf_counter() - started) * 1000)),
            "key_id": None,
            "fallback_attempts": 0,
        })

    if not settings.llm_api_keys:
        raise ProvidersUnavailable()

    simulated = _simulation_map(failure_header) if settings.enable_failure_simulation else {}
    failures = 0
    for index, api_key in enumerate(settings.llm_api_keys, start=1):
        key_id = f"key_{index}"
        if "*" in simulated or key_id in simulated:
            failures += 1
            continue
        try:
            response = completion(
                model=settings.model,
                messages=messages,
                api_key=api_key,
                caching=True,
                timeout=45,
            )
            content = response.choices[0].message.content
            if not content:
                content = "I couldn't generate a response. Please try again."
            input_tokens, output_tokens = _usage(response)
            latency = max(0, int((time.perf_counter() - started) * 1000))
            metadata = {
                "resolution_source": "LIVE_INFERENCE",
                "model": settings.model,
                "latency_ms": latency,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "key_id": key_id,
                "fallback_attempts": failures,
            }
            _RESPONSE_CACHE[key] = {"reply": content, "metadata": metadata}
            return Result(content, metadata)
        except Exception as exc:
            status = getattr(exc, "status_code", None)
            name = type(exc).__name__.lower()
            retryable = status in (429, 500, 502, 503) or any(x in name for x in ("ratelimit", "quota", "serviceunavailable", "internalserver"))
            if retryable:
                failures += 1
                continue
            # Authentication/configuration errors also move to the next configured key.
            failures += 1
    raise ProvidersUnavailable()
