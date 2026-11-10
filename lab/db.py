"""Build the SQLite database: raw tables, the identity map, and the analysis views."""
import sqlite3
from pathlib import Path

from lab.generate import AS_OF, generate
from lab.resolve import resolve

ROOT = Path(__file__).resolve().parent.parent
SQL = ROOT / "sql"
SCHEMA = """
CREATE TABLE accounts (account_id TEXT PRIMARY KEY, brand TEXT NOT NULL, email TEXT NOT NULL,
  phone TEXT, full_name TEXT NOT NULL, created_at TEXT NOT NULL);
CREATE TABLE subscriptions (subscription_id TEXT PRIMARY KEY,
  account_id TEXT NOT NULL REFERENCES accounts, brand TEXT NOT NULL, plan TEXT NOT NULL,
  price REAL NOT NULL CHECK (price > 0), period_months INTEGER NOT NULL CHECK (period_months IN (1, 12)),
  started_at TEXT NOT NULL, ended_at TEXT,
  end_reason TEXT CHECK (end_reason IN ('voluntary', 'payment_failed')));
CREATE TABLE payments (payment_id TEXT PRIMARY KEY,
  subscription_id TEXT NOT NULL REFERENCES subscriptions, due_date TEXT NOT NULL,
  attempt_no INTEGER NOT NULL, attempted_at TEXT NOT NULL, amount REAL NOT NULL,
  status TEXT NOT NULL CHECK (status IN ('succeeded', 'failed')), decline_code TEXT,
  UNIQUE (subscription_id, due_date, attempt_no));
CREATE TABLE identity_map (account_id TEXT PRIMARY KEY REFERENCES accounts,
  customer_id TEXT NOT NULL, linked_by TEXT);
CREATE TABLE settings (as_of TEXT NOT NULL);
"""


def build(path=":memory:", n_people=3000, seed=7):
    data = generate(n_people, seed)
    mapping, rule = resolve(data["accounts"])
    con = sqlite3.connect(path)
    con.executescript(SCHEMA)
    con.executemany("INSERT INTO accounts VALUES (?,?,?,?,?,?)", data["accounts"])
    con.executemany("INSERT INTO subscriptions VALUES (?,?,?,?,?,?,?,?,?)", data["subscriptions"])
    con.executemany("INSERT INTO payments VALUES (?,?,?,?,?,?,?,?)", data["payments"])
    con.executemany("INSERT INTO identity_map VALUES (?,?,?)",
                    [(a, c, rule.get(a)) for a, c in mapping.items()])
    con.execute("INSERT INTO settings VALUES (?)", (AS_OF.isoformat(),))
    con.executescript((SQL / "views.sql").read_text())
    con.commit()
    return con, data, mapping
