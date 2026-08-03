<script lang="ts">
	/**
	 * +page.svelte (Single-User SCORE-bands)
	 *
	 * @author Stina Palomäki <palomakistina@gmail.com>
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @created December 2025
	 * @updated August 2026
	 *
	 * @description
	 * Placeholder page for single-user SCORE-bands interactive multiobjective optimization method.
	 * This is a template/demonstration page copied from GDM-SCORE-bands and adapted for individual use.
	 * Currently shows visualization only - actual method functionality needs to be implemented.
	 *
	 * @status PLACEHOLDER - For demonstration and future development
	 * Ready for implementation by adding proper API endpoints and method logic
	 *
	 * @props
	 * @property {Object} data - Contains optimization problems from server
	 * @property {ProblemInfo[]} data.problems - Available problems for selection
	 *
	 * @features
	 * - SCORE-bands visualization (demonstration)
	 * - Configuration controls (non-functional)
	 * - Solution table placeholder
	 *
	 * @todo
	 * - Implement actual SCORE-bands method endpoints
	 * - Add proper configuration functionality
	 * - Connect visualization to real method results
	 * - Implement solution selection and preference handling
	 * - Add decision phase workflow (there is no actual decision phase in single-user, but view to handle solutions is still needed)
	 *
	 * @dependencies
	 * - ScoreBands: Visualization component (works with mock data)
	 * - ParallelCoordinates: Alternative visualization for solutions. Not used, need to add solution selection view
	 * - ScoreBandsSolutionTable: Solution display (needs real data integration) Not used, need to add solution selection view
	 */

	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import { onMount } from 'svelte';
	import type { ProblemInfo, SCOREBandsResult} from '$lib/gen/endpoints/DESDEOFastAPI';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage } from '../../../stores/uiState';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import {
		calculateScales,
		generateClusterColors,
		generateAxisOptions,
		canToggleBands,
		canToggleMedians,
	} from './helper-functions.js';

	import type {
		SCOREBandsConfig,
	} from '$lib/gen/endpoints/DESDEOFastAPI';

	import { handle_initialize_scorebands } from './handlers';
	// Page data props
	//type Problem = ProblemInfo;

	let problem: ProblemInfo | null = $state(null);
	const { data } = $props<{ data: ProblemInfo[] }>();
	let problem_list = $derived(data.problems ?? []);

	let data_loaded = $state(false);
	let loading_error: string | null = $state(null);

	// SCORE-bands state variables
	let scoreBandsResult: SCOREBandsResult | null = $state(null);


	let StateId: number | null = $state(null);

	let SCOREBands = $derived.by(() => {
		if (!scoreBandsResult) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				// Empty objects for pre-calculated bands and medians
				bands: {},
				medians: {},
				scales: {}
			};
		}

		// Type assertion to help TypeScript understand the structure
		const result = scoreBandsResult as SCOREBandsResult;

		const derivedData = {
			// Direct mappings
			axisNames: result.ordered_dimensions,
			clusterIds: Object.keys(result.bands)
				.sort((a, b) => parseInt(a) - parseInt(b))
				.map((id) => Number(id)),
			// Convert axis_positions dict to ordered array
			axisPositions: result.ordered_dimensions.map(
				(objName: string) => result.axis_positions[objName]
			) as number[],

			// Missing data - need fallbacks
			axisSigns: new Array(result.ordered_dimensions.length).fill(1), // Default: no flipping
			data: [], // Empty - use bands-only mode

			// Pre-calculated bands and medians as original key-based structure
			// bands[clusterId][axisName] = [minValue, maxValue] - quantile-based band limits
			bands: result.bands,
			// medians[clusterId][axisName] = medianValue - median values per cluster per axis
			medians: result.medians,
			// scales[axisName] = [minValue, maxValue] - normalization scales for converting raw values to [0,1]
			scales: calculateScales(problem, result)
		};

		return derivedData;
	});

	// Reactive options with checkboxes
	let show_bands = $state(true);
	let show_solutions = $state(false); // Disabled for now - no individual solutions
	let show_medians = $state(false); // Hide medians by default
	let quantile_value = $state(0.25);

	// Score bands calculation parameters
	let dist_parameter = $state(0.05);
	let use_absolute_corr = $state(false);
	let distance_formula = $state(1); // 1 for euclidean, 2 for manhattan
	let flip_axes = $state(true);
	let clustering_algorithm = $state('DBSCAN'); // 'DBSCAN' or 'GMM'
	let clustering_score = $state('silhouette'); // Note: This is the correct spelling used in DESDEO

	let options = $derived.by(() => {
		return {
			bands: show_bands,
			solutions: show_solutions,
			medians: show_medians,
			quantile: quantile_value
		};
	});

	// Cluster visibility controls - dynamically generated based on data
	let cluster_visibility_map: Record<number, boolean> = $state({});

	// Helper function to initialize all clusters as visible
	function clusters_to_visible() {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			SCOREBands.clusterIds.forEach((clusterId) => {
				cluster_visibility_map[clusterId] = true;
			});
		}
	}

	// Update cluster visibility when groups data changes
	$effect(() => {
		if (SCOREBands && SCOREBands.clusterIds.length > 0) {
			// Initialize all clusters as visible if not already set
			SCOREBands.clusterIds.forEach((clusterId) => {
				if (!(clusterId in cluster_visibility_map)) {
					cluster_visibility_map[clusterId] = true;
				}
			});
			// Remove clusters that no longer exist in the data
			Object.keys(cluster_visibility_map).forEach((clusterId) => {
				if (!SCOREBands.clusterIds.includes(Number(clusterId))) {
					delete cluster_visibility_map[Number(clusterId)];
				}
			});
		}
	});

	// Axis order control
	let custom_axis_order: number[] = $state([]);
	let use_custom_order = $state(false);

	// For SCORE bands, the axisNames from the result are already in optimal order,
	// so we use the default sequential order [0, 1, 2, ...] unless custom order is specified
	let effective_axis_order = $derived.by(() => {
		const axisCount = SCOREBands.axisNames.length;
		if (use_custom_order && custom_axis_order.length === axisCount) {
			return custom_axis_order;
		}
		// Default sequential order [0, 1, 2, ...] is counted in component, no need here
		return [];
	});

	// Load data on component mount
	onMount(async () => {
		methodSelection.set($methodSelection.selectedProblemId, 'Explainable NIMBUS');
		if ($methodSelection.selectedProblemId) {
			problem = problem_list.find(
				(p: ProblemInfo) => String(p.id) === String($methodSelection.selectedProblemId)
			);
			if (problem) {
				await fetch_score_bands();
			}
		}
	});

	let cluster_colors = $derived(
		SCOREBands.clusterIds.length > 0 ? generateClusterColors(SCOREBands.clusterIds) : {}
	);

	let axis_options = $derived(
		SCOREBands.axisNames.length > 0 ? generateAxisOptions(SCOREBands.axisNames) : []
	);

	// Selection state
	let selected_band: number | null = $state(null);
	let selected_axis: number | null = $state(null);

	let selected_solution: number | null = $state(null);

	// Selection handlers
	function handle_band_select(clusterId: number | null) {
		selected_band = clusterId;
	}

	function handle_axis_select(axisIndex: number | null) {
		selected_axis = axisIndex;
	}

	async function fetch_score_bands() {
		if (!problem) {
			const message = 'No problem selected.';

			loading_error = message;
			errorMessage.set(message);
			return;
		}

		data_loaded = false;
		loading_error = null;

		try {
			const response =
				await handle_initialize_scorebands(problem);

			if (!response) {
				loading_error =
					'SCORE Bands did not return a result.';
				return;
			}

			StateId = response.state_id;
			scoreBandsResult = response.result;

			selected_band = null;
			selected_axis = null;

			cluster_visibility_map = Object.fromEntries(
				Object.keys(response.result.bands).map(
					(clusterId) => [Number(clusterId), true]
				)
			);
		} catch (error) {
			const message =
				error instanceof Error
					? error.message
					: 'Unable to load SCORE Bands.';

			loading_error = message;
			errorMessage.set(message);

			console.error(
				'Error fetching SCORE Bands:',
				error
			);
		} finally {
			data_loaded = true;
		}
	}
</script>

<svelte:head>
	<title>SCORE-bands Method | DESDEO</title>
	<meta name="description" content="SCORE-bands interactive multiobjective optimization method" />
</svelte:head>

<div class="container mx-auto p-6">
	{#if $errorMessage}
		<Alert title="Error" message={$errorMessage} variant="destructive" />
	{/if}

	{#if !data_loaded}
		<div class="flex h-96 items-center justify-center">
			<div class="text-center">
				<div class="loading loading-spinner loading-lg"></div>
				<p class="mt-4">Loading data...</p>
				{#if loading_error}
					<p class="text-error mt-2">Error: {loading_error}</p>
				{/if}
			</div>
		</div>
	{:else}
		<!-- Header and Instructions -->
		<div>
			<div class="mb-4 rounded-xl border border-blue-200 bg-blue-50 p-5">
				<div class="flex gap-4">
					<!-- Header Section -->
					<div class="font-semibold">SCORE Bands demo page</div>
					<div>Select one band that best matches your preferred objective ranges, then click "Iterate"</div>
				</div>
			</div>
		</div>

		<!-- Parameter Controls -->
		<div class="card bg-base-100 mb-6 shadow-xl">
			<div class="card-body">
				<h3 class="card-title">Score Bands Parameters</h3>
				<div class="grid grid-cols-2 gap-4">
					<div class="form-control">
						<label for="dist_parameter" class="label">
							<span class="label-text">Distance Parameter</span>
						</label>
						<input
							id="dist_parameter"
							type="number"
							bind:value={dist_parameter}
							min="0"
							max="1"
							step="0.1"
							class="input input-bordered"
						/>
					</div>
					<div class="form-control">
						<label for="distance_formula" class="label">
							<span class="label-text">Distance Formula</span>
						</label>
						<select
							id="distance_formula"
							bind:value={distance_formula}
							class="select select-bordered"
						>
							<option value={1}>Euclidean</option>
							<option value={2}>Manhattan</option>
						</select>
					</div>
					<div class="form-control">
						<label for="clustering_algorithm" class="label">
							<span class="label-text">Clustering Algorithm</span>
						</label>
						<select
							id="clustering_algorithm"
							bind:value={clustering_algorithm}
							class="select select-bordered"
						>
							<option value="DBSCAN">DBSCAN</option>
							<option value="GMM">GMM</option>
						</select>
					</div>
					<div class="form-control">
						<label for="clustering_score" class="label">
							<span class="label-text">Clustering Score</span>
						</label>
						<select
							id="clustering_score"
							bind:value={clustering_score}
							class="select select-bordered"
						>
							<option value="silhoutte">Silhouette</option>
							<option value="BIC">BIC</option>
						</select>
					</div>
				</div>
				<div class="mt-4 flex items-center gap-4">
					<label class="label cursor-pointer">
						<input
							type="checkbox"
							bind:checked={use_absolute_corr}
							class="checkbox checkbox-primary mr-2"
						/>
						<span class="label-text">Use Absolute Correlation</span>
					</label>
					<label class="label cursor-pointer">
						<input
							type="checkbox"
							bind:checked={flip_axes}
							class="checkbox checkbox-primary mr-2"
						/>
						<span class="label-text">Flip Axes</span>
					</label>
					<button
						onclick={fetch_score_bands}
						class="btn btn-primary"
						disabled={!problem || !data_loaded}
					>
						{data_loaded
							? 'Recalculate Parameters'
							: 'Calculating...'}
					</button>
				</div>
			</div>
		</div>
		<!-- LEARNING PHASE: Existing SCORE Bands Content -->

		<div class="grid grid-cols-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
			<!-- Controls Panel -->
			 <aside class="space-y-4">
				<div class="space-y-6 lg:col-span-1">
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Visualization Options</h2>

							<!-- Display Options -->
							<div class="form-control">
								<label class="label cursor-pointer">
									<span class="label-text">Show Bands</span>
									<input
										type="checkbox"
										bind:checked={show_bands}
										disabled={!canToggleBands(show_bands, show_medians, show_solutions)}
										class="checkbox checkbox-primary"
										title={canToggleBands(show_bands, show_medians, show_solutions)
											? ''
											: 'At least one visualization option must remain active'}
									/>
								</label>
							</div>

							<div class="form-control">
								<label class="label cursor-pointer">
									<span class="label-text text-gray-500">Show Solutions</span>
									<input
										type="checkbox"
										bind:checked={show_solutions}
										disabled={true}
										class="checkbox checkbox-primary"
										title="Individual solutions are not available"
									/>
								</label>
							</div>

							<div class="form-control">
								<label class="label cursor-pointer">
									<span class="label-text">Show Medians</span>
									<input
										type="checkbox"
										bind:checked={show_medians}
										disabled={!canToggleMedians(show_bands, show_medians, show_solutions)}
										class="checkbox checkbox-primary"
										title={canToggleMedians(show_bands, show_medians, show_solutions)
											? ''
											: 'At least one visualization option must remain active'}
									/>
								</label>
							</div>

							<!-- Quantile Slider -->
							<div class="form-control">
								<label for="quantile_slider" class="label">
									<span class="label-text">Quantile: {quantile_value}</span>
								</label>
								<input
									id="quantile_slider"
									type="range"
									min="0.1"
									max="0.5"
									step="0.05"
									bind:value={quantile_value}
									class="range range-primary"
									title="Adjust quantile to change band width (triggers API call)"
								/>
								<div class="flex w-full justify-between px-2 text-xs">
									<span>0.1</span>
									<span>0.3</span>
									<span>0.5</span>
								</div>
							</div>
						</div>
					</div>

					<!-- Cluster Visibility -->
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Cluster Visibility</h2>

							{#each SCOREBands.clusterIds as clusterId}
								<div class="form-control">
									<label class="label cursor-pointer">
										<span class="label-text">
											<span
												class="inline-block h-4 w-4 rounded"
												style="background-color: {cluster_colors[clusterId] || '#000000'};"
											></span>
											Cluster {clusterId}
										</span>
										<input
											type="checkbox"
											bind:checked={cluster_visibility_map[clusterId]}
											class="checkbox checkbox-primary"
										/>
									</label>
								</div>
							{/each}

							{#if SCOREBands.clusterIds.length === 0}
								<p class="text-sm text-gray-500">No clusters available</p>
							{/if}
						</div>
					</div>

					<!-- Selection Info -->
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Selection</h2>
							<div class="space-y-2">
								{#if selected_band !== null}
									<div class="alert alert-info">
										<span class="font-medium">Band {selected_band} selected</span>
									</div>
								{:else}
									<div class="text-sm text-gray-500">No band selected</div>
								{/if}

								{#if selected_axis !== null}
									<div class="alert alert-warning">
										<span class="font-medium"
											>Axis "{SCOREBands.axisNames[selected_axis] || 'Unknown'}" selected</span
										>
									</div>
								{:else}
									<div class="text-sm text-gray-500">No axis selected</div>
								{/if}

								{#if selected_band === null && selected_axis === null}
									<div class="mt-2 text-xs text-gray-400">Click on bands or axes to select them</div>
								{/if}
							</div>
						</div>
					</div>

					<!-- "Voting buttons" -->
					<div class="card bg-base-100 shadow-xl">
						<div class="card-body">
							<h2 class="card-title">Voting</h2>
							<div class="space-y-2 p-2">
								<Button
									onclick={() => {}}
									disabled={selected_band === null}
								>
									Iterate
								</Button>
							</div>
						</div>
					</div>
				</div>
			</aside>

			<!-- Visualization Area -->
			<main class="space-y-4">
				<div class="rounded-lg border bg-card shadow-sm">
					
						<div class="h-[520px] p-4">
							
								<ScoreBands
									data={SCOREBands.data}
									axisNames={SCOREBands.axisNames}
									axisPositions={SCOREBands.axisPositions}
									axisSigns={SCOREBands.axisSigns}
									groups={SCOREBands.clusterIds}
									{options}
									bands={SCOREBands.bands}
									medians={SCOREBands.medians}
									scales={SCOREBands.scales}
									clusterVisibility={cluster_visibility_map}
									clusterColors={cluster_colors}
									axisOptions={axis_options}
									axisOrder={effective_axis_order}
									onBandSelect={handle_band_select}
									onAxisSelect={handle_axis_select}
									selectedBand={selected_band}
									selectedAxis={selected_axis}
								/>
							
						</div>
					
				</div>
			</main>
		</div>
	{/if}
</div>

<style>
	:global(.container) {
		max-width: 100%;
	}
</style>
