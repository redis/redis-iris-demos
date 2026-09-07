from __future__ import annotations

import importlib
import importlib.util
import sys
from functools import lru_cache
from pathlib import Path

from backend.app.core.domain_contract import DomainPack
from backend.app.settings import Settings

ROOT = Path(__file__).resolve().parents[3]


def _module_name(domain_id: str) -> str:
    return f"domains.{domain_id}.domain"


def _load_hyphenated_domain_module(domain_id: str):
    """Load domains/<id>/domain.py when <id> is not a valid Python package name."""
    path = ROOT / "domains" / domain_id / "domain.py"
    if not path.exists():
        raise ModuleNotFoundError(_module_name(domain_id))
    mod_name = f"domains_{domain_id.replace('-', '_')}_domain"
    spec = importlib.util.spec_from_file_location(mod_name, path)
    if spec is None or spec.loader is None:
        raise ModuleNotFoundError(_module_name(domain_id))
    module = importlib.util.module_from_spec(spec)
    sys.modules[mod_name] = module
    spec.loader.exec_module(module)
    return module


@lru_cache(maxsize=16)
def load_domain(domain_id: str) -> DomainPack:
    try:
        module = importlib.import_module(_module_name(domain_id))
    except ModuleNotFoundError:
        module = _load_hyphenated_domain_module(domain_id)
    domain = getattr(module, "DOMAIN", None)
    if domain is None:
        raise RuntimeError(f"Domain module '{_module_name(domain_id)}' must export DOMAIN")
    errors = domain.validate()
    if errors:
        joined = "\n".join(f"- {error}" for error in errors)
        raise RuntimeError(f"Domain '{domain_id}' failed validation:\n{joined}")
    return domain


def get_active_domain(settings: Settings) -> DomainPack:
    return load_domain(settings.demo_domain)
