<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import type { ProblemInfo, Solution } from '$lib/types';
	import {
		ShapHeatmap,
		ShapBarchart,
		ShapReferenceGuide
	} from '$lib/components/visualizations/shap-heatmap';
	import { Combobox } from '$lib/components/ui/combobox';

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		solutions: Array<Solution>;
		perturbedReferencePoints?: Array<{ aspiration_levels?: Record<string, number> }>;
		SHAP_values: Record<string, Record<string, number>> | null;
		isLoading?: boolean;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		solutions,
		perturbedReferencePoints = [],
		SHAP_values,
		isLoading = false,
		ref = null
	}: Props = $props();

	const objectiveOptions = $derived(
		problem.objectives.map((o) => ({ value: o.symbol, label: o.name ?? o.symbol }))
	);

	let selectedObjectiveSymbol = $state('');

	// Set/reset selection when SHAP values or objectives change
	$effect(() => {
		const firstSymbol = problem.objectives[0]?.symbol ?? '';
		if (!selectedObjectiveSymbol || (SHAP_values && !(selectedObjectiveSymbol in SHAP_values))) {
			selectedObjectiveSymbol = SHAP_values ? (Object.keys(SHAP_values)[0] ?? firstSymbol) : firstSymbol;
		}
	});

	const selectedRow = $derived(
		SHAP_values && selectedObjectiveSymbol ? (SHAP_values[selectedObjectiveSymbol] ?? {}) : {}
	);

	const selectedObjectiveName = $derived(
		problem.objectives.find((o) => o.symbol === selectedObjectiveSymbol)?.name ??
			selectedObjectiveSymbol
	);

	type ScenarioDelta = {
		symbol: string;
		name: string;
		delta: number;
		percentDelta: number | null;
		isImprovement: boolean;
	};

	type HypotheticalScenario = {
		key: string;
		improvedSymbol: string;
		improvedName: string;
		improvementMagnitude: number;
		deltas: ScenarioDelta[];
	};

	type ScenarioDiffDisplayMode = 'value' | 'percent';
	let scenarioDiffDisplayMode = $state<ScenarioDiffDisplayMode>('value');

	const baselineObjectiveValues = $derived(solutions[0]?.objective_values ?? null);

	const hypotheticalScenarios = $derived.by(() => {
		if (!baselineObjectiveValues || solutions.length < 2 || perturbedReferencePoints.length === 0) {
			return [] as HypotheticalScenario[];
		}

		const scenarios: HypotheticalScenario[] = [];

		perturbedReferencePoints.forEach((perturbed, perturbedIndex) => {
			const aspirationLevels = perturbed.aspiration_levels ?? {};
			const scenarioSolution = solutions[perturbedIndex + 1];
			if (!scenarioSolution?.objective_values) return;

			let bestImprovedSymbol = '';
			let bestImprovedName = '';
			let bestImprovedMagnitude = 0;

			problem.objectives.forEach((obj, idx) => {
				const basePref = preferenceValues[idx];
				const perturbedPref = aspirationLevels[obj.symbol];
				if (basePref == null || perturbedPref == null) return;

				const diff = perturbedPref - basePref;
				const preferredDirectionShift = obj.maximize ? diff : -diff;
				if (preferredDirectionShift <= 0) return;

				if (preferredDirectionShift > bestImprovedMagnitude) {
					bestImprovedSymbol = obj.symbol;
					bestImprovedName = obj.name ?? obj.symbol;
					bestImprovedMagnitude = preferredDirectionShift;
				}
			});

			if (!bestImprovedSymbol) return;

			const deltas: ScenarioDelta[] = problem.objectives.map((obj) => {
				const baseValRaw = baselineObjectiveValues[obj.symbol];
				const scenarioValRaw = scenarioSolution.objective_values?.[obj.symbol];
				const baseVal = Array.isArray(baseValRaw) ? baseValRaw[0] : baseValRaw;
				const scenarioVal = Array.isArray(scenarioValRaw) ? scenarioValRaw[0] : scenarioValRaw;
				const delta = Number((Number(scenarioVal ?? 0) - Number(baseVal ?? 0)).toFixed(4));
				const objectiveRange =
					obj.ideal == null || obj.nadir == null
						? null
						: Math.abs(Number(obj.ideal) - Number(obj.nadir));
				const percentDelta =
					objectiveRange == null || !Number.isFinite(objectiveRange) || objectiveRange === 0
						? null
						: Number(((delta / objectiveRange) * 100).toFixed(2));
				const isImprovement = obj.maximize ? delta > 0 : delta < 0;

				return {
					symbol: obj.symbol,
					name: obj.name ?? obj.symbol,
					delta,
					percentDelta,
					isImprovement
				};
			});

			scenarios.push({
				key: `${bestImprovedSymbol}-${perturbedIndex}`,
				improvedSymbol: bestImprovedSymbol,
				improvedName: bestImprovedName,
				improvementMagnitude: bestImprovedMagnitude,
				deltas
			});
		});

		return scenarios;
	});

	const maxAbsScenarioDelta = $derived.by(() => {
		const allAbs = hypotheticalScenarios.flatMap((s) => s.deltas.map((d) => Math.abs(d.delta)));
		return Math.max(1, ...allAbs);
	});

	const maxAbsScenarioPercent = $derived.by(() => {
		const allAbs = hypotheticalScenarios.flatMap((s) =>
			s.deltas.map((d) => Math.abs(d.percentDelta ?? 0))
		);
		return Math.max(1, ...allAbs);
	});

	function formatSigned(value: number): string {
		const fixed = Math.abs(value).toFixed(3);
		if (value > 0) return `+${fixed}`;
		if (value < 0) return `-${fixed}`;
		return '0.000';
	}

	function formatSignedPercent(value: number | null): string {
		if (value == null || !Number.isFinite(value)) {
			return 'n/a';
		}

		const fixed = Math.abs(value).toFixed(2);
		if (value > 0) return `+${fixed}%`;
		if (value < 0) return `-${fixed}%`;
		return '0.00%';
	}
</script>

<Sidebar.Root side="right" class="fixed top-12 right-0 h-[calc(100vh-3rem)]">
	<Sidebar.Header>
		<span class="text-sm font-semibold">Explanations</span>
	</Sidebar.Header>
	<Sidebar.Content class="px-4">
		<Tooltip.Provider>
			{#if isLoading}
				<div class="py-8 text-center text-sm text-gray-500">Computing explanations…</div>
			{:else if solutions.length === 0 || SHAP_values === null || Object.keys(SHAP_values).length === 0}
				<div class="py-8 text-center text-sm text-gray-500">No solution details available yet.</div>
			{:else}
				<div class="space-y-5">
					<div class="rounded-md border border-gray-200 bg-gray-50 px-3 py-2 text-xs text-gray-600">
						<div class="flex items-start justify-between gap-2">
							<p>
								Use the selected <strong>outcome</strong> to decide which <strong>aspiration</strong>
								to tighten or relax next.
							</p>
							<Tooltip.Root>
								<Tooltip.Trigger class="mt-0.5 inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-72">
									<p>
										An <strong>outcome</strong> is a result you care about. An <strong>aspiration</strong>
										is the level you ask for.
									</p>
									<p class="mt-1">
										These charts show how changing one aspiration is likely to affect each outcome.
										To set the next reference point, start from the outcome you want to improve,
										then look for the most helpful aspiration. If an aspiration is marked as making
										the outcome harder to improve, it may be too strict and may need to be relaxed.
									</p>
								</Tooltip.Content>
							</Tooltip.Root>
						</div>
					</div>

					<!-- Objective selector -->
					<div>
						<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
							<span>Focus outcome</span>
							<Tooltip.Root>
								<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-56">
									Choose the outcome you want to inspect. The charts below update for that outcome.
								</Tooltip.Content>
							</Tooltip.Root>
						</div>
						<Combobox
							options={objectiveOptions}
							defaultSelected={selectedObjectiveSymbol}
							onChange={(e) => (selectedObjectiveSymbol = e.value)}
						/>
					</div>

					<Tabs.Root value="influences" class="w-full">
						<Tabs.List class="grid w-full grid-cols-3">
							<Tabs.Trigger value="influences">Influences</Tabs.Trigger>
							<Tabs.Trigger value="overview">Overview</Tabs.Trigger>
							<Tabs.Trigger value="scenarios">Scenarios</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="influences" class="mt-3 w-full">
							<div>
								<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
									<span>Main influences</span>
									<Tooltip.Root>
										<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
											<InfoIcon class="h-3.5 w-3.5" />
										</Tooltip.Trigger>
										<Tooltip.Content sideOffset={6} class="max-w-64">
											Shows how each aspiration affects <strong>{selectedObjectiveName}</strong>. Red pushes the outcome up, blue pushes it down, black marks its own aspiration, and ★ marks the most helpful aspiration.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>
								<p class="mb-1 text-xs text-gray-500">For <em>{selectedObjectiveName}</em></p>
								<ShapBarchart shapRow={selectedRow} selectedOutputSymbol={selectedObjectiveSymbol} {problem} />
							</div>
						</Tabs.Content>

						<Tabs.Content value="overview" class="mt-3 w-full">
							<div>
								<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
									<span>Overview</span>
									<Tooltip.Root>
										<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
											<InfoIcon class="h-3.5 w-3.5" />
										</Tooltip.Trigger>
										<Tooltip.Content sideOffset={6} class="max-w-64">
											Rows are outcomes and columns are aspirations. Each cell shows how changing an aspiration affects an outcome. Stronger color means stronger influence.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>
								<ShapHeatmap shapValues={SHAP_values} {problem} />
							</div>
						</Tabs.Content>

						<Tabs.Content value="scenarios" class="mt-3 w-full">
							<div class="space-y-3">
								<div class="mb-1 flex items-center gap-1 text-xs font-medium text-gray-600">
									<span>Hypothetical scenarios</span>
									<Tooltip.Root>
										<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
											<InfoIcon class="h-3.5 w-3.5" />
										</Tooltip.Trigger>
										<Tooltip.Content sideOffset={6} class="max-w-72">
											Each card summarizes: if a perturbed reference point improves one aspiration,
											what objective changes were observed in the corresponding perturbed solution.
										</Tooltip.Content>
									</Tooltip.Root>
								</div>

										<div class="flex items-center gap-1">
											<button
												type="button"
												class={`rounded px-2 py-0.5 text-xs ${scenarioDiffDisplayMode === 'value' ? 'bg-gray-200 font-medium text-gray-800' : 'bg-gray-100 text-gray-600'}`}
												onclick={() => (scenarioDiffDisplayMode = 'value')}
											>
												Value
											</button>
											<button
												type="button"
												class={`rounded px-2 py-0.5 text-xs ${scenarioDiffDisplayMode === 'percent' ? 'bg-gray-200 font-medium text-gray-800' : 'bg-gray-100 text-gray-600'}`}
												onclick={() => (scenarioDiffDisplayMode = 'percent')}
											>
												Percent
											</button>
										</div>

								{#if hypotheticalScenarios.length === 0}
									<div class="rounded border bg-gray-50 p-3 text-xs text-gray-500">
										No perturbed scenarios available yet.
									</div>
								{:else}
									{#each hypotheticalScenarios as scenario}
										<div class="rounded-md border border-gray-200 bg-white p-3">
											<div class="mb-2 text-xs text-gray-700">
												If preference improves <strong>{scenario.improvedName}</strong>
												(<span class="font-mono">{formatSigned(scenario.improvementMagnitude)}</span>),
												then observed effects are:
											</div>

											<div class="space-y-1.5">
												{#each scenario.deltas as delta}
													<div class="grid grid-cols-[64px_1fr_62px] items-center gap-2 text-xs">
														<div class="font-medium text-gray-700" title={delta.symbol}>{delta.name}</div>
														<div class="h-2 overflow-hidden rounded bg-gray-100">
															<div
																class={`h-full ${delta.isImprovement ? 'bg-emerald-500' : 'bg-rose-500'}`}
																style={`width: ${scenarioDiffDisplayMode === 'percent'
																	? (Math.abs(delta.percentDelta ?? 0) / maxAbsScenarioPercent) * 100
																	: (Math.abs(delta.delta) / maxAbsScenarioDelta) * 100}%`}
															></div>
														</div>
														<div class={`text-right font-mono ${delta.isImprovement ? 'text-emerald-700' : 'text-rose-700'}`}>
															{scenarioDiffDisplayMode === 'percent'
																? formatSignedPercent(delta.percentDelta)
																: formatSigned(delta.delta)}
														</div>
													</div>
												{/each}
											</div>
										</div>
									{/each}
								{/if}
							</div>
						</Tabs.Content>
					</Tabs.Root>
				</div>
			{/if}
		</Tooltip.Provider>
	</Sidebar.Content>
	<Sidebar.Rail />
</Sidebar.Root>
