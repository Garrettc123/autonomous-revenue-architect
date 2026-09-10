"""Garcar Autonomous Revenue Architect — broker/team Lead Leak Audit engine.

Autonomy-first, approval-gated revenue operations. Stores prospects locally in SQLite,
qualifies them from evidence, generates outreach drafts, tracks pipeline state, and
accepts Stripe webhook events. No automated unsolicited messages are sent by this app.
"""
from __future__ import annotations

import csv, io, json, os, sqlite3, uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from pydantic import BaseModel, Field

DB_PATH = os.getenv("GARCAR_DB", "garcar_revenue.db")
AUDIT_PRICE = int(os.getenv("AUDIT_PRICE_USD", "500"))
CHECKOUT_URL = os.getenv("AUDIT_CHECKOUT_URL", "")

app = FastAPI(title="Garcar Autonomous Revenue Architect", version="1.0.0")

SCHEMA = """
CREATE TABLE IF NOT EXISTS prospects (
 id TEXT PRIMARY KEY, company TEXT NOT NULL, city TEXT, state TEXT DEFAULT 'TX', website TEXT,
 phone TEXT, decision_maker TEXT, title TEXT, email TEXT, linkedin TEXT,
 agent_count INTEGER DEFAULT 0, lead_form INTEGER DEFAULT 0, seller_lead INTEGER DEFAULT 0,
 buyer_lead INTEGER DEFAULT 0, appointment_booking INTEGER DEFAULT 0, after_hours INTEGER DEFAULT 0,
 crm_signal INTEGER DEFAULT 0, paid_lead_signal INTEGER DEFAULT 0, active_listings INTEGER DEFAULT 0,
 evidence TEXT DEFAULT '', score INTEGER DEFAULT 0, status TEXT DEFAULT 'new',
 last_contact TEXT, next_action TEXT, notes TEXT DEFAULT '', created_at TEXT NOT NULL,
 updated_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS events (
 id INTEGER PRIMARY KEY AUTOINCREMENT, prospect_id TEXT, event_type TEXT NOT NULL,
 payload TEXT DEFAULT '{}', created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS audits (
 id TEXT PRIMARY KEY, prospect_id TEXT NOT NULL, status TEXT DEFAULT 'proposed',
 findings TEXT DEFAULT '[]', price_cents INTEGER NOT NULL, created_at TEXT NOT NULL,
 completed_at TEXT
);
"""

def now(): return datetime.now(timezone.utc).isoformat()

def db():
    c = sqlite3.connect(DB_PATH)
    c.row_factory = sqlite3.Row
    c.executescript(SCHEMA)
    return c

def score(p):
    s = 0
    s += 3 if p["agent_count"] >= 5 else 0
    s += 3 if p["lead_form"] else 0
    s += 2 if p["active_listings"] else 0
    s += 3 if p["paid_lead_signal"] else 0
    s += 2 if p["crm_signal"] else 0
    s += 3 if p["decision_maker"] else 0
    s += 2 if p["phone"] else 0
    s += 2 if p["seller_lead"] or p["buyer_lead"] else 0
    s += 4 if any(x in (p["evidence"] or '').lower() for x in ("broken", "no acknowledgement", "no confirmation", "no routing", "no booking")) else 0
    if p["agent_count"] == 1 and not p["lead_form"]: s -= 4
    return s

def log(c, pid, typ, payload=None):
    c.execute("INSERT INTO events(prospect_id,event_type,payload,created_at) VALUES(?,?,?,?)", (pid, typ, json.dumps(payload or {}), now()))

def prospect_dict(r):
    d = dict(r)
    d["score"] = score(d)
    return d

class Prospect(BaseModel):
    company: str
    city: str = ""
    state: str = "TX"
    website: str = ""
    phone: str = ""
    decision_maker: str = ""
    title: str = ""
    email: str = ""
    linkedin: str = ""
    agent_count: int = 0
    lead_form: bool = False
    seller_lead: bool = False
    buyer_lead: bool = False
    appointment_booking: bool = False
    after_hours: bool = False
    crm_signal: bool = False
    paid_lead_signal: bool = False
    active_listings: bool = False
    evidence: str = ""
    notes: str = ""

@app.get("/health")
def health(): return {"status":"healthy","service":"garcar-autonomous-revenue-architect"}

@app.get("/api/prospects")
def prospects(status: Optional[str]=None, min_score: int=0):
    c=db(); q="SELECT * FROM prospects WHERE 1=1"; args=[]
    if status: q += " AND status=?"; args.append(status)
    q += " ORDER BY score DESC, updated_at DESC"
    rows=[prospect_dict(r) for r in c.execute(q,args)]
    return [r for r in rows if r["score"] >= min_score]

@app.post("/api/prospects")
def create_prospect(p: Prospect):
    c=db(); pid=str(uuid.uuid4()); t=now(); d=p.model_dump(); d["score"]=score(d)
    cols=list(d.keys()); vals=[int(v) if isinstance(v,bool) else v for v in d.values()]
    c.execute(f"INSERT INTO prospects(id,{','.join(cols)},created_at,updated_at) VALUES(?,{','.join('?'*len(vals))},?,?)", [pid,*vals,t,t])
    log(c,pid,"prospect.discovered",{"source":"manual/api"}); c.commit()
    return prospect_dict(c.execute("SELECT * FROM prospects WHERE id=?",(pid,)).fetchone())

@app.post("/api/prospects/import")
async def import_csv(file: UploadFile=File(...)):
    raw=(await file.read()).decode("utf-8-sig"); reader=csv.DictReader(io.StringIO(raw)); count=0
    for row in reader:
        p=Prospect(
          company=row.get("Company",row.get("company","")), city=row.get("City",row.get("city","")), state=row.get("State", "TX"),
          website=row.get("Website",row.get("website","")), phone=row.get("Phone",row.get("phone","")),
          decision_maker=row.get("Owner/Broker",row.get("Decision Maker",row.get("decision_maker",""))), title=row.get("Title",row.get("title","")),
          email=row.get("Email",row.get("email","")), linkedin=row.get("LinkedIn",row.get("linkedin","")),
          agent_count=int(row.get("Agent Count",row.get("agent_count",0)) or 0),
          lead_form=str(row.get("Lead Form?",row.get("lead_form",0))).lower() in ("1","true","yes"),
          seller_lead=str(row.get("Seller Lead?",0)).lower() in ("1","true","yes"), buyer_lead=str(row.get("Buyer Lead?",0)).lower() in ("1","true","yes"),
          appointment_booking=str(row.get("Appointment Booking?",0)).lower() in ("1","true","yes"), after_hours=str(row.get("After-Hours?",0)).lower() in ("1","true","yes"),
          crm_signal=str(row.get("CRM Signal?",0)).lower() in ("1","true","yes"), paid_lead_signal=str(row.get("Paid Lead Signal?",0)).lower() in ("1","true","yes"),
          active_listings=str(row.get("Active Listings?",0)).lower() in ("1","true","yes"), evidence=row.get("Evidence", ""), notes=row.get("Notes", ""))
        create_prospect(p); count += 1
    return {"imported":count}

@app.post("/api/prospects/{pid}/qualify")
def qualify(pid:str):
    c=db(); r=c.execute("SELECT * FROM prospects WHERE id=?",(pid,)).fetchone()
    if not r: raise HTTPException(404,"Prospect not found")
    s=score(dict(r)); status="qualified" if s>=10 else "research"
    c.execute("UPDATE prospects SET score=?,status=?,next_action=?,updated_at=? WHERE id=?",(s,status,"contact decision-maker" if status=="qualified" else "collect more evidence",now(),pid))
    log(c,pid,"prospect.qualified",{"score":s,"status":status}); c.commit(); return prospect_dict(c.execute("SELECT * FROM prospects WHERE id=?",(pid,)).fetchone())

@app.get("/api/prospects/{pid}/outreach")
def outreach(pid:str):
    c=db(); r=c.execute("SELECT * FROM prospects WHERE id=?",(pid,)).fetchone()
    if not r: raise HTTPException(404,"Prospect not found")
    p=dict(r); name=p["decision_maker"] or "there"; company=p["company"]; ev=p["evidence"] or "your inbound lead flow"
    body=f"Hi {name},\n\nI’m Garrett with Garcar Enterprise. I reviewed {company}’s public inbound lead path and noticed {ev}.\n\nI help brokerages and real-estate teams identify where inquiries can get delayed, misrouted, or left without a clear next step. I run a 48-hour Lead Leak Audit for ${AUDIT_PRICE}: we map the lead path, document observable gaps, and produce a prioritized repair plan.\n\nIf there is a material issue, the audit can be followed by implementation. If not, you still get the findings.\n\nWould you like the audit details?\n\nGarrett Carrol\nGarcar Enterprise"
    return {"subject":f"Lead-flow question for {company}","body":body,"phone_script":f"Hi {name}, Garrett with Garcar Enterprise. I’m calling about {company}’s inbound lead flow. I noticed {ev}. Who owns response and routing for new inquiries?"}

@app.post("/api/prospects/{pid}/mark-contacted")
def contacted(pid:str):
    c=db(); r=c.execute("SELECT 1 FROM prospects WHERE id=?",(pid,)).fetchone()
    if not r: raise HTTPException(404,"Prospect not found")
    c.execute("UPDATE prospects SET status='contacted',last_contact=?,next_action='follow up or handle reply',updated_at=? WHERE id=?",(now(),now(),pid)); log(c,pid,"outreach.logged"); c.commit(); return {"status":"contacted"}

@app.post("/api/audits")
def create_audit(pid:str):
    c=db(); r=c.execute("SELECT * FROM prospects WHERE id=?",(pid,)).fetchone()
    if not r: raise HTTPException(404,"Prospect not found")
    aid=str(uuid.uuid4()); c.execute("INSERT INTO audits(id,prospect_id,price_cents,created_at) VALUES(?,?,?,?)",(aid,pid,AUDIT_PRICE*100,now()))
    c.execute("UPDATE prospects SET status='audit_proposed',next_action='send checkout',updated_at=? WHERE id=?",(now(),pid)); log(c,pid,"audit.proposed",{"audit_id":aid,"price_usd":AUDIT_PRICE}); c.commit()
    return {"audit_id":aid,"price_usd":AUDIT_PRICE,"checkout_url":CHECKOUT_URL}

@app.get("/api/audits")
def audits():
    c=db(); return [dict(r) for r in c.execute("SELECT a.*,p.company,p.decision_maker FROM audits a JOIN prospects p ON p.id=a.prospect_id ORDER BY a.created_at DESC")]

@app.post("/webhooks/stripe")
async def stripe_webhook(payload: dict):
    # Configure signature verification at the edge/provider before production use.
    event_type=payload.get("type",""); obj=payload.get("data",{}).get("object",{})
    if event_type not in ("checkout.session.completed","payment_intent.succeeded"):
        return {"received":True,"ignored":True}
    meta=obj.get("metadata",{}); pid=meta.get("prospect_id")
    if pid:
        c=db(); c.execute("UPDATE prospects SET status='paid_audit',next_action='start audit',updated_at=? WHERE id=?",(now(),pid)); log(c,pid,"audit.paid",{"stripe_event":event_type}); c.commit()
    return {"received":True}

@app.get("/api/export.csv")
def export_csv():
    rows=prospects(); out=io.StringIO(); fields=list(rows[0].keys()) if rows else ["id","company","city","state","website","phone","decision_maker","title","email","score","status"]
    w=csv.DictWriter(out,fieldnames=fields); w.writeheader(); w.writerows(rows); out.seek(0)
    return StreamingResponse(iter([out.getvalue()]),media_type="text/csv",headers={"Content-Disposition":"attachment; filename=garcar_prospects.csv"})

@app.get("/",response_class=HTMLResponse)
def dashboard():
    return HTMLResponse("""<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><title>Garcar Revenue Architect</title><style>body{font-family:system-ui;max-width:1100px;margin:auto;padding:24px;background:#0b0d10;color:#eee}button,input{padding:10px;margin:4px;border-radius:8px;border:1px solid #333;background:#151922;color:#eee}.card{background:#12161d;border:1px solid #262c36;border-radius:14px;padding:16px;margin:12px 0}.hot{border-left:4px solid #fff}.muted{color:#9aa4b2}a{color:#b84dff}pre{white-space:pre-wrap}</style></head><body><h1>Garcar Autonomous Revenue Architect</h1><p class='muted'>Lead Leak Audit acquisition control plane — approval-gated external actions.</p><div id='stats'></div><div class='card'><input id='csv' type='file' accept='.csv'><button onclick='upload()'>Import CSV</button><button onclick='load()'>Refresh</button><a href='/api/export.csv'>Export CSV</a></div><div id='list'></div><script>async function load(){let r=await fetch('/api/prospects');let d=await r.json();document.getElementById('stats').innerHTML=`<div class=card><b>${d.length}</b> prospects · <b>${d.filter(x=>x.score>=10).length}</b> qualified · <b>${d.filter(x=>x.status==='paid_audit').length}</b> paid audits</div>`;document.getElementById('list').innerHTML=d.map(x=>`<div class='card ${x.score>=10?'hot':''}'><b>${x.company}</b> — ${x.city} ${x.state}<br>${x.decision_maker||'Decision maker unknown'} ${x.title?'('+x.title+')':''}<br>Score: <b>${x.score}</b> · ${x.status}<br><span class=muted>${x.evidence||'No evidence recorded'}</span><br><button onclick="qualify('${x.id}')">Qualify</button> <button onclick="outreach('${x.id}')">Draft outreach</button> <button onclick="audit('${x.id}')">Create audit</button></div>`).join('')}async function qualify(id){await fetch('/api/prospects/'+id+'/qualify',{method:'POST'});load()}async function outreach(id){let r=await fetch('/api/prospects/'+id+'/outreach');let x=await r.json();alert(x.subject+'\n\n'+x.body)}async function audit(id){let r=await fetch('/api/audits?pid='+id);alert('Use POST /api/audits with pid='+id+' to create an audit proposal.')}async function upload(){let f=document.getElementById('csv').files[0];if(!f)return;let fd=new FormData();fd.append('file',f);await fetch('/api/prospects/import',{method:'POST',body:fd});load()}load()</script></body></html>""")
