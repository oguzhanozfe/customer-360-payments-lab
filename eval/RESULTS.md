# Agent evaluation

Model: `qwen3.5:4b`, one run per question, temperature 0.

**6/8 answers contain the correct number.**

| id | result | expected | SQL calls | answer (start) | time |
|---|---|---|---|---|---|
| mrr | pass | 167366 | 1 | The total MRR on 2026-09-01 was **167,365.5 TRY**. This figure represents the sum of all Monthly Recurring Revenue (MRR) | 7 s |
| customers | pass | 3097 | 1 | There are **3,097** distinct customers after merging accounts across brands. This count comes from the `customer_360` vi | 6 s |
| multi_brand | pass | 1077 | 1 | **1,077 customers** have accounts on more than one brand. This represents **34.8%** of the total customer base (**3,097* | 6 s |
| top_decline | pass | 487 | 1 | The decline code **insufficient_funds** causes the most failed first payment attempts, with **487** failures. This repre | 10 s |
| involuntary_sep | pass | 24 | 1 | There were **24 subscriptions** that ended in September 2026 because payment failed. This represents the total count acr | 20 s |
| expired_recovery | FAIL | 23.24 | 1 | Of billing cycles whose first attempt failed with `expired_card` and whose retries are finished, **22.76%** were eventua | 8 s |
| tv_active | FAIL | 486 | 2 | There are **6,164** active TV subscriptions as of October 1, 2026. This count includes all TV brand subscriptions that:  | 11 s |
| top_customer | pass | 7668 | 1 | The highest lifetime revenue of a single customer is **7,668 TRY**. This represents the maximum cumulative revenue gener | 6 s |

## Why the two failures happened

Both wrong answers looked plausible, and both came from the SQL, not the arithmetic:

- `tv_active`: the model counted rows of `subscription_months` over every month instead of
  one month, so each subscription was counted once per month it was active (6,164 instead
  of 486). This is a grain mistake: a join or view at a finer grain than the question.
- `expired_recovery`: the model read "retries are finished" as `attempts > 1`, while the
  metric definition is "paid, or all four attempts used". The number was close (22.8% vs
  23.2%) and still wrong.

The prompt was not tuned on these questions afterwards, because that would only fit this
set. The general fixes are a metric layer with named, tested definitions (for example a
`current_subscriptions` view and a `dunning_recovery` metric) that the model calls instead
of writing raw SQL, and showing the SQL with every answer so a person can check it.
