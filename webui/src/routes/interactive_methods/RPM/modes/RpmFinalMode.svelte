<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import EndStateView from '../../GNIMBUS/components/EndStateView.svelte';
	import { mapSolutionsToObjectiveValues } from '../helper-functions';

	import type { ProblemInfo, Solution } from '$lib/types';
	import type { MapState } from '../types';

	let {
		problem,
		final_solution,
		hasUtopiaMetadata,
		mapState,
		last_iterated_preference,
		type_preferences,
		perturbed_reference_point_values_for_plot,
		perturbed_reference_point_labels_for_plot
	}: {
		problem: ProblemInfo | null;
		final_solution: Solution | null;
		hasUtopiaMetadata: boolean;
		mapState: MapState;
		last_iterated_preference: number[];
		type_preferences: string;
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
	} = $props();

	$effect(() => {
	console.log(
		'RpmFinalMode final_solution:',
		final_solution
	);

	console.log(
		'RpmFinalMode objective values:',
		final_solution?.objective_values
	);
});
</script>

<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final Solution">
	{#snippet visualizationArea(height)}
		{#if problem && final_solution}
			<div class="h-full">
				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<Resizable.Pane defaultSize={65} minSize={40} class="h-full">
						<VisualizationsPanel
							{height}
							{problem}
							previousPreferenceValues={[last_iterated_preference]}
							previousPreferenceType={type_preferences}
							currentPreferenceValues={[]}
							currentPreferenceType={type_preferences}
							perturbedReferencePointValues={perturbed_reference_point_values_for_plot}
							referenceDataLabels={{
								perturbedRefLabels: perturbed_reference_point_labels_for_plot
							}}
							solutionsObjectiveValues={problem
								&& final_solution
								? mapSolutionsToObjectiveValues([final_solution], problem)
								: []}
							externalSelectedIndexes={[]}
							onSelectSolution={() => {}}
						/>
					</Resizable.Pane>

					{#if hasUtopiaMetadata}
						<ResizableHandle withHandle class="border-l border-gray-200 shadow-sm" />
						<Resizable.Pane defaultSize={35} minSize={20} class="h-full">
							<UtopiaMap
								mapOptions={mapState.mapOptions}
								bind:selectedPeriod={mapState.selectedPeriod}
								yearlist={mapState.yearlist}
								geoJSON={mapState.geoJSON}
								mapName={mapState.mapName}
								mapDescription={mapState.mapDescription}
							/>
						</Resizable.Pane>
					{/if}
				</Resizable.PaneGroup>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No problem data available for visualization
			</div>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if problem && final_solution}
			<EndStateView {problem} tableData={[final_solution as any]} />
		{/if}
	{/snippet}
</BaseLayout>
