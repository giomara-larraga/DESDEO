<script lang="ts">
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { formatNumber } from '$lib/helpers';
	import type { ProblemInfo, Solution } from '$lib/types';

	type InfluenceRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

	interface Props {
		selectedObjectiveName: string;
		preferenceValues: number[];
		selectedSolution: Solution;
		selectedObjectiveIndex: number;
		achievedValueNumber: number;
		selectedObjectiveDigits: number;
		mainTradeoff: InfluenceRow | undefined;
		mainSynergy: InfluenceRow | undefined;
		selectedRow: Record<string, number>;
		selectedObjectiveSymbol: string;
		problem: ProblemInfo;
		selectedSHAPBaseline: number | undefined;
		selectedSolutionValue: number | undefined;
		explanationText: string | null;
		onExploreClick: () => void;
	}

	let {
		selectedObjectiveName,
		preferenceValues,
		selectedSolution,
		selectedObjectiveIndex,
		achievedValueNumber,
		selectedObjectiveDigits,
		mainTradeoff,
		mainSynergy,
		selectedRow,
		selectedObjectiveSymbol,
		problem,
		selectedSHAPBaseline,
		selectedSolutionValue,
		onExploreClick
	}: Props = $props();

	function formatValue(value: unknown): string {
		const num = Array.isArray(value) ? Number(value[0]) : Number(value);
		if (!Number.isFinite(num)) return '—';
		return num.toFixed(2);
	}
	let directionSelectedObjective = $derived(() => {
		const objective = problem.objectives[selectedObjectiveIndex];
		return objective.maximize ? 'max' : 'min';
	});


	function computeDifferenceWithTolerance(desired: number, achieved: number, tolerance: number): string {
		if (!Number.isFinite(desired) || !Number.isFinite(achieved)) return 'unchanged';
		const diff = achieved - desired;
		if (Math.abs(diff) <= tolerance) return 'has met the desired value';
		return directionSelectedObjective() === 'max' ? (achieved > desired ? 'is better than the desired value' : 'is worse than the desired value') : (achieved < desired ? 'is better than the desired value' : 'is worse than the desired value');
	}
</script>

<div class="space-y-3">

	

	<!-- Solution overview -->
<!-- 	<div class="rounded-md border border-sky-100 bg-sky-50 p-3">
		<div class="mb-2 text-sm font-semibold text-gray-900">
			Current solution overview
		</div>

		<div class="flex items-center gap-4 text-sm">
			<div class="flex items-center gap-1 text-green-700">
				<span>✓</span>
				<span>
					<strong>{objectiveSummary.met}</strong>
					met
				</span>
			</div>

			<div class="flex items-center gap-1 text-amber-700">
				<span>⚠</span>
				<span>
					<strong>{objectiveSummary.unmet}</strong>
					unmet
				</span>
			</div>
		</div>

		<div class="mt-2 text-sm font-medium text-gray-800">
			{objectiveSummary.headline}
		</div>

		<p class="mt-1 text-sm leading-relaxed text-gray-600">
			{objectiveSummary.description}
		</p>
	</div> -->

	<!-- Objective status -->
	<div class="rounded-md border border-gray-200 bg-white p-3">
		<div class="mb-2 text-sm font-semibold text-gray-900">
			{selectedObjectiveName}
		</div>

		<div class="grid grid-cols-2 gap-2 text-sm">
			<div class="rounded bg-gray-50 p-2">
				<div class="text-xs text-gray-500">Desired value</div>
				<div class="font-semibold text-gray-800">
					{formatValue(preferenceValues[selectedObjectiveIndex])}
				</div>
			</div>

			<div class="rounded bg-gray-50 p-2">
				<div class="text-xs text-gray-500">Achieved value</div>
				<div class="font-semibold text-gray-800">
					{formatNumber(achievedValueNumber, selectedObjectiveDigits)}
				</div>
			</div>
		</div>
		<div class="mt-2 text-sm text-gray-600">
			The achieved value {computeDifferenceWithTolerance(preferenceValues[selectedObjectiveIndex], achievedValueNumber, 0.01)}.
		</div>
	</div>

	<!-- Main visual relationship -->
	<div class="rounded-md border border-blue-100 bg-blue-50 p-3">
		{#if mainTradeoff}
			<div class="mb-2 text-sm font-semibold text-gray-900">
				Main trade-off
			</div>

			<div class="rounded-md bg-white p-3">
				<div class="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
					<div class="text-center">
						<div class="text-xs font-medium text-amber-600">Desired value of</div>
						<div class="font-semibold">{mainTradeoff.name}</div>
					</div>

					<div class="text-sm font-medium text-[#DC3220]">
						limits →
					</div>

					<div class="text-center">
						<div class="text-xs font-medium text-blue-600">Achieved value of</div>
						<div class="font-semibold">{selectedObjectiveName}</div>
					</div>
				</div>
			</div>

			<p class="mt-2 text-sm text-gray-600">
				Relaxing the desired value for <strong>{mainTradeoff.name}</strong>
				could create room for improving <strong>{selectedObjectiveName}</strong>.
			</p>

		{:else if mainSynergy}
			<div class="mb-2 flex items-center gap-1 text-sm font-semibold text-gray-900">
				<span>Main synergy</span>

				<Tooltip.Root>
					<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
						<InfoIcon class="h-3.5 w-3.5" />
					</Tooltip.Trigger>

					<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
						A synergy means that the desired value for another objective appears to
						support the achieved value of <strong>{selectedObjectiveName}</strong>.
					</Tooltip.Content>
				</Tooltip.Root>
			</div>

			<div class="rounded-md bg-white p-3">
				<div class="grid grid-cols-[1fr_auto_1fr] items-center gap-3">
					<div class="text-center">
						<div class="text-xs font-medium text-amber-600">Desired value of</div>
						<div class="font-semibold">{mainSynergy.name}</div>
					</div>

					<div class="text-sm font-medium text-[#0C7BDC]">
						supports →
					</div>

					<div class="text-center">
						<div class="text-xs font-medium text-blue-600">Achieved value of</div>
						<div class="font-semibold">{selectedObjectiveName}</div>
					</div>
				</div>
			</div>

			<div class="mt-2 flex items-center justify-between gap-2 rounded-md bg-white/70 px-2 py-1 text-sm text-gray-600">
				<span>No major trade-offs detected.</span>

				<Tooltip.Root>
					<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
						<InfoIcon class="h-3.5 w-3.5" />
					</Tooltip.Trigger>

					<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
						No desired value for another objective appears to limit
						<strong>{selectedObjectiveName}</strong>. Further improvements may depend
						mainly on adjusting the desired value for
						<strong>{selectedObjectiveName}</strong> itself.
					</Tooltip.Content>
				</Tooltip.Root>
			</div>

<!-- 			<Tooltip.Root>
				<Tooltip.Trigger asChild>
					<Button
						type="button"
						size="sm"
						variant="outline"
						class="mt-3 w-full justify-center gap-2 border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
						onclick={onExploreClick}
					>
						Explore possible changes
						<span aria-hidden="true">→</span>
					</Button>
				</Tooltip.Trigger>

				<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
					Open the Explore tab to inspect what may happen if some desired values are adjusted.
				</Tooltip.Content>
			</Tooltip.Root> -->

		{:else}
			<div class="mb-2 flex items-center gap-1 text-sm font-semibold text-gray-900">
				<span>No major interactions detected</span>

				<Tooltip.Root>
					<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
						<InfoIcon class="h-3.5 w-3.5" />
					</Tooltip.Trigger>

					<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
						No desired value for another objective appears to strongly affect
						the achieved value of <strong>{selectedObjectiveName}</strong>.
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
<!-- 
			<Tooltip.Root>
				<Tooltip.Trigger asChild>
					<Button
						type="button"
						size="sm"
						variant="outline"
						class="mt-2 w-full justify-center gap-2 border-blue-200 bg-blue-50 text-blue-700 hover:bg-blue-100"
						onclick={onExploreClick}
					>
						Explore possible changes
						<span aria-hidden="true">→</span>
					</Button>
				</Tooltip.Trigger>

				<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
					Open the Explore tab to inspect what may happen if some desired values are adjusted.
				</Tooltip.Content>
			</Tooltip.Root> -->
		{/if}
	</div>


</div>