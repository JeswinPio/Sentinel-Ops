from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from app.security.contracts import Contract, Risk
from app.security.taint import ContractViolation, Tainted

CONTRACT_DOC = yaml.safe_load((Path(__file__).parents[1] / "fixtures" / "pg-disk-full.yaml").read_text())
CONTRACT = Contract.model_validate(CONTRACT_DOC)

CLEANUP = {"tool": "cleanup_old_logs", "args": {"container": "lab-postgres", "path": "/var/log/postgresql", "older_than_days": 7}}


def test_permitted_low_risk_call_needs_no_approval():
    call = CONTRACT.enforce(CLEANUP)
    assert call.risk == Risk.LOW
    assert call.requires_approval is False
    assert call.args["older_than_days"] == 7


def test_risk_comes_from_contract_not_from_the_plan():
    call = CONTRACT.enforce({"tool": "restart_container", "args": {"container": "lab-postgres"}, "risk": "LOW"})
    assert call.risk == Risk.CRITICAL
    assert call.requires_approval is True


def test_tainted_value_equal_to_allowed_value_is_untainted():
    plan = {"tool": "restart_container", "args": {"container": Tainted("lab-postgres", "alert.labels.container")}}
    assert CONTRACT.enforce(plan).args == {"container": "lab-postgres"}


def test_injected_argument_is_blocked_and_names_its_source():
    plan = {"tool": "restart_container", "args": {"container": Tainted("lab-postgres; rm -rf /", "log_line[3]")}}
    with pytest.raises(ContractViolation, match=r"log_line\[3\]"):
        CONTRACT.enforce(plan)


@pytest.mark.parametrize("plan", [
    {"tool": "drop_database", "args": {}},                                          # invented tool
    {"tool": Tainted("drop_database", "alert.message"), "args": {}},
    {"tool": "restart_container", "args": {"container": "lab-webapp"}},              # target swap
    {**CLEANUP, "args": {**CLEANUP["args"], "older_than_days": 0}},                  # below range
    {**CLEANUP, "args": {**CLEANUP["args"], "older_than_days": 31}},                 # above range
    {**CLEANUP, "args": {**CLEANUP["args"], "older_than_days": "7"}},                # wrong type
    {**CLEANUP, "args": {**CLEANUP["args"], "older_than_days": True}},               # bool is not a number
    {**CLEANUP, "args": {**CLEANUP["args"], "older_than_days": float("nan")}},
    {**CLEANUP, "args": {**CLEANUP["args"], "path": "/var/log/postgresql/../../etc"}},  # traversal
    {**CLEANUP, "args": {**CLEANUP["args"], "extra": 1}},                            # extra argument
    {"tool": "cleanup_old_logs", "args": {"container": "lab-postgres"}},              # missing arguments
    {"tool": "restart_container", "args": "container=lab-postgres"},                 # args not a dict
    "restart_container lab-postgres",                                                # not a dict at all
])
def test_out_of_contract_calls_are_blocked(plan):
    with pytest.raises(ContractViolation):
        CONTRACT.enforce(plan)


@pytest.mark.parametrize("bad_actions", [
    [{"tool": "t", "risk": "LOW"}, {"tool": "t", "risk": "CRITICAL"}],           # duplicate tool
    [{"tool": "t", "risk": "LOW", "args": {"a": []}}],                            # empty allow-list
    [{"tool": "t", "risk": "LOW", "args": {"a": {"min": 5, "max": 1}}}],          # inverted range
    [{"tool": "t", "risk": "LOW", "args": {"a": {"min": 1}}}],                    # incomplete range
    [{"tool": "t", "risk": "SAFE"}],                                              # unknown risk
])
def test_malformed_contracts_are_rejected_at_load(bad_actions):
    with pytest.raises(ValidationError):
        Contract.model_validate({**CONTRACT_DOC, "allowed_actions": bad_actions})
