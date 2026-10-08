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
	import { PREFERENCE_TYPES, options_segmented_control } from '$lib/constants';

	import { mapSolutionsToObjectiveValues } from '../helper-functions';
	import type { MethodMode, ProblemInfo, Solution, SolutionType } from '$lib/types';
	import type { MapState, Response, ReferencePoint } from '../types';

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
		iterate_explanation_solutions,
		iterate_explanation_reference_values,
		iterate_explanation_perturbed_reference_points,
		previous_iterate_presented_solution,
		previous_iterate_reference_values,
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
		last_iterated_preference: number[];
		chosen_solutions: Solution[];
		current_perturbed_solutions: Solution[];
		selectedIndexes: number[];
		hasUtopiaMetadata: boolean;
		mapState: MapState;
		perturbed_reference_point_values_for_plot: number[][];
		perturbed_reference_point_labels_for_plot: string[];
		iterate_explanation_solutions: Solution[];
		iterate_explanation_reference_values: number[];
		iterate_explanation_perturbed_reference_points: ReferencePoint[];
		previous_iterate_presented_solution: Solution | null;
		previous_iterate_reference_values: number[];
		current_SHAP_values: Record<string, Record<string, number>>;
		current_SHAP_baseline: Record<string, number>;
		current_rximo_results: Record<
			string,
			{
				rival_index: number;
				rival_symbol: string;
				explanation: string;
				suggestion: string;
				explanation_index: number;
				best_effect: number;
				worst_effect: number;
			}
		> | null;
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
	let table_expanded_rows = $derived.by(() => (use_expandable_rows ? collapsed_solutions : []));
	let table_expanded_row_indexes = $derived.by(() =>
		use_expandable_rows ? collapsed_solution_indexes : []
	);

	let visualization_solutions = $derived.by(() => {
		if (selected_type_solutions === 'current') {
			return primary_table_solution;
		}

		return chosen_solutions;
	});

	type ObjectiveValue = number | number[] | null | undefined;

	function normalizeSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function isSameSolution(a: Solution | null | undefined, b: Solution | null | undefined): boolean {
		if (!a || !b) return false;

		return (
			a.state_id === b.state_id &&
			a.solution_index !== null &&
			b.solution_index !== null &&
			a.solution_index === b.solution_index
		);
	}
	function getSolutionObjectiveValue(
		solution: Solution | null,
		symbol: string
	): number | undefined {
		if (!solution?.objective_values) {
			return undefined;
		}

		const normalizedSymbol = normalizeSymbol(symbol);

		const entry = Object.entries(solution.objective_values).find(
			([key]) => normalizeSymbol(key) === normalizedSymbol
		);

		if (!entry) return undefined;

		const raw = entry[1] as ObjectiveValue;

		const value = Array.isArray(raw) ? Number(raw[0]) : Number(raw);

		return Number.isFinite(value) ? value : undefined;
	}

	let current_solution_index_in_visualization = $derived.by(() => {
		const currentSolution = iterate_explanation_solutions[0];

		if (!currentSolution) {
			return null;
		}

		const index = visualization_solutions.findIndex((solution) =>
			isSameSolution(solution, currentSolution)
		);

		return index >= 0 ? index : null;
	});

	let selected_solution_for_left_sidebar = $derived.by(() => {
		if (chosen_solutions.length === 0) {
			return null;
		}

		const selectedIndex = selectedIndexes[0] ?? 0;

		return chosen_solutions[selectedIndex] ?? chosen_solutions[0] ?? null;
	});

	let selected_objective_values = $derived.by(() => {
		if (!problem) return [];

		return problem.objectives.map((objective) =>
			getSolutionObjectiveValue(selected_solution_for_left_sidebar, objective.symbol)
		);
	});

	let iterate_explanation_presented_solution = $derived(iterate_explanation_solutions[0] ?? null);

	let iterate_explanation_objective_values = $derived.by(() => {
		if (!problem || !iterate_explanation_presented_solution) {
			return [];
		}

		const values = problem.objectives.map((objective) =>
			getSolutionObjectiveValue(iterate_explanation_presented_solution, objective.symbol)
		);

		if (values.some((value) => value === undefined)) {
			return [];
		}

		return values as number[];
	});

	let previous_presented_objective_values = $derived.by(() => {
		if (!problem || !previous_iterate_presented_solution) {
			return [];
		}

		return mapSolutionsToObjectiveValues([previous_iterate_presented_solution], problem);
	});

	let previous_presented_objective_records = $derived.by(() => {
		const objectiveValues = previous_iterate_presented_solution?.objective_values;
		return objectiveValues ? [objectiveValues] : [];
	});
</script>

<BaseLayout
	showLeftSidebar={canShowLeftSidebar}
	showRightSidebar={hasRightSidebarContent}
	bind:isLeftSidebarCollapsed
	bind:isRightSidebarCollapsed
	bottomPanelTitle={selected_type_solutions_label}
>
	{#snippet leftSidebar()}
		<div class="relative h-full">
			{#if problem}
				<AppSidebar
					{problem}
					preferenceTypes={[PREFERENCE_TYPES.ReferencePoint]}
					showNumSolutions={false}
					numSolutions={current_num_iteration_solutions}
					typePreferences={type_preferences}
					preferenceValues={current_preference}
					objectiveValues={selected_objective_values}
					lastIteratedPreference={last_iterated_preference}
					fitParent={true}
					onPreferenceChange={handle_preference_change}
					onIterate={handle_iterate}
					isFinishButton={false}
				/>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerControls()}
		<div class="relative h-full flex-row flex items-center">
			<!-- <SegmentedControl bind:value={mode} options={options_segmented_control} class="mr-2" /> -->
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
				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<Resizable.Pane defaultSize={65} minSize={40} maxSize={80} class="h-full">
						<VisualizationsPanel
							{height}
							{problem}
							previousPreferenceValues={previous_iterate_reference_values.length > 0
								? [previous_iterate_reference_values]
								: []}
							currentPreferenceValues={current_preference}
							previousPreferenceType={type_preferences}
							currentPreferenceType={type_preferences}
							currentSolutionIndex={current_solution_index_in_visualization}
							perturbedReferencePointValues={perturbed_reference_point_values_for_plot}
							referenceDataLabels={{
								previousSolutionLabels:
									previous_presented_objective_values.length > 0 ? ['Previous solution'] : [],
								perturbedRefLabels: perturbed_reference_point_labels_for_plot
							}}
							solutionsObjectiveValues={mapSolutionsToObjectiveValues(
								visualization_solutions,
								problem
							)}
							previousObjectiveValues={selected_type_solutions === 'current'
								? previous_presented_objective_values
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
					preferences={iterate_explanation_reference_values.length > 0
						? iterate_explanation_reference_values
						: last_iterated_preference}
					previousPreferences={previous_iterate_reference_values}
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
						? previous_presented_objective_records
						: []}
				/>
			</div>
		{/if}
	{/snippet}

	{#snippet rightSidebar()}
		{#if problem}
			<div class="relative h-full">
				<RximoSidebar
					{problem}
					preferenceValues={iterate_explanation_reference_values}
					scenarioReferenceValues={iterate_explanation_reference_values}
					solutions={iterate_explanation_solutions}
					perturbedReferencePoints={iterate_explanation_perturbed_reference_points}
					SHAP_values={current_SHAP_values}
					SHAP_baseline={current_SHAP_baseline}
					rximo_results={current_rximo_results}
					onApplyScenarioPreferences={(values) =>
						handle_preference_change({
							numSolutions: current_num_iteration_solutions,
							typePreferences: type_preferences,
							preferenceValues: values,
							objectiveValues: iterate_explanation_objective_values
						})}
					isLoading={is_fetching_explanation}
					fitParent={true}
				/>
			</div>
		{/if}
	{/snippet}
</BaseLayout>
