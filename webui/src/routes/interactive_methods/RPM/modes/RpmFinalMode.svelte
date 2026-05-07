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
		selected_iteration_index,
		chosen_solutions,
		hasUtopiaMetadata,
		mapState,
		last_iterated_preference,
		type_preferences,
		perturbed_reference_point_values_for_plot,
		perturbed_reference_point_labels_for_plot
	}: {
		problem: ProblemInfo | null;
		selected_iteration_index: number[];
		chosen_solutions: Solution[];
		hasUtopiaMetadata: boolean;
		mapState: MapState;
		last_iterated_preference: number[];
		type_preferences: string;
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
	} = $props();
</script>

<BaseLayout showLeftSidebar={false} showRightSidebar={false} bottomPanelTitle="Final Solution">
	{#snippet visualizationArea(height)}
		{#if problem && selected_iteration_index.length > 0}
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
								? mapSolutionsToObjectiveValues([chosen_solutions[selected_iteration_index[0]]], problem)
								: []}
							externalSelectedIndexes={selected_iteration_index}
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
		{#if problem && chosen_solutions.length > 0 && selected_iteration_index.length > 0}
			<EndStateView {problem} tableData={[chosen_solutions[selected_iteration_index[0]] as any]} />
		{/if}
	{/snippet}
</BaseLayout>
