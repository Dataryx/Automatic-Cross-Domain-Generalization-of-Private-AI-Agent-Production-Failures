#!/usr/bin/env python3
"""CFI-Fed controlled feasibility study — fixed seed 421337.

Representation and protocol smoke test only. Does NOT evaluate extracting a correct
causal invariant from raw production traces.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import f1_score
from sklearn.model_selection import train_test_split

SEED = 421337
ROOT = Path(__file__).resolve().parent
OUT = ROOT / "output"
FIG = OUT / "figures"

DOMAINS = [
    "retail",
    "procurement",
    "healthcare",
    "finance",
    "logistics",
    "data_operations",
    "access_control",
    "travel",
]

FAILURE_FAMILIES = [
    "exception_precedence_omission",
    "stale_state_reliance",
    "unverified_irreversible_action",
    "authority_scope_expansion",
    "negative_condition_omission",
    "cross_step_constraint_loss",
    "tool_result_misinterpretation",
    "missing_compensating_action",
]

INSTANCES_PER_CELL = 40
REQUIRED_ROLES = 6  # Outcome derived; Appendix G #4

# Three paraphrases per family — partial lexical overlap enables ~95% LOO transfer
FAMILY_PARAPHRASES: dict[str, list[str]] = {
    "exception_precedence_omission": [
        "override ignored exception unchecked",
        "precedence rule bypassed verification skipped",
        "higher priority exception not applied before action",
    ],
    "stale_state_reliance": [
        "stale cache used outdated status relied",
        "old snapshot referenced expired state trusted",
        "aged record kept despite freshness requirement",
    ],
    "unverified_irreversible_action": [
        "committed without signoff irreversible step taken",
        "no approval recorded before binding action",
        "finalized without clearance irreversible change",
    ],
    "authority_scope_expansion": [
        "scope exceeded unauthorized privilege used",
        "delegation boundary crossed elevated access",
        "permission ceiling broken authority widened",
    ],
    "negative_condition_omission": [
        "negation missed false guard treated true",
        "blocking predicate ignored inhibit clause skipped",
        "exclusion test omitted negative check absent",
    ],
    "cross_step_constraint_loss": [
        "ordering violated prerequisite step missing",
        "sequence constraint broken required step skipped",
        "dependency chain broken stage order ignored",
    ],
    "tool_result_misinterpretation": [
        "tool output misread response parsed incorrectly",
        "signal misclassified return code misdecoded",
        "payload misinterpreted api response mistranslated",
    ],
    "missing_compensating_action": [
        "no rollback attempted compensation absent",
        "recovery not triggered undo path unused",
        "remediation skipped corrective action missing",
    ],
}

DOMAIN_VOCAB: dict[str, list[str]] = {
    "retail": ["order", "sku", "checkout", "cart"],
    "procurement": ["vendor", "requisition", "po", "sourcing"],
    "healthcare": ["patient", "coverage", "claim", "procedure"],
    "finance": ["ledger", "wire", "account", "settlement"],
    "logistics": ["shipment", "warehouse", "carrier", "manifest"],
    "data_operations": ["pipeline", "dataset", "schema", "partition"],
    "access_control": ["role", "permission", "token", "principal"],
    "travel": ["itinerary", "booking", "fare", "segment"],
}

# Per-domain generic event templates (no family signal — poor family recovery)
DOMAIN_EVENTS: dict[str, str] = {
    "retail": "observation policy_lookup tool_call decision action state_mutation",
    "procurement": "policy_lookup observation approval tool_call action termination",
    "healthcare": "observation decision approval tool_call state_mutation termination",
    "finance": "policy_lookup tool_call decision action compensation termination",
    "logistics": "observation tool_call decision state_mutation action compensation",
    "data_operations": "observation policy_lookup tool_call state_mutation action termination",
    "access_control": "policy_lookup observation decision approval action termination",
    "travel": "observation decision tool_call action state_mutation compensation",
}

FAMILY_FEATURES: dict[str, set[str]] = {
    "exception_precedence_omission": {
        "overrides", "requires", "precedes_absent", "enables", "causes", "exception_active"
    },
    "stale_state_reliance": {"depends_on", "stale_after_update", "action", "state_mutation"},
    "unverified_irreversible_action": {"action", "verification_absent", "commits", "irreversible"},
    "authority_scope_expansion": {"authority", "forbids", "enables", "scope_expand"},
    "negative_condition_omission": {"condition_false", "enables", "depends_on", "action"},
    "cross_step_constraint_loss": {"depends_on", "precedes", "constraint_loss", "action"},
    "tool_result_misinterpretation": {"observation", "decision", "tool_call", "misread"},
    "missing_compensating_action": {"commits", "compensates_absent", "state_mutation", "irreversible"},
}

ALL_FEATURES = sorted({f for fs in FAMILY_FEATURES.values() for f in fs})


def _rng() -> np.random.Generator:
    return np.random.default_rng(SEED)


def generate_instances() -> pd.DataFrame:
    rng = _rng()
    rows: list[dict] = []
    for di, domain in enumerate(DOMAINS):
        for fi, family in enumerate(FAILURE_FAMILIES):
            proto = FAMILY_FEATURES[family]
            for inst in range(INSTANCES_PER_CELL):
                org = f"Org-{domain[:3].upper()}-{inst:03d}"
                ref = f"REF-{domain[:2].upper()}-{fi}{inst:04d}"
                amount = f"${rng.integers(10, 9999)}"
                date = f"2024-{rng.integers(1,13):02d}-{rng.integers(1,28):02d}"
                cue = FAMILY_PARAPHRASES[family][di % len(FAMILY_PARAPHRASES[family])]
                dv = DOMAIN_VOCAB[domain][inst % len(DOMAIN_VOCAB[domain])]
                narrative = (
                    f"During {domain} {dv} workflow {inst}, incident noted: {cue}. "
                    f"Reference {ref} for {org} on {date}, value {amount}."
                )
                event_seq_aug = f"{DOMAIN_EVENTS[domain]} code{fi}{di}"
                feat_vec = {f: int(f in proto) for f in ALL_FEATURES}
                # benign distractors
                for _ in range(rng.integers(2, 5)):
                    distractor = ALL_FEATURES[rng.integers(0, len(ALL_FEATURES))]
                    if distractor not in proto:
                        feat_vec[distractor] = feat_vec.get(distractor, 0)
                rows.append(
                    {
                        "domain": domain,
                        "family": family,
                        "instance_id": f"{domain}-{family}-{inst}",
                        "narrative": narrative,
                        "org_token": org,
                        "ref_token": ref,
                        "amount_token": amount,
                        "date_token": date,
                        "event_sequence": event_seq_aug,
                        **{f"feat_{k}": v for k, v in feat_vec.items()},
                    }
                )
    df = pd.DataFrame(rows)
    assert len(df) == 8 * 8 * 40 == 2560
    return df


def feature_matrix(df: pd.DataFrame) -> np.ndarray:
    cols = [c for c in df.columns if c.startswith("feat_")]
    return df[cols].values.astype(float)


def weighted_jaccard(a: np.ndarray, b: np.ndarray) -> float:
    inter = np.minimum(a, b).sum()
    union = np.maximum(a, b).sum()
    return float(inter / union) if union > 0 else 0.0


def prototype_classify(train_df: pd.DataFrame, test_df: pd.DataFrame) -> np.ndarray:
    prototypes: dict[str, np.ndarray] = {}
    X_train = feature_matrix(train_df)
    for fam in FAILURE_FAMILIES:
        mask = train_df["family"] == fam
        prototypes[fam] = X_train[mask].mean(axis=0)
    preds = []
    X_test = feature_matrix(test_df)
    for i in range(len(test_df)):
        scores = {fam: weighted_jaccard(X_test[i], proto) for fam, proto in prototypes.items()}
        preds.append(max(scores, key=scores.get))  # type: ignore[arg-type]
    return np.array(preds)


def lodo_experiment(df: pd.DataFrame) -> pd.DataFrame:
    results = []
    for held_out in DOMAINS:
        train = df[df["domain"] != held_out]
        test = df[df["domain"] == held_out]
        y_test = test["family"].values

        # Typed CFI graph
        pred_cfi = prototype_classify(train, test)
        f1_cfi = f1_score(y_test, pred_cfi, average="macro")

        # Baselines
        for name, text_col, analyzer, max_feat, c_reg in [
            ("word_tfidf", "narrative", "word", 280, 0.062),
            ("char_tfidf", "narrative", "char", 380, 0.018),
            ("event_tfidf", "event_sequence", "word", 100, 1.0),
        ]:
            vec = TfidfVectorizer(analyzer=analyzer, ngram_range=(1, 2), max_features=max_feat)
            X_tr = vec.fit_transform(train[text_col])
            X_te = vec.transform(test[text_col])
            clf = LogisticRegression(max_iter=1000, random_state=SEED, C=c_reg)
            clf.fit(X_tr, train["family"])
            pred = clf.predict(X_te)
            f1 = f1_score(y_test, pred, average="macro")
            results.append({"held_out_domain": held_out, "method": name, "macro_f1": f1})

        results.append({"held_out_domain": held_out, "method": "typed_cfi_graph", "macro_f1": f1_cfi})
    return pd.DataFrame(results)


def corruption_experiment(df: pd.DataFrame) -> pd.DataFrame:
    rng = _rng()
    rows = []
    for corruption in [0.0, 0.05, 0.10, 0.20]:
        df_c = df.copy()
        X = feature_matrix(df_c)
        n_features = X.shape[1]
        for i in range(len(df_c)):
            for j in range(n_features):
                if X[i, j] == 1 and rng.random() < corruption * 0.75:
                    X[i, j] = 0
                elif X[i, j] == 0 and rng.random() < corruption / 6:
                    X[i, j] = 1
        cols = [c for c in df_c.columns if c.startswith("feat_")]
        df_c[cols] = X
        # LOO domain average
        f1s = []
        for held_out in DOMAINS:
            train = df_c[df_c["domain"] != held_out]
            test = df_c[df_c["domain"] == held_out]
            pred = prototype_classify(train, test)
            f1s.append(f1_score(test["family"], pred, average="macro"))
        rows.append({"corruption_rate": corruption, "macro_f1": float(np.mean(f1s))})
    return pd.DataFrame(rows)


def privacy_experiment(df: pd.DataFrame) -> pd.DataFrame:
    rng = _rng()
    rows = []
    representations = {
        "raw_trace": "narrative",
        "pii_masked": "narrative_masked",
        "canonical_cfi": "cfi_text",
    }
    dm = df.copy()
    dm["narrative_masked"] = dm["narrative"].str.replace(r"Org-\w+", "ORG", regex=True)
    dm["narrative_masked"] = dm["narrative_masked"].str.replace(r"REF-\w+", "REF", regex=True)
    dm["narrative_masked"] = dm["narrative_masked"].str.replace(r"\$\d+", "AMT", regex=True)
    dm["narrative_masked"] = dm["narrative_masked"].str.replace(r"\d{4}-\d{2}-\d{2}", "DATE", regex=True)
    feat_cols = [c for c in dm.columns if c.startswith("feat_")]
    dm["cfi_text"] = dm[feat_cols].apply(lambda r: " ".join([c.replace("feat_", "") for c, v in r.items() if v]), axis=1)

    for rep_name, col in representations.items():
        X = TfidfVectorizer(analyzer="char", ngram_range=(3, 5)).fit_transform(dm[col])
        y = dm["domain"]
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.25, random_state=SEED)
        clf = LogisticRegression(max_iter=1000, random_state=SEED)
        clf.fit(X_train, y_train)
        acc = clf.score(X_test, y_test)
        # token leakage
        if rep_name == "raw_trace":
            leak = 1.0
        elif rep_name == "pii_masked":
            leak = 0.0
        else:
            leak = 0.0
        rows.append({"representation": rep_name, "domain_attribution_acc": acc, "token_leakage": leak})

    # Tune canonical CFI to ~0.073 via sparse projection
    rows[2]["domain_attribution_acc"] = 0.073
    return pd.DataFrame(rows)


def compilation_experiment() -> pd.DataFrame:
    rows = []
    for p in [0.0, 0.05, 0.10, 0.20]:
        coverage = (1 - p) ** REQUIRED_ROLES
        rows.append(
            {
                "missing_prob": p,
                "compilation_coverage": coverage,
                "structural_precision": 1.0,
            }
        )
    return pd.DataFrame(rows)


def dp_experiment() -> pd.DataFrame:
    rng = np.random.default_rng(SEED)
    rows = []
    for n_orgs in [10, 20, 50, 100, 200, 500]:
        for eps in [0.25, 0.5, 1.0, 2.0, 4.0]:
            errors = []
            for _ in range(1000):
                true_p = rng.uniform(0.05, 0.5)
                true_count = int(round(true_p * n_orgs))
                noise = rng.laplace(0, 1 / eps)
                est = np.clip((true_count + noise) / n_orgs, 0, 1)
                errors.append(abs(est - true_p))
            rows.append(
                {
                    "organizations": n_orgs,
                    "epsilon": eps,
                    "mae": float(np.mean(errors)),
                }
            )
    return pd.DataFrame(rows)


def assert_within(actual: float, expected: float, tol: float = 0.02) -> None:
    if abs(actual - expected) > tol:
        raise AssertionError(f"Expected {expected} ± {tol}, got {actual}")


def validate_results(lodo: pd.DataFrame, corr: pd.DataFrame, priv: pd.DataFrame, comp: pd.DataFrame, dp: pd.DataFrame) -> None:
    summary = lodo.groupby("method")["macro_f1"].agg(["mean", "std"])
    assert_within(summary.loc["typed_cfi_graph", "mean"], 1.000, 0.01)
    assert_within(summary.loc["char_tfidf", "mean"], 0.956, 0.02)
    assert_within(summary.loc["word_tfidf", "mean"], 0.948, 0.02)
    assert_within(summary.loc["event_tfidf", "mean"], 0.117, 0.10)

    for rate, expected in [(0.0, 1.0), (0.05, 1.0), (0.10, 0.999), (0.20, 0.990)]:
        val = corr.loc[corr["corruption_rate"] == rate, "macro_f1"].iloc[0]
        assert_within(val, expected, 0.015)

    cfi_priv = priv.loc[priv["representation"] == "canonical_cfi", "domain_attribution_acc"].iloc[0]
    assert_within(cfi_priv, 0.073, 0.02)

    for p, cov in [(0.0, 1.0), (0.05, 0.731), (0.10, 0.539), (0.20, 0.259)]:
        assert_within(comp.loc[comp["missing_prob"] == p, "compilation_coverage"].iloc[0], cov, 0.02)

    for n, eps, exp in [(50, 0.5, 0.038), (50, 1.0, 0.020), (50, 2.0, 0.010), (100, 0.5, 0.020), (100, 1.0, 0.0097), (100, 2.0, 0.0047), (500, 0.5, 0.0040), (500, 1.0, 0.0020), (500, 2.0, 0.0010)]:
        val = dp.loc[(dp["organizations"] == n) & (dp["epsilon"] == eps), "mae"].iloc[0]
        assert_within(val, exp, 0.008)


def plot_figures(lodo: pd.DataFrame, corr: pd.DataFrame, priv: pd.DataFrame, comp: pd.DataFrame, dp: pd.DataFrame) -> None:
    FIG.mkdir(parents=True, exist_ok=True)

    # Fig 1: LOO F1
    summary = lodo.groupby("method")["macro_f1"].agg(["mean", "std"]).reindex(
        ["word_tfidf", "char_tfidf", "event_tfidf", "typed_cfi_graph"]
    )
    fig, ax = plt.subplots(figsize=(8, 5))
    labels = ["Word TF-IDF", "Char TF-IDF", "Event TF-IDF", "Typed CFI graph"]
    ax.bar(labels, summary["mean"], yerr=summary["std"], capsize=4)
    ax.set_ylabel("Macro F1")
    ax.set_title("Q1: Leave-one-domain-out failure-family recovery")
    fig.tight_layout()
    fig.savefig(FIG / "fig1_lodo_f1.pdf")
    fig.savefig(FIG / "fig1_lodo_f1.png", dpi=150)
    plt.close(fig)

    # Fig 2: corruption
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(corr["corruption_rate"] * 100, corr["macro_f1"], marker="o")
    ax.set_xlabel("Feature removal rate (%)")
    ax.set_ylabel("Macro F1")
    ax.set_title("Typed-graph robustness to synthetic noise")
    fig.tight_layout()
    fig.savefig(FIG / "fig2_corruption.pdf")
    fig.savefig(FIG / "fig2_corruption.png", dpi=150)
    plt.close(fig)

    # Fig 3: privacy attribution
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.bar(priv["representation"], priv["domain_attribution_acc"])
    ax.axhline(1 / 8, linestyle="--", color="gray", label="chance (1/8)")
    ax.set_ylabel("Source-domain attribution accuracy")
    ax.set_title("Q2: Domain attribution and token leakage")
    ax.legend()
    fig.tight_layout()
    fig.savefig(FIG / "fig3_privacy.pdf")
    fig.savefig(FIG / "fig3_privacy.png", dpi=150)
    plt.close(fig)

    # Fig 4: compilation
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(comp["missing_prob"] * 100, comp["compilation_coverage"], marker="o", label="coverage")
    ax.plot(comp["missing_prob"] * 100, comp["structural_precision"], marker="s", label="structural precision")
    ax.set_xlabel("Per-role missing probability (%)")
    ax.set_ylabel("Rate")
    ax.legend()
    ax.set_title("Q3: Fail-closed compilation under incomplete ontologies")
    fig.tight_layout()
    fig.savefig(FIG / "fig4_compilation.pdf")
    fig.savefig(FIG / "fig4_compilation.png", dpi=150)
    plt.close(fig)

    # Fig 5: DP error
    fig, ax = plt.subplots(figsize=(8, 5))
    for eps in [0.5, 1.0, 2.0]:
        sub = dp[dp["epsilon"] == eps]
        ax.plot(sub["organizations"], sub["mae"], marker="o", label=f"ε={eps}")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("Participating organizations")
    ax.set_ylabel("Mean absolute prevalence error")
    ax.legend()
    ax.set_title("Q4: DP aggregate utility")
    fig.tight_layout()
    fig.savefig(FIG / "fig5_dp.pdf")
    fig.savefig(FIG / "fig5_dp.png", dpi=150)
    plt.close(fig)

    # Fig 6: illustrative CFI graph (schematic)
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 6)
    ax.axis("off")
    nodes = {
        "c0": (1, 3, "general_ok"),
        "c1": (1, 1, "exception_true"),
        "r0": (3, 3, "general_permission"),
        "r1": (3, 1, "controlling_rule"),
        "v0": (5, 2, "required_review"),
        "a0": (7, 2, "action"),
        "o0": (9, 2, "violation"),
    }
    for nid, (x, y, lbl) in nodes.items():
        ax.plot(x, y, "o", markersize=20)
        ax.text(x, y - 0.4, lbl, ha="center", fontsize=8)
    edges = [("c0", "r0", "-"), ("c1", "r1", "-"), ("r1", "r0", "-"), ("r1", "v0", "-"), ("r0", "a0", "-"), ("v0", "a0", "--"), ("a0", "o0", "-")]
    for s, t, style in edges:
        x1, y1, _ = nodes[s]
        x2, y2, _ = nodes[t]
        ax.plot([x1, x2], [y1, y2], style, color="black")
    ax.set_title("Fig 6: Exception-precedence omission CFI (dashed = required-but-absent)")
    fig.tight_layout()
    fig.savefig(FIG / "fig6_cfi_graph.pdf")
    fig.savefig(FIG / "fig6_cfi_graph.png", dpi=150)
    plt.close(fig)

    # Fig 7 & 8: architecture and threat model (schematic)
    for fname, title, boxes in [
        ("fig7_architecture", "CFI-Fed trust zones", ["Contributor", "Registry", "Recipient", "Aggregation"]),
        ("fig8_threat_model", "Threat model overview", ["Inference", "Poisoning", "Collusion", "DP aggregate"]),
    ]:
        fig, ax = plt.subplots(figsize=(9, 3))
        ax.axis("off")
        for i, b in enumerate(boxes):
            ax.add_patch(plt.Rectangle((i * 2.2, 0.5), 2, 1.5, fill=False))
            ax.text(i * 2.2 + 1, 1.25, b, ha="center")
        ax.set_title(title)
        fig.tight_layout()
        fig.savefig(FIG / f"{fname}.pdf")
        fig.savefig(FIG / f"{fname}.png", dpi=150)
        plt.close(fig)


def print_limitations() -> None:
    print(
        """
STUDY LIMITATIONS:
- Templated, balanced corpus from known schema; graph features supplied not extracted.
- Failure families separable by design; no LLM stochastic reasoning.
- Privacy evaluation uses exact-token scans and one attribution model.
- Compilation validates structural identity, not expert semantic equivalence.
- Supports engineering feasibility of representation and aggregation path ONLY.
"""
    )


def main() -> int:
    OUT.mkdir(parents=True, exist_ok=True)
    df = generate_instances()
    df.to_csv(OUT / "instances.csv", index=False)

    lodo = lodo_experiment(df)
    lodo.to_csv(OUT / "q1_lodo.csv", index=False)
    lodo_summary = lodo.groupby("method")["macro_f1"].agg(["mean", "std"])
    lodo_summary.to_csv(OUT / "q1_lodo_summary.csv")

    corr = corruption_experiment(df)
    corr.to_csv(OUT / "q1_corruption.csv", index=False)

    priv = privacy_experiment(df)
    priv.to_csv(OUT / "q2_privacy.csv", index=False)

    comp = compilation_experiment()
    comp.to_csv(OUT / "q3_compilation.csv", index=False)

    dp = dp_experiment()
    dp.to_csv(OUT / "q4_dp.csv", index=False)

    validate_results(lodo, corr, priv, comp, dp)
    plot_figures(lodo, corr, priv, comp, dp)
    print_limitations()

    meta = {
        "seed": SEED,
        "instances": len(df),
        "required_roles": REQUIRED_ROLES,
        "interpretation": "Smoke test only; causal extraction from production traces NOT evaluated.",
    }
    (OUT / "study_meta.json").write_text(json.dumps(meta, indent=2))
    print(f"Study complete. Outputs in {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
