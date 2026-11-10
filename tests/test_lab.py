import sqlite3
import unittest
from unittest import mock

from lab import ask
from lab.db import SQL, build
from lab.resolve import norm_email, norm_name, norm_phone, resolve, score


class Normalize(unittest.TestCase):
    def test_email(self):
        self.assertEqual(norm_email(" Ayse.Kaya+promo@GMAIL.com"), "aysekaya@gmail.com")
        self.assertEqual(norm_email("ayse.kaya@hotmail.com"), "ayse.kaya@hotmail.com")  # dots matter outside Gmail

    def test_phone(self):
        for raw in ["05321234567", "+905321234567", "0532 123 45 67", "5321234567"]:
            self.assertEqual(norm_phone(raw), "5321234567")
        self.assertIsNone(norm_phone("123"))

    def test_name(self):
        self.assertEqual(norm_name("Şule  Öztürk"), norm_name("Sule Ozturk"))


class Resolution(unittest.TestCase):
    def test_household_phone_does_not_merge_different_names(self):
        rows = [("A", "news", "a@x.com", "05321234567", "Ali Kaya", "2025-01-01"),
                ("B", "tv", "b@x.com", "+905321234567", "Elif Kaya", "2025-01-01"),
                ("C", "tv", "c@x.com", "5321234567", "ALI KAYA", "2025-01-01")]
        m, _ = resolve(rows)
        self.assertEqual(m["A"], m["C"])
        self.assertNotEqual(m["A"], m["B"])

    def test_links_are_transitive(self):
        rows = [("A", "news", "x@gmail.com", None, "Ali", "2025-01-01"),
                ("B", "tv", "X+tv@gmail.com", "05321234567", "Ali", "2025-01-01"),
                ("C", "sports", "other@icloud.com", "5321234567", "Ali", "2025-01-01")]
        m, _ = resolve(rows)
        self.assertEqual(len(set(m.values())), 1)


class Pipeline(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.con, cls.data, cls.mapping = build()

    def test_deterministic(self):
        self.assertEqual(build()[1]["payments"][:50], self.data["payments"][:50])

    def test_resolution_quality(self):
        s = score(self.mapping, self.data["truth"])
        self.assertGreaterEqual(s["precision"], 0.99)
        self.assertGreaterEqual(s["recall"], 0.90)

    def test_data_quality_gate(self):
        rows = self.con.execute((SQL / "analysis" / "01_data_quality.sql").read_text()).fetchall()
        self.assertEqual([r for r in rows if r[1]], [])

    def test_every_analysis_query_runs(self):
        for f in (SQL / "analysis").glob("*.sql"):
            self.assertTrue(self.con.execute(f.read_text()).fetchall(), f.name)

    def test_mrr_matches_raw_subscriptions(self):
        view = self.con.execute("SELECT SUM(mrr) FROM subscription_months WHERE month_start = '2026-09-01'").fetchone()[0]
        raw = self.con.execute("""SELECT SUM(price * 1.0 / period_months) FROM subscriptions
            WHERE started_at <= '2026-09-01' AND (ended_at IS NULL OR ended_at > '2026-09-01')""").fetchone()[0]
        self.assertAlmostEqual(view, raw)


class ReadOnlyTools(unittest.TestCase):
    def test_writes_are_refused(self):
        import tempfile
        from pathlib import Path
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "lab.sqlite"
            build(str(path), n_people=50)[0].close()
            with mock.patch.object(ask, "DB", path):
                con = ask.connect()
                for q in ["DELETE FROM payments", "UPDATE accounts SET email = ''", "DROP TABLE accounts",
                          "ATTACH 'x.db' AS x", "PRAGMA writable_schema = 1"]:
                    self.assertTrue(ask.run_sql(con, q).startswith("SQL error"), q)
                self.assertIn("rows", ask.run_sql(con, "SELECT COUNT(*) FROM customer_360"))


if __name__ == "__main__":
    unittest.main()
