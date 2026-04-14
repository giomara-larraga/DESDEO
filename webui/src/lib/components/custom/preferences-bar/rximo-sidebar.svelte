<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import type { ProblemInfo, Solution } from '$lib/types';
	import {
		ShapHeatmap,
		ShapBarchart,
		ShapReferenceGuide
	} from '$lib/components/visualizations/shap-heatmap';
	import { Combobox } from '$lib/components/ui/combobox';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		SHAP_values: Record<string, Record<string, number>> | null;
		isLoading?: boolean;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		solutions,
		SHAP_values,
		isLoading = false,
		ref = null
	}: Props = $props();

	const objectiveOptions = $derived(
		problem.objectives.map((o) => ({ value: o.symbol, label: o.name ?? o.symbol }))
	);

	let selectedObjectiveSymbol = $state('');

	// Set/reset selection when SHAP values or objectives change
	$effect(() => {
		const firstSymbol = problem.objectives[0]?.symbol ?? '';
		if (!selectedObjectiveSymbol || (SHAP_values && !(selectedObjectiveSymbol in SHAP_values))) {
			selectedObjectiveSymbol = SHAP_values ? (Object.keys(SHAP_values)[0] ?? firstSymbol) : firstSymbol;
		}
	});

	const selectedRow = $derived(
		SHAP_values && selectedObjectiveSymbol ? (SHAP_values[selectedObjectiveSymbol] ?? {}) : {}
	);

	const selectedObjectiveName = $derived(
		problem.objectives.find((o) => o.symbol === selectedObjectiveSymbol)?.name ??
			selectedObjectiveSymbol
	);
</script>

<Sidebar.Root side="right" class="fixed top-12 right-0 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span class="text-sm font-semibold">Explanations</span>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		<Tooltip.Provider>
			{#if isLoading}
				<div class="py-8 text-center text-sm text-gray-500">Computing explanations…</div>
			{:else if solutions.length === 0 || SHAP_values === null || Object.keys(SHAP_values).length === 0}
				<div class="py-8 text-center text-sm text-gray-500">No solution details available yet.</div>
			{:else}
				<div class="space-y-5">
					<div class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
						<div class="flex items-start justify-between gap-2">
							<p>
								Use the selected <strong>outcome</strong> to decide which <strong>aspiration</strong>
								to tighten or relax next.
							</p>
							<Tooltip.Root>
								<Tooltip.Trigger class="mt-0.5 inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-72">
									<p>
										An <strong>outcome</strong> is a result you care about. An <strong>aspiration</strong>
										is the level you ask for.
									</p>
									<p class="mt-1">
										These charts show how changing one aspiration is likely to affect each outcome.
										To set the next reference point, start from the outcome you want to improve,
										then look for the most helpful aspiration. If an aspiration is marked as making
										the outcome harder to improve, it may be too strict and may need to be relaxed.
									</p>
								</Tooltip.Content>
							</Tooltip.Root>
						</div>
					</div>

					<!-- Objective selector -->
					<div>
						<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
							<span>Focus outcome</span>
							<Tooltip.Root>
								<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-56">
									Choose the outcome you want to inspect. The charts below update for that outcome.
								</Tooltip.Content>
							</Tooltip.Root>
						</div>
						<Combobox
							options={objectiveOptions}
							defaultSelected={selectedObjectiveSymbol}
							onChange={(e) => (selectedObjectiveSymbol = e.value)}
						/>
					</div>

					<Tabs.Root value="influences" class="w-full">
						<Tabs.List class="grid w-full grid-cols-3">
							<Tabs.Trigger value="influences">Influences</Tabs.Trigger>
							<Tabs.Trigger value="overview">Overview</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="influences" class="mt-3 w-full">
							<div>
								<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
									<span>Main influences</span>
									<Tooltip.Root>
										<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
											<InfoIcon class="h-3.5 w-3.5" />
										</Tooltip.Trigger>
										<Tooltip.Content sideOffset={6} class="max-w-64">
											Shows how each aspiration affects <strong>{selectedObjectiveName}</strong>. Red pushes the outcome up, blue pushes it down, black marks its own aspiration, and ★ marks the most helpful aspiration.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>
								<p class="mb-1 text-xs text-gray-500">For <em>{selectedObjectiveName}</em></p>
								<ShapBarchart shapRow={selectedRow} selectedOutputSymbol={selectedObjectiveSymbol} {problem} />
							</div>
						</Tabs.Content>

						<Tabs.Content value="overview" class="mt-3 w-full">
							<div>
								<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
									<span>Overview</span>
									<Tooltip.Root>
										<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
											<InfoIcon class="h-3.5 w-3.5" />
										</Tooltip.Trigger>
										<Tooltip.Content sideOffset={6} class="max-w-64">
											Rows are outcomes and columns are aspirations. Each cell shows how changing an aspiration affects an outcome. Stronger color means stronger influence.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>
								<ShapHeatmap shapValues={SHAP_values} {problem} />
							</div>
						</Tabs.Content>
					</Tabs.Root>
				</div>
			{/if}
		</Tooltip.Provider>
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
