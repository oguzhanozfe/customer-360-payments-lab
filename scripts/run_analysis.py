"""Build the database, score identity resolution, and print every analysis query as Markdown."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.db import ROOT, SQL, build  # noqa: E402
from lab.resolve import resolve, score  # noqa: E402


def markdown(cur):
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()
    out = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    out += ["| " + " | ".join("" if v is None else str(v) for v in r) + " |" for r in rows]
    return "\n".join(out)


def main():
    db = ROOT / "data" / "lab.sqlite"
    db.parent.mkdir(exist_ok=True)
    if db.exists():
        db.unlink()
    con, data, mapping = build(str(db))
    s = score(mapping, data["truth"])
    print("## Identity resolution against the generator's truth\n")
    print("Same-person links: {correct} of {predicted_links} predicted are right (precision {p:.1%}); "
          "{correct} of {true_links} true links found (recall {r:.1%}).\n".format(
              p=s["precision"], r=s["recall"], **s))
    loose = score(resolve(data["accounts"], phone_needs_name=False)[0], data["truth"])
    print("Matching on phone alone instead would give precision {:.1%} and recall {:.1%}: "
          "families share a number.\n".format(loose["precision"], loose["recall"]))
    for f in sorted((SQL / "analysis").glob("*.sql")):
        print("## " + f.stem + "\n")
        print(markdown(con.execute(f.read_text())) + "\n")
    print("Database written to " + str(db.relative_to(ROOT)))


if __name__ == "__main__":
    main()
