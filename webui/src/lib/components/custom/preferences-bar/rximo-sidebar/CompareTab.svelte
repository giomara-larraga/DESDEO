<script lang="ts">
	import type { ProblemInfo } from '$lib/types';
	import ShapCaseRelationshipNetwork from '$lib/components/visualizations/shap-case-relationship-network/ShapCaseRelationshipNetwork.svelte';
	import { ShapHeatmap } from '$lib/components/visualizations/shap-heatmap';

	type InfluenceRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

  type ObjectiveValue = number | number[] | null | undefined;


	interface Props {
		selectedObjectiveName: string;
		mainHurter: InfluenceRow | undefined;
		mainHelper: InfluenceRow | undefined;
		ownInfluence: InfluenceRow | undefined;
		influenceRows: InfluenceRow[];
		maxAbsInfluence: number;
		problem: ProblemInfo;
		preferenceValues: number[];
		baselineObjectiveValues: Record<string, ObjectiveValue> | null;
		SHAP_values: Record<string, Record<string, number>>;
	}

	let {
		selectedObjectiveName,
		mainHurter,
		mainHelper,
		ownInfluence,
		influenceRows,
		maxAbsInfluence,
		problem,
		preferenceValues,
		baselineObjectiveValues,
		SHAP_values
	}: Props = $props();

	function formatSigned(value: number): string {
		const fixed = Math.abs(value).toFixed(3);
		if (value > 0) return `+${fixed}`;
		if (value < 0) return `-${fixed}`;
		return '0.000';
	}
</script>

<div class="space-y-3">
	<!-- Bridge to the other tabs -->
	<div class="rounded-md border border-blue-100 bg-blue-50 p-3">
		<div class="text-sm font-semibold text-gray-900">
			Explanation details for {selectedObjectiveName}
		</div>

		<p class="mt-1 text-sm text-gray-600">
			This view expands what you saw in <strong>Understand</strong> and
			<strong>Explore</strong>: it shows how objectives support or limit one another.
		</p>
	</div>

	<!-- Visual first -->
	<div class="rounded-md border border-gray-200 bg-white p-3">
		<div class="mb-1 text-sm font-semibold text-gray-900">
			Objective relationship map
		</div>

		<p class="mb-2 text-xs text-gray-500">
			Blue arrows indicate support. Red arrows indicate trade-offs.
		</p>

		<ShapCaseRelationshipNetwork
			objectives={problem.objectives.map((o) => ({
				symbol: o.symbol,
				name: o.name,
				maximize: o.maximize
			}))}
			{preferenceValues}
			achievedValues={baselineObjectiveValues}
			shapValues={SHAP_values}
			threshold={0}
			targetObjectiveSymbol={problem.objectives.find((o) => o.name === selectedObjectiveName)?.symbol || ''}
		/>
	</div>

	<!-- Explain connection to Understand / Explore -->
	<div class="grid grid-cols-2 gap-2 text-xs">
		<div class="rounded-md border border-gray-200 bg-white p-2">
			<div class="font-semibold text-gray-800">Understand</div>
			<div class="mt-1 text-gray-500">
				Uses the strongest relationship to explain the current value.
			</div>
		</div>

		<div class="rounded-md border border-gray-200 bg-white p-2">
			<div class="font-semibold text-gray-800">Explore</div>
			<div class="mt-1 text-gray-500">
				Uses trade-offs to inspect possible compromises.
			</div>
		</div>
	</div>

	<!-- Technical detail collapsed -->
	<details class="rounded-md border border-gray-200 bg-white p-3">
		<summary class="cursor-pointer text-sm font-semibold text-gray-700">
			Show influence strengths
		</summary>

		<p class="mt-2 text-xs text-gray-500">
			These bars show the SHAP contribution of each desired value to the achieved
			value of <strong>{selectedObjectiveName}</strong>.
		</p>

		<div class="mt-3 space-y-1.5">
			{#each influenceRows as row}
				<div class="grid grid-cols-[82px_1fr_52px] items-center gap-2 text-sm">
					<div class="truncate font-medium text-gray-700" title={row.symbol}>
						{row.name}{row.isOwn ? ' (own)' : ''}
					</div>

					<div class="h-2 overflow-hidden rounded bg-gray-100">
						<div
							class={`h-full ${row.isHelpful ? 'bg-[#0C7BDC]' : 'bg-[#DC3220]'}`}
							style={`width: ${(Math.abs(row.helpScore) / maxAbsInfluence) * 100}%`}
						></div>
					</div>

					<div
						class={`text-right font-mono ${
							row.isHelpful ? 'text-[#0C7BDC]' : 'text-[#DC3220]'
						}`}
					>
						{formatSigned(row.helpScore)}
					</div>
				</div>
			{/each}
		</div>
	</details>

	<details class="rounded-md border border-gray-200 bg-white p-3">
		<summary class="cursor-pointer text-sm font-semibold text-gray-700">
			Advanced: show full SHAP matrix
		</summary>

		<p class="mt-2 text-xs text-gray-500">
			The matrix shows all pairwise effects between desired values and achieved
			objective values.
		</p>

		<div class="mt-3">
			<ShapHeatmap shapValues={SHAP_values} {problem} />
		</div>
	</details>
</div>


<style>
  .card,
  .details {
    background: white;
    border: 1px solid #d8e0eb;
    border-radius: 0.65rem;
    padding: 0.8rem;
  }

  .card + .card,
  .details {
    margin-top: 0.8rem;
  }

  h3 {
    margin: 0 0 0.5rem;
    font-size: 0.86rem;
  }

  p {
    margin: 0;
    line-height: 1.4;
  }

  .muted {
    color: #64748b;
  }

  .impact-list {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
  }

  .impact-row {
    display: flex;
    justify-content: space-between;
    gap: 0.75rem;
    font-size: 0.82rem;
  }

  .positive {
    color: #059669;
  }

  .negative {
    color: #dc2626;
  }

  summary {
    cursor: pointer;
    font-weight: 700;
  }

  table {
    width: 100%;
    margin-top: 0.6rem;
    border-collapse: collapse;
    font-size: 0.75rem;
  }

  th,
  td {
    padding: 0.35rem;
    border-bottom: 1px solid #e2e8f0;
    text-align: right;
  }

  th:first-child,
  td:first-child {
    text-align: left;
  }
</style>