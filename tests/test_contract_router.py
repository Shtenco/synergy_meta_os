import pytest

from runtime.contract_router import (
    ContractRouteError,
    FederationContractRouter,
    RouteRule,
    RouteStatus,
    ValidatedContractRef,
)


def router():
    return FederationContractRouter(
        [
            RouteRule("TradingExecutionIntent", "Shtenco/synergy_pay_system", "payment_execution_settlement"),
            RouteRule("FinancialCommitmentArtifact", "Shtenco/synergy_ai_blockchain", "pq_chain_trust"),
        ]
    )


def ref(**overrides):
    values = {
        "contract_id": "contract-1",
        "contract_type": "TradingExecutionIntent",
        "consumer_repo": "Shtenco/synergy_pay_system",
        "consumer_authority": "payment_execution_settlement",
        "correlation_id": "corr-1",
        "causation_id": None,
        "validation_receipt_ref": "synergy-system:validation:1",
    }
    values.update(overrides)
    return ValidatedContractRef(**values)


def test_routes_only_to_registered_consumer():
    decision = router().route(ref())
    assert decision.status == RouteStatus.ROUTE
    assert decision.consumer_repo == "Shtenco/synergy_pay_system"
    assert decision.topic.startswith("synergy.contract.synergy-pay-system.")


def test_consumer_authority_spoofing_is_rejected():
    with pytest.raises(ContractRouteError, match="consumer authority"):
        router().route(ref(consumer_authority="trading_intelligence"))


def test_unvalidated_reference_is_rejected():
    with pytest.raises(ContractRouteError, match="validation receipt"):
        ref(validation_receipt_ref="")


def test_duplicate_contract_is_not_routed_twice():
    r = router()
    first = r.route(ref())
    second = r.route(ref())
    assert first.status == RouteStatus.ROUTE
    assert second.status == RouteStatus.DUPLICATE
    assert second.topic is None


def test_meta_os_has_no_domain_execution_authority():
    assert FederationContractRouter.execution_authority == "NONE"
