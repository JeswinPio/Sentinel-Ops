import copy

import pytest
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from app.security.signing import ContractSignatureError, load_contract, sign_contract, verify_contract
from tests.unit.test_contracts import CONTRACT_DOC

KEY = Ed25519PrivateKey.generate()
TRUSTED = {"reviewer-1": KEY.public_key()}
SIGNED = sign_contract(CONTRACT_DOC, KEY, "reviewer-1")


def test_signed_contract_loads():
    contract = load_contract(SIGNED, TRUSTED)
    assert contract.playbook_id == "pg-disk-full"


def test_loaded_contract_is_not_affected_by_later_edits_to_the_document():
    doc = copy.deepcopy(SIGNED)
    contract = load_contract(doc, TRUSTED)
    doc["allowed_actions"][1]["args"]["container"].append("lab-webapp")
    assert contract.allowed_actions[1].args["container"] == ["lab-postgres"]


def test_modified_contract_is_refused():
    doc = copy.deepcopy(SIGNED)
    doc["allowed_actions"][1]["risk"] = "LOW"  # attacker downgrades restart to auto-execute
    with pytest.raises(ContractSignatureError):
        load_contract(doc, TRUSTED)


@pytest.mark.parametrize("signature", [
    None,
    "not-a-dict",
    {"alg": "rsa", "key_id": "reviewer-1", "value": SIGNED["signature"]["value"]},
    {"alg": "ed25519", "key_id": "attacker", "value": SIGNED["signature"]["value"]},
    {"alg": "ed25519", "key_id": ["reviewer-1"], "value": SIGNED["signature"]["value"]},
    {"alg": "ed25519", "key_id": "reviewer-1", "value": "%%%not base64%%%"},
    {"alg": "ed25519", "key_id": "reviewer-1"},
])
def test_bad_or_missing_signatures_are_refused(signature):
    doc = {**SIGNED, "signature": signature}
    with pytest.raises(ContractSignatureError):
        verify_contract(doc, TRUSTED)


def test_contract_signed_by_untrusted_key_is_refused():
    forged = sign_contract(CONTRACT_DOC, Ed25519PrivateKey.generate(), "reviewer-1")
    with pytest.raises(ContractSignatureError):
        verify_contract(forged, TRUSTED)
