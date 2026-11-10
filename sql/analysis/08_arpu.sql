-- Monthly collected revenue, ARPU over all known customers and ARPPU over paying customers.
WITH rev AS (
  SELECT date(p.attempted_at, 'start of month') AS month_start, i.customer_id, SUM(p.amount) AS revenue
  FROM payments p JOIN subscriptions s USING (subscription_id)
  JOIN identity_map i ON i.account_id = s.account_id
  WHERE p.status = 'succeeded'
  GROUP BY 1, 2
), known AS (
  SELECT m.month_start, COUNT(DISTINCT c.customer_id) AS customers
  FROM months m JOIN customer_360 c ON c.first_seen < date(m.month_start, '+1 month')
  GROUP BY m.month_start
)
SELECT r.month_start, ROUND(SUM(r.revenue)) AS revenue, k.customers, COUNT(*) AS paying_customers,
       ROUND(100.0 * COUNT(*) / k.customers, 1) AS payer_pct,
       ROUND(SUM(r.revenue) / k.customers, 2) AS arpu,
       ROUND(SUM(r.revenue) / COUNT(*), 2) AS arppu
FROM rev r JOIN known k USING (month_start)
WHERE r.month_start >= '2025-04-01' AND r.month_start < (SELECT as_of FROM settings)
GROUP BY r.month_start
ORDER BY r.month_start;
