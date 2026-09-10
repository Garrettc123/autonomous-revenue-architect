# Garcar Autonomous Revenue Architect

An approval-gated autonomous operating system for selling and delivering the **$500 Lead Leak Audit** to Texas real-estate brokerages, teams, investors, and property managers.

## Flow

`Discover → Resolve → Inspect → Qualify → Draft → Approve → Contact → Audit → Implement → Retain`

The system stores prospects in SQLite, calculates qualification signals, generates individualized outreach drafts, tracks pipeline state, creates audit records, exports CSV, and accepts payment webhook events. External outreach is intentionally approval-gated; the system does not autonomously send unsolicited calls, texts, or email.

## Run on Termux

```bash
pkg update
pkg install python -y
python -m pip install -r requirements.txt
export AUDIT_PRICE_USD=500
export AUDIT_CHECKOUT_URL='YOUR_STRIPE_CHECKOUT_URL'
uvicorn app:app --host 0.0.0.0 --port 8000
```

Open `http://127.0.0.1:8000`.

## Docker

```bash
docker build -t garcar-revenue .
docker run --rm -p 8000:8000 -e AUDIT_CHECKOUT_URL='YOUR_STRIPE_CHECKOUT_URL' garcar-revenue
```

## API

- `GET /health`
- `GET /api/prospects`
- `POST /api/prospects`
- `POST /api/prospects/import`
- `POST /api/prospects/{id}/qualify`
- `GET /api/prospects/{id}/outreach`
- `POST /api/prospects/{id}/mark-contacted`
- `POST /api/audits?pid={id}`
- `GET /api/audits`
- `POST /webhooks/stripe`
- `GET /api/export.csv`

## Prospect CSV

Accepted columns include:

`Company, City, State, Website, Phone, Owner/Broker, Title, Email, LinkedIn, Agent Count, Lead Form?, Seller Lead?, Buyer Lead?, Appointment Booking?, After-Hours?, CRM Signal?, Paid Lead Signal?, Active Listings?, Evidence, Notes`

## Qualification model

Signals include team size, inbound lead capture, seller/buyer funnels, active listings, paid-lead indicators, CRM indicators, identified decision-maker, phone availability, and concrete observable website evidence. A score of 10+ is treated as qualified for initial workflow triage; the score is not a claim about a prospect's likelihood to buy.

## Revenue ladder

- **$500** — 48-hour Lead Leak Audit
- **$2,500** — Lead Recovery Implementation
- **$997/month** — Revenue Ops Automation

The audit is the paid diagnostic entry point. Implementation and recurring operations follow only after the client's needs are established.

## Safety / compliance

Use public business information and appropriate contact channels. Do not use this application as a robocall, unsolicited bulk-text, or deceptive outreach system. Keep payment, contract, account-access, and other irreversible actions behind explicit approval.
