<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import WhatIfCaseNetwork from '$lib/components/visualizations/what-if-case-network/WhatIfCaseNetwork.svelte';
	import type { ProblemInfo } from '$lib/types';

	type InfluenceRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

	type ScenarioDelta = {
		symbol: string;
		name: string;
		delta: number;
		percentDelta: number | null;
		isImprovement: boolean;
	};

	type HypotheticalScenario = {
		key: string;
		impairedSymbol: string;
		impairedName: string;
		impairmentMagnitude: number;
		impairedTargetValue: number;
		scenarioPreferenceValues: number[];
		deltas: ScenarioDelta[];
	};

	interface Props {
		selectedObjectiveName: string;
		selectedObjectiveSymbol: string;
		mainHurter: InfluenceRow | undefined;
		ownInfluence: InfluenceRow | undefined;
		hypotheticalScenarios: HypotheticalScenario[];
		problem: ProblemInfo;
		maxAbsScenarioDelta: number;
		maxAbsScenarioPercent: number;
		onApplyScenarioPreferences?: (values: number[]) => void;
	}

	let {
		selectedObjectiveName,
		selectedObjectiveSymbol,
		mainHurter,
		ownInfluence,
		hypotheticalScenarios,
		problem,
		maxAbsScenarioDelta,
		maxAbsScenarioPercent,
		onApplyScenarioPreferences
	}: Props = $props();

	type ScenarioDiffDisplayMode = 'value' | 'percent';
	let scenarioDiffDisplayMode = $state<ScenarioDiffDisplayMode>('value');
  let selectedImpairedSymbol = $state<string | null>(null);

  const filteredScenarios = $derived.by(() => {
    if (!selectedImpairedSymbol || selectedImpairedSymbol === null) return hypotheticalScenarios;

    return hypotheticalScenarios.filter(
      (scenario) => scenario.impairedSymbol === selectedImpairedSymbol
    );
  });

	function formatSigned(value: number): string {
		const fixed = Math.abs(value).toFixed(3);
		if (value > 0) return `+${fixed}`;
		if (value < 0) return `-${fixed}`;
		return '0.000';
	}

	function formatSignedPercent(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return 'n/a';
		const fixed = Math.abs(value).toFixed(2);
		if (value > 0) return `+${fixed}%`;
		if (value < 0) return `-${fixed}%`;
		return '0.00%';
	}


</script>

<div class="space-y-3">

		<div class="space-y-3">
      <div class="rounded-md border border-blue-100 bg-blue-50 p-3">
          <div class="font-semibold text-sm text-gray-900">
              Explore possible compromises
          </div>

          <p class="mt-1 text-gray-600 text-sm">
            To improve <strong>{selectedObjectiveName}</strong>, you may need to relax the
            desired value of another objective. Select an objective in the graph to inspect
            what happens when it is relaxed.
          </p>
      </div>
<!-- 			<div class="flex items-center gap-1">
				<button
					type="button"
					class={`rounded px-2 py-0.5 text-sm ${scenarioDiffDisplayMode === 'value' ? 'bg-gray-200 font-medium text-gray-800' : 'bg-gray-100 text-gray-600'}`}
					onclick={() => (scenarioDiffDisplayMode = 'value')}
				>
					Value
				</button>

				<button
					type="button"
					class={`rounded px-2 py-0.5 text-sm ${scenarioDiffDisplayMode === 'percent' ? 'bg-gray-200 font-medium text-gray-800' : 'bg-gray-100 text-gray-600'}`}
					onclick={() => (scenarioDiffDisplayMode = 'percent')}
				>
					Percent
				</button>
			</div> -->

			{#if hypotheticalScenarios.length === 0}
				<div class="rounded border bg-gray-50 p-3 text-sm text-gray-500">
					No perturbed cases available yet.
				</div>
			{:else}
				<WhatIfCaseNetwork
					objectives={problem.objectives.map((o) => ({ symbol: o.symbol, name: o.name }))}
					cases={hypotheticalScenarios.map((caseItem) => ({
						impairedSymbol: caseItem.impairedSymbol,
						deltas: caseItem.deltas.map((delta) => ({
							symbol: delta.symbol,
							delta: delta.delta,
							percentDelta: delta.percentDelta
						}))
					}))}
					mode={scenarioDiffDisplayMode}
          onSelectNode={(symbol) => (selectedImpairedSymbol = symbol)
          }
	        disabledNodeSymbol={selectedObjectiveSymbol}
				/>

				{#each filteredScenarios as scenario}
					<div class="rounded-md border border-gray-200 bg-white p-3">
						<div class="mb-2 text-sm text-gray-700">
							What if <strong>{scenario.impairedName}</strong> is impaired by
							<strong>{scenario.impairmentMagnitude.toFixed(3)}</strong>
							(to target value
							<strong>{scenario.impairedTargetValue.toFixed(3)}</strong>),
							the
							observed effects are:
						</div>

						<div class="mb-2">
							<Button
								type="button"
								variant="outline"
								size="sm"
								onclick={() => onApplyScenarioPreferences?.(scenario.scenarioPreferenceValues)}
							>
								Set preferences like this
							</Button>
						</div>

						<div class="space-y-1.5">
							{#each scenario.deltas as delta}
								<div class="grid grid-cols-[64px_1fr_62px] items-center gap-2 text-sm">
									<div class="truncate font-medium text-gray-700" title={delta.symbol}>
										{delta.name}
									</div>

									<div class="h-2 overflow-hidden rounded bg-gray-100">
										<div
											class={`h-full ${delta.isImprovement ? 'bg-[#0C7BDC]' : 'bg-[#DC3220]'}`}
											style={`width: ${scenarioDiffDisplayMode === 'percent'
												? (Math.abs(delta.percentDelta ?? 0) / maxAbsScenarioPercent) * 100
												: (Math.abs(delta.delta) / maxAbsScenarioDelta) * 100}%`}
										></div>
									</div>

									<div
										class={`text-right font-mono ${delta.isImprovement ? 'text-[#0C7BDC]' : 'text-[#DC3220]'}`}
									>
										{scenarioDiffDisplayMode === 'percent'
											? formatSignedPercent(delta.percentDelta)
											: formatSigned(delta.delta)}
									</div>
								</div>
							{/each}
						</div>
					</div>
				{/each}
			{/if}
		</div>

</div>




