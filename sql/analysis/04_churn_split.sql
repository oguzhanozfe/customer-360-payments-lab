-- Monthly churn rate split into voluntary (cancelled) and involuntary (payment failed).
-- Denominator: subscriptions active on the first day of the month.
WITH base AS (
  SELECT month_start, COUNT(*) AS active_at_start FROM subscription_months GROUP BY month_start
), ended AS (
  SELECT date(ended_at, 'start of month') AS month_start,
         SUM(end_reason = 'voluntary') AS voluntary,
         SUM(end_reason = 'payment_failed') AS involuntary
  FROM subscriptions WHERE ended_at IS NOT NULL
  GROUP BY 1
)
SELECT b.month_start, b.active_at_start,
       COALESCE(e.voluntary, 0) AS voluntary, COALESCE(e.involuntary, 0) AS involuntary,
       ROUND(100.0 * COALESCE(e.voluntary, 0) / b.active_at_start, 1) AS voluntary_pct,
       ROUND(100.0 * COALESCE(e.involuntary, 0) / b.active_at_start, 1) AS involuntary_pct
FROM base b LEFT JOIN ended e USING (month_start)
WHERE b.month_start >= '2025-04-01'  -- earlier months have too few subscribers to read
  AND b.month_start < date((SELECT as_of FROM settings), 'start of month')  -- whole months only
ORDER BY b.month_start;
