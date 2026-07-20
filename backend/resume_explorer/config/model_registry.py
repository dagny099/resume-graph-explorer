"""
Model registry — the single source of truth for which LLM models the app may
use, per provider, and the date that list was last verified.

Backed by ``models.yaml`` (edit that file to add/remove models; bump ``as_of``
when you re-verify against provider docs). Cloud providers (claude, openai) are
validated strictly against their list so a wrong/retired model fails fast at
startup with the valid options — instead of a silent 404 at request time.
Ollama is ``validation: open`` because local models are arbitrary pulled tags.
"""

import os
from functools import lru_cache
from typing import Any, Dict, List

import yaml

_REGISTRY_PATH = os.path.join(os.path.dirname(__file__), "models.yaml")


class ModelValidationError(ValueError):
    """Raised when a model isn't valid for its provider (unknown provider, or
    a model not in a strict provider's allow-list)."""


@lru_cache(maxsize=1)
def _registry() -> Dict[str, Any]:
    with open(_REGISTRY_PATH, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict) or "providers" not in data:
        raise ValueError(f"Invalid model registry at {_REGISTRY_PATH}")
    return data


def as_of() -> str:
    """Date the model lists were last verified against provider docs."""
    return str(_registry().get("as_of", "unknown"))


def list_providers() -> List[str]:
    return list(_registry()["providers"].keys())


def _provider_cfg(provider: str) -> Dict[str, Any]:
    providers = _registry()["providers"]
    if provider not in providers:
        raise ModelValidationError(
            f"Unknown provider '{provider}'. Known providers: {', '.join(providers)}."
        )
    return providers[provider]


def default_model(provider: str) -> str:
    return _provider_cfg(provider).get("default")


def list_models(provider: str) -> List[Dict[str, Any]]:
    """Full model dicts (id, label, pricing, notes) for a provider."""
    return _provider_cfg(provider).get("models", [])


def model_ids(provider: str) -> List[str]:
    return [m["id"] for m in list_models(provider)]


def is_open(provider: str) -> bool:
    """True when the provider accepts any model string (e.g. Ollama local tags)."""
    return _provider_cfg(provider).get("validation", "strict") == "open"


def validate_model(provider: str, model: str) -> None:
    """Raise ModelValidationError if ``model`` isn't allowed for ``provider``.

    Strict providers (claude, openai) require an exact id match; open providers
    (ollama) accept any non-empty value.
    """
    cfg = _provider_cfg(provider)
    if not model:
        raise ModelValidationError(f"No model specified for provider '{provider}'.")
    if cfg.get("validation", "strict") == "open":
        return
    ids = model_ids(provider)
    if model not in ids:
        raise ModelValidationError(
            f"Model '{model}' is not in the '{provider}' allow-list (as of "
            f"{as_of()}). Valid options: {', '.join(ids)}. Add it to "
            f"backend/resume_explorer/config/models.yaml if it's newly available."
        )


__all__ = [
    "ModelValidationError",
    "as_of",
    "list_providers",
    "default_model",
    "list_models",
    "model_ids",
    "is_open",
    "validate_model",
]
