"""Step 2: extract package names, check registries, and summarize hallucination rates."""
import concurrent.futures as cf
import json
from collections import Counter, defaultdict
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from slopbench import registry  # noqa: E402
from slopbench.extract import extract  # noqa: E402

RES = Path(__file__).parent / "results"


def load_responses():
    latest = {}
    for r in map(json.loads, (RES / "responses.jsonl").open()):
        if not r["error"] and r["response"].strip():
            latest[(r["model"], r["id"], r["sample"])] = r
    return list(latest.values())


MIN_COVERAGE = 0.75  # drop models that answered fewer than 75% of tasks


def main():
    rows = load_responses()
    n_tasks = len({r["id"] for r in rows})
    answered = Counter(r["model"] for r in rows)
    excluded = {m: n for m, n in answered.items() if n < MIN_COVERAGE * n_tasks}
    rows = [r for r in rows if r["model"] not in excluded]
    mentions = []  # one row per (response, package, source)
    for r in rows:
        found = extract(r["response"], r["lang"])
        for source, names in found.items():
            for name in names:
                mentions.append({"model": r["model"], "id": r["id"], "lang": r["lang"],
                                 "difficulty": r["difficulty"], "task": r["task"],
                                 "package": name, "source": source})
    df = pd.DataFrame(mentions)
    # PEP 503 normalization so kicad_sch and kicad-sch count as the same name.
    py = df.lang == "python"
    df.loc[py, "package"] = df.loc[py, "package"].str.lower().str.replace(r"[-_.]+", "-", regex=True)
    df = df.drop_duplicates(["model", "id", "package", "source"])

    unique = df[["package", "lang"]].drop_duplicates().itertuples(index=False)
    with cf.ThreadPoolExecutor(16) as ex:
        status = dict(zip(((p, l) for p, l in unique),
                          ex.map(lambda pl: registry.exists(*pl),
                                 df[["package", "lang"]].drop_duplicates().itertuples(index=False))))
    registry.save()
    df["exists"] = [status[(p, l)] for p, l in zip(df.package, df.lang)]
    df = df[df.exists.notna()]
    df["hallucinated"] = ~df.exists.astype(bool)
    df.to_csv(RES / "mentions.csv", index=False)

    # Primary metric: names the model explicitly told the user to `pip/npm install`.
    inst = df[df.source == "install"]
    by_model = (inst.groupby("model")
                .agg(packages=("package", "size"), hallucinated=("hallucinated", "sum"))
                .assign(rate=lambda d: 100 * d.hallucinated / d.packages))
    resp_any = (inst.groupby(["model", "id"]).hallucinated.any().groupby("model").mean() * 100)
    by_model["responses_with_fake_%"] = resp_any
    by_model = by_model.sort_values("rate", ascending=False).round(1)

    by_diff = (inst.groupby(["lang", "difficulty"])
               .agg(packages=("package", "size"), hallucinated=("hallucinated", "sum"))
               .assign(rate=lambda d: (100 * d.hallucinated / d.packages).round(1)))

    fakes = inst[inst.hallucinated]
    repeat = fakes.groupby(["lang", "package"]).agg(
        models=("model", "nunique"), mentions=("id", "size")).reset_index()
    cross_model = repeat[repeat.models >= 2].sort_values(["models", "mentions"], ascending=False)

    # Import-only signal (noisier: import name != distribution name for some packages).
    imp = df[(df.source == "import")]
    imp_rate = (imp.groupby("model").hallucinated.mean() * 100).round(1)

    summary = {
        "responses": len(rows),
        "responses_per_model": {m: n for m, n in answered.items() if m not in excluded},
        "excluded_low_coverage": excluded,
        "install_mentions": len(inst),
        "unique_install_names": int(inst[["lang", "package"]].drop_duplicates().shape[0]),
        "unique_fake_names": int(fakes[["lang", "package"]].drop_duplicates().shape[0]),
        "fake_names_suggested_by_2plus_models": int(len(cross_model)),
        "overall_install_hallucination_rate_%": round(100 * inst.hallucinated.mean(), 2),
    }
    (RES / "summary.json").write_text(json.dumps(summary, indent=2))
    by_model.to_csv(RES / "by_model.csv")
    by_diff.to_csv(RES / "by_difficulty.csv")
    cross_model.to_csv(RES / "cross_model_fakes.csv", index=False)

    print(json.dumps(summary, indent=2))
    print("\nBy model (install commands):\n", by_model.to_string())
    print("\nBy language/difficulty:\n", by_diff.to_string())
    print("\nImport-statement hallucination rate (noisier):\n", imp_rate.to_string())
    print("\nFake names suggested by >=2 models:\n", cross_model.head(20).to_string(index=False))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    short = [m.split("/")[1] for m in by_model.index]
    ax.barh(short, by_model.rate, color="#c0392b")
    ax.invert_yaxis()
    ax.set_xlabel("% of `pip/npm install` package names that do not exist")
    ax.set_title("Package hallucination rate by model")
    for i, v in enumerate(by_model.rate):
        ax.text(v + 0.1, i, f"{v:.1f}%", va="center", fontsize=9)
    fig.tight_layout()
    fig.savefig(RES / "hallucination_by_model.png", dpi=150)

    fig, ax = plt.subplots(figsize=(6, 4))
    piv = by_diff.rate.unstack()
    piv.plot.bar(ax=ax, color=["#7f8c8d", "#c0392b"], rot=0)
    for bars in ax.containers:
        ax.bar_label(bars, fmt="%.1f%%", fontsize=9)
    ax.set_ylabel("% hallucinated install names")
    ax.set_title("Common vs niche tasks")
    fig.tight_layout()
    fig.savefig(RES / "hallucination_by_difficulty.png", dpi=150)


if __name__ == "__main__":
    main()
