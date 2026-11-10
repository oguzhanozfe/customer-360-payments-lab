-- Subscriptions of customers on one brand vs several. Rates are per subscription:
-- a per-customer "ever cancelled" rate would punish people who simply hold more subscriptions.
-- Still a correlation, not a cause: people who join several brands may be more engaged to begin with.
SELECT CASE WHEN c.brands = 1 THEN '1 brand' ELSE '2+ brands' END AS segment,
       COUNT(DISTINCT c.customer_id) AS customers,
       COUNT(*) AS subscriptions,
       ROUND(100.0 * SUM(s.end_reason = 'voluntary') / COUNT(*), 1) AS cancelled_pct,
       ROUND(100.0 * SUM(s.end_reason = 'payment_failed') / COUNT(*), 1) AS lost_to_payment_pct,
       ROUND(SUM(c.lifetime_revenue) / COUNT(DISTINCT c.customer_id)) AS revenue_per_customer
FROM subscriptions s
JOIN identity_map i USING (account_id)
JOIN customer_360 c USING (customer_id)
GROUP BY 1;
