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
				(band) => band.source_state_id === currentGenerationId && band.cluster_id === selectedBand
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

<div class="container mx-auto space-y-4 p-4">
	{#if $errorMessage}
		<Alert title="SCORE Bands error" message={$errorMessage} variant="destructive" />
	{/if}

	<header class="flex flex-wrap items-start justify-between gap-3">
		<div>
			<h1 class="text-2xl font-semibold">SCORE Bands</h1>
			<p class="text-muted-foreground text-sm">
				Select a band to guide a new evolutionary search. Saved bands and all iterations are stored
				in your session.
			</p>
			{#if sessionId !== null}
				<p class="text-muted-foreground text-xs">
					Session {sessionId}
					· Viewing state {viewedStateId ?? '—'}
					· Latest saved state {stateId ?? '—'}
					· {history.length} generations
				</p>
			{/if}
		</div>
		<Button variant="outline" onclick={createNewScoreBandsSession} disabled={!problem || busy}>
			New SCORE Bands session
		</Button>
	</header>

	{#if loading}
		<div class="py-20 text-center">Loading SCORE Bands...</div>
	{:else if !problem}
		<p>Select a problem from the Methods page.</p>
	{:else}
		<div class="grid grid-cols-1 gap-4 xl:grid-cols-[280px_minmax(0,1fr)_340px]">
			<aside class="space-y-4">
				<section class="space-y-3 rounded-lg border p-4">
					<h2 class="font-semibold">Visualization</h2>
					<label class="flex items-center justify-between gap-2 text-sm">
						Show bands
						<input
							type="checkbox"
							bind:checked={showBands}
							disabled={!canToggleBands(showBands, showMedians, showSolutions)}
						/>
					</label>
					<label class="flex items-center justify-between gap-2 text-sm">
						Show medians
						<input
							type="checkbox"
							bind:checked={showMedians}
							disabled={!canToggleMedians(showBands, showMedians, showSolutions)}
						/>
					</label>
					<label
						class="text-muted-foreground flex items-center justify-between gap-2 text-sm"
						title="Individual solutions require a separate visualization"
					>
						Show individual solutions
						<input type="checkbox" bind:checked={showSolutions} disabled />
					</label>
					<div class="text-muted-foreground text-xs">
						Bands are recalculated from a new evolutionary population at every zoom.
					</div>
				</section>

				<section class="space-y-3 rounded-lg border p-4">
					<h2 class="font-semibold">Optimization setup</h2>
					<label class="block text-sm">
						Evolutionary algorithm
						<select class="mt-1 w-full rounded border p-2" bind:value={algorithm} disabled={busy}>
							<option value="nsga3">NSGA-III</option>
							<option value="rvea">RVEA</option>
						</select>
					</label>
					<label class="flex items-center justify-between gap-2 text-sm">
						Optimize initial population
						<input
							type="checkbox"
							bind:checked={initialOptimization}
							disabled={busy || problem?.discrete_representation == null}
						/>
					</label>
					<label class="block text-sm">
						Number of initial clusters
						<input
							class="mt-1 w-full rounded border p-2"
							type="number"
							min="2"
							max="20"
							bind:value={numClusters}
							disabled={busy}
						/>
					</label>
					<label class="block text-sm">
						Distance parameter
						<input
							class="mt-1 w-full rounded border p-2"
							type="number"
							step="0.01"
							min="0"
							max="1"
							bind:value={distanceParameter}
							disabled={busy}
						/>
					</label>
					{#if problem?.discrete_representation == null}
						<p class="text-muted-foreground text-xs">
							No precomputed discrete front is available. Initialization automatically runs {algorithm.toUpperCase()}
							without preferences to approximate the Pareto front. Selecting a band later guides the next
							optimization run.
						</p>
					{:else}
						<p class="text-muted-foreground text-xs">
							Initialization uses the existing discrete solutions unless you enable evolutionary
							optimization.
						</p>
					{/if}
					<p class="text-muted-foreground text-xs">
						Initial options apply when creating a new session; resume always uses stored states.
					</p>
				</section>

				<section class="space-y-3 rounded-lg border p-4">
					<h2 class="font-semibold">Visible bands</h2>
					{#each visual.clusterIds as clusterId}
						<label class="flex items-center justify-between gap-2 text-sm">
							<span class="flex items-center gap-2">
								<span
									class="inline-block h-3 w-3 rounded"
									style={`background-color:${colors[clusterId] || '#888'}`}
								></span>
								Band {clusterId}
							</span>
							<input type="checkbox" bind:checked={clusterVisibility[clusterId]} />
						</label>
					{/each}
					{#if !visual.clusterIds.length}<p class="text-muted-foreground text-sm">
							No bands generated.
						</p>{/if}
				</section>

				<section class="space-y-2 rounded-lg border p-4">
					<h2 class="font-semibold">Exploration history</h2>

					<p class="text-muted-foreground text-xs">
						Select any generation to view it. Exploring one of its bands creates a new branch.
					</p>

					{#each historyWithDepth as item (item.state_id)}
						<button
							class={`block rounded border p-2 text-left text-sm
                ${
									viewedStateId === item.state_id
										? 'border-primary bg-primary/10 font-medium'
										: 'hover:bg-muted'
								}`}
							style={`margin-left: ${item.depth * 16}px;
                width: calc(100% - ${item.depth * 16}px);`}
							disabled={busy}
							onclick={() => navigateTo(item.state_id)}
						>
							{#if item.depth > 0}
								↳
							{/if}

							{#if item.action === 'initialize'}
								Initial bands
							{:else}
								Explored band {item.selected_cluster_id}
							{/if}

							<span class="text-muted-foreground text-xs">
								(State {item.state_id})
							</span>

							{#if viewedStateId === item.state_id}
								<span class="text-xs font-semibold"> · Viewing </span>
							{/if}
						</button>
					{/each}

					{#if history.length > 1}
						<div class="flex flex-wrap gap-2 pt-2">
							<Button
								variant="outline"
								disabled={busy || parentViewedStateId === null}
								onclick={() => {
									if (parentViewedStateId !== null) {
										navigateTo(parentViewedStateId);
									}
								}}
							>
								Back
							</Button>

							<Button
								variant="outline"
								disabled={busy || initialGenerationStateId === null}
								onclick={() => {
									if (initialGenerationStateId !== null) {
										navigateTo(initialGenerationStateId);
									}
								}}
							>
								All bands
							</Button>
						</div>
					{/if}
				</section>
			</aside>

			<main class="min-w-0 space-y-4">
				<div class="rounded-lg border p-3">
					{#if scoreBandsResult}
						<div class="h-[520px]">
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
						</div>
					{:else}
						<p class="py-20 text-center text-sm">
							No SCORE Bands result yet. Check the error above or create a new session.
						</p>
					{/if}
				</div>
			</main>

			<aside class="space-y-4">
				<section class="space-y-3 rounded-lg border p-4">
					<h2 class="font-semibold">Selected band</h2>
					{#if selectedBand !== null}
						<p class="text-sm font-medium">Band {selectedBand}</p>
						<p class="text-muted-foreground text-xs">
							Objective preferences for the next evolutionary iteration:
						</p>
						{#if selectedRanges}
							<div class="space-y-1">
								{#each Object.entries(selectedRanges) as [name, bounds]}
									<div class="flex justify-between gap-3 text-xs">
										<span>{name}</span>
										<span class="text-right"
											>{bounds[0].toPrecision(4)} – {bounds[1].toPrecision(4)}</span
										>
									</div>
								{/each}
							</div>
						{/if}
						<Button class="w-full" onclick={iterateSelectedBand} disabled={busy}>
							{busy ? 'Working...' : 'Explore band with evolutionary optimization'}
						</Button>
						<Button class="w-full" variant="outline" onclick={toggleSavedBand} disabled={busy}>
							{isSaved ? 'Remove saved band' : 'Save band'}
						</Button>
					{:else}
						<p class="text-muted-foreground text-sm">
							Click a band in the visualization to see its objective ranges and explore it.
						</p>
					{/if}
				</section>

				<section class="space-y-3 rounded-lg border p-4">
					<h2 class="font-semibold">Saved bands ({savedBands.length})</h2>
					{#each savedBands as band}
						<div class="rounded border p-2 text-sm">
							<div class="font-medium">{band.name ?? `Band ${band.cluster_id}`}</div>
							<div class="text-muted-foreground text-xs">
								From state {band.source_state_id}, band {band.cluster_id}
							</div>
							<button
								class="mt-1 text-xs underline disabled:opacity-50"
								disabled={busy}
								onclick={() => removeSavedBand(band)}>Remove saved band</button
							>
							<div class="mt-1 space-y-1">
								{#each Object.entries(band.preferred_ranges) as [symbol, interval]}
									<div class="flex justify-between gap-2 text-xs">
										<span>{symbol}</span><span
											>{interval[0].toPrecision(4)} – {interval[1].toPrecision(4)}</span
										>
									</div>
								{/each}
							</div>
						</div>
					{/each}
					{#if savedBands.length === 0}
						<p class="text-muted-foreground text-sm">No bands saved in this session.</p>
					{/if}
				</section>
			</aside>
		</div>
	{/if}
</div>
