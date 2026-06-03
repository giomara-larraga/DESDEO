<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import * as Tabs from '$lib/components/ui/tabs';
	import InfoIcon from '@lucide/svelte/icons/info';
	import * as Tooltip from '$lib/components/ui/tooltip/index.js';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { ProblemInfo, Solution } from '$lib/types';
	import { getDisplayAccuracy, formatNumber } from '$lib/helpers';

	import { ShapHeatmap, ShapBarchart } from '$lib/components/visualizations/shap-heatmap';
	import { Combobox } from '$lib/components/ui/combobox';
	import ShapWaterfall from '$lib/components/visualizations/shap-waterfall/ShapWaterfall.svelte';
	import WhatIfCaseNetwork from '$lib/components/visualizations/what-if-case-network/WhatIfCaseNetwork.svelte';
	import ShapCaseRelationshipNetwork from '$lib/components/visualizations/shap-case-relationship-network/ShapCaseRelationshipNetwork.svelte';

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

	function formatValue(value: unknown): string {
		const num = Array.isArray(value) ? Number(value[0]) : Number(value);
		if (!Number.isFinite(num)) return '—';
		return num.toFixed(2);
	}


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

	const mainHelper = $derived(influenceRows.find((r) => r.helpScore > 0));
	const mainHurter = $derived(influenceRows.find((r) => r.helpScore < 0 && !r.isOwn));
	const ownInfluence = $derived(influenceRows.find((r) => r.isOwn));

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

	const suggestionSentence = $derived.by(() => {
		if (apiRXIMOResult) return apiRXIMOResult.suggestion;
		if (!rival) {
			return `No clear non-own rival aspiration was detected for ${selectedObjectiveName}. Try tightening ${selectedObjectiveName} directly.`;
		}

		return `To improve ${selectedObjectiveName}, try tightening ${selectedObjectiveName} and relaxing ${rival.name}.`;
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

	function formatSigned(value: number): string {
		const fixed = Math.abs(value).toFixed(3);
		if (value > 0) return `+${fixed}`;
		if (value < 0) return `-${fixed}`;
		return '0.000';
	}

	function formatSignedPercent(value: number | null): string {
		if (value == null || !Number.isFinite(value)) return 'n/a';

		const fixed = Math.abs(value).toFixed(2);
		if (value > 0) return `+${fixed}%`;
		if (value < 0) return `-${fixed}%`;
		return '0.00%';
	}
</script>

<Sidebar.Root side="right" class="fixed top-12 right-0 h-[calc(100vh-3rem)]" bind:ref>
	<Sidebar.Header>
		<div>
			<span class="text-sm font-semibold">Explanations</span>
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
						<div class="flex shrink-0 items-center gap-1 text-xs font-medium text-gray-600">
							<span>Target</span>
							<Tooltip.Root>
								<Tooltip.Trigger class="inline-flex items-center text-gray-400 hover:text-gray-600">
									<InfoIcon class="h-3.5 w-3.5" />
								</Tooltip.Trigger>
								<Tooltip.Content sideOffset={6} class="max-w-56">
									Choose the outcome you want to understand or improve.
								</Tooltip.Content>
							</Tooltip.Root>
						</div>

						<div class="min-w-0 max-w-xs">
							<Combobox
								options={objectiveOptions}
								defaultSelected={selectedObjectiveSymbol}
								onChange={(e) => (selectedObjectiveSymbol = e.value)}
							/>
						</div>
					</div>

					<Tabs.Root bind:value={explanationTab} class="w-full">
						<Tabs.List class="grid w-full grid-cols-3">
							<Tabs.Trigger value="why">Breakdown</Tabs.Trigger>
							<Tabs.Trigger value="how">Improve</Tabs.Trigger>
							<Tabs.Trigger value="compare">Summary</Tabs.Trigger>
						</Tabs.List>

						<Tabs.Content value="why" class="mt-3 w-full">
							<div class="space-y-3">
								<div class="rounded-md border border-blue-100 bg-blue-50 p-3 text-xs text-gray-700">
									<div class="mb-1 font-semibold text-gray-900">
										Why is {selectedObjectiveName} = {formatNumber(achievedValueNumber, selectedObjectiveDigits)}?
									</div>

									<ul class="list-disc space-y-1 pl-4">
										{#if mainHurter}
											<li>
												<strong>{mainHurter.name}</strong> is the main non-own aspiration making
												this outcome harder to improve.
											</li>
										{/if}

										{#if mainHelper}
											<li>
												<strong>{mainHelper.name}</strong> helps this outcome the most.
											</li>
										{/if}

										{#if ownInfluence}
											<li>
												The aspiration for <strong>{selectedObjectiveName}</strong>
												{ownInfluence.isHelpful ? 'supports' : 'works against'}
												its own outcome.
											</li>
										{/if}

										{#if !mainHurter && !mainHelper && !ownInfluence}
											<li>No strong SHAP effect was detected for this outcome.</li>
										{/if}
									</ul>
								</div>

								<div>

								<div class="mb-2 text-xs text-gray-600">
									<span class="font-medium text-gray-700">How this result is built:</span>
									<br />
									Starting from a <strong>reference level</strong>, each bar shows how a
									preference moves the outcome up or down.
								</div>
									<ShapWaterfall
										shapRow={selectedRow}
										selectedOutputSymbol={selectedObjectiveSymbol}
										{problem}
										baseline={selectedSHAPBaseline}
										achieved={selectedSolutionValue}
									/>
								</div>

<!-- 								<details class="rounded-md border border-gray-200 bg-white p-3">
									<summary class="cursor-pointer text-xs font-semibold text-gray-700">
										Show full SHAP matrix
									</summary>

									<div class="mt-3">
										<ShapHeatmap shapValues={SHAP_values} {problem} />
									</div>
								</details> -->
							</div>
						</Tabs.Content>

						<Tabs.Content value="how" class="mt-3 w-full">
							<div class="space-y-3">
								<div class="rounded-md border border-amber-200 bg-amber-50 p-3">
									<div class="mb-1 flex items-center gap-2 text-sm font-semibold text-gray-900">
										<span>💡</span>
										<span>Suggested next step</span>
									</div>

									<p class="text-xs leading-relaxed text-gray-700">
										{suggestionSentence}
									</p>

									{#if rival}
										<div class="mt-2 rounded bg-white px-2 py-1 text-xs text-gray-600">
											Main non-own rival:
											<strong>{rival.name}</strong>
											<span class={rival.isHelpful ? 'text-[#0C7BDC]' : 'text-[#DC3220]'}>
												({formatSigned(rival.helpScore)})
											</span>
										</div>
									{/if}

									{#if explanationText}
										<details class="mt-2 rounded bg-white px-2 py-1 text-xs text-gray-700">
											<summary class="cursor-pointer font-medium text-gray-700">
												Why this suggestion?
											</summary>
											<p class="mt-1 leading-relaxed">{explanationText}</p>
										</details>
									{/if}
								</div>

								<div class="rounded-md border border-gray-200 bg-white p-3">
									<div class="mb-2 text-xs font-semibold text-gray-700">
										Trade-off interpretation
									</div>

									{#if mainHurter}
										<p class="text-xs leading-relaxed text-gray-600">
											Relaxing <strong>{mainHurter.name}</strong> may create room for improving
											<strong>{selectedObjectiveName}</strong>.
										</p>
									{:else if ownInfluence && !ownInfluence.isHelpful}
										<p class="text-xs leading-relaxed text-gray-600">
											The strongest negative effect comes from the selected outcome’s own aspiration.
											No separate rival aspiration was detected, so try tightening
											<strong>{selectedObjectiveName}</strong> directly or inspect nearby scenarios.
										</p>
									{:else}
										<p class="text-xs leading-relaxed text-gray-600">
											No strong conflicting aspiration was detected. You may try tightening
											<strong>{selectedObjectiveName}</strong> directly.
										</p>
									{/if}
								</div>

								<details class="rounded-md border border-gray-200 bg-white p-3">
									<summary class="cursor-pointer text-xs font-semibold text-gray-700">
										Show What-if Cases
									</summary>

									<div class="mt-3 space-y-3">
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
												No perturbed cases available yet.
											</div>
										{:else}
											<WhatIfCaseNetwork
												objectives={problem.objectives.map((o) => ({ symbol: o.symbol, name: o.name }))}
												cases={hypotheticalScenarios.map((caseItem) => ({
													impairedSymbol: caseItem.impairedSymbol,
													deltas: caseItem.deltas.map((delta) => ({
														symbol: delta.symbol,
														delta: delta.delta,
														percentDelta: delta.percentDelta
													}))
												}))}
												mode={scenarioDiffDisplayMode}
											/>

											{#each hypotheticalScenarios as scenario}
												<div class="rounded-md border border-gray-200 bg-white p-3">
													<div class="mb-2 text-xs text-gray-700">
														If <strong>{scenario.impairedName}</strong> is impaired by
														<strong>{scenario.impairmentMagnitude.toFixed(3)}</strong>
														(to target value
														<strong>{scenario.impairedTargetValue.toFixed(3)}</strong>),
														the
														observed effects are:
													</div>

													<div class="mb-2">
														<Button
															type="button"
															variant="outline"
															size="sm"
															onclick={() => onApplyScenarioPreferences?.(scenario.scenarioPreferenceValues)}
														>
															Set preferences to this case
														</Button>
													</div>

													<div class="space-y-1.5">
														{#each scenario.deltas as delta}
															<div class="grid grid-cols-[64px_1fr_62px] items-center gap-2 text-xs">
																<div class="truncate font-medium text-gray-700" title={delta.symbol}>
																	{delta.name}
																</div>

																<div class="h-2 overflow-hidden rounded bg-gray-100">
																	<div
																		class={`h-full ${delta.isImprovement ? 'bg-[#0C7BDC]' : 'bg-[#DC3220]'}`}
																		style={`width: ${scenarioDiffDisplayMode === 'percent'
																			? (Math.abs(delta.percentDelta ?? 0) / maxAbsScenarioPercent) * 100
																			: (Math.abs(delta.delta) / maxAbsScenarioDelta) * 100}%`}
																	></div>
																</div>

																<div
																	class={`text-right font-mono ${delta.isImprovement ? 'text-[#0C7BDC]' : 'text-[#DC3220]'}`}
																>
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
								</details>
							</div>
						</Tabs.Content>

						<Tabs.Content value="compare" class="mt-3 w-full">
							<div class="space-y-3">
								<div class="rounded-md border border-gray-200 bg-white p-3">
									<div class="mb-2 text-xs font-semibold text-gray-700">
										Current explanation summary
									</div>

									<div class="space-y-2 text-xs text-gray-700">
										{#if mainHurter}
											<div class="flex items-center justify-between gap-3">
												<span>Largest non-own conflict</span>
												<strong class="text-[#DC3220]">{mainHurter.name}</strong>
											</div>
										{/if}

										{#if mainHelper}
											<div class="flex items-center justify-between gap-3">
												<span>Largest support</span>
												<strong class="text-[#0C7BDC]">{mainHelper.name}</strong>
											</div>
										{/if}

										{#if ownInfluence}
											<div class="flex items-center justify-between gap-3">
												<span>Own aspiration effect</span>
												<strong class={ownInfluence.isHelpful ? 'text-[#0C7BDC]' : 'text-[#DC3220]'}>
													{formatSigned(ownInfluence.helpScore)}
												</strong>
											</div>
										{/if}

										<div class="flex items-center justify-between gap-3">
											<span>Selected outcome</span>
											<strong>{selectedObjectiveName}</strong>
										</div>
									</div>
								</div>

								<ShapCaseRelationshipNetwork
									objectives={problem.objectives.map((o) => ({
										symbol: o.symbol,
										name: o.name,
										maximize: o.maximize
									}))}
									preferenceValues={preferenceValues}
									achievedValues={baselineObjectiveValues}
									shapValues={SHAP_values}
									threshold={0}
								/>

								<div class="rounded-md border border-gray-200 bg-white p-3">
									<div class="mb-2 text-xs font-semibold text-gray-700">
										All influences on {selectedObjectiveName}
									</div>

									<div class="space-y-1.5">
										{#each influenceRows as row}
											<div class="grid grid-cols-[82px_1fr_52px] items-center gap-2 text-xs">
												<div class="truncate font-medium text-gray-700" title={row.symbol}>
													{row.name}{row.isOwn ? ' (own)' : ''}
												</div>

												<div class="h-2 overflow-hidden rounded bg-gray-100">
													<div
														class={`h-full ${row.isHelpful ? 'bg-[#0C7BDC]' : 'bg-[#DC3220]'}`}
														style={`width: ${(Math.abs(row.helpScore) / maxAbsInfluence) * 100}%`}
													></div>
												</div>

												<div
													class={`text-right font-mono ${row.isHelpful ? 'text-[#0C7BDC]' : 'text-[#DC3220]'}`}
												>
													{formatSigned(row.helpScore)}
												</div>
											</div>
										{/each}
									</div>
								</div>

								<details class="rounded-md border border-gray-200 bg-white p-3">
									<summary class="cursor-pointer text-xs font-semibold text-gray-700">
										Show full overview matrix
									</summary>

									<div class="mt-3">
										<ShapHeatmap shapValues={SHAP_values} {problem} />
									</div>
								</details>
							</div>
						</Tabs.Content>
					</Tabs.Root>
				</div>
			{/if}
		</Tooltip.Provider>
	</Sidebar.Content>


</Sidebar.Root>
