"""
root_cause_analysis.py

Systematic (not hypothesis-by-hypothesis) root-cause analysis for
confirmed false-positive entity matches. Where earlier scripts in this
project tested SPECIFIC suspected patterns (Punjabi suffixes, Vietnamese
tokens), this script is designed to find patterns nobody has hypothesized
yet -- the whole point being that a known root cause (e.g. name-matching
bias) may only explain a small fraction of the total confirmed FP
population, and you need a systematic method to find the rest rather
than continuing to test hunches one at a time.

Four complementary methods, deliberately different in what they're each
good at finding:

1. SUBGROUP DISCOVERY (pysubgroup) -- searches over combinations of
   features to find segments where the FP rate deviates most from
   baseline, ranked by effect size. Good at finding UNEXPECTED feature
   COMBINATIONS you would not have thought to test directly.

2. DECISION TREE SURROGATE (sklearn) -- a shallow, readable tree trained
   on the same features. Not used for prediction -- used because its
   splits are a prioritized, human-readable map of which features the
   data itself finds most discriminating. Cross-checking this against
   your production XGBoost + SHAP output tells you where the two agree
   (well-corroborated) and where the simple tree surfaces something SHAP
   didn't foreground.

3. ASSOCIATION RULE MINING (mlxtend, apriori/fpgrowth) -- surfaces
   frequent co-occurring CATEGORICAL conditions associated with FP status
   without requiring you to specify the combination in advance.
   Complementary to subgroup discovery: subgroup discovery optimizes for
   a single best-quality segment structure, association rules surface
   many frequent patterns at once (useful for casting a wide net).

4. STRATIFIED ERROR-RATE ANALYSIS -- systematically breaks the confirmed
   FP rate down by EVERY operational dimension (not just identity-match
   fields), with a proportion test and multiple-testing correction, since
   a spike unrelated to name/DOB/DL/address (e.g. one match_data_type, one
   record_type, one state) points to a completely different root-cause
   category (pipeline/ETL defect) that identity-matching analysis alone
   would never surface.

Together these directly implement the systematic root-cause framework:
build a MECE taxonomy, tag/analyze the full confirmed population (not
just suspected cases), discover unknown patterns algorithmically, and
quantify what fraction of the total FP population each discovered
pattern actually explains (the Pareto/coverage step) -- rather than
declaring victory after the first plausible story.

Usage
-----
    python root_cause_analysis.py \\
        --data_csv confirmed_matches_for_rca.csv \\
        --output_dir ./rca_results
"""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import pysubgroup as ps
from mlxtend.frequent_patterns import association_rules, fpgrowth
from mlxtend.preprocessing import TransactionEncoder
from scipy import stats
from sklearn.tree import DecisionTreeClassifier, export_text, plot_tree

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
logger = logging.getLogger(__name__)

RANDOM_STATE = 42

# Operational/categorical dimensions to check systematically -- not just
# the identity-match fields. This list is deliberately broad: the whole
# point of stratified analysis is to look where you haven't already
# looked, so include any dimension you have, not just the ones you
# suspect.
STRATIFICATION_DIMENSIONS = [
    "name_eval_ind", "birth_date_eval_ind", "driver_license_eval_ind", "address_eval_ind",
    "match_data_type", "match_type", "record_type", "state_of_origin", "label_source",
]


# =========================================================================
# 1. FEATURE PREPARATION
# =========================================================================

def prepare_analysis_frame(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds derived categorical features useful for discovery methods that
    work best on categorical/binned data (subgroup discovery, association
    rules) -- absent_count, a coarse total_score band, and an is_false_positive
    boolean guaranteed to be a clean 0/1 for pysubgroup's BinaryTarget.
    """
    out = df.copy()
    ind_cols = ["name_eval_ind", "birth_date_eval_ind", "driver_license_eval_ind", "address_eval_ind"]
    ind_matrix = out[ind_cols].to_numpy()
    out["absent_count"] = (ind_matrix == "A").sum(axis=1)
    out["hard_conflict_count"] = (ind_matrix == "D").sum(axis=1)
    out["total_score_band"] = pd.cut(
        out["total_score"], bins=[0, 20, 24, 28, 32, 36],
        labels=["20-20", "21-24", "25-28", "29-32", "33-36"], include_lowest=True,
    ).astype(str)
    out["is_false_positive"] = out["is_false_positive"].astype(bool)
    return out


# =========================================================================
# 2. SUBGROUP DISCOVERY
# =========================================================================

def run_subgroup_discovery(
    df: pd.DataFrame, result_set_size: int = 20, depth: int = 3,
) -> pd.DataFrame:
    """
    Searches over combinations of categorical/discrete features for
    segments where the confirmed FP rate deviates most from the overall
    baseline. qf=WRAccQF (weighted relative accuracy) balances segment
    size against effect size, so results aren't dominated by tiny,
    noisy subgroups.
    """
    search_cols = STRATIFICATION_DIMENSIONS + ["absent_count", "hard_conflict_count", "total_score_band"]
    search_cols = [c for c in search_cols if c in df.columns]
    sg_df = df[search_cols + ["is_false_positive"]].copy()
    for c in search_cols:
        sg_df[c] = sg_df[c].astype(str)

    target = ps.BinaryTarget("is_false_positive", True)
    search_space = ps.create_selectors(sg_df, ignore=["is_false_positive"])
    task = ps.SubgroupDiscoveryTask(
        sg_df, target, search_space, result_set_size=result_set_size, depth=depth, qf=ps.WRAccQF(),
    )
    result = ps.BeamSearch().execute(task)
    result_df = result.to_dataframe()

    baseline_rate = df["is_false_positive"].mean()
    result_df["baseline_fp_rate"] = baseline_rate
    result_df["lift_over_baseline"] = result_df["target_share_sg"] / baseline_rate
    result_df = result_df.sort_values("lift_over_baseline", ascending=False).reset_index(drop=True)
    logger.info("Subgroup discovery: top result -> %s (FP rate %.1f%% vs baseline %.1f%%, lift %.2fx)",
                result_df.iloc[0]["subgroup"], result_df.iloc[0]["target_share_sg"] * 100,
                baseline_rate * 100, result_df.iloc[0]["lift_over_baseline"])
    return result_df


# =========================================================================
# 3. DECISION TREE SURROGATE
# =========================================================================

def run_decision_tree_surrogate(
    df: pd.DataFrame, output_dir: Path, max_depth: int = 4,
) -> tuple[DecisionTreeClassifier, str]:
    """
    A shallow, readable decision tree trained to predict is_false_positive
    from all available features (one-hot encoded categoricals + numeric
    scores). NOT for production prediction -- for reading off which
    feature combinations the data itself finds most discriminating,
    ranked by how early/often they're chosen as splits. Compare the
    top splits here against your production model's SHAP output: where
    they agree, that's corroborated; where the tree finds something SHAP
    doesn't foreground, that's worth a specific look.
    """
    feature_cols = STRATIFICATION_DIMENSIONS + ["absent_count", "hard_conflict_count", "total_score"]
    feature_cols = [c for c in feature_cols if c in df.columns and c != "label_source"]
    numeric_cols = ["absent_count", "hard_conflict_count", "total_score"]
    categorical_cols = [c for c in feature_cols if c not in numeric_cols]
    # Explicit categorical/numeric split rather than dtype detection --
    # pandas 3.0 defaults CSV string columns to a native 'str' dtype, not
    # the legacy 'object' dtype a dtype==object check expects, which
    # silently skips one-hot encoding those columns and passes raw
    # strings into sklearn. Listing the known categorical columns
    # explicitly avoids depending on pandas-version-specific dtype
    # behaviour entirely.
    X = pd.get_dummies(df[feature_cols], columns=categorical_cols)
    y = df["is_false_positive"].astype(int)

    tree = DecisionTreeClassifier(
        max_depth=max_depth, min_samples_leaf=max(20, int(0.005 * len(df))),
        class_weight="balanced", random_state=RANDOM_STATE,
    )
    tree.fit(X, y)

    rules_text = export_text(tree, feature_names=list(X.columns))
    (output_dir / "decision_tree_rules.txt").write_text(rules_text)

    plt.figure(figsize=(22, 10))
    plot_tree(tree, feature_names=list(X.columns), class_names=["Not FP", "FP"],
              filled=True, rounded=True, fontsize=7, max_depth=max_depth)
    plt.tight_layout()
    plt.savefig(output_dir / "decision_tree_surrogate.png", dpi=150, bbox_inches="tight")
    plt.close()

    importances = pd.Series(tree.feature_importances_, index=X.columns).sort_values(ascending=False)
    importances.to_csv(output_dir / "decision_tree_feature_importance.csv", header=["importance"])
    logger.info("Decision tree surrogate: top 5 features by importance:\n%s", importances.head(5).to_string())

    return tree, rules_text


# =========================================================================
# 4. ASSOCIATION RULE MINING
# =========================================================================

def run_association_rules(
    df: pd.DataFrame, min_support: float = 0.03, min_confidence: float = 0.15, max_len: int = 4,
) -> pd.DataFrame:
    """
    Surfaces frequent co-occurring categorical PREDICTOR conditions and
    reports their FP rate, without requiring the combination to be
    specified in advance.

    Deliberately uses only the raw categorical/eval-indicator columns and
    operational dimensions here -- NOT absent_count/hard_conflict_count,
    even though those are available elsewhere in this script. Those two
    are deterministic functions of the four eval-indicator columns, so
    including both creates a combinatorially redundant item lattice that
    makes fpgrowth's search explode without adding real information --
    subgroup discovery already covers derived-count-based segments well.

    Method note: this mines frequent PREDICTOR itemsets only (min_support
    applied to how often the CONDITION occurs), then computes each
    itemset's FP rate directly from the data, rather than asking fpgrowth
    to find frequent {condition + FP-outcome} itemsets jointly. The joint
    approach fails in practice whenever the target is rare (here, FP is
    only ~4% of records): the support of {condition AND FP} is bounded
    above by the base FP rate no matter how strongly the condition
    predicts FP, so a reasonable min_support threshold silently excludes
    every real pattern before confidence/lift are even computed. Mining
    conditions first and scoring their outcome rate separately is the
    standard practical fix for rare-target association-rule mining.
    """
    cat_cols = STRATIFICATION_DIMENSIONS + ["total_score_band"]
    cat_cols = [c for c in cat_cols if c in df.columns]

    transactions = [[f"{c}={row[c]}" for c in cat_cols] for _, row in df.iterrows()]
    te = TransactionEncoder()
    te_array = te.fit(transactions).transform(transactions)
    trans_df = pd.DataFrame(te_array, columns=te.columns_)

    frequent_itemsets = fpgrowth(trans_df, min_support=min_support, use_colnames=True, max_len=max_len)
    if len(frequent_itemsets) == 0:
        logger.warning("No frequent condition itemsets found at min_support=%.3f -- try lowering it.", min_support)
        return pd.DataFrame()

    baseline_fp_rate = df["is_false_positive"].mean()
    rows = []
    for _, item in frequent_itemsets.iterrows():
        itemset = item["itemsets"]
        mask = pd.Series(True, index=df.index)
        for token in itemset:
            col, _, val = token.partition("=")
            mask &= (df[col].astype(str) == val)
        n_matching = mask.sum()
        if n_matching == 0:
            continue
        fp_rate = df.loc[mask, "is_false_positive"].mean()
        if fp_rate < min_confidence:
            continue
        rows.append({
            "condition": " AND ".join(sorted(itemset)),
            "support": item["support"], "n_matching": n_matching,
            "confidence_fp_rate": fp_rate,
            "lift": fp_rate / baseline_fp_rate if baseline_fp_rate > 0 else np.inf,
        })

    fp_rules = pd.DataFrame(rows).sort_values("lift", ascending=False).reset_index(drop=True) if rows else pd.DataFrame()

    logger.info("Association rule mining: %d conditions found with FP rate >= %.0f%% "
                "(min_support=%.3f).", len(fp_rules), min_confidence * 100, min_support)
    if len(fp_rules) > 0:
        top = fp_rules.iloc[0]
        logger.info("Top condition by lift: IF %s THEN FP rate=%.1f%% (n=%d, lift=%.2fx baseline)",
                    top["condition"], top["confidence_fp_rate"] * 100, top["n_matching"], top["lift"])
    return fp_rules


# =========================================================================
# 5. STRATIFIED ERROR-RATE ANALYSIS (with multiple-testing correction)
# =========================================================================

def run_stratified_analysis(df: pd.DataFrame, dimensions: list[str]) -> pd.DataFrame:
    """
    For every category within every stratification dimension, computes
    the confirmed FP rate and a two-proportion z-test against the rest of
    the population. Benjamini-Hochberg FDR correction is applied across
    ALL tests performed (not per-dimension), since testing many
    categories/dimensions inflates false-discovery risk -- without this,
    "found a significant subgroup" becomes nearly guaranteed by chance
    alone given enough categories tested.
    """
    baseline_n = len(df)
    baseline_fp = df["is_false_positive"].sum()

    rows = []
    for dim in dimensions:
        if dim not in df.columns:
            continue
        for category, group in df.groupby(dim):
            n_group = len(group)
            fp_group = group["is_false_positive"].sum()
            n_rest = baseline_n - n_group
            fp_rest = baseline_fp - fp_group
            if n_group < 10 or n_rest < 10:
                continue  # too small to test meaningfully

            p_group = fp_group / n_group
            p_rest = fp_rest / n_rest
            p_pool = (fp_group + fp_rest) / (n_group + n_rest)
            se = np.sqrt(p_pool * (1 - p_pool) * (1 / n_group + 1 / n_rest))
            z = (p_group - p_rest) / se if se > 0 else 0.0
            p_value = 2 * (1 - stats.norm.cdf(abs(z)))

            rows.append({
                "dimension": dim, "category": category, "n": n_group,
                "fp_rate": p_group, "baseline_rest_fp_rate": p_rest,
                "lift": p_group / p_rest if p_rest > 0 else np.inf,
                "z_score": z, "p_value": p_value,
            })

    result = pd.DataFrame(rows)
    if len(result) == 0:
        return result

    # Benjamini-Hochberg FDR correction across all tests performed.
    result = result.sort_values("p_value").reset_index(drop=True)
    m = len(result)
    result["bh_rank"] = np.arange(1, m + 1)
    result["bh_critical_value"] = result["bh_rank"] / m * 0.05
    result["significant_after_correction"] = result["p_value"] <= result["bh_critical_value"]
    result = result.sort_values("lift", ascending=False).reset_index(drop=True)

    n_sig = result["significant_after_correction"].sum()
    logger.info(
        "Stratified analysis: %d category-tests run across %d dimensions, %d significant "
        "after Benjamini-Hochberg correction (q<0.05).", m, len(dimensions), n_sig,
    )
    return result


# =========================================================================
# 6. COVERAGE SUMMARY (the Pareto step)
# =========================================================================

def compute_coverage(
    df: pd.DataFrame, stratified_results: pd.DataFrame, top_n: int = 5,
) -> pd.DataFrame:
    """
    For the top-N significant stratified findings, computes what fraction
    of the TOTAL confirmed FP population each one covers -- this is what
    turns "we found a pattern" into "this pattern explains X% of the
    problem", which is what you need to prioritize remediation honestly
    rather than by whichever finding is most recent or most interesting.
    """
    sig = stratified_results[stratified_results["significant_after_correction"]].head(top_n)
    total_fp = df["is_false_positive"].sum()

    coverage_rows = []
    covered_mask = pd.Series(False, index=df.index)
    for _, r in sig.iterrows():
        mask = df[r["dimension"]] == r["category"]
        fp_in_segment = df.loc[mask, "is_false_positive"].sum()
        coverage_rows.append({
            "dimension": r["dimension"], "category": r["category"],
            "fp_count_in_segment": fp_in_segment,
            "pct_of_total_confirmed_fp": fp_in_segment / total_fp if total_fp else 0,
            "lift": r["lift"],
        })
        covered_mask |= mask

    union_covered = df.loc[covered_mask, "is_false_positive"].sum()
    coverage_df = pd.DataFrame(coverage_rows)
    logger.info(
        "Coverage: top %d significant findings jointly cover %.1f%% of all confirmed FPs "
        "(%d / %d) -- the remainder is still unexplained by these dimensions and warrants "
        "further investigation (case-note mining, SHAP-vector clustering, or manual review).",
        len(sig), 100 * union_covered / total_fp if total_fp else 0, union_covered, total_fp,
    )
    return coverage_df


# =========================================================================
# MAIN
# =========================================================================

def main() -> None:
    parser = argparse.ArgumentParser(description="Systematic root-cause analysis of confirmed false positives.")
    parser.add_argument("--data_csv", type=str, required=True)
    parser.add_argument("--output_dir", type=str, default="./rca_results")
    parser.add_argument("--subgroup_result_size", type=int, default=20)
    parser.add_argument("--subgroup_depth", type=int, default=3)
    parser.add_argument("--tree_max_depth", type=int, default=4)
    parser.add_argument("--assoc_min_support", type=float, default=0.03)
    parser.add_argument("--assoc_min_confidence", type=float, default=0.15,
                         help="Minimum FP rate (not joint support) for a condition to be reported.")
    parser.add_argument("--coverage_top_n", type=int, default=5)
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    raw_df = pd.read_csv(args.data_csv)
    if "is_false_positive" not in raw_df.columns:
        raise ValueError("Input data must contain a confirmed is_false_positive column.")
    df = prepare_analysis_frame(raw_df)
    logger.info("Loaded %d confirmed records, overall FP rate %.2f%%.",
                len(df), 100 * df["is_false_positive"].mean())

    # --- 1. Subgroup discovery ---
    subgroup_df = run_subgroup_discovery(df, args.subgroup_result_size, args.subgroup_depth)
    subgroup_df.to_csv(output_dir / "subgroup_discovery_results.csv", index=False)

    # --- 2. Decision tree surrogate ---
    tree, rules_text = run_decision_tree_surrogate(df, output_dir, args.tree_max_depth)

    # --- 3. Association rules ---
    assoc_df = run_association_rules(df, args.assoc_min_support, args.assoc_min_confidence)
    assoc_df.to_csv(output_dir / "association_rules.csv", index=False)

    # --- 4. Stratified error-rate analysis ---
    strat_df = run_stratified_analysis(df, STRATIFICATION_DIMENSIONS)
    strat_df.to_csv(output_dir / "stratified_analysis.csv", index=False)

    # --- 5. Coverage summary ---
    coverage_df = compute_coverage(df, strat_df, args.coverage_top_n)
    coverage_df.to_csv(output_dir / "coverage_summary.csv", index=False)

    logger.info("All results written to %s", output_dir.resolve())


if __name__ == "__main__":
    main()
