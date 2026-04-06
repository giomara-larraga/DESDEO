<script lang="ts">
	import { ExplainableLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import Button from '$lib/components/ui/button/button.svelte';
	import Alert from '$lib/components/custom/notifications/alert.svelte';
	import LoadingSpinner from '$lib/components/custom/notifications/loading-spinner.svelte';
	import { onMount } from 'svelte';

	import { methodSelection } from '../../../stores/methodSelection';
	import { errorMessage, isLoading } from '../../../stores/uiState';
	import { explainWithRXIMO, fetchBackgroundDatasets } from './handlers';

	import type { ProblemInfo } from '$lib/types';
	import type {
		BackgroundDatasetInfo,
		RXIMOExplainResponse,
		RXIMOPageData
	} from './types';

	const { data } = $props<{ data: RXIMOPageData }>();
	let problem_list = $derived(data.problems ?? []);
	let selectedProblemId = $state<number | null>(null);
	let selectedDatasetId = $state<number | null>(null);
	let backgroundDatasets = $state<BackgroundDatasetInfo[]>([]);
	let explanation = $state<RXIMOExplainResponse | null>(null);
	let pageNotice = $state<string | null>(null);
	let referencePointValues = $state<Record<string, number>>({});

	let problem = $derived.by(() => {
		if (selectedProblemId === null) return null;
		return problem_list.find((item) => item.id === selectedProblemId) ?? null;
	});

	// Initialize selectedProblemId when problem_list changes
	$effect(() => {
		if (selectedProblemId === null && problem_list.length > 0) {
			selectedProblemId = problem_list[0].id;
		}
	});

	// Load background data when problem changes
	$effect(() => {
		const currentProblem = problem;
		if (!currentProblem) return;
		referencePointValues = Object.fromEntries(
			currentProblem.objectives.map((objective) => [
				objective.symbol,
				typeof objective.ideal === 'number' ? objective.ideal : 0
			])
		);
		explanation = null;
		pageNotice = null;
		void loadBackgroundData(currentProblem.id);
	});

	onMount(() => {
		methodSelection.set('RXIMO');
	});

	async function loadBackgroundData(problemId: number) {
		const datasets = await fetchBackgroundDatasets(problemId);
		if (!datasets) return;

		backgroundDatasets = datasets;
		selectedDatasetId = datasets[0]?.id ?? null;
		if (datasets.length === 0) {
			pageNotice =
				'No background data available for this problem. Generate it first from the background data interface.';
		}
	}

	function updateReferenceValue(symbol: string, value: string) {
		const parsed = Number(value);
		if (Number.isFinite(parsed)) {
			referencePointValues = { ...referencePointValues, [symbol]: parsed };
		}
	}

	function handleProblemChange(event: Event) {
		const value = Number((event.currentTarget as HTMLSelectElement).value);
		selectedProblemId = Number.isFinite(value) ? value : null;
	}

	function handleDatasetChange(event: Event) {
		const value = Number((event.currentTarget as HTMLSelectElement).value);
		selectedDatasetId = Number.isFinite(value) ? value : null;
	}

	async function handleExplain() {
		if (!problem) return;
		if (!selectedDatasetId) {
			pageNotice =
				'Select a background dataset before requesting RXIMO explanations.';
			return;
		}

		const result = await explainWithRXIMO(problem.id, referencePointValues, selectedDatasetId);
		if (!result) return;
		explanation = result;
		pageNotice = null;
	}

	function formatNumber(value: number) {
		if (!Number.isFinite(value)) return String(value);
		return value.toFixed(4);
	}
</script>

{#if $isLoading}
	<LoadingSpinner />
{/if}

{#if $errorMessage}
	<div class="p-2">
		<Alert title="Error" message={$errorMessage} variant="destructive" />
	</div>
{/if}

{#if pageNotice}
	<div class="p-2">
		<Alert title="Notice" message={pageNotice} variant="default" />
	</div>
{/if}

<BaseLayout showLeftSidebar={true} showRightSidebar={false} bottomPanelTitle="SHAP Values">
	{#snippet leftSidebar()}
		<div class="space-y-4 p-4">
			<div>
				<h2 class="text-lg font-semibold">RXIMO Controls</h2>
				<p class="text-sm text-muted-foreground">
					Configure a reference point and request SHAP explanations for RPM.
				</p>
			</div>

			<div class="space-y-2">
				<label class="text-sm font-medium" for="problem">Problem</label>
				<select
					id="problem"
					class="w-full rounded border p-2"
					onchange={handleProblemChange}
					value={selectedProblemId ?? ''}
				>
					{#each problem_list as item}
						<option value={item.id}>{item.name}</option>
					{/each}
				</select>
			</div>

			<div class="space-y-2">
				<label class="text-sm font-medium" for="dataset">Background dataset</label>
				<select
					id="dataset"
					class="w-full rounded border p-2"
					onchange={handleDatasetChange}
					disabled={backgroundDatasets.length === 0}
					value={selectedDatasetId ?? ''}
				>
					{#each backgroundDatasets as item}
						<option value={item.id}>
							{item.name ?? `Dataset ${item.id}`} ({item.num_samples} samples)
						</option>
					{/each}
				</select>
			</div>

			{#if problem}
				<div class="space-y-2">
					<h3 class="text-sm font-semibold">Reference point</h3>
					{#each problem.objectives as objective}
						<div class="grid grid-cols-[7rem_1fr] items-center gap-2">
							<label class="text-xs font-medium" for={`rp-${objective.symbol}`}>
								{objective.symbol}
							</label>
							<input
								id={`rp-${objective.symbol}`}
								type="number"
								step="any"
								class="rounded border p-2"
								value={referencePointValues[objective.symbol] ?? 0}
								oninput={(event) =>
									updateReferenceValue(
										objective.symbol,
										(event.currentTarget as HTMLInputElement).value
									)
								}
							/>
						</div>
					{/each}
				</div>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerControls()}
		<Button onclick={handleExplain} disabled={!problem || backgroundDatasets.length === 0}>
			Get RXIMO Explanation
		</Button>
	{/snippet}

	{#snippet visualizationArea(_height)}
		{#if explanation}
			<div class="h-full overflow-auto rounded border bg-white p-4">
				<h3 class="mb-3 text-lg font-semibold">Explanation Summary</h3>
				<div class="mb-4 grid gap-4 md:grid-cols-2">
					<div>
						<h4 class="mb-2 text-sm font-semibold">Predicted objective values</h4>
						<ul class="space-y-1 text-sm">
							{#each explanation.output_symbols as symbol}
								<li><span class="font-medium">{symbol}:</span> {formatNumber(explanation.explained_objective_values[symbol])}</li>
							{/each}
						</ul>
					</div>
					<div>
						<h4 class="mb-2 text-sm font-semibold">Base values</h4>
						<ul class="space-y-1 text-sm">
							{#each explanation.output_symbols as symbol}
								<li><span class="font-medium">{symbol}:</span> {formatNumber(explanation.base_values[symbol])}</li>
							{/each}
						</ul>
					</div>
				</div>

				<h4 class="mb-2 text-sm font-semibold">SHAP values (output -> input contributions)</h4>
				<div class="overflow-auto rounded border">
					<table class="w-full text-sm">
						<thead class="bg-gray-100">
							<tr>
								<th class="border p-2 text-left">Output</th>
								{#each explanation.input_symbols as inputSymbol}
									<th class="border p-2 text-left">{inputSymbol}</th>
								{/each}
							</tr>
						</thead>
						<tbody>
							{#each explanation.output_symbols as outputSymbol}
								<tr>
									<td class="border p-2 font-medium">{outputSymbol}</td>
									{#each explanation.input_symbols as inputSymbol}
										<td class="border p-2">{formatNumber(explanation.shap_values[outputSymbol][inputSymbol])}</td>
									{/each}
								</tr>
							{/each}
						</tbody>
					</table>
				</div>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center rounded border bg-gray-50 text-sm text-muted-foreground">
				Select problem and background data, set reference point, then request RXIMO explanation.
			</div>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if explanation}
			<div class="h-full overflow-auto rounded border bg-white p-3">
				<pre class="text-xs">{JSON.stringify(explanation, null, 2)}</pre>
			</div>
		{/if}
	{/snippet}
</BaseLayout>
