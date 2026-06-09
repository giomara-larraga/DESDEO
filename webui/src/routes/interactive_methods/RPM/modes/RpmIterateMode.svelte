<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { Combobox } from '$lib/components/ui/combobox';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import Button from '$lib/components/ui/button/button.svelte';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import SolutionTable from '$lib/components/custom/expandible-solution-table/solution-table.svelte';
	import VisualizationsPanel from '$lib/components/custom/visualizations-panel/visualizations-panel.svelte';
	import UtopiaMap from '$lib/components/custom/nimbus/utopia-map.svelte';
	import RximoSidebar from '$lib/components/custom/preferences-bar/rximo-sidebar/RXIMOSidebar.svelte';
	import { PREFERENCE_TYPES, options_segmented_control
	 } from '$lib/constants';

	import { mapSolutionsToObjectiveValues, processPreviousObjectiveValues } from '../helper-functions';
	import type { MethodMode, ProblemInfo, Solution, SolutionType } from '$lib/types';
	import type { MapState, Response } from '../types';

	let {
		mode = $bindable('iterate' as MethodMode),
		problem,
		current_state,
		selected_type_solutions,
		frameworks,
		selected_type_solutions_label,
		canShowLeftSidebar,
		hasRightSidebarContent,
		isLeftSidebarCollapsed = $bindable(false),
		isRightSidebarCollapsed = $bindable(false),
		current_num_iteration_solutions,
		type_preferences,
		current_preference,
		selected_iteration_objectives,
		last_iterated_preference,
		chosen_solutions,
		current_perturbed_solutions,
		selectedIndexes,
		hasUtopiaMetadata,
		mapState,
		perturbed_reference_point_values_for_plot,
		perturbed_reference_point_labels_for_plot,
		current_SHAP_values,
		current_SHAP_baseline,
		current_rximo_results,
		is_fetching_explanation,
		handle_type_solutions_change,
		handle_preference_change,
		handle_iterate,
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
		hasRightSidebarContent: boolean;
		isLeftSidebarCollapsed?: boolean;
		isRightSidebarCollapsed?: boolean;
		current_num_iteration_solutions: number;
		type_preferences: string;
		current_preference: number[];
		selected_iteration_objectives: Record<string, number>;
		last_iterated_preference: number[];
		chosen_solutions: Solution[];
		current_perturbed_solutions: Solution[];
		selectedIndexes: number[];
		hasUtopiaMetadata: boolean;
		mapState: MapState;
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
		current_SHAP_values: Record<string, Record<string, number>>;
		current_SHAP_baseline: Record<string, number>;
		current_rximo_results: Record<string, {
			rival_index: number;
			rival_symbol: string;
			explanation: string;
			suggestion: string;
			explanation_index: number;
			best_effect: number;
			worst_effect: number;
		}> | null;
		is_fetching_explanation: boolean;
		handle_type_solutions_change: (event: { value: string }) => void;
		handle_preference_change: (data: {
			numSolutions: number;
			typePreferences: string;
			preferenceValues: number[];
			objectiveValues: number[];
		}) => void;
		handle_iterate: (data: {
			numSolutions: number;
			typePreferences: string;
			preferenceValues: number[];
		}) => Promise<void>;
		handle_solution_click: (index: number) => void;
		confirm_finish: () => void;
		handle_save: (solution: Solution, name: string | undefined) => Promise<void>;
		handle_change: (solution: Solution) => void;
		confirm_remove_saved: (solution: Solution, rowIndex?: number) => void;
		isSaved: (solution: Solution) => boolean;
	} = $props();

	let primary_table_solution = $derived.by(() =>
		chosen_solutions.length > 0 ? [chosen_solutions[0]] : []
	);
	let collapsed_solutions = $derived.by(() =>
		selected_type_solutions === 'current' ? current_perturbed_solutions : chosen_solutions.slice(1)
	);
	let collapsed_solution_indexes = $derived.by(() =>
		collapsed_solutions.map((_, index) => index + 1)
	);
	let use_expandable_rows = $derived(selected_type_solutions === 'current');
	let table_solver_results = $derived.by(() =>
		use_expandable_rows ? primary_table_solution : chosen_solutions
	);
	let table_expanded_rows = $derived.by(() =>
		use_expandable_rows ? collapsed_solutions : []
	);
	let table_expanded_row_indexes = $derived.by(() =>
		use_expandable_rows ? collapsed_solution_indexes : []
	);
</script>

<BaseLayout
	showLeftSidebar={canShowLeftSidebar && !isLeftSidebarCollapsed}
	showRightSidebar={hasRightSidebarContent && !isRightSidebarCollapsed}
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
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.ReferencePoint]}
					showNumSolutions={false}
					numSolutions={current_num_iteration_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={Object.values(selected_iteration_objectives)}
					lastIteratedPreference={last_iterated_preference}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					isFinishButton={false}
				/>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerControls()}
		<div class="relative h-full flex-row flex items-center">
			<SegmentedControl
				bind:value={mode}
				options={options_segmented_control}
				class="mr-2"
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
					class="ml-2"
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

				{#if hasRightSidebarContent}
					<Button
						onclick={() => (isRightSidebarCollapsed = false)}
						variant="outline"
						size="icon"
						class="fixed right-1 top-1/2 z-30 h-8 w-8 -translate-y-1/2 bg-white"
						aria-label={isRightSidebarCollapsed ? 'Show right panel' : 'Hide right panel'}
						title={isRightSidebarCollapsed ? 'Show right panel' : 'Hide right panel'}
						hidden={!isRightSidebarCollapsed}
					>
						&lt;
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
							solutionsObjectiveValues={mapSolutionsToObjectiveValues(primary_table_solution, problem)}
							previousObjectiveValues={selected_type_solutions === 'current'
								? processPreviousObjectiveValues(current_state, problem)
								: []}
							externalSelectedIndexes={selectedIndexes}
							onSelectSolution={handle_solution_click}
						/>
					</Resizable.Pane>

					{#if hasUtopiaMetadata}
						<ResizableHandle withHandle class=" border-4 border-gray-200 shadow-sm" />
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
		{#if problem && chosen_solutions.length > 0}
			<div class="relative h-full flex-row flex items-center px-4">
				<SolutionTable
					{problem}
					preferences={last_iterated_preference}
					expandable={false}
					solverResults={table_solver_results}
					expandedRowsData={table_expanded_rows}
					expandedRowIndexes={table_expanded_row_indexes}
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

	{#snippet rightSidebar()}
		{#if hasRightSidebarContent && problem}
			<div class="relative h-full">
				<Button
					onclick={() => (isRightSidebarCollapsed = true)}
					variant="outline"
					size="icon"
					class="absolute -left-4 top-1/2 z-20 h-8 w-8 -translate-y-1/2 bg-white"
					aria-label="Hide right panel"
					title="Hide right panel"
				>
					&gt;
				</Button>

				<RximoSidebar
					{problem}
					preferenceValues={current_preference}
					scenarioReferenceValues={last_iterated_preference}
					solutions={chosen_solutions}
					perturbedReferencePoints={current_state.perturbed_reference_points ?? []}
					SHAP_values={current_SHAP_values}
					SHAP_baseline={current_SHAP_baseline}
					rximo_results={current_rximo_results}
					onApplyScenarioPreferences={(values) =>
						handle_preference_change({
							numSolutions: current_num_iteration_solutions,
							typePreferences: type_preferences,
							preferenceValues: values,
							objectiveValues: Object.values(selected_iteration_objectives)
						})}
					isLoading={is_fetching_explanation}
				/>
			</div>
		{/if}
	{/snippet}
</BaseLayout>
