from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class ContractRouteError(ValueError):
    pass


class RouteStatus(str, Enum):
    ROUTE = "ROUTE"
    DUPLICATE = "DUPLICATE"


@dataclass(frozen=True)
class RouteRule:
    contract_type: str
    consumer_repo: str
    consumer_authority: str


@dataclass(frozen=True)
class ValidatedContractRef:
    contract_id: str
    contract_type: str
    consumer_repo: str
    consumer_authority: str
    correlation_id: str
    causation_id: str | None
    validation_receipt_ref: str

    def __post_init__(self) -> None:
        if not self.contract_id or not self.contract_type:
            raise ContractRouteError("contract_id and contract_type are required")
        if not self.validation_receipt_ref:
            raise ContractRouteError("validated contract routing requires a validation receipt")


@dataclass(frozen=True)
class RouteDecision:
    status: RouteStatus
    contract_id: str
    topic: str | None
    consumer_repo: str
    consumer_authority: str


class FederationContractRouter:
    """Routes validated references only. It never executes domain actions."""

    execution_authority = "NONE"

    def __init__(self, rules: list[RouteRule]):
        self._rules = {rule.contract_type: rule for rule in rules}
        if len(self._rules) != len(rules):
            raise ContractRouteError("duplicate contract_type route rule")
        self._seen_contract_ids: set[str] = set()

    @staticmethod
    def topic_for(rule: RouteRule) -> str:
        repo_slug = rule.consumer_repo.replace("Shtenco/", "").replace("_", "-")
        contract_slug = "".join(("-" + c.lower()) if c.isupper() else c for c in rule.contract_type).lstrip("-")
        return f"synergy.contract.{repo_slug}.{contract_slug}.v1"

    def route(self, ref: ValidatedContractRef) -> RouteDecision:
        rule = self._rules.get(ref.contract_type)
        if rule is None:
            raise ContractRouteError(f"unregistered contract route: {ref.contract_type}")
        if ref.consumer_repo != rule.consumer_repo:
            raise ContractRouteError("consumer repo does not match route registry")
        if ref.consumer_authority != rule.consumer_authority:
            raise ContractRouteError("consumer authority does not match route registry")

        if ref.contract_id in self._seen_contract_ids:
            return RouteDecision(
                status=RouteStatus.DUPLICATE,
                contract_id=ref.contract_id,
                topic=None,
                consumer_repo=ref.consumer_repo,
                consumer_authority=ref.consumer_authority,
            )

        self._seen_contract_ids.add(ref.contract_id)
        return RouteDecision(
            status=RouteStatus.ROUTE,
            contract_id=ref.contract_id,
            topic=self.topic_for(rule),
            consumer_repo=ref.consumer_repo,
            consumer_authority=ref.consumer_authority,
        )
