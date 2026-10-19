<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import EndStateView from '../../GNIMBUS/components/EndStateView.svelte';
	import { mapSolutionsToObjectiveValues } from '../helper-functions';
	import Button from '$lib/components/ui/button/button.svelte';
import RotateCcw from '@lucide/svelte/icons/rotate-ccw';
import CheckCircle2 from '@lucide/svelte/icons/check-circle-2';

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
		perturbed_reference_point_labels_for_plot,
		onStartNewOptimization
	}: {
		problem: ProblemInfo | null;
		final_solution: Solution | null;
		hasUtopiaMetadata: boolean;
		mapState: MapState;
		last_iterated_preference: number[];
		type_preferences: string;
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
		onStartNewOptimization: () => void | Promise<void>;
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
{#snippet explorerTitle()}
	<div class="flex items-center gap-3">
		<div
			class="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-emerald-50 text-emerald-700"
		>
			<CheckCircle2 class="h-5 w-5" />
		</div>

		<div>
			<h2 class="text-base font-semibold text-gray-900">
				Final solution selected
			</h2>

			<p class="text-xs font-normal text-gray-500">
				Optimization completed. The selected solution is shown below.
			</p>
		</div>
	</div>
{/snippet}

{#snippet explorerControls()}
	<Button
		variant="outline"
		class="flex shrink-0 items-center gap-2"
		onclick={onStartNewOptimization}
	>
		<RotateCcw class="h-4 w-4" />
		Start new optimization
	</Button>
{/snippet}
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
