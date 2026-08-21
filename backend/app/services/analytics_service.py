"""Aggregations for the operations dashboard and analytics pages.

All inputs come from principal-scoped repositories, so a support agent's
dashboard reflects only their assigned accounts while a manager sees everything.
SLA breach status is computed live against the dataset snapshot.
"""

from __future__ import annotations

from collections import Counter, defaultdict

from sqlalchemy.orm import Session

from app.core.security import Principal
from app.services.known_issues import KNOWN_ISSUES, match_known_issues
from app.services.sla_service import compute_sla


class AnalyticsService:
    def __init__(self, session: Session, principal: Principal) -> None:
        from app.repositories.logistics_repo import (
            AgreementRepository,
            OrderRepository,
            TicketRepository,
        )
        from app.repositories.organization_repo import AccountRepository
        from app.repositories.workflow_repo import EscalationRepository

        self.session = session
        self.principal = principal
        self.accounts = AccountRepository(session, principal).list_accounts()
        self.orders = OrderRepository(session, principal).list_all()
        self.tickets = TicketRepository(session, principal).list_all()
        self.escalations = EscalationRepository(session, principal).list_recent()
        self._agr_repo = AgreementRepository(session, principal)
        self._acct_by_id = {a.id: a for a in self.accounts}

    # --- shared computation ---------------------------------------------
    def _open_tickets_with_sla(self) -> list[dict]:
        rows = []
        for t in self.tickets:
            if t.status != "open" or not t.business_created_at:
                continue
            account = self._acct_by_id.get(t.account_id)
            if account is None:
                continue
            agreement = self._agr_repo.get_current_for_account(t.account_id)
            sla = compute_sla(account, agreement, t.severity or "P3", t.business_created_at)
            rows.append({
                "code": t.code, "account": account.name, "account_code": account.code,
                "subject": t.subject, "severity": t.severity or "P3", "assigned_to": t.assigned_to,
                "sla_target": sla.target_human, "breached": sla.breached,
                "remaining_minutes": sla.remaining_minutes, "source": sla.source,
            })
        return rows

    # --- dashboard -------------------------------------------------------
    def dashboard(self) -> dict:
        open_sla = self._open_tickets_with_sla()
        high_sev = [r for r in open_sla if r["severity"] in ("P1", "P2")]
        breaches = [r for r in open_sla if r["breached"]]

        recurring = Counter()
        for t in self.tickets:
            for m in match_known_issues(f"{t.subject} {t.description}"):
                recurring[m["code"]] += 1

        carrier_counter = Counter(o.carrier for o in self.orders)
        carrier_fault = Counter(o.carrier for o in self.orders if o.carrier_fault)

        insights = self._ai_insights(open_sla, breaches, recurring, carrier_fault)

        return {
            "totals": {
                "accounts": len(self.accounts),
                "open_tickets": len([t for t in self.tickets if t.status == "open"]),
                "orders": len(self.orders),
                "sla_breaches": len(breaches),
                "escalations": len(self.escalations),
            },
            "high_severity_tickets": sorted(high_sev, key=lambda r: (r["severity"], not r["breached"])),
            "sla_breaches": breaches,
            "recurring_problems": [
                {**next(k for k in KNOWN_ISSUES if k["code"] == code), "count": n}
                for code, n in recurring.most_common()
            ],
            "carrier_problems": [
                {"carrier": c, "orders": carrier_counter[c], "fault_orders": carrier_fault.get(c, 0)}
                for c in carrier_counter
            ],
            "customer_health": sorted(
                [{"code": a.code, "name": a.name, "plan": a.plan, "health_score": a.health_score}
                 for a in self.accounts],
                key=lambda a: a["health_score"],
            ),
            "recent_escalations": [
                {"code": e.code, "severity": e.severity, "reason": e.reason,
                 "assigned_to": e.assigned_to, "status": e.status,
                 "created_at": e.created_at.isoformat()}
                for e in self.escalations
            ],
            "open_investigations": [k for k in KNOWN_ISSUES if k["status"] in ("Investigating", "Monitoring")],
            "ai_insights": insights,
        }

    def _ai_insights(self, open_sla, breaches, recurring, carrier_fault) -> list[str]:
        out = []
        p1_breaches = [r for r in breaches if r["severity"] == "P1"]
        if p1_breaches:
            out.append(f"🚨 {len(p1_breaches)} P1 SLA(s) breached and need immediate escalation: "
                       + ", ".join(r["code"] for r in p1_breaches) + ".")
        if recurring.get("KI-208"):
            out.append(f"📈 KI-208 (bulk-upload) is affecting {recurring['KI-208']} ticket(s); recommend proactive notice to Growth/Enterprise accounts.")
        if recurring.get("KI-211"):
            out.append("⚠️ KI-211 (SwiftShip webhook delay) is present — verify carrier status before telling customers a pickup failed.")
        if carrier_fault:
            worst = carrier_fault.most_common(1)[0]
            out.append(f"🚚 Carrier '{worst[0]}' has {worst[1]} at-fault shipment(s); watch for a systemic issue.")
        low_health = [a for a in self.accounts if a.health_score < 70]
        if low_health:
            out.append(f"💛 {len(low_health)} account(s) below 70 health: " + ", ".join(a.name for a in low_health) + ".")
        return out or ["✅ No critical signals in scope right now."]

    # --- analytics -------------------------------------------------------
    def analytics(self) -> dict:
        by_day = defaultdict(int)
        for t in self.tickets:
            if t.business_created_at:
                by_day[t.business_created_at.date().isoformat()] += 1

        severity_dist = Counter(t.severity or "P3" for t in self.tickets)
        status_dist = Counter(t.status for t in self.tickets)
        open_sla = self._open_tickets_with_sla()
        breached = len([r for r in open_sla if r["breached"]])
        compliant = len(open_sla) - breached

        top_issues = Counter()
        for t in self.tickets:
            for m in match_known_issues(f"{t.subject} {t.description}"):
                top_issues[m["code"]] += 1

        carrier_failures = Counter(o.carrier for o in self.orders if o.carrier_fault)
        support_load = Counter(t.assigned_to for t in self.tickets if t.assigned_to)
        top_customers = Counter(self._acct_by_id[t.account_id].name for t in self.tickets if t.account_id in self._acct_by_id)

        return {
            "ticket_volume": [{"date": d, "count": by_day[d]} for d in sorted(by_day)],
            "severity_distribution": [{"severity": s, "count": severity_dist[s]} for s in ("P1", "P2", "P3")],
            "status_distribution": [{"status": s, "count": n} for s, n in status_dist.items()],
            "sla_compliance": [{"label": "Compliant", "count": compliant}, {"label": "Breached", "count": breached}],
            "top_issues": [{"code": c, "count": n} for c, n in top_issues.most_common()],
            "carrier_failures": [{"carrier": c, "count": n} for c, n in carrier_failures.most_common()],
            "support_load": [{"agent": a, "count": n} for a, n in support_load.most_common()],
            "top_customers": [{"name": a, "tickets": n} for a, n in top_customers.most_common()],
        }
