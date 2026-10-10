"""ATS integration providers."""
from __future__ import annotations
from app.services.ats.base import ATSProvider
from app.services.ats.greenhouse import GreenhouseProvider
from app.services.ats.lever import LeverProvider
from app.services.ats.workday import WorkdayProvider

_PROVIDERS = {
    "greenhouse": GreenhouseProvider,
    "lever": LeverProvider,
    "workday": WorkdayProvider,
}

SUPPORTED_PROVIDERS = tuple(_PROVIDERS.keys())


def get_provider(name: str, connection) -> ATSProvider:
    """Return an ATSProvider instance for ``name`` bound to ``connection``.

    Raises ValueError for unknown providers.
    """
    cls = _PROVIDERS.get((name or "").lower())
    if not cls:
        raise ValueError(f"Unsupported ATS provider: {name}")
    return cls(connection)


__all__ = ["get_provider", "ATSProvider", "SUPPORTED_PROVIDERS"]
