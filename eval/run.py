"""Score the agent: each answer must contain the number a fixed SQL query gives (within 1%)."""
import json
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from lab.ask import MODEL, ask, connect  # noqa: E402

HERE = Path(__file__).resolve().parent


def numbers(text):
    return [float(n.replace(",", "")) for n in re.findall(r"\d[\d,]*\.?\d*", text)]


def main():
    con = connect()
    passed, rows = 0, []
    for q in json.loads((HERE / "questions.json").read_text()):
        expected = con.execute(q["truth"]).fetchone()[0]
        t = time.time()
        answer, queries = ask(q["question"], con, log=lambda *_: None)
        secs = time.time() - t
        ok = any(abs(n - expected) <= max(0.01 * abs(expected), 0.05) for n in numbers(answer))
        ok = ok and q.get("must_mention", "").lower() in answer.lower()
        passed += ok
        rows.append("| {} | {} | {:g} | {} | {} | {:.0f} s |".format(
            q["id"], "pass" if ok else "FAIL", round(expected, 2), len(queries),
            " ".join(answer.split())[:120].replace("|", "/"), secs))
        print(rows[-1], flush=True)
    report = ["# Agent evaluation", "", "Model: `{}`, one run per question, temperature 0.".format(MODEL), "",
              "**{}/{} answers contain the correct number.**".format(passed, len(rows)), "",
              "| id | result | expected | SQL calls | answer (start) | time |", "|---|---|---|---|---|---|"] + rows
    (HERE / "RESULTS.md").write_text("\n".join(report) + "\n")
    print("{}/{}".format(passed, len(rows)))


if __name__ == "__main__":
    main()
