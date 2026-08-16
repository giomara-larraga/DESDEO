<script lang="ts">
  import type { ADMLog } from "$lib/adm/types";
  import { getIteration } from "$lib/adm/adapters";

  export let log: ADMLog;
  export let selectedIteration: number;

  $: iteration = getIteration(log, selectedIteration);
  $: phiValues = log.methods.map((method) => ({
    method,
    phi: iteration.hypervolume[method].phi_iteration
  }));
  $: best = [...phiValues].sort((a, b) => b.phi - a.phi)[0];
</script>

<section class="narrative">
  <h3>Narrative Explanation</h3>

  <p>
    At iteration {iteration.iteration}, the ADM is in the
    <strong>{iteration.phase}</strong> phase.
  </p>

  <p>
    The selected reference vector is
    <strong>{iteration.preference_information.selected_reference_vector}</strong>,
    using the rule
    <strong>{iteration.preference_information.selection_rule}</strong>.
  </p>

  <p>
    {iteration.preference_information.description}
  </p>

  <p>
    Based on the iteration-level Φ value,
    <strong>{best.method}</strong> currently has the strongest response
    with Φ = <strong>{best.phi.toFixed(4)}</strong>.
  </p>
</section>

<style>
  .narrative {
    background: #f8fafc;
    border-radius: 1rem;
    padding: 1rem;
    line-height: 1.65;
  }

  h3 {
    margin-top: 0;
  }

  p {
    color: #334155;
  }
</style>