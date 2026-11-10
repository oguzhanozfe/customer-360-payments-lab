-- Gate before any metric: every check should return 0.
SELECT 'payments without a subscription' AS check_name, COUNT(*) AS rows_failing
FROM payments p LEFT JOIN subscriptions s USING (subscription_id) WHERE s.subscription_id IS NULL
UNION ALL
SELECT 'subscriptions ending before they start', COUNT(*) FROM subscriptions WHERE ended_at < started_at
UNION ALL
SELECT 'successful payment after the subscription ended', COUNT(*)
FROM payments p JOIN subscriptions s USING (subscription_id)
WHERE p.status = 'succeeded' AND s.ended_at IS NOT NULL AND p.attempted_at > s.ended_at
UNION ALL
SELECT 'accounts missing from the identity map', COUNT(*)
FROM accounts a LEFT JOIN identity_map i USING (account_id) WHERE i.account_id IS NULL
UNION ALL
SELECT 'billing cycles paid twice', COUNT(*) FROM (
  SELECT subscription_id, due_date FROM payments WHERE status = 'succeeded'
  GROUP BY 1, 2 HAVING COUNT(*) > 1);
