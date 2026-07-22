<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	//import * as Tabs from '$lib/components/ui/tabs';
	import * as Accordion from '$lib/components/ui/accordion';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import type { ProblemInfo, Solution } from '$lib/types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';
	import {COLOR_PALETTE} from '$lib/components/visualizations/utils/colors';
	import WhyTab from './WhyTab.svelte';
	import HowTab from './HowTab.svelte';
	import CompareTab from './CompareTab.svelte';
	import AccordionItem from '$lib/components/ui/accordion/accordion-item.svelte';

	interface RXIMOResultEntry {
		rival_index: number;
		rival_symbol: string;
		explanation: string;
		suggestion: string;
		explanation_index: number;
		best_effect: number;
		worst_effect: number;
	}

	interface Props {
		problem: ProblemInfo;
		preferenceValues: number[];
		scenarioReferenceValues?: number[];
		solutions: Array<Solution>;
		perturbedReferencePoints?: Array<{ aspiration_levels?: Record<string, number> }>;
		SHAP_values: Record<string, Record<string, number>> | null;
		SHAP_baseline: Record<string, number>;
		// R-XIMO results from the API, keyed by output objective symbol. When
		// supplied, this drives the rival selection and suggestion text instead of
		// the local JS heuristic. Each value carries `find_rival`'s output for
		// that target objective (rival, case 1-9, explanation, suggestion).
		rximo_results?: Record<string, RXIMOResultEntry> | null;
		onApplyScenarioPreferences?: (values: number[]) => void;
		isLoading?: boolean;
		ref?: HTMLElement | null;
	}

	let {
		problem,
		preferenceValues,
		scenarioReferenceValues = preferenceValues,
		solutions,
		perturbedReferencePoints = [],
		SHAP_values,
		SHAP_baseline,
		rximo_results = null,
		onApplyScenarioPreferences,
		isLoading = false,
		ref = null
	}: Props = $props();

	// Look up the API-provided R-XIMO result for the currently selected target.
	const apiRXIMOResult = $derived.by<RXIMOResultEntry | null>(() => {
		if (!rximo_results) return null;
		return (
			rximo_results[selectedObjectiveSymbol] ??
			rximo_results[`z_${selectedObjectiveSymbol}`] ??
			null
		);
	});

	type ExplanationTab = 'why' | 'how' | 'compare';
	let explanationTab = $state<ExplanationTab>('why');
	let displayAccuracy = $derived.by(() => getDisplayAccuracy(problem));


	const objectiveOptions = $derived(
		problem.objectives.map((o) => ({ value: o.symbol, label: o.name ?? o.symbol }))
	);

	const achievedValueNumber = $derived.by(() => {
		const raw = solutions[0]?.objective_values?.[selectedObjectiveSymbol];
		const value = Array.isArray(raw) ? Number(raw[0]) : Number(raw);
		return Number.isFinite(value) ? value : 0;
	});

	let selectedObjectiveSymbol = $state('');

	$effect(() => {
		const firstSymbol = problem.objectives[0]?.symbol ?? '';
		const shapOutputs = SHAP_values ? Object.keys(SHAP_values).map(normalizeObjectiveSymbol) : [];

		if (!selectedObjectiveSymbol || (SHAP_values && !shapOutputs.includes(selectedObjectiveSymbol))) {
			selectedObjectiveSymbol = firstSymbol;
		}
	});

	function normalizeObjectiveSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function isOwnAspiration(inputSymbol: string, outputSymbol: string): boolean {
		return normalizeObjectiveSymbol(inputSymbol) === normalizeObjectiveSymbol(outputSymbol);
	}

	function displayAspirationName(symbol: string): string {
		const normalized = normalizeObjectiveSymbol(symbol);
		const obj = problem.objectives.find((o) => o.symbol === normalized);
		return obj?.name ?? normalized;
	}

	function findShapRow(
		values: Record<string, Record<string, number>> | null,
		outputSymbol: string
	): Record<string, number> {
		if (!values) return {};
		return (
			values[outputSymbol] ??
			values[`z_${outputSymbol}`] ??
			Object.entries(values).find(([key]) => normalizeObjectiveSymbol(key) === outputSymbol)?.[1] ??
			{}
		);
	}

	const selectedRow = $derived(findShapRow(SHAP_values, selectedObjectiveSymbol));

	const selectedObjective = $derived(
		problem.objectives.find((o) => o.symbol === selectedObjectiveSymbol)
	);

	const selectedObjectiveName = $derived(selectedObjective?.name ?? selectedObjectiveSymbol);
	const selectedObjectiveIndex = $derived(
		problem.objectives.findIndex((o) => o.symbol === selectedObjectiveSymbol)
	);
	const selectedObjectiveDigits = $derived.by(() => {
		if (selectedObjectiveIndex < 0) return 3;
		const digits = displayAccuracy[selectedObjectiveIndex];
		return Number.isInteger(digits) ? digits : 3;
	});

	type InfluenceRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

	const selectedSolutionValue = $derived.by(() => {
		const raw = solutions[0]?.objective_values?.[selectedObjectiveSymbol];
		return raw;
	});

	const selectedSHAPBaseline = $derived.by(() => {
		const raw = SHAP_baseline?.[selectedObjectiveSymbol];
		return raw;
	});

	const influenceRows = $derived.by(() => {
		if (!selectedRow) return [] as InfluenceRow[];

		const selectedIsMax = selectedObjective?.maximize ?? true;

		return Object.entries(selectedRow)
			.map(([symbol, raw]) => {
				const rawValue = Number(raw ?? 0);
				const helpScore = selectedIsMax ? rawValue : -rawValue;

				return {
					symbol,
					name: displayAspirationName(symbol),
					rawValue,
					helpScore,
					isOwn: isOwnAspiration(symbol, selectedObjectiveSymbol),
					isHelpful: helpScore > 0
				};
			})
			.sort((a, b) => Math.abs(b.helpScore) - Math.abs(a.helpScore));
	});

	const mainTradeoff = $derived(influenceRows.find((r) => r.helpScore < 0 && !r.isOwn));
	const mainSynergy = $derived(influenceRows.find((r) => r.helpScore > 0 && !r.isOwn));
	const ownInfluence = $derived(influenceRows.find((r) => r.isOwn));

	// Keep these aliases only if the rest of the file still uses the old names.
	const mainHurter = $derived(mainTradeoff);
	const mainHelper = $derived(mainSynergy);

	const rival = $derived.by(() => {
		// Prefer the rival picked by the backend's find_rival call, which runs
		// the full R-XIMO Algorithm 1 on the SHAP matrix and is the source of
		// truth for the suggestion. The matching influence row (used for the
		// "(score)" badge in the UI) is found by symbol.
		if (apiRXIMOResult) {
			const apiRow = influenceRows.find(
				(r) => normalizeObjectiveSymbol(r.symbol) === apiRXIMOResult.rival_symbol
			);
			if (apiRow) return apiRow;
		}

		// Fallback: simplified heuristic for when the API didn't return R-XIMO
		// results (e.g., older backend or feature toggled off).
		const negativeNonOwn = influenceRows.find((r) => r.helpScore < 0 && !r.isOwn);
		if (negativeNonOwn) return negativeNonOwn;

		return influenceRows
			.filter((r) => !r.isOwn)
			.sort((a, b) => a.helpScore - b.helpScore)[0];
	});

	// Misitano et al. (2022) found DMs preferred suggestions over explanations,
	// so the explanation text is exposed only on demand via a disclosure.
	const explanationText = $derived(apiRXIMOResult?.explanation ?? null);

	type ScenarioDelta = {
		symbol: string;
		name: string;
		delta: number;
		percentDelta: number | null;
		isImprovement: boolean;
	};

	type HypotheticalScenario = {
		key: string;
		impairedSymbol: string;
		impairedName: string;
		impairmentMagnitude: number;
		impairedTargetValue: number;
		scenarioPreferenceValues: number[];
		deltas: ScenarioDelta[];
	};

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

			let bestImpairedSymbol = '';
			let bestImpairedName = '';
			let bestImpairedMagnitude = 0;
			let bestImpairedTargetValue = 0;

			problem.objectives.forEach((obj, idx) => {
				const basePref = scenarioReferenceValues[idx];
				const perturbedPref = aspirationLevels[obj.symbol] ?? aspirationLevels[`z_${obj.symbol}`];
				if (basePref == null || perturbedPref == null) return;

				const diff = perturbedPref - basePref;
				// Nadir direction: minimization nadir is larger (+diff), maximization nadir is smaller (-diff)
				const nadirDirectionShift = obj.maximize ? -diff : diff;
				if (nadirDirectionShift <= 0) return;

				if (nadirDirectionShift > bestImpairedMagnitude) {
					bestImpairedSymbol = obj.symbol;
					bestImpairedName = obj.name ?? obj.symbol;
					bestImpairedMagnitude = nadirDirectionShift;
					bestImpairedTargetValue = Number(perturbedPref);
				}
			});

			if (!bestImpairedSymbol) return;

			const scenarioPreferenceValues = problem.objectives.map((obj, idx) => {
				const perturbedPref = aspirationLevels[obj.symbol] ?? aspirationLevels[`z_${obj.symbol}`];
				const fallback = scenarioReferenceValues[idx] ?? preferenceValues[idx] ?? 0;
				return Number(perturbedPref ?? fallback);
			});

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
				key: `${bestImpairedSymbol}-${perturbedIndex}`,
				impairedSymbol: bestImpairedSymbol,
				impairedName: bestImpairedName,
				impairmentMagnitude: bestImpairedMagnitude,
				impairedTargetValue: bestImpairedTargetValue,
				scenarioPreferenceValues,
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

	const maxAbsInfluence = $derived.by(() => {
		return Math.max(0.0001, ...influenceRows.map((r) => Math.abs(r.helpScore)));
	});

	function objectiveColor(index: number): string {
	return COLOR_PALETTE[index % COLOR_PALETTE.length];
}

function getObjectiveAchievedValue(symbol: string): number | null {
	const raw = solutions[0]?.objective_values?.[symbol];
	const value = Array.isArray(raw) ? Number(raw[0]) : Number(raw);
	return Number.isFinite(value) ? value : null;
}

function objectiveMeetsDesired(index: number): boolean | null {
	const objective = problem.objectives[index];
	const desired = Number(preferenceValues[index]);
	const achieved = getObjectiveAchievedValue(objective.symbol);

	if (!Number.isFinite(desired) || achieved == null) return null;

	const tolerance = 0.01;

	return objective.maximize
		? achieved >= desired - tolerance
		: achieved <= desired + tolerance;
}

const objectiveStatuses = $derived.by(() =>
	problem.objectives.map((objective, index) => ({
		symbol: objective.symbol,
		name: objective.name ?? objective.symbol,
		color: objectiveColor(index),
		met: objectiveMeetsDesired(index),
		isSelected: objective.symbol === selectedObjectiveSymbol
	}))
);
</script>

<Sidebar.Root 
	side="right" 
	collapsible="none"
	class="fixed top-12 right-0 h-[calc(100vh-3rem)] w-[25rem]" 
	bind:ref
>
	<Sidebar.Header>
		<div>
			<span class="text-sm font-semibold">Explanations</span>
			<Tooltip.Root>
				<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
					<InfoIcon class="h-3.5 w-3.5" />
				</Tooltip.Trigger>
				<Tooltip.Content sideOffset={6} class="max-w-84">
			
					<strong>Explanation tabs</strong>
					<ul>
						<li><strong>Understand:</strong> Why was this value obtained?</li>
						<li><strong>Explore:</strong> What trade-offs are possible?</li>
						<li><strong>Details:</strong> What relationships and contributions explain it?</li>
					</ul>
				
				</Tooltip.Content>
			</Tooltip.Root>
		</div>
	</Sidebar.Header>

	<Sidebar.Content class="px-4">
		<Tooltip.Provider>
			{#if isLoading}
				<div class="py-8 text-center text-sm text-gray-500">Computing explanations…</div>
			{:else if solutions.length === 0 || SHAP_values === null || Object.keys(SHAP_values).length === 0}
				<div class="py-8 text-center text-sm text-gray-500">No solution details available yet.</div>
			{:else}
				<div class="space-y-4">
					<div class="flex items-center gap-3">
					<div class="rounded-md border border-gray-200 bg-white p-3">
	<div class="mb-2 flex items-center justify-between gap-2">
		<div>
			<div class="text-sm font-semibold text-gray-900">
				Objectives
			</div>

			<div class="text-xs text-gray-500">
				Click an objective to view its explanation.
			</div>
		</div>
	</div>

	<div class="flex flex-wrap gap-1.5">
		{#each objectiveStatuses as objective}
			<Tooltip.Root>
				<Tooltip.Trigger asChild>
					<button
						type="button"
						class={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs transition
							${objective.isSelected
								? 'border-blue-300 bg-blue-50 font-semibold text-blue-900 ring-1 ring-blue-200'
								: 'border-gray-200 bg-gray-50 text-gray-700 hover:bg-gray-100'}`}
						onclick={() => (selectedObjectiveSymbol = objective.symbol)}
						aria-label={`Explain ${objective.name}`}
					>
						<span
							class="h-2.5 w-2.5 rounded-full"
							style={`background-color: ${objective.color}`}
						></span>
						<span class="truncate">{objective.name}</span>

						<span>
							{objective.met === true ? '✓' : objective.met === false ? '⚠' : '?'}
						</span>
					</button>
				</Tooltip.Trigger>

				<Tooltip.Content sideOffset={6} class="max-w-64 text-sm">
					<strong>{objective.name}</strong>
					<br />

					{#if objective.met === true}
						Achieved value meets or exceeds the desired value.
					{:else if objective.met === false}
						Achieved value does not meet the desired value.
					{:else}
						Status unavailable.
					{/if}

					<br />
					Click to explain this objective.
				</Tooltip.Content>
			</Tooltip.Root>
		{/each}
	</div>
	<div class="mt-1 flex flex-wrap items-center gap-3 text-[11px] text-gray-500 place-self-center">
		<span class="flex items-center gap-1">
			<span class="font-semibold text-green-600">✓</span>
			Meets desired
		</span>

		<span class="flex items-center gap-1">
			<span class="font-semibold text-amber-600">⚠</span>
			Below desired
		</span>
	</div>
</div>
<!-- 						<div class="flex shrink-0 items-center gap-1 text-sm font-medium text-gray-600">
							<span>Objective to explain</span>
							<Tooltip.Root>
								<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-56">
									Select the objective whose achieved value you want to analyze. The explanations below will focus on this objective.
								</Tooltip.Content>
							</Tooltip.Root>
						</div>

						<div class="min-w-0 max-w-xs">
							<Combobox
								options={objectiveOptions}
								defaultSelected={selectedObjectiveSymbol}
								onChange={(e) => (selectedObjectiveSymbol = e.value)}
							/>
						</div> -->
					</div>

					<Accordion.Root type="single" value="why" class="w-full">
					    <Accordion.Item value="why">
						<Accordion.Trigger class="w-full text-left">
							<div class="flex items-center justify-between gap-2">
								<span class="text-sm font-semibold">Why does {selectedObjectiveName} have this value?</span>
								<InfoIcon class="h-3.5 w-3.5 text-gray-400" />
							</div>
						</Accordion.Trigger>
						
						<Accordion.Content class="mt-3 w-full">
								<WhyTab
									{selectedObjectiveName}
									{preferenceValues}
									selectedSolution={solutions[0]}
									{selectedObjectiveIndex}
									{achievedValueNumber}
									{selectedObjectiveDigits}
									{mainTradeoff}
									{mainSynergy}
									selectedRow={selectedRow}
									{selectedObjectiveSymbol}
									{problem}
									selectedSHAPBaseline={selectedSHAPBaseline}
									selectedSolutionValue={selectedSolutionValue}
									{explanationText}
									onExploreClick={() => (explanationTab = 'how')}
								/>
							</Accordion.Content>
						</Accordion.Item>
						<AccordionItem value="how" class="mt-3 w-full">
							<Accordion.Trigger class="w-full text-left">
								<div class="flex items-center justify-between gap-2">
									<span class="text-sm font-semibold">How can I improve {selectedObjectiveName}?</span>
									<InfoIcon class="h-3.5 w-3.5 text-gray-400" />
								</div>
							</Accordion.Trigger>
						<Accordion.Content class="mt-3 w-full">
								<HowTab
									{selectedObjectiveName}
									selectedObjectiveSymbol={selectedObjectiveSymbol}
									mainHurter={mainHurter}
									ownInfluence={ownInfluence}
									{hypotheticalScenarios}
									{problem}
									{maxAbsScenarioDelta}
									{maxAbsScenarioPercent}
									{onApplyScenarioPreferences}
								/>
						</Accordion.Content>
						</AccordionItem>
						<AccordionItem value="compare" class="mt-3 w-full">
							<Accordion.Trigger class="w-full text-left">
								<div class="flex items-center justify-between gap-2">
									<span class="text-sm font-semibold">How was this explanation generated?</span>
									<InfoIcon class="h-3.5 w-3.5 text-gray-400" />
								</div>
							</Accordion.Trigger>

						<Accordion.Content class="mt-3 w-full">
								<CompareTab
									{selectedObjectiveName}
									{selectedObjectiveSymbol}
									selectedRow={selectedRow}
									{problem}
									{preferenceValues}
									baselineObjectiveValues={baselineObjectiveValues}
									SHAP_values={SHAP_values}
									explanationText={explanationText}
									selectedSHAPBaseline={selectedSHAPBaseline}
									selectedSolutionValue={selectedSolutionValue}
								/>
							</Accordion.Content>
						</AccordionItem>
						
					</Accordion.Root>
				</div>
			{/if}
		</Tooltip.Provider>
	</Sidebar.Content>


</Sidebar.Root>
