<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { Combobox } from '$lib/components/ui/combobox';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import Button from '$lib/components/ui/button/button.svelte';
	import IntermediateSidebar from '$lib/components/custom/nimbus/intermediate-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/nimbus/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';

	import { mapSolutionsToObjectiveValues } from '../helper-functions';

	import type { MethodMode, ProblemInfo, Solution, SolutionType } from '$lib/types';
	import type { Response } from '../types';

	let {
		mode = $bindable('intermediate' as MethodMode),
		problem,
		current_state,
		selected_type_solutions,
		frameworks,
		selected_type_solutions_label,
		canShowLeftSidebar,
		isLeftSidebarCollapsed = $bindable(false),
		selected_solutions_for_intermediate,
		current_num_intermediate_solutions = $bindable(1),
		last_iterated_preference,
		type_preferences,
		current_preference,
		chosen_solutions,
		selectedIndexes,
		perturbed_reference_point_values_for_plot,
		perturbed_reference_point_labels_for_plot,
		handle_type_solutions_change,
		handle_intermediate,
		handle_solution_click,
		confirm_finish,
		handle_save,
		handle_change,
		confirm_remove_saved,
		isSaved
	}: {
		mode?: MethodMode;
		problem: ProblemInfo | null;
		current_state: Response;
		selected_type_solutions: SolutionType;
		frameworks: { value: string; label: string }[];
		selected_type_solutions_label: string;
		canShowLeftSidebar: boolean;
		isLeftSidebarCollapsed?: boolean;
		selected_solutions_for_intermediate: Solution[];
		current_num_intermediate_solutions?: number;
		last_iterated_preference: number[];
		type_preferences: string;
		current_preference: number[];
		chosen_solutions: Solution[];
		selectedIndexes: number[];
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
		handle_type_solutions_change: (event: { value: string }) => void;
		handle_intermediate: () => Promise<void>;
		handle_solution_click: (index: number) => void;
		confirm_finish: () => void;
		handle_save: (solution: Solution, name: string | undefined) => Promise<void>;
		handle_change: (solution: Solution) => void;
		confirm_remove_saved: (solution: Solution) => void;
		isSaved: (solution: Solution) => boolean;
	} = $props();
</script>

<BaseLayout
	showLeftSidebar={canShowLeftSidebar && !isLeftSidebarCollapsed}
	showRightSidebar={false}
	bottomPanelTitle={selected_type_solutions_label}
>
	{#snippet leftSidebar()}
		<div class="relative h-full">
			<Button
				onclick={() => (isLeftSidebarCollapsed = true)}
				variant="outline"
				size="icon"
				class="absolute -right-4 top-1/2 z-20 h-8 w-8 -translate-y-1/2 bg-white"
				aria-label="Hide left panel"
				title="Hide left panel"
			>
				&lt;
			</Button>

			{#if problem}
				<div class="flex flex-col">
					<IntermediateSidebar
						currentSolutions={selected_solutions_for_intermediate}
						bind:numSolutions={current_num_intermediate_solutions}
						minNumSolutions={1}
						maxNumSolutions={4}
						onClick={handle_intermediate}
					/>
				</div>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerControls()}
		<div class="relative h-full flex-row flex items-center px-4">
			<SegmentedControl
				bind:value={mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' },
					{ value: 'history', label: 'History' }
				]}
				class="mr-10"
			/>
			<span>View: </span>
			<Combobox
				options={frameworks}
				defaultSelected={selected_type_solutions}
				onChange={handle_type_solutions_change}
			/>

			<span
				class="inline-block"
				title={selectedIndexes.length !== 1
					? 'Please select exactly one solution to finish with it.'
					: 'Select final solution and finish the NIMBUS method with it'}
			>
				<Button
					onclick={selectedIndexes.length === 1 ? confirm_finish : undefined}
					disabled={selectedIndexes.length !== 1 || current_state.response_type === 'rpm.finalize'}
					variant="destructive"
					class="ml-10"
				>
					Finish
				</Button>
			</span>
		</div>
	{/snippet}

	{#snippet visualizationArea(height)}
		{#if problem && current_state}
			<div class="relative h-full">
				{#if canShowLeftSidebar}
					<Button
						onclick={() => (isLeftSidebarCollapsed = false)}
						variant="outline"
						size="icon"
						class="fixed left-1 top-1/2 z-30 h-8 w-8 -translate-y-1/2 bg-white"
						aria-label={isLeftSidebarCollapsed ? 'Show left panel' : 'Hide left panel'}
						title={isLeftSidebarCollapsed ? 'Show left panel' : 'Hide left panel'}
						hidden={!isLeftSidebarCollapsed}
					>
						&gt;
					</Button>
				{/if}

				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
						<VisualizationsPanel
							{height}
							{problem}
							previousPreferenceValues={[last_iterated_preference]}
							currentPreferenceValues={current_preference}
							previousPreferenceType={type_preferences}
							currentPreferenceType={type_preferences}
							perturbedReferencePointValues={perturbed_reference_point_values_for_plot}
							referenceDataLabels={{
								perturbedRefLabels: perturbed_reference_point_labels_for_plot
							}}
							solutionsObjectiveValues={mapSolutionsToObjectiveValues(chosen_solutions, problem)}
							previousObjectiveValues={[]}
							externalSelectedIndexes={selectedIndexes}
							onSelectSolution={handle_solution_click}
						/>
					</Resizable.Pane>
				</Resizable.PaneGroup>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No problem data available for visualization
			</div>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if problem && chosen_solutions.length > 0}
			<div class="relative h-full flex-row flex items-center px-4">
				<SolutionTable
					{problem}
					solverResults={chosen_solutions}
					selectedSolutions={selectedIndexes}
					{handle_save}
					{handle_change}
					handle_remove_saved={confirm_remove_saved}
					handle_row_click={handle_solution_click}
					{isSaved}
					{selected_type_solutions}
					secondaryObjectiveValues={selected_type_solutions === 'current'
						? [
								...(current_state.previous_objectives ? [current_state.previous_objectives] : []),
								...(current_state.reference_solution_1 ? [current_state.reference_solution_1] : []),
								...(current_state.reference_solution_2 ? [current_state.reference_solution_2] : [])
							]
						: []}
				/>
			</div>
		{/if}
	{/snippet}
</BaseLayout>
