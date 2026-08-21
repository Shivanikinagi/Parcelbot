# Demo script

A 5–7 minute walkthrough that showcases every headline capability. All data is real (from the assessment
pack); the reference time is the workbook snapshot `2026-08-16 11:00 IST`.

> Tip: use the identity switcher (top-right) to hop between roles and show RBAC live.

## 0. Setup (30s)

- Backend running on `:8000`, frontend on `:3000`.
- Open `http://localhost:3000` → the landing page → **Sign in**.
- Note the sidebar footer: **"LLM: offline mock"** (or your model) and the **snapshot time**.

## 1. Multi-step reasoning + SLA + conflict + escalation (as Support)

Sign in as **Maya Iyer (support)**. Ask:

> **What is the SLA on TKT-501 and is it breached?**

Expected:
- Streamed answer: **15m (24×7), sourced from the customer agreement, BREACHED (elapsed 30m)**.
- **Confidence: HIGH (82%)**.
- **Conflicts tab (1):** Northstar agreement `15m` (rank 1) > Support Policy v3 `30m` (rank 2) >
  Support Policy v2 `1h` (rank 7, struck through). Resolution cites Support Policy §1.
- **Escalation recommended** callout.
- **Sources tab:** ranked citations with authority dots and source-type labels.
- **Reasoning tab:** the full node trace. **Tools tab:** `document_search`, `known_issue_match`,
  `ticket_lookup`, `sla_calculator` with latencies.

## 2. State-changing action with confirmation (as Support)

> **Escalate TKT-501**

Expected:
- A **Confirmation required** card: *"Escalate TKT-501 (Northstar Logistics) at P1 to Priya Mehta."* with
  consequences listed. **Nothing has changed yet.**
- Click **Confirm & execute** → *"✅ Escalation ESC-0001 created for TKT-501."*
- Open **Audit Logs** (switch to a manager) → the `create_escalation` entry with actor, resource, and
  request-ID correlation.

## 3. The cancellation conflict (as Customer)

Switch to **Anjali Nair (Northstar customer)**. Ask:

> **Can I cancel ORD-1001?**

Expected:
- **Allowed, fee ₹0 (waived by the agreement).**
- **Conflict card:** agreement §2 "no fee" (rank 1) vs SOP "₹250 after 30 min" (rank 3) vs historical
  ticket TKT-450 "₹250 charged" (rank 6, struck through). Resolution: agreement wins; historical tickets
  are context-only.

## 4. Service-credit override + guardrail (as Customer)

Switch to **Ravi Menon (LumenWorks customer)**. Ask:

> **Am I eligible for a service credit on ORD-2002?**

Expected: **Eligible, ₹300** — the agreement's fixed amount and >4h threshold **override** the SOP
default (lower of ₹500 or 10%, >2h). Explanation notes carrier fault, no customer fault, 4h30m past the
pickup window.

## 5. RBAC boundary (as Customer)

Still as Ravi, ask:

> **Show me ORD-1001**  *(that's Northstar's order)*

Expected: politely blocked — *"not found or not in your scope."* No data leak. (In the Tools tab you can
see `order_lookup` returned `not found`.)

## 6. Known-issue intelligence (as Support)

Switch to **Maya**. Ask:

> **Why is bulk upload failing for LumenWorks?**

Expected: matches **KI-208** — the product limit is 5,000 rows, failures appear ~3,000; recommend the
split-file workaround. (Contrast with the *wrong* historical ticket TKT-451 that claimed a 3,000-row
limit.)

## 7. Proactive operations & analytics (as Manager)

Switch to **Priya Mehta (manager)**.
- **Operations** → KPIs, **AI Insights** (P1 breach, KI-208 impact, KI-211 caution, carrier fault, low
  account health), high-severity tickets, SLA breaches, recurring problems, customer health bars.
- **Analytics** → ticket volume, severity/SLA-compliance donuts, carrier failures, top issues, support
  load.
- **Audit Logs** → every action and tool execution.

## 8. Polish to point out

- Dark/light theme toggle. Streaming typewriter. Copy on messages. Conversation history + pinning.
- Knowledge-base search with live conflict detection. Confidence badges everywhere.
- The whole thing runs offline with zero cost — add an OpenRouter key for live LLM prose (same facts).
