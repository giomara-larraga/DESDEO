<script lang="ts">
	/** Single-user SCORE Bands: persisted state lineage, evolutionary zoom, saved bands. */
	import { onMount } from 'svelte';
	import type { PageData } from './$types';
	import type { ProblemInfo, SCOREBandsResult } from '$lib/gen/endpoints/DESDEOFastAPI';
	import { Button } from '$lib/components/ui/button';
	import ScoreBands from '$lib/components/visualizations/score-bands/score-bands.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage } from '../../../stores/uiState';
	import { create_session } from '../../methods/sessions/handler';
	import ScoreBandsLayout from '$lib/components/custom/method_layout/score-bands-layout.svelte';

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
	let quantile = $state(0.25);
	let numClusters = $state(5);
	let distanceParameter = $state(0.05);
	let initialOptimization = $state(false);
	let algorithm: 'nsga3' | 'rvea' = $state('nsga3');

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
		return {
			axisNames: result.ordered_dimensions,
			clusterIds: Object.keys(result.bands)
				.map(Number)
				.sort((a, b) => a - b),
			axisPositions: result.ordered_dimensions.map((name) => result.axis_positions[name]),
			axisSigns: result.ordered_dimensions.map(() => 1),
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
		result.clustering_algorithm = { name: 'KMeans', n_clusters: numClusters };
		result.distance_parameter = distanceParameter;
		result.interval_size = quantile;
		return result;
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
		if (busy || !problem || sessionId === null || viewedStateId === null || selectedBand === null) {
			return;
		}
		busy = true;
		errorMessage.set(null);
		const opt: ScoreBandsOptimizationOptions = { optimize: true, algorithm };
		try {
			const response = await handle_iterate_scorebands({
				problem_id: problem.id,
				session_id: sessionId,
				parent_state_id: viewedStateId,
				preference: { preference_type: 'score_bands.band', cluster_id: selectedBand },
				optimization_options: opt
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

			<!-- Optimization inputs -->
			<section class="space-y-3 rounded-lg border p-3">
				<h3 class="font-semibold">Optimization settings</h3>

				<label class="block space-y-1 text-sm">
					<span>Evolutionary algorithm</span>

					<select class="w-full rounded border p-2" bind:value={algorithm} disabled={busy}>
						<option value="nsga3">NSGA-III</option>
						<option value="rvea">RVEA</option>
					</select>
				</label>

				<label class="block space-y-1 text-sm">
					<span>Number of initial clusters</span>

					<input
						type="number"
						min="2"
						max="20"
						class="w-full rounded border p-2"
						bind:value={numClusters}
						disabled={busy}
					/>
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
					<span>Optimize initial population</span>

					<input
						type="checkbox"
						bind:checked={initialOptimization}
						disabled={busy || problem?.discrete_representation == null}
					/>
				</label>

				<p class="text-muted-foreground text-xs">
					Initial settings apply when starting a new session. Zoom iterations use the selected
					band's ranges.
				</p>
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
					disabled={busy || selectedBand === null || viewedStateId === null}
				>
					{busy ? 'Processing...' : 'Explore selected band'}
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
								<span>{name}</span>
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
