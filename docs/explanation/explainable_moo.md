# Explainable interactive multiobjective optimization with SHAP values

## Explainable interactive multiobjective optimization

In interactive multiobjective optimization a decision maker (DM) progressively
expresses their preferences. Here, we assume that preferences have been
expressed as a *reference point* of aspiration levels for each objective. We
also assume that each iteration a scalarization-based solver returns a Pareto
optimal solution that best matches those preferences. The DM may then inspect
the solution, adjust their preferences, and repeat.

Even though this loop is conceptually simple, the mapping from the
preferences to the resulting solution is rarely transparent. Two issues recur
in practice:

- It is hard to tell *why* a particular solution looks the way it does. Why
  did the solver fail to satisfy a specific aspiration level? Which other
  aspiration level was the binding constraint?
- It is hard to know *how* to change the reference point in order to move the
  solution in a desired direction. Should the DM relax some objective?
  Tighten another? Which one?

Explainable interactive methods aim to give the DM principled answers to
these questions. DESDEO provides a SHAP-based family of such tools in
[`desdeo.explanations`](../api/desdeo_explanations.md), including the R-XIMO method.

## SHAP values in multiobjective optimization

SHAP (Shapley Additive exPlanations) values were introduced by Lundberg and
Lee (2017) as a unifying framework for local feature attribution in machine
learning models. DESDEO repurposes the same machinery to explain a
reference-point-based solver as if it were a learned model:

- The "model" is the black-box mapping
  $\mathfrak{B}: \bar{\mathbf{z}} \mapsto \mathbf{z}$ that takes a reference
  point $\bar{\mathbf{z}}$ and returns a Pareto optimal solution
  $\mathbf{z}$.
- The "features" are the components of the reference point.
- The "outputs" are the components of the solution.

Because the black-box has $k$ inputs and $k$ outputs, SHAP produces a
$k \times k$ matrix $\Phi$ where $\Phi_{ij}$ is the contribution of the
$j$-th component of the reference point to the $i$-th component of the
solution. With everything in minimization form, a negative
$\Phi_{ij}$ marks an *improving* effect (the $j$-th aspiration level pushed
the $i$-th objective down) while a positive $\Phi_{ij}$ marks an
*impairing* effect.

The Shapley-based decomposition gives three properties that make the
explanations meaningful:

1. **Local accuracy.** For each output $i$,
   $\phi_0^{(i)} + \sum_{j=1}^{k} \Phi_{ij} = z_i$. The base value plus the
   feature contributions exactly reconstruct the solution component.
2. **Missingness.** A reference point component that has no effect on the
   black-box receives a SHAP value of zero.
3. **Consistency.** If the black-box changes so that a feature contributes
   at least as much in every coalition, that feature's SHAP value cannot
   decrease.

These properties carry over directly to multiobjective optimization, which
makes SHAP an attractive foundation for explaining reference-point methods.

## R-XIMO: reference point based explainable interactive multiobjective optimization

R-XIMO (Misitano, Afsar, Lárraga, & Miettinen, 2022) is a method built on
top of the SHAP matrix. Given a reference point, the resulting solution, and
a *target* objective $i_\text{target}$ that the DM wants to improve further,
R-XIMO answers two questions:

- **Why does the target look the way it does?** It identifies the most
  impairing and most improving components of the reference point with respect
  to the target's row of $\Phi$.
- **What should the DM change?** It picks a *rival* objective whose
  aspiration level is responsible for the target not being achieved (or, in
  the symmetric case, for the target being unexpectedly successful) and
  recommends an actionable adjustment of the form *"try improving the
  component $i_\text{target}$ and impairing the component $j_\text{rival}$".*

The choice between the target's row maximum, second maximum, or the most
improving entry depends on whether every objective improved relative to the
reference point, none did, or only some of them did, and on whether the
target itself appears as the best- or worst-effect column. There are
**nine** explanation cases in total, each producing a tailored textual
explanation alongside the suggestion. The full case analysis is implemented
in [`desdeo.explanations.find_rival`][desdeo.explanations.find_rival] and
the convenience wrapper
[`desdeo.explanations.run_rximo`][desdeo.explanations.run_rximo] glues
together SHAP value computation and rival selection.

## Choosing the SHAP baseline

The base value $\phi_0$ in SHAP is the expected output of the black-box
under the *background* (or *missing*) distribution. Conceptually, it is the
"default" solution the DM would receive if they expressed no specific
preference. Because the SHAP values describe how the actual reference point
deviates from this default, the choice of baseline shapes the narrative of
every explanation.

DESDEO's [`ShapExplainer`][desdeo.explanations.ShapExplainer] supports three
baseline strategies:

- **`setup(background_data)` — global baseline.** Pass a sample of points
  (typically drawn from the Pareto front). The base value averages the
  black-box over this sample. Use this when you want explanations relative
  to the overall behavior of the method.
- **`setup_with_baseline(baseline_point)` — precise local baseline.** Pass
  a single point. With $k \le 10$ features the SHAP library picks the
  Exact algorithm automatically, so the SHAP values themselves remain exact;
  the base value collapses to the prediction at the chosen point. A natural
  choice for R-XIMO is the current solution: explanations then describe how
  the new reference point pushes the solution away from where the DM is now.
- **`setup_with_shifted_background(background_data, target_mean)` —
  centered baseline.** Shift every row of the background dataset by a
  constant so that its mean lands exactly on a target. Cheaper than solving
  the MIQP behind
  [`generate_biased_mean_data`][desdeo.explanations.generate_biased_mean_data]
  while still giving a baseline that is "centered" where the DM expects.

The MIQP-based [`generate_biased_mean_data`][desdeo.explanations.generate_biased_mean_data]
remains available when a rigorous subset-of-real-points baseline is
required. It is slower but produces a background whose rows are all genuine
samples from the supplied dataset.

## The `ShapExplainer` in DESDEO

[`ShapExplainer`][desdeo.explanations.ShapExplainer] wraps `shap.Explainer`
together with a nearest-neighbor lookup over a tabular dataset of
reference-point/solution pairs. It exposes:

- `setup`, `setup_with_baseline`, `setup_with_shifted_background`: three
  ways to fix the baseline as described above.
- `evaluate`: the function SHAP queries when computing values. By default
  it does a $k$-d-tree lookup on the training data. Replacing this attribute
  with a "true" black-box (for example, a closed-form scalarization solver
  or a nearest-neighbor lookup directly on the discrete Pareto front) lets
  SHAP work against the actual mapping rather than its tabular
  approximation.
- `explain_input`: return a `shap.Explanation` for a given reference point.

The R-XIMO entry points on top of these are
[`why_objective_i`][desdeo.explanations.why_objective_i],
[`find_rival`][desdeo.explanations.find_rival], and
[`run_rximo`][desdeo.explanations.run_rximo]. For a worked example on the
river pollution problem, see the how-to guide
[*How to use R-XIMO for explainable interactive multiobjective
optimization*](../howtoguides/rximo.ipynb).

## References

- Lundberg, S. M., & Lee, S.-I. (2017). *A Unified Approach to Interpreting
  Model Predictions.* In *Advances in Neural Information Processing Systems
  30* (pp. 4768–4777).
- Misitano, G., Afsar, B., Lárraga, G., & Miettinen, K. (2022). *Towards
  explainable interactive multiobjective optimization: R-XIMO.* Autonomous
  Agents and Multi-Agent Systems, 36(43).
