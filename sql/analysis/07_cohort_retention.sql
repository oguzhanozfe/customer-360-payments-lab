-- Share of each start-month cohort still subscribed k months later (only where k months have passed).
WITH cohort AS (
  SELECT subscription_id, started_at, ended_at, strftime('%Y-%m', started_at) AS cohort
  FROM subscriptions
), k(n) AS (VALUES (1), (2), (3), (6), (12))
SELECT c.cohort, COUNT(DISTINCT c.subscription_id) AS size,
       ROUND(100.0 * SUM(CASE WHEN k.n = 1 THEN c.ended_at IS NULL OR c.ended_at > date(c.started_at, '+1 month') END)
             / NULLIF(SUM(CASE WHEN k.n = 1 THEN 1 END), 0), 1) AS m1_pct,
       ROUND(100.0 * SUM(CASE WHEN k.n = 3 THEN c.ended_at IS NULL OR c.ended_at > date(c.started_at, '+3 month') END)
             / NULLIF(SUM(CASE WHEN k.n = 3 THEN 1 END), 0), 1) AS m3_pct,
       ROUND(100.0 * SUM(CASE WHEN k.n = 6 THEN c.ended_at IS NULL OR c.ended_at > date(c.started_at, '+6 month') END)
             / NULLIF(SUM(CASE WHEN k.n = 6 THEN 1 END), 0), 1) AS m6_pct,
       ROUND(100.0 * SUM(CASE WHEN k.n = 12 THEN c.ended_at IS NULL OR c.ended_at > date(c.started_at, '+12 month') END)
             / NULLIF(SUM(CASE WHEN k.n = 12 THEN 1 END), 0), 1) AS m12_pct
-- A cohort shows month k only once every member has had k full months.
FROM cohort c JOIN k ON date(c.cohort || '-01', '+1 month', '+' || k.n || ' month', '-1 day') < (SELECT as_of FROM settings)
GROUP BY c.cohort
ORDER BY c.cohort;
