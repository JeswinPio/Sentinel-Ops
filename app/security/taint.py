"""L5 taint tracking: values derived from alerts, logs or retrieved text reach a tool only if the contract permits them."""

from dataclasses import dataclass
from typing import Any


class ContractViolation(Exception):
    """A proposed tool call is not permitted by the contract. The call must be blocked, never retried as-is."""


@dataclass(frozen=True)
class Tainted:
    value: Any
    source: str  # e.g. "alert.message", "log_line[42]"


def _same(a: Any, b: Any) -> bool:
    # Strict type match: stops True == 1, 1.0 == 1 and "3" vs 3 from slipping past an allow-list.
    return type(a) is type(b) and a == b


def untaint_via_contract(arg_name: str, v: Any, allowed: dict) -> Any:
    """Returns the raw value if the contract permits it for arg_name, else raises ContractViolation."""
    raw = v.value if isinstance(v, Tainted) else v
    if arg_name not in allowed:
        raise ContractViolation(f"argument {arg_name!r} not in contract")
    spec = allowed[arg_name]
    if isinstance(spec, list):
        if any(_same(raw, item) for item in spec):
            return raw
    elif isinstance(spec, dict):
        if isinstance(raw, (int, float)) and not isinstance(raw, bool) and spec["min"] <= raw <= spec["max"]:
            return raw
    elif _same(raw, spec):
        return raw
    raise ContractViolation(f"{arg_name}={raw!r} from {getattr(v, 'source', 'llm')} not permitted")
