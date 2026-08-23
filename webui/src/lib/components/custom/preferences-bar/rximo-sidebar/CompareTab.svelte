<script lang="ts">
	import type { ProblemInfo } from '$lib/types';
	import {findShapColumn, findShapRow, displayAspirationName, isOwnAspiration, normalizeObjectiveSymbol} from './helpers';

	import ShapCaseRelationshipNetwork from '$lib/components/visualizations/shap-case-relationship-network/ShapCaseRelationshipNetwork.svelte';
	import { ShapHeatmap } from '$lib/components/visualizations/shap-heatmap';
	import ShapWaterfall from '$lib/components/visualizations/shap-waterfall/ShapWaterfall.svelte';

	import * as Tabs from '$lib/components/ui/tabs/index.js';

	import DesiredValueEffects from '$lib/components/visualizations/desired-value-effects/DesiredValueEffects.svelte';
	import { onMount } from 'svelte';

	type ObjectiveValue = number | number[] | null | undefined;


	interface Props {
		selectedObjectiveName: string;
		selectedObjectiveSymbol: string;
		problem: ProblemInfo;
		preferenceValues: number[];
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
		preferenceValues,
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

	const selectedAchievedEffects = $derived(
		networkSelection?.side === 'achieved' && networkSelection?.symbol
			? findShapRow(SHAP_values, networkSelection.symbol)
			: null
	);
		
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
	<p class="text-xs leading-relaxed text-gray-700">
		The explanation shows how your desired values affected the objective values
		achieved by the current solution.
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
				Interactive view
			</Tabs.Trigger>

			<Tabs.Trigger
				value="matrix"
				class="rounded px-2 py-1.5 text-xs font-medium data-[state=active]:bg-white data-[state=active]:text-gray-900 data-[state=active]:shadow-sm"
			>
				Matrix view
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
		<h4
			id="influence-map-heading"
			class="text-sm font-semibold text-gray-900"
		>
			Explore objective influences
		</h4>

		<div class="mt-2 space-y-1.5 text-xs leading-relaxed text-gray-500">
			<p>
				Click a <span class="font-medium text-gray-700">desired value</span>
				on the left to see its effects.
			</p>

			<p>
				Click an <span class="font-medium text-gray-700">achieved value</span>
				on the right to see what influenced it.
			</p>
		</div>

<div
	class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-xs text-gray-500"
	aria-label="Influence legend"
>
	<span class="inline-flex items-center gap-1.5">
		<span
			class="h-0.5 w-4 rounded-full bg-[#0C7BDC]"
			aria-hidden="true"
		></span>
		Supports
	</span>

	<span class="inline-flex items-center gap-1.5">
		<span
			class="h-0.5 w-4 rounded-full bg-[#DC3220]"
			aria-hidden="true"
		></span>
		Limits
	</span>

<span class="inline-flex items-center gap-1.5">
	<span class="inline-flex items-center gap-0.5" aria-hidden="true">
		<span class="h-px w-3 rounded-full bg-gray-400"></span>
		<span class="h-1 w-3 rounded-full bg-gray-400"></span>
	</span>
	Thicker = stronger influence
</span>
</div>

	<ShapCaseRelationshipNetwork
		{objectives}
		{preferenceValues}
		achievedValues={baselineObjectiveValues}
		shapValues={SHAP_values}
		threshold={0}
		targetObjectiveSymbol={selectedObjectiveSymbol}
		onNodeSelect={(node) => {
			networkSelection = node;
		}}
	/>
</section>
			<!-- Contributions for the selected objective -->
<section
	class="rounded-md border border-gray-200 bg-white p-3"
	aria-labelledby="contributions-heading"
>
	{#if networkSelection?.side === 'desired'}
		<div class="mb-3">
			<h4
				id="contributions-heading"
				class="text-sm font-semibold text-gray-900"
			>
				Effects of desired value of {networkSelection.name}
			</h4>

			<p class="mt-1 text-xs text-gray-500">
				How this desired value affected each achieved objective.
			</p>
		</div>

		<DesiredValueEffects
			effects={selectedDesiredEffects}
		/>

	{:else}
		<div class="mb-3">
			<h4
				id="contributions-heading"
				class="text-sm font-semibold text-gray-900"
			>
				Influences on achieved value of
				{networkSelection?.name ?? selectedObjectiveName}
			</h4>

			<p class="mt-1 text-xs text-gray-500">
				How each desired value influenced this achieved value.
			</p>
		</div>

		<ShapWaterfall
			shapRow={selectedAchievedEffects}
			selectedOutputSymbol={selectedObjectiveSymbol}
			{problem}
			baseline={selectedSHAPBaseline}
			achieved={selectedSolutionValue}
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
					<h4
						id="relationship-matrix-heading"
						class="text-sm font-semibold text-gray-900"
					>
						All objective relationships
					</h4>

					<p class="mt-1 text-xs leading-relaxed text-gray-500">
							Compare all objective influences

					</p>
				</div>

				<div class="overflow-x-auto">
					<ShapHeatmap
						shapValues={SHAP_values}
						{problem}
					/>
				</div>
			</section>
		</Tabs.Content>
	</Tabs.Root>

	<!-- Optional generated explanation -->
	{#if explanationText}
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

				<span class="text-xs font-semibold text-gray-700">
					Method note
				</span>
			</div>

			<p class="text-xs leading-relaxed text-gray-500">
				{explanationText}
			</p>
		</div>
	{/if}
</div>