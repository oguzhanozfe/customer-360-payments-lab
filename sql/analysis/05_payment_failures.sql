-- First-attempt declines by reason, and how many dunning retries recovered.
-- Cycles whose retries were still running on the as-of date are left out of the recovery rate.
SELECT first_decline AS decline_code,
       COUNT(*) AS failed_cycles,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS share_of_declines_pct,
       SUM(paid) AS recovered,
       ROUND(100.0 * SUM(paid) / COUNT(*), 1) AS recovery_pct,
       ROUND(AVG(paid_on_attempt), 2) AS avg_recovering_attempt
FROM billing_cycles
WHERE first_decline IS NOT NULL
  AND (paid = 1 OR attempts = 4)
GROUP BY first_decline
ORDER BY failed_cycles DESC;
