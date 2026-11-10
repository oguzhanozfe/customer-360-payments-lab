-- How much did identity resolution collapse, and by which rule?
SELECT (SELECT COUNT(*) FROM accounts) AS accounts,
       (SELECT COUNT(DISTINCT customer_id) FROM identity_map) AS customers,
       (SELECT COUNT(*) FROM customer_360 WHERE brands > 1) AS multi_brand_customers,
       (SELECT COUNT(*) FROM identity_map WHERE linked_by = 'email') AS linked_by_email,
       (SELECT COUNT(*) FROM identity_map WHERE linked_by = 'phone+name') AS linked_by_phone_and_name;
