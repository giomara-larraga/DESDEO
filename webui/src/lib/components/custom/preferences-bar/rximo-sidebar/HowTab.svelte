<script lang="ts">
	import Button from '$lib/components/ui/button/button.svelte';
	import WhatIfCaseNetwork from '$lib/components/visualizations/what-if-case-network/WhatIfCaseNetwork.svelte';
	import { WhatIfDeltaChart } from '$lib/components/visualizations/what-if-delta';
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

	const selectedObjectiveDelta = $derived.by(() => {
		if (!selectedScenario) return null;

		return (
			selectedScenario.deltas.find((delta) => delta.symbol === selectedObjectiveSymbol) ?? null
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

	const selectedScenario = $derived.by(() => {
		if (!selectedImpairedSymbol) return null;

		return (
			hypotheticalScenarios.find(
				(scenario) => scenario.impairedSymbol === selectedImpairedSymbol
			) ?? null
		);
	});
</script>

<div class="space-y-3">
	<div class="space-y-3">
		<p class="text-xs leading-relaxed text-gray-700">
			Improving <strong>{selectedObjectiveName}</strong> requires accepting a worse value in at
			least one other objective. Select a desired value to relax and inspect what is gained in
			<strong>{selectedObjectiveName}</strong>
			and what is given up elsewhere.
		</p>

		{#if hypotheticalScenarios.length === 0}
			<div class="rounded border bg-gray-50 p-3 text-sm text-gray-500">
				No perturbed cases available yet.
			</div>
		{:else}
			<div
				class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500"
				aria-label="What-if result legend"
			>
				<span class="inline-flex items-center gap-1.5">
					<span class="h-0.5 w-4 rounded-full bg-[#0C7BDC]" aria-hidden="true"></span>
					Improved
				</span>

				<span class="inline-flex items-center gap-1.5">
					<span class="w-4 border-t-2 border-dashed border-[#DC3220]" aria-hidden="true"></span>
					Worsened
				</span>

				<span class="inline-flex items-center gap-1.5">
					<span class="w-4 border-t border-dotted border-gray-400" aria-hidden="true"></span>
					No change
				</span>

				<span class="inline-flex items-center gap-1.5">
					<span class="inline-flex items-center gap-0.5" aria-hidden="true">
						<span class="h-px w-3 rounded-full bg-gray-400"></span>
						<span class="h-1 w-3 rounded-full bg-gray-400"></span>
					</span>
					Thicker = larger change
				</span>

				<span class="inline-flex items-center gap-1.5">
					<span class="text-md font-semibold text-blue-700" aria-hidden="true"> ◆ </span>
					Selected objective
				</span>
			</div>
			<WhatIfCaseNetwork
				objectives={problem.objectives.map((o) => ({
					symbol: o.symbol,
					name: o.name,
					maximize: o.maximize
				}))}
				cases={hypotheticalScenarios.map((caseItem) => ({
					impairedSymbol: caseItem.impairedSymbol,
					impairmentMagnitude: caseItem.impairmentMagnitude,
					impairedTargetValue: caseItem.impairedTargetValue,
					deltas: caseItem.deltas.map((delta) => ({
						symbol: delta.symbol,
						delta: delta.delta,
						percentDelta: delta.percentDelta
					}))
				}))}
				mode={scenarioDiffDisplayMode}
				onSelectNode={(symbol) => (selectedImpairedSymbol = symbol)}
				disabledNodeSymbol={selectedObjectiveSymbol}
			/>

			{#if !selectedScenario}
				<div class="rounded-md bg-gray-50 p-3 text-sm text-gray-500">
					Select a desired value above to inspect its what-if result.
				</div>
			{:else}
				<!-- selected scenario -->
				<div class="rounded-md border border-gray-200 bg-white p-3">
					<div class="text-sm font-semibold text-gray-900">
						Relax {selectedScenario.impairedName}
					</div>

					<div class="mt-1 text-xs text-gray-600">
						New desired value:
						<strong>{selectedScenario.impairedTargetValue.toFixed(3)}</strong>
						<span class="text-gray-400">
							(relaxed by {selectedScenario.impairmentMagnitude.toFixed(3)})
						</span>
					</div>

					<div class="mt-3">
						<div class="mb-2 text-xs font-semibold text-gray-700">
							Resulting achieved-value changes
						</div>

						<WhatIfDeltaChart
							deltas={selectedScenario.deltas}
							{selectedObjectiveSymbol}
							mode={scenarioDiffDisplayMode}
						/>
					</div>

					<div class="mt-3">
						<Button
							type="button"
							variant="outline"
							size="sm"
							onclick={() =>
								onApplyScenarioPreferences?.(selectedScenario.scenarioPreferenceValues)}
						>
							Use these desired values
						</Button>
					</div>
				</div>
			{/if}
		{/if}
	</div>
</div>
