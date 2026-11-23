"""L5 contract enforcer: deterministic code between the planner LLM and the tools.

Which tool, which arguments and how risky it is all come from the contract, never from the LLM or the alert.
"""

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from app.security.taint import ContractViolation, Tainted, untaint_via_contract


class Risk(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


APPROVAL_RISKS = {Risk.HIGH, Risk.CRITICAL}


class AllowedAction(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    tool: str
    args: dict[str, Any] = {}
    risk: Risk
    reversible: bool = True

    @field_validator("args")
    @classmethod
    def _valid_specs(cls, args: dict[str, Any]) -> dict[str, Any]:
        for name, spec in args.items():
            if isinstance(spec, list) and not spec:
                raise ValueError(f"{name}: empty allow-list")
            if isinstance(spec, dict) and not (
                spec.keys() == {"min", "max"}
                and all(isinstance(spec[k], (int, float)) and not isinstance(spec[k], bool) for k in spec)
                and spec["min"] <= spec["max"]
            ):
                raise ValueError(f"{name}: a dict spec must be a numeric {{min, max}} range")
        return args


@dataclass(frozen=True)
class ApprovedCall:
    """A tool call that passed the contract. Arguments are raw (untainted) values."""

    tool: str
    args: dict[str, Any]
    risk: Risk
    reversible: bool

    @property
    def requires_approval(self) -> bool:
        return self.risk in APPROVAL_RISKS or not self.reversible


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    playbook_id: str
    version: int
    applies_to: dict[str, Any] = {}
    preconditions: list[dict[str, Any]] = []
    allowed_actions: list[AllowedAction]
    postconditions: list[dict[str, Any]] = []
    rollback: list[dict[str, Any]] = []
    on_postcondition_fail: list[str] = ["rollback", "escalate"]

    @field_validator("allowed_actions")
    @classmethod
    def _unique_tools(cls, actions: list[AllowedAction]) -> list[AllowedAction]:
        tools = [a.tool for a in actions]
        if len(tools) != len(set(tools)):
            raise ValueError("each tool may appear once in allowed_actions")
        return actions

    def enforce(self, call: Any) -> ApprovedCall:
        """Checks one planner-proposed call {"tool": ..., "args": {...}}. Any other key (e.g. "risk") is ignored."""
        if not isinstance(call, dict) or not isinstance(call.get("args", {}), dict):
            raise ContractViolation("call must be a dict with an 'args' dict")
        tool = call.get("tool")
        tool = tool.value if isinstance(tool, Tainted) else tool
        action = next((a for a in self.allowed_actions if isinstance(tool, str) and a.tool == tool), None)
        if action is None:
            raise ContractViolation(f"tool {tool!r} not in contract {self.playbook_id}")
        args = call.get("args", {})
        if args.keys() != action.args.keys():
            raise ContractViolation(f"{tool}: arguments {sorted(map(str, args))} must be exactly {sorted(action.args)}")
        clean = {name: untaint_via_contract(name, value, action.args) for name, value in args.items()}
        return ApprovedCall(tool=action.tool, args=clean, risk=action.risk, reversible=action.reversible)
