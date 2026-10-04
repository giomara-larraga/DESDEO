<script lang="ts">
	import type { ProblemInfo } from '$lib/types';
	import {
		findShapColumn,
		findShapRow,
		displayAspirationName,
		isOwnAspiration,
		normalizeObjectiveSymbol
	} from './helpers';

	import ShapCaseRelationshipNetwork from '$lib/components/visualizations/shap-case-relationship-network/ShapCaseRelationshipNetwork.svelte';
	import { ShapHeatmap } from '$lib/components/visualizations/shap-heatmap';
	import ContributionChart from '$lib/components/visualizations/barchart/ContributionChart.svelte';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import InfoIcon from '@lucide/svelte/icons/info';

	import DesiredValueEffects from '$lib/components/visualizations/desired-value-effects/DesiredValueEffects.svelte';
	import { onMount } from 'svelte';

	type ObjectiveValue = number | number[] | null | undefined;
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
		selectedObjectiveSymbol: string;
		problem: ProblemInfo;
		iterationDesiredValues: number[];
		baselineObjectiveValues: Record<string, ObjectiveValue> | null;
		SHAP_values: Record<string, Record<string, number>>;
		explanationText: string | null;
		selectedSHAPBaseline: number | undefined;
		selectedSolutionValue: number | undefined;
	}

	let {
		selectedObjectiveName,
		selectedObjectiveSymbol,
		problem,
		iterationDesiredValues,
		baselineObjectiveValues,
		SHAP_values,
		explanationText,
		selectedSHAPBaseline,
		selectedSolutionValue
	}: Props = $props();

	type NetworkSelection = {
		side: 'desired' | 'achieved';
		symbol: string;
		name: string;
	};

	let networkSelection = $state<NetworkSelection | null>(null);

	let selectedEvidenceView = $state<'overview' | 'matrix'>('overview');

	const objectives = $derived(
		problem.objectives.map((objective) => ({
			symbol: objective.symbol,
			name: objective.name,
			maximize: objective.maximize
		}))
	);

	const selectedDesiredEffects = $derived(
		networkSelection?.side === 'desired' && networkSelection?.symbol
			? findShapColumn(SHAP_values, networkSelection.symbol)
			: null
	);

	const inspectedAchievedSymbol = $derived(
		networkSelection?.side === 'achieved' ? networkSelection.symbol : selectedObjectiveSymbol
	);

	const inspectedAchievedObjective = $derived(
		problem.objectives.find(
			(objective) =>
				normalizeObjectiveSymbol(objective.symbol) ===
				normalizeObjectiveSymbol(inspectedAchievedSymbol)
		)
	);

	const selectedAchievedEffects = $derived(findShapRow(SHAP_values, inspectedAchievedSymbol));

	function getContributionValue(row: Record<string, number> | null, symbol: string): number {
		if (!row) return 0;

		const normalizedSymbol = normalizeObjectiveSymbol(symbol);

		const entry = Object.entries(row).find(
			([key]) => normalizeObjectiveSymbol(key) === normalizedSymbol
		);

		const value = Number(entry?.[1]);

		return Number.isFinite(value) ? value : 0;
	}
	const selectedContributionRows = $derived.by<ContributionRow[]>(() => {
		if (!selectedAchievedEffects || !inspectedAchievedObjective) {
			return [];
		}

		return problem.objectives
			.map((objective) => {
				const rawValue = getContributionValue(selectedAchievedEffects, objective.symbol);

				// Positive helpScore = supportive contribution.
				// Negative helpScore = limiting contribution.
				const helpScore = inspectedAchievedObjective.maximize ? rawValue : -rawValue;

				return {
					symbol: objective.symbol,
					name: objective.name,
					rawValue,
					helpScore,
					isOwn:
						normalizeObjectiveSymbol(objective.symbol) ===
						normalizeObjectiveSymbol(inspectedAchievedSymbol),
					isHelpful: helpScore > 0
				};
			})
			.sort((a, b) => Math.abs(b.helpScore) - Math.abs(a.helpScore));
	});

	onMount(() => {
		if (!networkSelection) {
			networkSelection = {
				side: 'achieved',
				symbol: selectedObjectiveSymbol,
				name: selectedObjectiveName
			};
		}
	});
</script>

<div class="space-y-2">
	<!-- Compact explanation-generation pipeline -->
	<p class="text-xs leading-relaxed text-gray-600">
		Explore the contribution structure behind the current solution.
		<strong>Relationship view</strong> supports interactive inspection of individual desired or
		achieved values, while
		<strong>Contribution matrix</strong> provides an overview of all pairwise contributions.
	</p>

	<!-- Evidence views -->
	<Tabs.Root bind:value={selectedEvidenceView} class="w-full">
		<Tabs.List
			class="grid h-auto w-full grid-cols-2 rounded-md bg-gray-100 p-1"
			aria-label="Explanation evidence views"
		>
			<Tabs.Trigger
				value="overview"
				class="rounded px-2 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
			>
				Relationship view
			</Tabs.Trigger>

			<Tabs.Trigger
				value="matrix"
				class="rounded px-2 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
			>
				Contribution matrix
			</Tabs.Trigger>
		</Tabs.List>

		<!-- Overview tab -->
		<Tabs.Content value="overview" class="mt-3 space-y-3 focus-visible:outline-none">
			<!-- Relationship network -->
			<section
				class="rounded-md border border-gray-200 bg-white p-3"
				aria-labelledby="influence-map-heading"
			>
				<div class="mb-3">
					<h4 class="text-sm font-semibold text-gray-900">Explore contributions</h4>

					<p class="mt-1 text-xs leading-relaxed text-gray-500">
						Select a <strong class="font-medium text-gray-700">desired value</strong>
						to see how it contributed across the achieved values, or select an
						<strong class="font-medium text-gray-700">achieved value</strong>
						to see which desired values contributed to it.
					</p>
					<div
						class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500"
						aria-label="Contribution legend"
					>
						<span class="inline-flex items-center gap-1.5">
							<span class="h-0.5 w-4 rounded-full bg-[#0C7BDC]"></span>
							Supportive
						</span>

						<span class="inline-flex items-center gap-1.5">
							<span class="h-0.5 w-4 rounded-full bg-[#DC3220]"></span>
							Limiting
						</span>

						<span class="inline-flex items-center gap-1.5">
							<span class="inline-flex items-center gap-0.5">
								<span class="h-px w-3 bg-gray-400"></span>
								<span class="h-1 w-3 bg-gray-400"></span>
							</span>
							Thicker = larger contribution
						</span>
						<span class="inline-flex items-center gap-1">
							<span class="font-semibold text-blue-700" aria-hidden="true"> ❤︎ </span>
							Selected achieved value
						</span>
					</div>
					<ShapCaseRelationshipNetwork
						{objectives}
						{iterationDesiredValues}
						achievedValues={baselineObjectiveValues}
						shapValues={SHAP_values}
						threshold={0}
						targetObjectiveSymbol={selectedObjectiveSymbol}
						onNodeSelect={(node) => {
							networkSelection = node;
						}}
						showLegend={false}
					/>
				</div>
			</section>
			<!-- Contributions for the selected objective -->
			<section
				class="rounded-md border border-gray-200 bg-white p-3"
				aria-labelledby="contributions-heading"
			>
				{#if networkSelection?.side === 'desired'}
					<div class="mb-3">
						<h4 class="text-sm font-semibold text-gray-900">
							Contributions from {networkSelection.name}
						</h4>

						<p class="mt-1 text-xs text-gray-500">
							How the desired value for {networkSelection.name}
							contributed to each achieved value.
						</p>
					</div>

					<DesiredValueEffects effects={selectedDesiredEffects} {objectives} />
				{:else}
					<div class="mb-3">
						<h4 class="text-sm font-semibold text-gray-900">
							Contributions to {networkSelection?.name ?? selectedObjectiveName}
						</h4>

						<p class="mt-1 text-xs leading-relaxed text-gray-500">
							How the desired values contributed to this achieved value.
						</p>
					</div>

					<ContributionChart
						contributions={selectedContributionRows}
						suggestedDesiredValueName={null}
						digits={3}
						showOwnContribution={true}
					/>
				{/if}
			</section>
		</Tabs.Content>

		<!-- Full SHAP matrix tab -->
		<Tabs.Content value="matrix" class="mt-3 focus-visible:outline-none">
			<section
				class="rounded-md border border-gray-200 bg-white p-3"
				aria-labelledby="relationship-matrix-heading"
			>
				<div class="mb-3">
					<h4 class="text-sm font-semibold text-gray-900">Contribution matrix</h4>

					<div class="mt-1 flex items-center gap-2">
						<p class="mt-1 text-xs leading-relaxed text-gray-500">
							Compare the contributions between all desired and achieved values.
						</p>
						<Tooltip.Root>
							<Tooltip.Trigger
								class="mt-0.5 inline-flex items-center text-gray-400 hover:text-gray-600"
							>
								<InfoIcon class="h-3.5 w-3.5" />
							</Tooltip.Trigger>

							<Tooltip.Content sideOffset={6} class="max-w-72">
								Each cell describes how one desired value contributed to one achieved value in the
								current solution. Contributions do not predict what will happen if a desired value
								is changed.
							</Tooltip.Content>
						</Tooltip.Root>
					</div>
				</div>

				<div class="overflow-x-auto">
					<ShapHeatmap shapValues={SHAP_values} {problem} />
				</div>
			</section>
		</Tabs.Content>
	</Tabs.Root>

	<!-- Optional generated explanation -->
	<!-- 	{#if explanationText}
		<div class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2.5">
			<div class="mb-1 flex items-center gap-1.5">
				<svg
					aria-hidden="true"
					class="h-4 w-4 shrink-0 text-gray-400"
					viewBox="0 0 24 24"
					fill="none"
					stroke="currentColor"
					stroke-width="2"
					stroke-linecap="round"
					stroke-linejoin="round"
				>
					<circle cx="12" cy="12" r="10"></circle>
					<path d="M12 16v-4"></path>
					<path d="M12 8h.01"></path>
				</svg>

				<span class="text-xs font-semibold text-gray-700"> Method note </span>
			</div>

			<p class="text-xs leading-relaxed text-gray-500">
				{explanationText}
			</p>
		</div>
	{/if} -->
</div>
