<script lang="ts">
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import { formatNumber } from '$lib/helpers';
	import type { ProblemInfo, Solution } from '$lib/types';
	import DesiredAchievedComparison from '$lib/components/visualizations/desired-achieved-comparison/DesiredAchievedComparison.svelte';
	import ContributionChart from '$lib/components/visualizations/barchart/ContributionChart.svelte';

	type ContributionRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

	interface Props {
		selectedObjectiveName: string;
		iterationDesiredValues: number[];
		selectedSolution: Solution;
		selectedObjectiveIndex: number;
		achievedValueNumber: number;
		selectedObjectiveDigits: number;
		contributionRows: ContributionRow[];

		strongestLimitingContribution: ContributionRow | undefined;
		strongestSupportiveContribution: ContributionRow | undefined;

		selectedRow: Record<string, number>;
		selectedObjectiveSymbol: string;
		problem: ProblemInfo;
		selectedSHAPBaseline: number | undefined;
		selectedSolutionValue: number | undefined;

		rximoSuggestion: string | null;
		suggestedDesiredValueName: string | null;
		onHowClick: () => void;
	}

	let {
		selectedObjectiveName,
		iterationDesiredValues,
		selectedSolution,
		selectedObjectiveIndex,
		achievedValueNumber,
		selectedObjectiveDigits,
		contributionRows,
		strongestLimitingContribution,
		strongestSupportiveContribution,
		selectedRow,
		selectedObjectiveSymbol,
		problem,
		selectedSHAPBaseline,
		selectedSolutionValue,
		rximoSuggestion,
		suggestedDesiredValueName,
		onHowClick
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

	let contributionDescription = $derived.by(() => {
		if (directionalDifference > 0.01) {
			return `${selectedObjectiveName} is better than desired overall. The chart shows which desired values had supportive or limiting contributions to this achieved value.`;
		}

		if (directionalDifference < -0.01) {
			return `The chart shows which desired values had supportive or limiting contributions to the achieved value of ${selectedObjectiveName}.`;
		}

		return `${selectedObjectiveName} meets its desired value. The chart shows the supportive and limiting contributions behind this achieved value.`;
	});

	function computeDifferenceWithTolerance(
		desired: number,
		achieved: number,
		tolerance: number
	): string {
		if (!Number.isFinite(desired) || !Number.isFinite(achieved)) return 'unchanged';
		const diff = achieved - desired;
		if (Math.abs(diff) <= tolerance) return 'has met the desired value';
		return directionSelectedObjective() === 'max'
			? achieved > desired
				? 'is better than the desired value'
				: 'is worse than the desired value'
			: achieved < desired
				? 'is better than the desired value'
				: 'is worse than the desired value';
	}

	let desiredValue = $derived(Number(iterationDesiredValues[selectedObjectiveIndex]));

	let selectedObjective = $derived(problem.objectives[selectedObjectiveIndex]);

	// Positive = better than desired, negative = worse than desired,
	// regardless of whether the objective is minimized or maximized.
	let directionalDifference = $derived.by(() => {
		const difference = achievedValueNumber - desiredValue;

		return selectedObjective?.maximize ? difference : -difference;
	});

	let objectiveRange = $derived.by(() => {
		const ideal = Number(selectedObjective?.ideal);
		const nadir = Number(selectedObjective?.nadir);

		if (!Number.isFinite(ideal) || !Number.isFinite(nadir)) return null;

		return Math.abs(ideal - nadir);
	});

	// Width of the graphical difference indicator.
	let differenceWidth = $derived.by(() => {
		if (!objectiveRange || objectiveRange === 0) return 0;

		return Math.min(50, (Math.abs(directionalDifference) / objectiveRange) * 50);
	});

	let differenceStatus = $derived.by(() => {
		if (Math.abs(directionalDifference) <= 0.01) {
			return 'Meets desired value';
		}

		return directionalDifference > 0 ? 'Better than desired' : 'Worse than desired';
	});
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
			Current status of {selectedObjectiveName}
		</div>

		<DesiredAchievedComparison
			objectiveName={selectedObjectiveName}
			desiredValue={iterationDesiredValues[selectedObjectiveIndex]}
			achievedValue={achievedValueNumber}
			maximize={problem.objectives[selectedObjectiveIndex].maximize}
			ideal={problem.objectives[selectedObjectiveIndex].ideal}
			nadir={problem.objectives[selectedObjectiveIndex].nadir}
			digits={selectedObjectiveDigits}
		/>

		<div class="mt-3 border-t border-gray-200 pt-3">
			<div class="mb-2 flex items-center gap-1 text-sm font-semibold">
				<span>What contributed to this achieved value?</span>

				<Tooltip.Root>
					<Tooltip.Trigger class="text-gray-400 hover:text-gray-600">
						<InfoIcon class="h-3.5 w-3.5" />
					</Tooltip.Trigger>

					<Tooltip.Content sideOffset={6} class="max-w-72 text-sm">
						Contributions describe the current solution and do not predict what will happen if a
						desired value is changed.
					</Tooltip.Content>
				</Tooltip.Root>
			</div>
			<p class="mb-2 text-xs leading-relaxed text-gray-500">
				{contributionDescription}
			</p>
			<ContributionChart
				contributions={contributionRows}
				{suggestedDesiredValueName}
				digits={selectedObjectiveDigits}
				showOwnContribution={true}
			/>
		</div>
	</div>
	<div class="rounded-md border border-amber-200 bg-amber-50 p-3">
		<div class="mb-1 flex items-center gap-1 text-sm font-semibold">
			<span>R-XIMO suggestion</span>

			<Tooltip.Root>
				<Tooltip.Trigger class="text-gray-400 hover:text-gray-600">
					<InfoIcon class="h-3.5 w-3.5" />
				</Tooltip.Trigger>

				<Tooltip.Content sideOffset={6} class="max-w-72 text-sm">
					This suggestion is derived from the contribution structure of the current solution. It
					identifies a desired value to consider adjusting, but does not predict the resulting
					solution. Open How to inspect the corresponding what-if changes.
				</Tooltip.Content>
			</Tooltip.Root>
		</div>

		{#if suggestedDesiredValueName}
			<p class="text-sm text-gray-700">
				Consider relaxing the desired value for
				<strong>{suggestedDesiredValueName}</strong>
				when seeking improvement in
				<strong>{selectedObjectiveName}</strong>.
			</p>
		{/if}

		<button
			type="button"
			class="mt-2 text-sm font-medium text-blue-700 hover:underline"
			onclick={onHowClick}
		>
			Inspect in How →
		</button>
	</div>
</div>
