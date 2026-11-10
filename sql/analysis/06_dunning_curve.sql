-- Of the cycles that failed first time, the cumulative share recovered by each retry.
WITH failed AS (
  SELECT * FROM billing_cycles WHERE first_decline IS NOT NULL AND (paid = 1 OR attempts = 4)
)
SELECT r.attempt_no AS by_attempt,
       ROUND(100.0 * SUM(f.paid_on_attempt <= r.attempt_no) / COUNT(*), 1) AS recovered_pct
FROM failed f CROSS JOIN (SELECT 2 AS attempt_no UNION ALL SELECT 3 UNION ALL SELECT 4) r
GROUP BY r.attempt_no
ORDER BY r.attempt_no;
