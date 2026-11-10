-- MRR and active subscribers on the first day of each month, with month-over-month change.
SELECT month_start,
       COUNT(*) AS active_subscriptions,
       COUNT(DISTINCT customer_id) AS active_customers,
       ROUND(SUM(mrr)) AS mrr,
       ROUND(SUM(mrr) - LAG(SUM(mrr)) OVER (ORDER BY month_start)) AS mrr_change
FROM subscription_months
GROUP BY month_start
ORDER BY month_start;
