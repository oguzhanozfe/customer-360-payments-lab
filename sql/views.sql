-- Month starts from the first subscription month up to the as-of date.
CREATE VIEW months AS
WITH RECURSIVE m(month_start) AS (
  SELECT '2025-01-01'
  UNION ALL
  SELECT date(month_start, '+1 month') FROM m
  WHERE date(month_start, '+1 month') <= (SELECT as_of FROM settings)
)
SELECT month_start FROM m;

-- One row per subscription per month it was active on the first day of that month.
-- Yearly plans count as price / 12 per month (MRR, not cash).
CREATE VIEW subscription_months AS
SELECT m.month_start, s.subscription_id, s.brand, s.plan, i.customer_id,
       s.price * 1.0 / s.period_months AS mrr
FROM months m
JOIN subscriptions s
  ON s.started_at <= m.month_start
 AND (s.ended_at IS NULL OR s.ended_at > m.month_start)
JOIN identity_map i ON i.account_id = s.account_id;

-- Single customer view: one row per resolved customer across all brands.
CREATE VIEW customer_360 AS
WITH acc AS (
  SELECT i.customer_id, COUNT(*) AS accounts, COUNT(DISTINCT a.brand) AS brands,
         GROUP_CONCAT(DISTINCT a.brand) AS brand_list, MIN(a.created_at) AS first_seen
  FROM identity_map i JOIN accounts a USING (account_id)
  GROUP BY i.customer_id
), sub AS (
  SELECT i.customer_id,
         COUNT(*) AS subscriptions,
         SUM(s.ended_at IS NULL) AS active_subscriptions,
         SUM(s.end_reason = 'voluntary') AS voluntary_cancels,
         SUM(s.end_reason = 'payment_failed') AS payment_failed_cancels
  FROM identity_map i JOIN subscriptions s USING (account_id)
  GROUP BY i.customer_id
), pay AS (
  SELECT i.customer_id,
         SUM(CASE WHEN p.status = 'succeeded' THEN p.amount END) AS lifetime_revenue,
         SUM(p.status = 'failed') AS failed_attempts,
         MAX(p.attempted_at) AS last_payment_at
  FROM identity_map i JOIN subscriptions s USING (account_id)
  JOIN payments p USING (subscription_id)
  GROUP BY i.customer_id
)
SELECT acc.*, COALESCE(sub.subscriptions, 0) AS subscriptions,
       COALESCE(sub.active_subscriptions, 0) AS active_subscriptions,
       COALESCE(sub.voluntary_cancels, 0) AS voluntary_cancels,
       COALESCE(sub.payment_failed_cancels, 0) AS payment_failed_cancels,
       COALESCE(pay.lifetime_revenue, 0) AS lifetime_revenue,
       COALESCE(pay.failed_attempts, 0) AS failed_attempts,
       pay.last_payment_at
FROM acc LEFT JOIN sub USING (customer_id) LEFT JOIN pay USING (customer_id);

-- Each billing cycle once: did the first attempt fail, and was it recovered later?
CREATE VIEW billing_cycles AS
SELECT p.subscription_id, s.brand, p.due_date,
       MAX(CASE WHEN p.attempt_no = 1 THEN p.decline_code END) AS first_decline,
       MAX(p.attempt_no) AS attempts,
       MAX(p.status = 'succeeded') AS paid,
       MIN(CASE WHEN p.status = 'succeeded' THEN p.attempt_no END) AS paid_on_attempt
FROM payments p JOIN subscriptions s USING (subscription_id)
GROUP BY p.subscription_id, s.brand, p.due_date;
