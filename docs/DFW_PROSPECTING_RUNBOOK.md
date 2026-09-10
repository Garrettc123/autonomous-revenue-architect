# DFW Lead Leak Audit — Autonomous Prospecting Runbook

## Objective

Convert qualified DFW real-estate brokerages and teams into paid $500 Lead Leak Audits, then route qualified customers into $2,500 implementation and $997/month Revenue Ops.

## Operating loop

1. Import prospect records from `data/dfw-real-estate-prospects.csv`.
2. Verify the decision-maker and public business contact path before outreach.
3. Inspect the public website for buyer/seller/home-value/showing/appointment flows.
4. Record only observable evidence. Never claim a lead is actually being lost without access to supporting operational data.
5. Generate an individualized outreach draft.
6. Human approval is required before external outreach.
7. Record responses and move qualified prospects to `audit_offered`.
8. Create the $500 audit after payment confirmation.
9. Deliver the audit and document evidence, risk, and recommended fixes.
10. Propose implementation where the audit identifies material operational gaps.
11. Offer ongoing monitoring/automation at $997/month where appropriate.

## Prospect qualification

Prioritize organizations showing several of these characteristics:

- Multi-agent team or brokerage
- Active buyer/seller lead capture
- Home valuation or seller funnel
- Appointment/showing flow
- Strong local presence
- Multiple service areas
- Evidence of active marketing
- Identifiable owner, broker-owner, founder, or team leader

## Evidence language

Use:

> Potential lead-response or handoff gap

Avoid unsupported claims such as:

> You are losing leads.

The audit is the mechanism for establishing whether a material leak actually exists.

## Outreach control

The system may draft and queue outreach. External sending requires explicit approval and must respect applicable calling, messaging, email, and opt-out requirements.

## Current seed

The first seed contains 10 DFW prospects with public evidence and decision-maker information where available. Expand in batches of 10 rather than building an unqualified list of hundreds.

## Revenue path

`Prospect -> Qualified -> Outreach Approved -> Conversation -> $500 Audit -> $2,500 Implementation -> $997/month`
