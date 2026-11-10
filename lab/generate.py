"""Deterministic synthetic data: three brands, messy accounts, subscriptions and payment attempts.

Everything is invented. The generator also returns the true person behind each
account so identity resolution can be scored; the analysis never reads it.
"""
import random
from datetime import date, timedelta

AS_OF = date(2026, 10, 1)
FIRST_START = date(2025, 1, 1)

BRANDS = {
    # brand: list of (plan, price in TRY, months per billing period)
    "news": [("premium_monthly", 99, 1), ("premium_yearly", 990, 12)],
    "sports": [("adfree_monthly", 59, 1)],
    "tv": [("basic_monthly", 149, 1), ("plus_monthly", 249, 1), ("plus_yearly", 2490, 12)],
}
DECLINES = [  # (code, weight on a first attempt, chance a later retry succeeds)
    ("insufficient_funds", 45, 0.45),
    ("do_not_honor", 20, 0.30),
    ("expired_card", 15, 0.08),
    ("3ds_failed", 12, 0.50),
    ("fraud_suspected", 8, 0.02),
]
RETRY_DAYS = [1, 3, 7]  # dunning schedule after a failed first attempt
FIRST = "Ahmet Ayşe Mehmet Fatma Mustafa Emine Ali Hatice Hüseyin Zeynep İbrahim Elif Can Şule Oğuz Gül Burak Özge Çağrı Merve".split()
LAST = "Yılmaz Kaya Aksoy Şahin Çelik Yıldız Yıldırım Öztürk Aydın Polat Arslan Doğan Kılıç Aslan Çetin Kara Koç Kurt Özkan Şimşek".split()
ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def add_months(d, n):
    y, m = divmod(d.month - 1 + n, 12)
    year, month = d.year + y, m + 1
    days = [31, 29 if year % 4 == 0 else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return date(year, month, min(d.day, days))


def _email_variant(rng, local, domain):
    """The same mailbox written the way different sign-up forms keep it."""
    if domain == "gmail.com" and rng.random() < 0.3:
        local = local.replace(".", "") if "." in local else local[:3] + "." + local[3:]
    if rng.random() < 0.15:
        local += "+" + rng.choice(["news", "promo", "tv"])
    email = local + "@" + domain
    return email.upper() if rng.random() < 0.1 else email.capitalize() if rng.random() < 0.2 else email


def _phone_variant(rng, digits):
    """digits is a ten-digit mobile number such as 5321234567."""
    return rng.choice([
        "0" + digits,
        "+90" + digits,
        "0{} {} {} {}".format(digits[:3], digits[3:6], digits[6:8], digits[8:]),
        digits,
    ])


def generate(n_people=3000, seed=7):
    rng = random.Random(seed)
    accounts, subscriptions, payments, truth = [], [], [], []
    households = []  # phones shared by more than one person
    for pid in range(1, n_people + 1):
        first, last = rng.choice(FIRST), rng.choice(LAST)
        # A mailbox belongs to one person, so the local part carries the person id.
        local = "{}.{}{}".format(first, last, pid).translate(ASCII).lower()
        domain = rng.choice(["gmail.com", "gmail.com", "hotmail.com", "yahoo.com", "outlook.com"])
        if households and rng.random() < 0.08:
            phone = rng.choice(households)  # a family member's phone
        else:
            phone = "5{}{:07d}".format(rng.randint(30, 59), rng.randint(0, 9999999))
            if rng.random() < 0.2:
                households.append(phone)
        brands = rng.sample(list(BRANDS), k=rng.choices([1, 2, 3], weights=[60, 30, 10])[0])
        second_email = rng.random() < 0.12  # uses a different address on one brand
        for i, brand in enumerate(brands):
            aid = "{}-{:05d}".format(brand[:2].upper(), len(accounts) + 1)
            if second_email and i == len(brands) - 1 and i > 0:
                email = "{}{}@icloud.com".format(first.translate(ASCII).lower(), pid)
                ph = _phone_variant(rng, phone) if rng.random() < 0.6 else None
            else:
                email = _email_variant(rng, local, domain)
                ph = _phone_variant(rng, phone) if rng.random() < 0.5 else None
            name = "{} {}".format(first, last)
            name = name.translate(ASCII) if rng.random() < 0.3 else name
            created = FIRST_START + timedelta(days=rng.randint(0, (AS_OF - FIRST_START).days - 1))
            accounts.append((aid, brand, email, ph, name, created.isoformat()))
            truth.append((aid, pid))
            if rng.random() < 0.55:
                _subscribe(rng, aid, brand, created, len(brands), subscriptions, payments)
    return {"accounts": accounts, "subscriptions": subscriptions, "payments": payments, "truth": truth}


def _subscribe(rng, aid, brand, created, n_brands, subscriptions, payments):
    plan, price, months = rng.choice(BRANDS[brand])
    sid = "S{:06d}".format(len(subscriptions) + 1)
    start = created + timedelta(days=rng.randint(0, 30))
    if start >= AS_OF:
        return
    # Monthly voluntary cancel chance; people on several brands stay a little longer.
    cancel_p = 0.06 if n_brands == 1 else 0.04
    due, n, ended, reason = start, 0, None, None
    while due < AS_OF:
        status, attempt, recovered = _charge(rng, sid, due, price, payments)
        if not recovered:
            ended, reason = due + timedelta(days=RETRY_DAYS[-1]), "payment_failed"
            break
        n += 1
        p = 0.12 if n == 1 else 1 - (1 - cancel_p) ** months  # chance to cancel within the paid period
        if rng.random() < p:
            ended, reason = add_months(due, months), "voluntary"  # runs to the end of the paid period
            break
        due = add_months(start, n * months)
    if ended and ended > AS_OF:
        ended, reason = None, None
    subscriptions.append((sid, aid, brand, plan, price, months, start.isoformat(),
                          ended.isoformat() if ended else None, reason))


def _charge(rng, sid, due, price, payments):
    """One billing cycle: a first attempt and, if it fails, up to three dunning retries."""
    def pay(attempt, when, ok, code):
        payments.append(("P{:07d}".format(len(payments) + 1), sid, due.isoformat(), attempt,
                         when.isoformat(), price, "succeeded" if ok else "failed", code))

    if rng.random() < 0.92:
        pay(1, due, True, None)
        return "succeeded", 1, True
    code, _, retry_ok = rng.choices(DECLINES, weights=[w for _, w, _ in DECLINES])[0]
    pay(1, due, False, code)
    for i, days in enumerate(RETRY_DAYS, start=2):
        when = due + timedelta(days=days)
        if when >= AS_OF:
            return "failed", i - 1, True  # still in dunning on the as-of date
        if rng.random() < retry_ok:
            pay(i, when, True, None)
            return "succeeded", i, True
        pay(i, when, False, code)
    return "failed", len(RETRY_DAYS) + 1, False
