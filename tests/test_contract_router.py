import pytest

from runtime.contract_router import (
    ContractRouteError,
    FederationContractRouter,
    RouteReplayLedger,
    RouteRule,
    RouteStatus,
    ValidatedContractRef,
)


NOW = "2026-09-06T10:45:00Z"


def rules():
    return [
        RouteRule("TradingExecutionIntent", "Shtenco/synergy_pay_system", "payment_execution_settlement"),
        RouteRule("FinancialCommitmentArtifact", "Shtenco/synergy_ai_blockchain", "pq_chain_trust"),
    ]


def router(path):
    ledger = RouteReplayLedger(path)
    return FederationContractRouter(rules(), ledger), ledger


def ref(**overrides):
    values = {
        "contract_id": "contract-1",
        "contract_type": "TradingExecutionIntent",
        "contract_payload_hash": "a" * 64,
        "consumer_repo": "Shtenco/synergy_pay_system",
        "consumer_authority": "payment_execution_settlement",
        "correlation_id": "corr-1",
        "causation_id": None,
        "validation_receipt_ref": "synergy-system:validation:1",
    }
    values.update(overrides)
    return ValidatedContractRef(**values)


def test_routes_only_to_registered_consumer(tmp_path):
    r, ledger = router(tmp_path / "router.db")
    decision = r.route(ref(), NOW)
    assert decision.status == RouteStatus.ROUTE
    assert decision.consumer_repo == "Shtenco/synergy_pay_system"
    assert decision.topic.startswith("synergy.contract.synergy-pay-system.")
    assert ledger.count() == 1
    ledger.close()


def test_consumer_authority_spoofing_is_rejected(tmp_path):
    r, ledger = router(tmp_path / "router.db")
    with pytest.raises(ContractRouteError, match="consumer authority"):
        r.route(ref(consumer_authority="trading_intelligence"), NOW)
    assert ledger.count() == 0
    ledger.close()


def test_unvalidated_reference_is_rejected():
    with pytest.raises(ContractRouteError, match="validation receipt"):
        ref(validation_receipt_ref="")


def test_invalid_payload_hash_is_rejected():
    with pytest.raises(ContractRouteError, match="sha256"):
        ref(contract_payload_hash="not-a-hash")


def test_duplicate_contract_is_not_routed_twice(tmp_path):
    r, ledger = router(tmp_path / "router.db")
    first = r.route(ref(), NOW)
    second = r.route(ref(), NOW)
    assert first.status == RouteStatus.ROUTE
    assert second.status == RouteStatus.DUPLICATE
    assert second.topic is None
    assert ledger.count() == 1
    ledger.close()


def test_duplicate_is_still_duplicate_after_router_restart(tmp_path):
    db = tmp_path / "restart.db"
    r1, ledger1 = router(db)
    assert r1.route(ref(), NOW).status == RouteStatus.ROUTE
    ledger1.close()

    r2, ledger2 = router(db)
    assert r2.route(ref(), NOW).status == RouteStatus.DUPLICATE
    assert ledger2.count() == 1
    ledger2.close()


def test_same_contract_id_with_different_hash_is_conflict_not_duplicate(tmp_path):
    r, ledger = router(tmp_path / "conflict.db")
    assert r.route(ref(), NOW).status == RouteStatus.ROUTE
    with pytest.raises(ContractRouteError, match="conflicts with durable routing record"):
        r.route(ref(contract_payload_hash="b" * 64), NOW)
    assert ledger.count() == 1
    ledger.close()


def test_same_contract_id_cannot_be_retargeted(tmp_path):
    r, ledger = router(tmp_path / "retarget.db")
    assert r.route(ref(), NOW).status == RouteStatus.ROUTE
    with pytest.raises(ContractRouteError):
        r.route(
            ref(
                contract_type="FinancialCommitmentArtifact",
                consumer_repo="Shtenco/synergy_ai_blockchain",
                consumer_authority="pq_chain_trust",
            ),
            NOW,
        )
    ledger.close()


def test_meta_os_has_no_domain_execution_authority(tmp_path):
    r, ledger = router(tmp_path / "authority.db")
    assert FederationContractRouter.execution_authority == "NONE"
    assert FederationContractRouter.accounting_authority == "NONE"
    assert FederationContractRouter.payment_authority == "NONE"
    ledger.close()
