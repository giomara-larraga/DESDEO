<script lang="ts">
	/** Single-user SCORE Bands: persisted state lineage, evolutionary zoom, saved bands. */
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import type {
		ProblemInfo,
		SCOREBandsResult,
		SCOREBandsConfig
	} from '$lib/gen/endpoints/DESDEOFastAPI';
	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage } from '../../../stores/uiState';
	import { create_session } from '../../methods/sessions/handler';
	import ScoreBandsLayout from '$lib/components/custom/method_layout/score-bands-layout.svelte';
	import SCOREbandsCorrelationMatrix from '$lib/components/visualizations/score-bands-correlation-heatmap/score-bands-correlation-matrix.svelte';

	import {
		defaultScoreBandsOptions,
		handle_initialize_scorebands,
		handle_iterate_scorebands,
		handle_save_scorebands,
		handle_scorebands_history,
		type ScoreBandsHistoryItem,
		type ScoreBandsOptimizationOptions,
		type ScoreBandsSavedBand,
		type ScoreBandsResponse
	} from './handlers';
	import {
		calculateScales,
		generateClusterColors,
		generateAxisOptions,
		canToggleBands,
		canToggleMedians
	} from './helper-functions';

	import ScoreBandsHistoryGraph from '$lib/components/custom/score-bands-history-graph/score-bands-history-graph.svelte';

	type ClusteringMethod = 'KMeans' | 'DBSCAN' | 'GMM' | 'DimensionCluster';

	let { data }: { data: PageData } = $props();
	let problem: ProblemInfo | null = $state(null);
	let sessionId: number | null = $state(null);
	let stateId: number | null = $state(null);
	let viewedStateId: number | null = $state(null);
	let scoreBandsResult: SCOREBandsResult | null = $state(null);
	let history: ScoreBandsHistoryItem[] = $state([]);
	let savedBands: ScoreBandsSavedBand[] = $state([]);
	let selectedBand: number | null = $state(null);
	let selectedAxis: number | null = $state(null);
	let clusterVisibility: Record<number, boolean> = $state({});

	let busy = $state(false);
	let loading = $state(true);
	let showBands = $state(true);
	let showMedians = $state(false);
	let showSolutions = $state(false);
	let quantile = $state(0.95);

	let leftCollapsed = $state(false);
	let rightCollapsed = $state(false);

	let viewedGeneration = $derived(history.find((item) => item.state_id === viewedStateId) ?? null);

	let latestGenerationId = $derived(history.at(-1)?.state_id ?? null);

	let visual = $derived.by(() => {
		if (!scoreBandsResult) {
			return {
				axisNames: [] as string[],
				clusterIds: [] as number[],
				axisPositions: [] as number[],
				axisSigns: [] as number[],
				data: [] as number[][],
				bands: {} as SCOREBandsResult['bands'],
				medians: {} as SCOREBandsResult['medians'],
				scales: {} as Record<string, [number, number]>
			};
		}

		const result = scoreBandsResult;
		const originalDimensions = result.ordered_dimensions;

		const reference = lockAxisPositions ? initialGeneration : null;

		// Use the initial objective ordering when locked.
		const axisNames = reference
			? [
					...reference.ordered_dimensions.filter((symbol) => originalDimensions.includes(symbol)),
					...originalDimensions.filter((symbol) => !reference.ordered_dimensions.includes(symbol))
				]
			: originalDimensions;

		// Keep the initial positions, but use the currently
		// viewed result's bands, medians, and scales.
		const axisPositions = axisNames.map(
			(symbol) => reference?.axis_positions[symbol] ?? result.axis_positions[symbol]
		);

		return {
			axisNames,
			clusterIds: Object.keys(result.bands)
				.map(Number)
				.sort((a, b) => a - b),
			axisPositions,
			axisSigns: axisNames.map(() => 1),
			data: [] as number[][],
			bands: result.bands,
			medians: result.medians,
			scales: calculateScales(problem, result)
		};
	});

	let colors = $derived(generateClusterColors(visual.clusterIds));
	let axisOptions = $derived(generateAxisOptions(visual.axisNames));
	let options = $derived({
		bands: showBands,
		medians: showMedians,
		solutions: showSolutions,
		quantile
	});
	let currentGenerationId = $derived(viewedStateId);
	let isSaved = $derived(
		selectedBand !== null &&
			savedBands.some(
				(band) => band.source_state_id === viewedStateId && band.cluster_id === selectedBand
			)
	);
	let selectedRanges = $derived(
		selectedBand === null || !scoreBandsResult
			? null
			: ((scoreBandsResult.bands as Record<string, Record<string, [number, number]>>)[
					String(selectedBand)
				] ?? null)
	);

	let historyWithDepth = $derived.by(() => {
		const depths = new Map<number, number>();

		return history.map((item) => {
			const parentDepth =
				item.parent_state_id === null ? -1 : (depths.get(item.parent_state_id) ?? 0);

			const depth = parentDepth + 1;

			depths.set(item.state_id, depth);

			return { ...item, depth };
		});
	});

	let parentViewedStateId = $derived(
		history.find((item) => item.state_id === viewedStateId)?.parent_state_id ?? null
	);

	let initialGenerationStateId = $derived(
		history.find((item) => item.action === 'initialize')?.state_id ?? null
	);

	let lockAxisPositions = $state(true);

	let initialGeneration = $derived(
		history.find((item) => item.action === 'initialize')?.result ?? null
	);

	let optimizeNext = $state(true);

	let algorithm: 'nsga3' | 'rvea' = $state('nsga3');

	let clusteringMethod: ClusteringMethod = $state('KMeans');

	let numClusters = $state(5);

	let clusteringObjective = $state('');

	let dimensionClusteringKind: 'EqualWidth' | 'EqualFrequency' = $state('EqualFrequency');

	let gmmScoringMethod: 'BIC' | 'silhouette' = $state('silhouette');

	let distanceFormula: 1 | 2 = $state(1);

	let distanceParameter = $state(0.05);

	let useAbsoluteCorrelations = $state(false);

	let intervalSize = $state(0.95);

	// Existing settings for starting a completely new session.
	let initialOptimization = $state(false);

	let objectiveNames = $derived(
		Object.fromEntries(
			(problem?.objectives ?? []).map((obj) => [obj.symbol, obj.name || obj.symbol])
		) as Record<string, string>
	);

	let axisLabels = $derived(visual.axisNames.map((symbol) => objectiveNames[symbol] ?? symbol));

	let displayCorrelationMatrix = $derived.by(() => {
		const matrix = scoreBandsResult?.correlation_matrix;

		if (!matrix) return null;

		const sourceDimensions = scoreBandsResult!.ordered_dimensions;

		const indices = visual.axisNames.map((symbol) => sourceDimensions.indexOf(symbol));

		return indices.map((i) =>
			indices.map((j) => (i >= 0 && j >= 0 ? (matrix[i]?.[j] ?? null) : null))
		);
	});

	function showResult(result: SCOREBandsResult) {
		scoreBandsResult = result;
		selectedBand = null;
		selectedAxis = null;
		clusterVisibility = Object.fromEntries(
			Object.keys(result.bands).map((id) => [Number(id), true])
		);
	}

	function saveInitial(response: ScoreBandsResponse) {
		sessionId = response.session_id;
		stateId = response.state_id;
		history = response.history;
		savedBands = response.saved_bands;

		const latestGeneration = response.history.at(-1);

		viewedStateId = latestGeneration?.state_id ?? response.state_id;

		methodSelection.setSession(response.session_id, $methodSelection.selectedSessionInfo);

		showResult(response.result);
	}

	function initialOptions() {
		const result = defaultScoreBandsOptions();
		result.clustering_algorithm = { name: 'DBSCAN', n_clusters: numClusters };
		result.distance_parameter = distanceParameter;
		result.interval_size = quantile;
		return result;
	}

	function buildScorebandsOptions(): SCOREBandsConfig {
		let clusteringAlgorithm: NonNullable<SCOREBandsConfig['clustering_algorithm']>;

		switch (clusteringMethod) {
			case 'KMeans':
				clusteringAlgorithm = {
					name: 'KMeans',
					n_clusters: numClusters
				};
				break;

			case 'DBSCAN':
				clusteringAlgorithm = {
					name: 'DBSCAN'
				};
				break;

			case 'GMM':
				clusteringAlgorithm = {
					name: 'GMM',
					scoring_method: gmmScoringMethod
				};
				break;

			case 'DimensionCluster': {
				const objective = clusteringObjective || visual.axisNames[0];

				if (!objective || !visual.axisNames.includes(objective)) {
					throw new Error('Choose an available objective for clustering.');
				}

				clusteringAlgorithm = {
					name: 'DimensionCluster',
					dimension_name: objective,
					n_clusters: numClusters,
					kind: dimensionClusteringKind
				};
				break;
			}
		}

		return {
			...defaultScoreBandsOptions(),
			clustering_algorithm: clusteringAlgorithm,
			distance_formula: distanceFormula,
			distance_parameter: distanceParameter,
			use_absolute_correlations: useAbsoluteCorrelations,
			interval_size: intervalSize,
			include_medians: true,

			// Calculate axis positions and scales from each new dataset.
			axis_positions: null,
			scales: null
		};
	}

	async function initializeProblem(selectedSessionId: number | null) {
		if (!problem) return;
		busy = true;
		errorMessage.set(null);
		try {
			const response = await handle_initialize_scorebands(
				problem,
				selectedSessionId,
				initialOptions(),
				{ optimize: initialOptimization, algorithm }
			);
			saveInitial(response);
		} catch (error) {
			errorMessage.set(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
			loading = false;
		}
	}

	onMount(() => {
		methodSelection.setMethod('SCORE-bands');
		const chosen = $methodSelection.selectedProblemId;
		problem = (data.problems ?? []).find((item) => item.id === chosen) ?? null;
		// No discrete representation: initialization must compute an
		// unpreferenced evolutionary approximation of the Pareto front.
		initialOptimization = problem?.discrete_representation == null;
		if (!problem) {
			errorMessage.set('Select a problem before opening SCORE Bands.');
			loading = false;
			return;
		}
		void initializeProblem($methodSelection.selectedSessionId);
	});
	async function iterateSelectedBand() {
		if (busy || !problem || sessionId === null || viewedStateId === null) {
			return;
		}

		busy = true;
		errorMessage.set(null);

		try {
			const optimizationOptions: ScoreBandsOptimizationOptions = {
				optimize: optimizeNext,
				algorithm
			};

			const response = await handle_iterate_scorebands({
				problem_id: problem.id,
				session_id: sessionId,

				// The generation the user is currently viewing.
				parent_state_id: viewedStateId,

				// Can be null when working with all existing solutions.
				preference:
					selectedBand === null
						? null
						: {
								preference_type: 'score_bands.band',
								cluster_id: selectedBand
							},

				// Use the CURRENT settings for this specific execution.
				optimization_options: optimizationOptions,
				scorebands_options: buildScorebandsOptions()
			});

			saveInitial(response);
		} catch (error) {
			errorMessage.set(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
		}
	}
	async function toggleSavedBand() {
		if (
			busy ||
			!problem ||
			sessionId === null ||
			stateId === null ||
			viewedStateId === null ||
			selectedBand === null
		) {
			return;
		}
		busy = true;
		errorMessage.set(null);
		try {
			const response = await handle_save_scorebands({
				problem_id: problem.id,
				session_id: sessionId,
				parent_state_id: stateId,
				preference: { preference_type: 'score_bands.band', cluster_id: selectedBand },
				save: !isSaved,
				name: `Band ${selectedBand}`,
				source_state_id: viewedStateId
			});
			stateId = response.state_id;
			savedBands = response.saved_bands;

			// The current SCORE Bands visualization and zoom history do not change.
		} catch (error) {
			errorMessage.set(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
		}
	}

	async function removeSavedBand(band: ScoreBandsSavedBand) {
		if (busy || !problem || sessionId === null || stateId === null) return;
		busy = true;
		errorMessage.set(null);
		try {
			const response = await handle_save_scorebands({
				problem_id: problem.id,
				session_id: sessionId,
				parent_state_id: stateId,
				preference: { preference_type: 'score_bands.band', cluster_id: band.cluster_id },
				save: false,
				source_state_id: band.source_state_id
			});
			stateId = response.state_id;
			savedBands = response.saved_bands;
		} catch (error) {
			errorMessage.set(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
		}
	}

	function navigateTo(targetStateId: number) {
		if (busy) return;

		const item = history.find((entry) => entry.state_id === targetStateId);

		if (!item) {
			errorMessage.set('History state not found.');
			return;
		}

		viewedStateId = item.state_id;
		showResult(item.result);
	}

	async function createNewScoreBandsSession() {
		if (busy || !problem) return;
		busy = true;
		errorMessage.set(null);
		try {
			const created = await create_session(`SCORE Bands — problem ${problem.id}`);
			if (created?.id == null) throw new Error('Failed to create an interactive session.');
			methodSelection.setSession(created.id, created.info ?? null);
			await initializeProblem(created.id);
		} catch (error) {
			errorMessage.set(error instanceof Error ? error.message : String(error));
		} finally {
			busy = false;
		}
	}
</script>

<svelte:head>
	<title>SCORE Bands | DESDEO</title>
	<meta name="description" content="Individual interactive SCORE Bands evolutionary optimization" />
</svelte:head>

<ScoreBandsLayout
	bottomPanelTitle="Exploration history"
	showBottomPanel={true}
	bind:isLeftSidebarCollapsed={leftCollapsed}
	bind:isRightSidebarCollapsed={rightCollapsed}
	leftSidebarWidth="clamp(16rem, 20vw, 21rem)"
	rightSidebarWidth="clamp(17rem, 23vw, 24rem)"
>
	<!-- LEFT SIDEBAR: USER INPUTS AND ACTIONS -->
	{#snippet leftSidebar()}
		<div class="h-full min-h-0 space-y-5 overflow-y-auto p-4">
			<div>
				<h2 class="text-lg font-semibold">Preferences</h2>
				<p class="text-muted-foreground text-xs">
					Select a band and click the "Explore selected band" button to start exploring it.
				</p>
			</div>

			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Settings</h3>
				<label class="flex items-center justify-between text-sm">
					<span>Run evolutionary optimization</span>

					<input type="checkbox" bind:checked={optimizeNext} disabled={busy} />
				</label>

				{#if optimizeNext}
					<!-- 					<label class="block space-y-1 text-sm">
						<span>Evolutionary algorithm</span>

						<select class="w-full rounded border p-2" bind:value={algorithm} disabled={busy}>
							<option value="nsga3">NSGA-III</option>
							<option value="rvea">RVEA</option>
						</select>
					</label> -->

					<p class="text-muted-foreground text-xs">
						Generate new solutions using the selected band's objective ranges as preferences.
					</p>
				{:else}
					<p class="text-muted-foreground text-xs">
						Reuse solutions from the viewed generation without running evolutionary optimization.
					</p>
				{/if}

				<label class="block space-y-1 text-sm">
					<span>Clustering algorithm</span>

					<select class="w-full rounded border p-2" bind:value={clusteringMethod} disabled={busy}>
						<option value="KMeans">K-Means</option>
						<option value="DBSCAN">DBSCAN</option>
						<option value="GMM">Gaussian Mixture Model</option>
						<option value="DimensionCluster"> Cluster by objective </option>
					</select>
				</label>

				{#if clusteringMethod === 'KMeans' || clusteringMethod === 'DimensionCluster'}
					<label class="block space-y-1 text-sm">
						<span>Number of clusters</span>

						<input
							type="number"
							min="2"
							max="20"
							step="1"
							class="w-full rounded border p-2"
							bind:value={numClusters}
							disabled={busy}
						/>
					</label>
				{/if}

				{#if clusteringMethod === 'DimensionCluster'}
					<label class="block space-y-1 text-sm">
						<span>Objective to cluster by</span>

						<select
							class="w-full rounded border p-2"
							bind:value={clusteringObjective}
							disabled={busy}
						>
							<option value="">Choose an objective</option>

							{#each visual.axisNames as objective}
								<option value={objective}>
									{problem?.objectives.find((obj) => obj.symbol === objective)?.name ?? objective}
								</option>
							{/each}
						</select>
					</label>

					<label class="block space-y-1 text-sm">
						<span>Division method</span>

						<select
							class="w-full rounded border p-2"
							bind:value={dimensionClusteringKind}
							disabled={busy}
						>
							<option value="EqualWidth"> Equal width </option>
							<option value="EqualFrequency"> Equal frequency </option>
						</select>
					</label>
				{/if}

				{#if clusteringMethod === 'GMM'}
					<label class="block space-y-1 text-sm">
						<span>Cluster selection criterion</span>

						<select class="w-full rounded border p-2" bind:value={gmmScoringMethod} disabled={busy}>
							<option value="silhouette">Silhouette</option>
							<option value="BIC">BIC</option>
						</select>
					</label>
				{/if}

				<label class="block space-y-1 text-sm">
					<span>Band interval size: {intervalSize.toFixed(2)}</span>

					<input
						type="range"
						min="0.1"
						max="0.99"
						step="0.01"
						class="w-full"
						bind:value={intervalSize}
						disabled={busy}
					/>
				</label>

				<label class="block space-y-1 text-sm">
					<span>Axis distance formula</span>

					<select class="w-full rounded border p-2" bind:value={distanceFormula} disabled={busy}>
						<option value={1}>Formula 1</option>
						<option value={2}>Formula 2</option>
					</select>
				</label>

				<label class="block space-y-1 text-sm">
					<span>Distance parameter</span>

					<input
						type="number"
						min="0"
						max="1"
						step="0.01"
						class="w-full rounded border p-2"
						bind:value={distanceParameter}
						disabled={busy}
					/>
				</label>

				<label class="flex items-center justify-between gap-2 text-sm">
					<span>Use absolute correlations</span>

					<input type="checkbox" bind:checked={useAbsoluteCorrelations} disabled={busy} />
				</label>
			</section>

			<!-- Exploration actions -->
			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Explore a band</h3>

				{#if selectedBand !== null}
					<p class="text-sm">
						Selected: <strong>Band {selectedBand}</strong>
					</p>
				{:else}
					<p class="text-muted-foreground text-sm">Select a band in the visualization.</p>
				{/if}

				<Button
					class="w-full"
					onclick={iterateSelectedBand}
					disabled={busy || viewedStateId === null}
				>
					{#if busy}
						Processing...
					{:else if optimizeNext}
						{selectedBand === null ? 'Optimize without preferences' : 'Explore selected band'}
					{:else}
						{selectedBand === null ? 'Recluster all solutions' : 'Recluster selected band'}
					{/if}
				</Button>

				<!-- 				<Button
					variant="outline"
					class="w-full"
					onclick={toggleSavedBand}
					disabled={busy || selectedBand === null || stateId === null}
				>
					{isSaved ? 'Remove saved band' : 'Save selected band'}
				</Button> -->
			</section>

			<!-- Actions for previously saved bands -->
			<!-- 			{#if savedBands.length > 0}
				<section class="space-y-2 rounded-lg border p-3">
					<h3 class="font-semibold">Manage saved bands</h3>

					{#each savedBands as band}
						<Button
							variant="outline"
							size="sm"
							class="w-full"
							disabled={busy}
							onclick={() => removeSavedBand(band)}
						>
							Remove {band.name ?? `Band ${band.cluster_id}`}
						</Button>
					{/each}
				</section>
			{/if} -->
		</div>
	{/snippet}

	<!-- TOP CENTER: HEADER -->
	{#snippet explorerTitle()}
		<div class="flex items-center gap-3">
			<span>SCORE Bands Explorer</span>
		</div>
	{/snippet}

	<!-- TOP CENTER: SCORE BANDS VISUALIZATION -->
	{#snippet visualizationArea(_height)}
		<div class="h-full min-h-0 w-full">
			{#if scoreBandsResult}
				<ScoreBands
					data={visual.data}
					axisNames={visual.axisNames}
					{axisLabels}
					axisPositions={visual.axisPositions}
					axisSigns={visual.axisSigns}
					groups={visual.clusterIds}
					{options}
					bands={visual.bands}
					medians={visual.medians}
					scales={visual.scales}
					{clusterVisibility}
					clusterColors={colors}
					{axisOptions}
					axisOrder={[]}
					onBandSelect={(id: number | null) => (selectedBand = id)}
					onAxisSelect={(id: number | null) => (selectedAxis = id)}
					{selectedBand}
					{selectedAxis}
				/>
			{:else}
				<div class="text-muted-foreground flex h-full items-center justify-center text-sm">
					No SCORE Bands result available.
				</div>
			{/if}
		</div>
	{/snippet}

	<!-- BOTTOM CENTER: BRANCHING HISTORY GRAPH -->
	{#snippet bottomPanel()}
		<div class="h-full min-h-0 w-full">
			<ScoreBandsHistoryGraph {history} {viewedStateId} onSelect={navigateTo} />
		</div>
	{/snippet}

	<!-- RIGHT SIDEBAR: READ-ONLY INFORMATION -->
	{#snippet rightSidebar()}
		<div class="h-full min-h-0 space-y-5 overflow-y-auto p-4">
			<div>
				<h2 class="text-lg font-semibold">Details</h2>
				<p class="text-muted-foreground text-xs">Details of the current iteration.</p>
			</div>
			<!-- Selected band ranges -->
			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Selected band information</h3>

				{#if selectedBand !== null && selectedRanges}
					<p class="text-sm font-medium">
						Band {selectedBand} ({scoreBandsResult?.cardinalities?.[String(selectedBand)] ?? 0} solutions)
					</p>
					<p class="text-muted-foreground text-xs">Objective ranges.</p>

					<div class="space-y-2">
						{#each Object.entries(selectedRanges) as [name, bounds]}
							<div class="flex justify-between gap-3 text-sm">
								<span>{objectiveNames[name] ?? name}</span>
								<span class="text-right font-mono text-xs">
									{bounds[0].toPrecision(4)} –
									{bounds[1].toPrecision(4)}
								</span>
							</div>
						{/each}
					</div>
				{:else}
					<p class="text-muted-foreground text-sm">
						Select a band to inspect its objective ranges.
					</p>
				{/if}
			</section>

			<!-- Band visibility and solution counts -->
			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Visible bands</h3>

				<p class="text-muted-foreground text-xs">
					Show or hide bands in the visualization. The number in parentheses indicates how many
					solutions belong to each band.
				</p>

				{#each visual.clusterIds as clusterId}
					<label class="flex cursor-pointer items-center justify-between gap-2 text-sm">
						<span class="flex items-center gap-2">
							<span
								class="h-3 w-3 shrink-0 rounded"
								style={`background-color: ${colors[clusterId] || '#888'}`}
							></span>

							<span>
								Band {clusterId}
								<span class="text-muted-foreground">
									({scoreBandsResult?.cardinalities?.[String(clusterId)] ?? 0})
								</span>
							</span>
						</span>

						<input
							type="checkbox"
							bind:checked={clusterVisibility[clusterId]}
							class="h-4 w-4 cursor-pointer"
						/>
					</label>
				{/each}

				{#if visual.clusterIds.length === 0}
					<p class="text-muted-foreground text-sm">No bands available.</p>
				{/if}
			</section>

			<!-- Visualization controls -->
			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Visualization options</h3>

				<label class="flex items-center justify-between text-sm">
					Show bands
					<input
						type="checkbox"
						bind:checked={showBands}
						disabled={!canToggleBands(showBands, showMedians, showSolutions)}
					/>
				</label>

				<label class="flex items-center justify-between text-sm">
					Show medians
					<input
						type="checkbox"
						bind:checked={showMedians}
						disabled={!canToggleMedians(showBands, showMedians, showSolutions)}
					/>
				</label>

				<label class="flex items-center justify-between gap-2 text-sm">
					<span>Keep objective positions fixed</span>

					<input type="checkbox" bind:checked={lockAxisPositions} />
				</label>

				<p class="text-muted-foreground text-xs">
					When enabled, objectives stay in their initial positions so you can compare different
					iterations.
				</p>
			</section>

			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Objective correlations</h3>

				<p class="text-muted-foreground text-xs">
					Pearson correlation coefficients for the solutions in the viewed iteration.
				</p>

				<SCOREbandsCorrelationMatrix
					dimensions={scoreBandsResult?.ordered_dimensions ?? []}
					matrix={displayCorrelationMatrix}
					descriptiveNames={objectiveNames}
				/>
			</section>

			<!-- Read-only saved bands -->
			<!-- 			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">
					Saved bands ({savedBands.length})
				</h3>

				{#each savedBands as band}
					<div class="space-y-1 rounded border p-2 text-sm">
						<p class="font-medium">
							{band.name ?? `Band ${band.cluster_id}`}
						</p>

						<p class="text-muted-foreground text-xs">
							State {band.source_state_id}
							· Band {band.cluster_id}
						</p>

						{#each Object.entries(band.preferred_ranges) as [name, bounds]}
							<div class="flex justify-between gap-2 text-xs">
								<span>{name}</span>
								<span>
									{bounds[0].toPrecision(4)} –
									{bounds[1].toPrecision(4)}
								</span>
							</div>
						{/each}
					</div>
				{/each}

				{#if savedBands.length === 0}
					<p class="text-muted-foreground text-sm">No saved bands in this session.</p>
				{/if}
			</section> -->
		</div>
	{/snippet}
</ScoreBandsLayout>
