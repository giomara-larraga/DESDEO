def print_final_validation_statistics(tradeoff_df):
    """Print final validation statistics for the manuscript."""

    df = tradeoff_df.copy()

    # Convert relative errors to percentages.
    df["implementation_vs_independent_pct"] = (
        100.0 * df["xnimbus_vs_independent_rel_diff"]
    )
    df["implementation_vs_fd_pct"] = (
        100.0 * df["xnimbus_vs_fd_rel_error"]
    )

    print("\n" + "=" * 72)
    print("FINAL VALIDATION STATISTICS")
    print("=" * 72)

    print(f"Number of pairwise comparisons: {len(df)}")
    print(f"Number of iterations represented: {df['iteration'].nunique()}")

    print("\nXNIMBUS implementation vs independently inferred scaling")
    print(
        f"  Median relative difference: "
        f"{df['implementation_vs_independent_pct'].median():.10g}%"
    )
    print(
        f"  Mean relative difference:   "
        f"{df['implementation_vs_independent_pct'].mean():.10g}%"
    )
    print(
        f"  Maximum relative difference:"
        f" {df['implementation_vs_independent_pct'].max():.10g}%"
    )

    print("\nXNIMBUS implementation vs finite differences")
    print(
        f"  Median relative error: "
        f"{df['implementation_vs_fd_pct'].median():.10g}%"
    )
    print(
        f"  Mean relative error:   "
        f"{df['implementation_vs_fd_pct'].mean():.10g}%"
    )
    print(
        f"  Maximum relative error:"
        f" {df['implementation_vs_fd_pct'].max():.10g}%"
    )

    print("\nBy scalarization:")
    grouped = (
        df.groupby("scalarization")["implementation_vs_fd_pct"]
        .agg(["count", "median", "mean", "max"])
    )
    print(grouped.to_string())

    # Identify the worst finite-difference comparison.
    worst_idx = df["implementation_vs_fd_pct"].idxmax()
    worst = df.loc[worst_idx]

    print("\nWorst finite-difference comparison:")
    print(f"  Iteration:       {int(worst['iteration'])}")
    print(f"  Solution index:  {int(worst['solution_index'])}")
    print(f"  Scalarization:   {worst['scalarization']}")
    print(
        f"  Trade-off:       "
        f"{worst['from_objective']} -> {worst['to_objective']}"
    )
    print(
        f"  XNIMBUS:         "
        f"{worst['xnimbus_implementation_tradeoff']:.16g}"
    )
    print(
        f"  Finite difference: "
        f"{worst['finite_difference_tradeoff']:.16g}"
    )
    print(
        f"  Relative error:  "
        f"{worst['implementation_vs_fd_pct']:.10g}%"
    )

    # Identify worst implementation-vs-independent discrepancy.
    worst_impl_idx = df["implementation_vs_independent_pct"].idxmax()
    worst_impl = df.loc[worst_impl_idx]

    print("\nWorst implementation vs independent-scaling comparison:")
    print(f"  Iteration:       {int(worst_impl['iteration'])}")
    print(f"  Solution index:  {int(worst_impl['solution_index'])}")
    print(f"  Scalarization:   {worst_impl['scalarization']}")
    print(
        f"  Trade-off:       "
        f"{worst_impl['from_objective']} -> "
        f"{worst_impl['to_objective']}"
    )
    print(
        f"  Relative difference: "
        f"{worst_impl['implementation_vs_independent_pct']:.10g}%"
    )

    print("=" * 72)

if __name__ == "__main__":
    import pandas as pd

    tradeoff_df = pd.read_csv("tradeoff_validation.csv")
    print_final_validation_statistics(tradeoff_df)