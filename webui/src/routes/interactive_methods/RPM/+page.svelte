<script lang="ts">
	/**
	 * +page.svelte (Reference Point Method with Explainer)
	 *
	 * @author AI Assistant
	 * @created July 2025
	 *
	 * @description
	 * This page implements the Reference Point Method (RPM) interactive multiobjective optimization method in DESDEO
	 * with integrated SHAP-based explainer functionality. It displays a sidebar with proble									<SolutionTable
										problem={problem}
										solverResults={current_state.solver_results}
										bind:selectedSolution={current_solution_index}
										onRowClick={() => handle_solution_change(current_solution_index)}
									/>mation and reference point
	 * selection, and includes explanation capabilities for understanding why solutions have certain characteristics.
	 *
	 * @props
	 * @property {Object} data - Contains a list of optimization problems fetched from the server.
	 * @property {ProblemInfo[]} data.problems - List of problems.
	 *
	 * @features
	 * - Sidebar with problem information and reference point preferences.
	 * - Solution explorer with RPM optimization and explanation capabilities.
	 * - Responsive, resizable layout using PaneGroup and Pane components.
	 * - SHAP-based explanations for understanding solution characteristics.
	 * - Tabbed interface for numerical values, explanations, and saved solutions.
	 */
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import type { components } from '$lib/api/client-types';
	import { onMount } from 'svelte';
	import { api } from '$lib/api/client';
	import Table from '$lib/components/ui/table/table.svelte';
	import TableBody from '$lib/components/ui/table/table-body.svelte';
	import TableRow from '$lib/components/ui/table/table-row.svelte';
	import TableHead from '$lib/components/ui/table/table-head.svelte';
	import TableCell from '$lib/components/ui/table/table-cell.svelte';
	import TableHeader from '$lib/components/ui/table/table-header.svelte';
	import ConfirmationDialog from '$lib/components/custom/confirmation-dialog.svelte';
	import SolutionTable from '$lib/components/custom/solution-table/solution-table.svelte';
	import { Button } from '$lib/components/ui/button';
	import { Card, CardContent, CardHeader, CardTitle } from '$lib/components/ui/card';
	import { Badge } from '$lib/components/ui/badge';
	import { Tabs, TabsContent, TabsList, TabsTrigger } from '$lib/components/ui/tabs';
	import { PREFERENCE_TYPES } from '$lib/constants';

	type ProblemInfo = components['schemas']['ProblemInfo'];
	type RPMSolveRequest = components['schemas']['RPMSolveRequest'];

	// Placeholder types for explainer functionality (until API is updated)
	type RPMExplainRequest = {
		state_id: number;
		solution_index: number;
	};

	type RPMExplanationResponse = {
		state_id: number;
		solution_index: number;
		explanations: {
			shap_values?: number[];
			base_values?: number[];
			data?: number[];
			variable_symbols?: string[];
			objective_symbols?: string[];
			cache_status?: string;
			problem_id?: number;
		};
		variable_importance: Record<string, number>;
		success: boolean;
		message: string;
	};

	// Define a general type for any state with solver_results
	type StateWithResults = {
		solver_results: Array<{
			optimal_objectives: Record<string, number>;
			optimal_variables: Record<string, number>;
			[key: string]: any;
		}>;
		[key: string]: any;
	};

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: { problems: ProblemInfo[] } }>();
	let problem_list = data.problems ?? [];

	// RPM state management
	let current_state: StateWithResults | null = $state(null);
	let current_state_id: number | null = $state(null);
	let current_solution_index: number = $state(0);
	let current_reference_point: number[] = $state([]);
	let is_solving: boolean = $state(false);

	// Explanation state management
	let explanations: Record<number, RPMExplanationResponse> = $state({});
	let is_explaining: boolean = $state(false);
	let explanation_error: string | null = $state(null);

	// UI state
	let show_confirm_dialog: boolean = $state(false);
	let selected_objectives: Record<string, number> = $state({});

	// Initialize when problem is selected
	$effect(() => {
		if (problem) {
			// Initialize reference point to ideal values or middle values
			current_reference_point = problem.objectives.map((obj) => {
				const ideal = obj.ideal ?? 0;
				const nadir = obj.nadir ?? 1;
				return ideal + (nadir - ideal) * 0.5; // Start at middle
			});
		}
	});

	onMount(() => {
		const unsubscribe = methodSelection.subscribe((selected) => {
			if (selected && selected.selectedProblemId) {
				const selectedProblem = problem_list.find(
					(p: ProblemInfo) => p.id === selected.selectedProblemId
				);
				if (selectedProblem) {
					problem = selectedProblem;
				}
			}
		});
		return unsubscribe;
	});

	// Validation: can solve when reference point is set
	function can_solve(): boolean {
		return (
			!!problem &&
			current_reference_point.length === problem.objectives.length &&
			current_reference_point.every((val) => !isNaN(val))
		);
	}

	// Validation: can explain when we have solutions
	function can_explain(solution_index: number): boolean {
		return (
			!!current_state &&
			!!current_state_id &&
			current_state.solver_results &&
			solution_index < current_state.solver_results.length
		);
	}

	// Solve RPM problem
	async function solve_rpm() {
		if (!problem || !can_solve()) return;

		is_solving = true;
		try {
			const request: RPMSolveRequest = {
				problem_id: problem.id,
				preference: {
					preference_type: 'reference_point',
					aspiration_levels: problem.objectives.reduce(
						(acc, obj, index) => {
							acc[obj.symbol] = current_reference_point[index];
							return acc;
						},
						{} as Record<string, number>
					)
				},
				scalarization_options: {},
				solver: 'scipy',
				solver_options: {}
			};

			// Call the server-side endpoint which proxies to the backend API
			const response = await fetch('/interactive_methods/RPM/solve', {
				method: 'POST',
				headers: {
					'Content-Type': 'application/json'
				},
				credentials: 'include', // Include cookies for authentication
				body: JSON.stringify(request)
			});

			const result = await response.json();

			if (!response.ok) {
				console.error('RPM solve error:', result);
				throw new Error(result.error || `Server error: ${response.status}`);
			}

			if (result.success && result.data) {
				current_state = result.data as StateWithResults;
				// In a real implementation, you'd get the state_id from the response
				// For now, we'll simulate it
				current_state_id = Date.now(); // Temporary solution
				current_solution_index = 0;
				explanations = {}; // Clear previous explanations

				// Update selected objectives from first solution
				if (current_state.solver_results && current_state.solver_results.length > 0) {
					selected_objectives = current_state.solver_results[0].optimal_objectives;
				}
			} else {
				throw new Error(result.error || 'Failed to solve problem');
			}
		} catch (error) {
			console.error('Error solving RPM:', error);
		} finally {
			is_solving = false;
		}
	}

	// Explain a specific solution (placeholder implementation)
	async function explain_solution(solution_index: number) {
		if (!can_explain(solution_index) || !current_state_id) return;

		is_explaining = true;
		explanation_error = null;

		try {
			const request: RPMExplainRequest = {
				state_id: current_state_id,
				solution_index: solution_index
			};

			// TODO: Replace with actual API call when explainer endpoint is available
			// const response = await api.POST('/method/rpm/explain', { body: request });

			// For now, create a mock explanation
			const mockExplanation: RPMExplanationResponse = {
				state_id: current_state_id,
				solution_index: solution_index,
				explanations: {
					shap_values: problem?.variables?.map(() => Math.random() * 0.2 - 0.1) || [],
					base_values: problem?.objectives.map(() => Math.random() * 0.5) || [],
					variable_symbols: problem?.variables?.map((v) => v.symbol) || [],
					objective_symbols: problem?.objectives.map((o) => o.symbol) || [],
					cache_status: 'new_cached',
					problem_id: problem?.id
				},
				variable_importance:
					problem?.variables?.reduce(
						(acc, variable, index) => {
							acc[variable.symbol] = Math.random() * 0.3;
							return acc;
						},
						{} as Record<string, number>
					) || {},
				success: true,
				message: 'Mock explanation generated successfully'
			};

			explanations[solution_index] = mockExplanation;
		} catch (error) {
			console.error('Error explaining solution:', error);
			explanation_error = error instanceof Error ? error.message : 'Unknown error';
		} finally {
			is_explaining = false;
		}
	}

	// Get current explanation for selected solution
	function get_current_explanation(): RPMExplanationResponse | null {
		return explanations[current_solution_index] || null;
	}

	// Handle preference change from sidebar
	function handle_preference_change(data: {
		numSolutions: number;
		typePreferences: string;
		preferenceValues: number[];
		objectiveValues: number[];
	}) {
		current_reference_point = [...data.preferenceValues];
	}

	// Update reference point from preferences
	function update_reference_point(preference_values: number[]) {
		current_reference_point = [...preference_values];
	}

	// Handle solution selection change
	function handle_solution_change(index: number) {
		current_solution_index = index;
		if (current_state?.solver_results?.[index]) {
			selected_objectives = current_state.solver_results[index].optimal_objectives;
		}
	}

	// Format explanation data for display
	function format_explanation_data(explanation: RPMExplanationResponse) {
		if (!explanation.explanations) return [];

		const { shap_values, variable_symbols } = explanation.explanations;
		const { variable_importance } = explanation;

		return (
			variable_symbols?.map((symbol, index) => ({
				variable: symbol,
				shap_value: shap_values?.[index] || 0,
				importance: variable_importance?.[symbol] || 0
			})) || []
		);
	}
</script>

<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false}>
	{#snippet leftSidebar()}
		{#if problem}
			<AppSidebar
				{problem}
				preferenceTypes={[PREFERENCE_TYPES.ReferencePoint]}
				showNumSolutions={false}
				numSolutions={1}
				typePreferences={PREFERENCE_TYPES.ReferencePoint}
				preferenceValues={current_reference_point}
				objectiveValues={Object.values(selected_objectives)}
				isIterationAllowed={false}
				isFinishAllowed={false}
				onPreferenceChange={handle_preference_change}
			/>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if !problem}
			<div class="flex h-full items-center justify-center">
				<Card class="w-96">
					<CardHeader>
						<CardTitle>Select a Problem</CardTitle>
					</CardHeader>
					<CardContent>
						<p class="text-muted-foreground">
							Please select a problem from the sidebar to begin using the Reference Point Method.
						</p>
					</CardContent>
				</Card>
			</div>
		{:else}
			<div class="flex flex-1 flex-col p-4">
				<!-- Header Section -->
				<div class="mb-4">
					<div class="flex items-center justify-between">
						<h1 class="text-2xl font-bold">Reference Point Method</h1>
						<div class="flex gap-2">
							<Button variant="default" disabled={!can_solve() || is_solving} onclick={solve_rpm}>
								{is_solving ? 'Solving...' : 'Solve'}
							</Button>
							{#if current_state}
								<Button
									variant="outline"
									disabled={!can_explain(current_solution_index) || is_explaining}
									onclick={() => explain_solution(current_solution_index)}
								>
									{is_explaining ? 'Explaining...' : 'Explain Solution'}
								</Button>
							{/if}
						</div>
					</div>

					{#if problem}
						<p class="text-muted-foreground mt-1">
							Problem: {problem.name} ({problem.objectives.length} objectives, {problem.variables
								?.length || 0} variables)
						</p>
					{/if}
				</div>

				<!-- Main Content Area -->
				{#if current_state && current_state.solver_results}
					<div class="flex-1">
						<Tabs value="solutions" class="flex h-full flex-col">
							<TabsList class="grid w-full grid-cols-3">
								<TabsTrigger value="solutions">Solutions</TabsTrigger>
								<TabsTrigger value="explanations">Explanations</TabsTrigger>
								<TabsTrigger value="cache">Cache Status</TabsTrigger>
							</TabsList>

							<TabsContent value="solutions" class="flex-1">
								<Card class="h-full">
									<CardHeader>
										<CardTitle>Solutions ({current_state.solver_results.length})</CardTitle>
									</CardHeader>
									<CardContent class="h-full overflow-auto">
										<SolutionTable
											{problem}
											solverResults={current_state.solver_results}
											bind:selectedSolution={current_solution_index}
											onRowClick={() => handle_solution_change(current_solution_index)}
										/>
									</CardContent>
								</Card>
							</TabsContent>

							<TabsContent value="explanations" class="flex-1">
								<Card class="h-full">
									<CardHeader>
										<div class="flex items-center justify-between">
											<CardTitle>Solution Explanations</CardTitle>
											{#if get_current_explanation()}
												<Badge variant="secondary">
													{get_current_explanation()?.explanations?.cache_status?.replace(
														'_',
														' '
													) || 'Unknown'}
												</Badge>
											{/if}
										</div>
									</CardHeader>
									<CardContent class="h-full overflow-auto">
										{#if explanation_error}
											<div class="rounded-md border border-red-200 bg-red-50 p-4 text-red-600">
												Error: {explanation_error}
											</div>
										{:else if get_current_explanation()}
											{@const explanation = get_current_explanation()}
											{#if explanation}
												{@const explanation_data = format_explanation_data(explanation)}

												<div class="space-y-4">
													<div>
														<h3 class="mb-2 text-lg font-semibold">
															Solution {current_solution_index + 1} Explanation
														</h3>
														<p class="text-muted-foreground mb-4 text-sm">
															{explanation?.message || 'Explanation generated successfully'}
														</p>
													</div>

													{#if explanation_data.length > 0}
														<Table>
															<TableHeader>
																<TableRow>
																	<TableHead>Variable</TableHead>
																	<TableHead>SHAP Value</TableHead>
																	<TableHead>Importance</TableHead>
																</TableRow>
															</TableHeader>
															<TableBody>
																{#each explanation_data as row}
																	<TableRow>
																		<TableCell class="font-medium">{row.variable}</TableCell>
																		<TableCell>
																			<span
																				class={row.shap_value >= 0
																					? 'text-green-600'
																					: 'text-red-600'}
																			>
																				{row.shap_value.toFixed(4)}
																			</span>
																		</TableCell>
																		<TableCell>{row.importance.toFixed(4)}</TableCell>
																	</TableRow>
																{/each}
															</TableBody>
														</Table>
													{/if}
												</div>
											{/if}
										{:else}
											<div class="flex h-full items-center justify-center">
												<div class="text-center">
													<p class="text-muted-foreground">No explanation available</p>
													<p class="text-muted-foreground mt-1 text-sm">
														Click "Explain Solution" to generate SHAP explanations
													</p>
												</div>
											</div>
										{/if}
									</CardContent>
								</Card>
							</TabsContent>

							<TabsContent value="cache" class="flex-1">
								<Card class="h-full">
									<CardHeader>
										<CardTitle>Explainer Cache Status</CardTitle>
									</CardHeader>
									<CardContent>
										<div class="space-y-4">
											<div class="text-muted-foreground text-sm">
												<p>Cache management for explainer functionality.</p>
												<p class="mt-2">
													<strong>Note:</strong> Currently showing mock data. Once the explainer API
													endpoints are available, this will display real cache information.
												</p>
											</div>

											{#if problem}
												<div class="space-y-2">
													<p class="text-sm font-medium">Problem ID: {problem.id}</p>
													<p class="text-muted-foreground text-sm">Cache operations:</p>
													<div class="flex gap-2">
														<Button
															variant="outline"
															size="sm"
															onclick={() => console.log('Cache status check - to be implemented')}
														>
															Check Status
														</Button>
														<Button
															variant="outline"
															size="sm"
															onclick={() => console.log('Cache clear - to be implemented')}
														>
															Clear Cache
														</Button>
													</div>
												</div>
											{/if}
										</div>
									</CardContent>
								</Card>
							</TabsContent>
						</Tabs>
					</div>
				{:else}
					<div class="flex flex-1 items-center justify-center">
						<Card class="w-96">
							<CardHeader>
								<CardTitle>Ready to Solve</CardTitle>
							</CardHeader>
							<CardContent>
								<p class="text-muted-foreground">
									Set your reference point values in the sidebar and click "Solve" to generate
									solutions using the Reference Point Method.
								</p>
								{#if current_reference_point.length > 0}
									<div class="mt-4">
										<p class="text-sm font-medium">Current reference point:</p>
										<p class="text-muted-foreground text-sm">
											[{current_reference_point.map((val) => val.toFixed(3)).join(', ')}]
										</p>
									</div>
								{/if}
							</CardContent>
						</Card>
					</div>
				{/if}
			</div>
		{/if}
	{/snippet}
</BaseLayout><!-- Confirmation Dialog -->
<ConfirmationDialog
	bind:open={show_confirm_dialog}
	title="Finish Optimization"
	description="Are you sure you want to finish the optimization process?"
	confirmText="Finish"
	cancelText="Cancel"
	onConfirm={() => {
		console.log('Optimization finished');
		show_confirm_dialog = false;
	}}
	onCancel={() => {
		show_confirm_dialog = false;
	}}
/>
