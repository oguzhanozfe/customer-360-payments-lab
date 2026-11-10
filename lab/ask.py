"""Ask questions about the subscription data in plain language.

A hand-written tool-calling loop (no agent framework) over an OpenAI-compatible
chat endpoint; by default a local Ollama model, so no API key is needed.
The model can only read: the database is opened read-only and a SQLite
authorizer rejects anything but SELECT, so a prompt cannot talk it into a write.

    python3 -m lab.ask "Which decline code loses the most revenue?"
"""
import json
import os
import sqlite3
import sys
import urllib.request

from lab.db import ROOT

BASE_URL = os.environ.get("LLM_BASE_URL", "http://localhost:11434/v1")
MODEL = os.environ.get("LLM_MODEL", "qwen3.5:4b")
API_KEY = os.environ.get("LLM_API_KEY", "ollama")
DB = ROOT / "data" / "lab.sqlite"
MAX_STEPS = 8  # model calls per question, so a confused model cannot loop forever
MAX_ROWS = 50

SYSTEM = """You answer questions about a subscription business with three brands (news, sports, tv).
Use the tools; never guess a number. Start with describe_schema, then run_sql (SQLite dialect, SELECT only).
Prefer the prepared views: customer_360 (one row per resolved customer across brands),
subscription_months (active subscriptions on each month's first day, with mrr),
billing_cycles (one row per billing cycle: first_decline, attempts, paid, paid_on_attempt), months.
Prices and revenue are in TRY. Definitions: MRR counts yearly plans as price/12. Voluntary churn is end_reason='voluntary';
involuntary churn is end_reason='payment_failed'. Dates are ISO text; the data runs to settings.as_of.
Answer briefly with the numbers and state what they are a share of. Say plainly when the data cannot answer.
All data is synthetic."""

ALLOWED = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION}
if hasattr(sqlite3, "SQLITE_RECURSIVE"):
    ALLOWED.add(sqlite3.SQLITE_RECURSIVE)


def connect():
    con = sqlite3.connect("file:{}?mode=ro".format(DB), uri=True)
    con.set_authorizer(lambda action, *_: sqlite3.SQLITE_OK if action in ALLOWED else sqlite3.SQLITE_DENY)
    return con


def describe_schema(con):
    rows = con.execute("SELECT type, name, sql FROM sqlite_master WHERE type IN ('table', 'view') ORDER BY type, name")
    return "\n\n".join("{} {}:\n{}".format(t, n, s) for t, n, s in rows)


def run_sql(con, query):
    try:
        cur = con.execute(query)
    except sqlite3.Error as e:
        return "SQL error: {}".format(e)
    cols = [d[0] for d in cur.description or []]
    rows = cur.fetchmany(MAX_ROWS + 1)
    more = "\n(more rows cut; aggregate or add LIMIT)" if len(rows) > MAX_ROWS else ""
    return json.dumps({"columns": cols, "rows": rows[:MAX_ROWS]}, default=str) + more


TOOLS = [
    {"type": "function", "function": {
        "name": "describe_schema", "description": "List every table and view with its CREATE statement.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "run_sql", "description": "Run one read-only SQLite SELECT and get up to 50 rows as JSON.",
        "parameters": {"type": "object", "properties": {"query": {"type": "string", "description": "One SELECT statement"}},
                       "required": ["query"]}}},
]


def chat(messages):
    body = json.dumps({"model": MODEL, "messages": messages, "tools": TOOLS, "temperature": 0}).encode()
    req = urllib.request.Request(BASE_URL.rstrip("/") + "/chat/completions", data=body, headers={
        "Content-Type": "application/json", "Authorization": "Bearer " + API_KEY})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.load(r)["choices"][0]["message"]


def ask(question, con=None, log=print):
    """Returns (answer, list of SQL queries the model ran)."""
    con = con or connect()
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": question}]
    queries = []
    for _ in range(MAX_STEPS):
        msg = chat(messages)
        calls = msg.get("tool_calls") or []
        messages.append({"role": "assistant", "content": msg.get("content") or "", "tool_calls": calls} if calls
                        else {"role": "assistant", "content": msg.get("content") or ""})
        if not calls:
            return (msg.get("content") or "").strip(), queries
        for call in calls:
            name = call["function"]["name"]
            try:
                args = json.loads(call["function"].get("arguments") or "{}")
            except ValueError:
                args = {}
            if name == "run_sql":
                queries.append(args.get("query", ""))
                log("SQL> " + " ".join(args.get("query", "").split()))
                result = run_sql(con, args.get("query", ""))
            elif name == "describe_schema":
                result = describe_schema(con)
            else:
                result = "Unknown tool " + name
            messages.append({"role": "tool", "tool_call_id": call.get("id", name), "content": result})
    return "I could not finish within {} steps.".format(MAX_STEPS), queries


if __name__ == "__main__":
    if not DB.exists():
        sys.exit("Run python3 scripts/run_analysis.py first to build data/lab.sqlite.")
    answer, _ = ask(" ".join(sys.argv[1:]) or "What was MRR on 2026-09-01, and how much of last month's churn was involuntary?")
    print("\n" + answer)
