from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Iterator


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
    contract_payload_hash: str
    consumer_repo: str
    consumer_authority: str
    correlation_id: str
    causation_id: str | None
    validation_receipt_ref: str

    def __post_init__(self) -> None:
        if not self.contract_id or not self.contract_type:
            raise ContractRouteError("contract_id and contract_type are required")
        if len(self.contract_payload_hash) != 64:
            raise ContractRouteError("contract_payload_hash must be a sha256 hex digest")
        try:
            int(self.contract_payload_hash, 16)
        except ValueError as exc:
            raise ContractRouteError("contract_payload_hash must be hexadecimal") from exc
        if not self.validation_receipt_ref:
            raise ContractRouteError("validated contract routing requires a validation receipt")


@dataclass(frozen=True)
class RouteDecision:
    status: RouteStatus
    contract_id: str
    topic: str | None
    consumer_repo: str
    consumer_authority: str


class RouteReplayLedger:
    """Persistent Meta-OS idempotency ledger.

    A retry of the same immutable contract is a DUPLICATE. Reusing a contract_id
    for a different payload, type, consumer, authority or correlation is a conflict.
    """

    def __init__(self, path: str | Path):
        self.path = str(path)
        self.conn = sqlite3.connect(self.path, isolation_level=None, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self.conn.execute("PRAGMA busy_timeout=5000")
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS routed_contracts (
                contract_id TEXT PRIMARY KEY,
                contract_type TEXT NOT NULL,
                contract_payload_hash TEXT NOT NULL,
                consumer_repo TEXT NOT NULL,
                consumer_authority TEXT NOT NULL,
                correlation_id TEXT NOT NULL,
                causation_id TEXT,
                validation_receipt_ref TEXT NOT NULL,
                first_seen_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_routed_correlation ON routed_contracts(correlation_id, first_seen_at)"
        )

    def close(self) -> None:
        self.conn.close()

    @contextmanager
    def transaction(self) -> Iterator[sqlite3.Connection]:
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            yield self.conn
        except Exception:
            self.conn.execute("ROLLBACK")
            raise
        else:
            self.conn.execute("COMMIT")

    @staticmethod
    def _fingerprint(ref: ValidatedContractRef) -> tuple[str, ...]:
        return (
            ref.contract_type,
            ref.contract_payload_hash,
            ref.consumer_repo,
            ref.consumer_authority,
            ref.correlation_id,
            ref.causation_id or "",
        )

    def record_once(self, ref: ValidatedContractRef, now: str) -> bool:
        with self.transaction() as tx:
            row = tx.execute(
                "SELECT * FROM routed_contracts WHERE contract_id=?",
                (ref.contract_id,),
            ).fetchone()
            if row is not None:
                stored = (
                    row["contract_type"],
                    row["contract_payload_hash"],
                    row["consumer_repo"],
                    row["consumer_authority"],
                    row["correlation_id"],
                    row["causation_id"] or "",
                )
                if stored != self._fingerprint(ref):
                    raise ContractRouteError("contract_id replay conflicts with durable routing record")
                return False
            tx.execute(
                """
                INSERT INTO routed_contracts(
                    contract_id, contract_type, contract_payload_hash,
                    consumer_repo, consumer_authority, correlation_id, causation_id,
                    validation_receipt_ref, first_seen_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ref.contract_id,
                    ref.contract_type,
                    ref.contract_payload_hash,
                    ref.consumer_repo,
                    ref.consumer_authority,
                    ref.correlation_id,
                    ref.causation_id,
                    ref.validation_receipt_ref,
                    now,
                ),
            )
            return True

    def count(self) -> int:
        return int(self.conn.execute("SELECT COUNT(*) FROM routed_contracts").fetchone()[0])


class FederationContractRouter:
    """Routes validated immutable references only. It never executes domain actions."""

    execution_authority = "NONE"
    accounting_authority = "NONE"
    payment_authority = "NONE"

    def __init__(self, rules: list[RouteRule], replay_ledger: RouteReplayLedger):
        self._rules = {rule.contract_type: rule for rule in rules}
        if len(self._rules) != len(rules):
            raise ContractRouteError("duplicate contract_type route rule")
        self._replay_ledger = replay_ledger

    @staticmethod
    def topic_for(rule: RouteRule) -> str:
        repo_slug = rule.consumer_repo.replace("Shtenco/", "").replace("_", "-")
        contract_slug = "".join(("-" + c.lower()) if c.isupper() else c for c in rule.contract_type).lstrip("-")
        return f"synergy.contract.{repo_slug}.{contract_slug}.v1"

    def route(self, ref: ValidatedContractRef, now: str) -> RouteDecision:
        rule = self._rules.get(ref.contract_type)
        if rule is None:
            raise ContractRouteError(f"unregistered contract route: {ref.contract_type}")
        if ref.consumer_repo != rule.consumer_repo:
            raise ContractRouteError("consumer repo does not match route registry")
        if ref.consumer_authority != rule.consumer_authority:
            raise ContractRouteError("consumer authority does not match route registry")

        inserted = self._replay_ledger.record_once(ref, now)
        if not inserted:
            return RouteDecision(
                status=RouteStatus.DUPLICATE,
                contract_id=ref.contract_id,
                topic=None,
                consumer_repo=ref.consumer_repo,
                consumer_authority=ref.consumer_authority,
            )

        return RouteDecision(
            status=RouteStatus.ROUTE,
            contract_id=ref.contract_id,
            topic=self.topic_for(rule),
            consumer_repo=ref.consumer_repo,
            consumer_authority=ref.consumer_authority,
        )
