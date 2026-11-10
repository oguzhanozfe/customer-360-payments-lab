"""Identity resolution: link accounts across brands into one customer id.

Rules, strongest first:
  1. Same normalized email (case, Gmail dots and +tags removed) -> same person.
  2. Same normalized phone AND same normalized name -> same person.
     A phone alone is not enough: families share one number.
Matches are transitive (union-find), so A~B and B~C puts A, B and C together.
"""
import re
from collections import defaultdict

ASCII = str.maketrans("çğıöşüÇĞİÖŞÜ", "cgiosuCGIOSU")


def norm_email(email):
    local, _, domain = email.strip().lower().partition("@")
    local = local.split("+", 1)[0]
    if domain in ("gmail.com", "googlemail.com"):
        local, domain = local.replace(".", ""), "gmail.com"
    return local + "@" + domain


def norm_phone(phone):
    if not phone:
        return None
    digits = re.sub(r"\D", "", phone)
    digits = digits[2:] if digits.startswith("90") and len(digits) == 12 else digits
    digits = digits[1:] if digits.startswith("0") and len(digits) == 11 else digits
    return digits if len(digits) == 10 else None


def norm_name(name):
    return " ".join(name.translate(ASCII).lower().split())


def resolve(accounts, phone_needs_name=True):
    """accounts: rows of (account_id, brand, email, phone, name, created_at).
    Returns {account_id: customer_id} and {account_id: rule that linked it}."""
    parent = {a[0]: a[0] for a in accounts}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    rule = {}
    keys = defaultdict(list)
    for aid, _, email, phone, name, _ in accounts:
        keys[("email", norm_email(email))].append(aid)
        p = norm_phone(phone)
        if p:
            keys[("phone+name", p, norm_name(name)) if phone_needs_name else ("phone", p)].append(aid)
    for key, ids in keys.items():
        for other in ids[1:]:
            a, b = find(ids[0]), find(other)
            if a != b:
                parent[b] = a
                rule.setdefault(other, key[0])
    # Stable, readable ids: C + the earliest account id in the cluster.
    clusters = defaultdict(list)
    for aid in parent:
        clusters[find(aid)].append(aid)
    mapping = {}
    for members in clusters.values():
        cid = "C-" + min(members)
        for aid in members:
            mapping[aid] = cid
    return mapping, rule


def score(mapping, truth):
    """Pairwise precision and recall of same-person links against the generator's truth."""
    from itertools import combinations

    def pairs(groups):
        out = set()
        for members in groups.values():
            out.update(combinations(sorted(members), 2))
        return out

    predicted, actual = defaultdict(list), defaultdict(list)
    for aid, cid in mapping.items():
        predicted[cid].append(aid)
    for aid, pid in truth:
        actual[pid].append(aid)
    p, t = pairs(predicted), pairs(actual)
    hit = len(p & t)
    return {"predicted_links": len(p), "true_links": len(t), "correct": hit,
            "precision": hit / len(p) if p else 1.0, "recall": hit / len(t) if t else 1.0}
