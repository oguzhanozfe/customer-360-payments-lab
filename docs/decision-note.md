# Decision note: where to act first on churn

Synthetic data, as of 2026-10-01. The note keeps four things apart: what the data shows,
what it does not prove, what to do next, and how to measure it.

## Observation

- About a third of churn is involuntary. In September 2026, 24 of the 70 subscriptions that
  ended were lost to failed payments (`04_churn_split`).
- Recovery depends on why the payment failed (`05_payment_failures`): insufficient funds and
  3DS failures mostly recover on a later retry (84-85%), expired cards rarely do (23%).
- Multi-brand customers cancel a little less per subscription (24.6% vs 28.8%) and bring
  about 2.6x the revenue per customer (`09_cross_brand`).

## What this does not show

- The multi-brand gap is a correlation. People who join several brands may already be the
  more engaged ones, and they hold more subscriptions, which alone raises revenue per customer.
  It does not show that a bundle would cut churn.
- Retry recovery is measured on a fixed day 1/3/7 schedule only, so it says nothing about
  better retry timing.

## Next step

1. For `expired_card`, stop relying on retries. Send update-card prompts (email, SMS, in-app)
   before the card expires and at the first decline. Use a card-updater or token service
   where the payment provider supports it.
2. Test retry timing for `insufficient_funds`, for example retrying near common paydays
   against the fixed schedule, with the subscription as the unit of randomization.
3. Test a cross-brand bundle as an experiment, not as a conclusion from the table above.

## How to measure

- Primary: involuntary churn rate per month, and recovered revenue over failed revenue.
- Guardrails: voluntary churn (reminders must not prompt cancellations), payment-provider
  fees per successful charge, and support contacts about billing.
