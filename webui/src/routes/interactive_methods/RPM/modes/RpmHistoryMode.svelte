<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import Button from '$lib/components/ui/button/button.svelte';
	import AppSidebar from '$lib/components/custom/preferences-bar/preferences-sidebar.svelte';
	import HistorySidebar from '$lib/components/custom/preferences-bar/history-sidebar.svelte';
	import { VisualizationsPanelHistory } from '$lib/components/custom/visualizations-panel';
	import { PREFERENCE_TYPES } from '$lib/constants';

	import type { MethodMode, ProblemInfo } from '$lib/types';
	import type { Response } from '../types';
	import { updatePreferencesFromState } from '../helper-functions';

	type IterationDisplayMode = 'both' | 'solutions' | 'reference';

	let {
		mode = $bindable('history' as MethodMode),
		problem,
		hasRightSidebarContent,
		stateHistory,
		currentStateIndex,
		iterationNames,
		onApplyIteration,
		onRenameIteration,
		isLeftSidebarCollapsed = $bindable(false),
		isRightSidebarCollapsed = $bindable(false)
	}: {
		mode?: MethodMode;
		problem: ProblemInfo | null;
		hasRightSidebarContent: boolean;
		stateHistory: Response[];
		currentStateIndex: number;
		iterationNames: Record<number, string>;
		onApplyIteration: (index: number) => void;
		onRenameIteration: (index: number, name: string) => void;
		isLeftSidebarCollapsed?: boolean;
		isRightSidebarCollapsed?: boolean;
	} = $props();

	let selectedPreviewIndex = $state<number>(-1);
	let selectedIterationIndexes = $state<number[]>([]);
	let iterationDisplayModes = $state<Record<number, IterationDisplayMode>>({});

	$effect(() => {
		if (stateHistory.length === 0) {
			selectedPreviewIndex = -1;
			selectedIterationIndexes = [];
			return;
		}

		if (selectedPreviewIndex < 0 || selectedPreviewIndex >= stateHistory.length) {
			selectedPreviewIndex = currentStateIndex >= 0 ? currentStateIndex : stateHistory.length - 1;
		}

		const valid = selectedIterationIndexes.filter((idx) => idx >= 0 && idx < stateHistory.length);
		if (valid.length === 0) {
			selectedIterationIndexes = stateHistory.map((_, idx) => idx);
		} else if (valid.length !== selectedIterationIndexes.length) {
			selectedIterationIndexes = valid;
		}

		const validModes: Record<number, IterationDisplayMode> = {};
		Object.entries(iterationDisplayModes).forEach(([k, v]) => {
			const idx = Number(k);
			if (Number.isInteger(idx) && idx >= 0 && idx < stateHistory.length) {
				validModes[idx] = v;
			}
		});
		if (Object.keys(validModes).length !== Object.keys(iterationDisplayModes).length) {
			iterationDisplayModes = validModes;
		}
	});

	let previewState = $derived.by(() => {
		if (selectedPreviewIndex < 0 || selectedPreviewIndex >= stateHistory.length) return null;
		return stateHistory[selectedPreviewIndex] ?? null;
	});

	let previewSolutions = $derived(previewState?.current_solutions ?? []);

	let previewPreferenceValues = $derived.by(() => {
		if (!problem || !previewState) return [];
		return updatePreferencesFromState(previewState, problem);
	});

	let previewObjectiveValues = $derived.by(() => {
		if (!problem || !previewState || previewSolutions.length === 0) return [];
		const first = previewSolutions[0];
		return problem.objectives.map((obj) => {
			const raw = first.objective_values?.[obj.symbol];
			return Array.isArray(raw) ? raw[0] : (raw ?? 0);
		});
	});

	let historyDimensions = $derived.by(() => {
		if (!problem) return [];
		return problem.objectives.map((obj) => ({
			symbol: obj.symbol,
			name: obj.name,
			min: Math.min(obj.ideal ?? 0, obj.nadir ?? 0),
			max: Math.max(obj.ideal ?? 0, obj.nadir ?? 0),
			direction: (obj.maximize ? 'max' : 'min') as 'max' | 'min'
		}));
	});

	let historyIterationsForPlot = $derived.by(() => {
		if (!problem || stateHistory.length === 0) return [];

		return stateHistory.map((state, index) => {
			const displayMode = iterationDisplayModes[index] ?? 'both';
			const values = (state.current_solutions ?? []).map((solution) => {
				const point: Record<string, number> = {};
				problem.objectives.forEach((obj) => {
					const raw = solution.objective_values?.[obj.symbol];
					const value = Array.isArray(raw) ? raw[0] : raw;
					if (value != null) point[obj.symbol] = value;
				});
				return point;
			});

			let referencePoint: Record<string, number> | undefined = undefined;
			const aspiration = state.previous_preference?.aspiration_levels;
			if (aspiration) {
				referencePoint = {};
				problem.objectives.forEach((obj) => {
					const value = aspiration[obj.symbol];
					if (value != null) referencePoint![obj.symbol] = value;
				});
			}

			return {
				id: state.state_id ?? index,
				name: getIterationLabel(index),
				data: displayMode === 'reference' ? [] : values,
				show: selectedIterationIndexes.includes(index),
				referencePoint: displayMode === 'solutions' ? undefined : referencePoint
			};
		});
	});

	function handlePreviewPreferenceChange() {
		// History sidebar preferences are preview-only and do not mutate active iteration.
	}

	async function handlePreviewIterate() {
		// Disabled in history mode; user must explicitly apply an iteration first.
	}

	function handleSelectIteration(index: number) {
		selectedPreviewIndex = index;
	}

	function handleToggleIterationSelection(index: number, selected: boolean) {
		if (selected) {
			if (!selectedIterationIndexes.includes(index)) {
				selectedIterationIndexes = [...selectedIterationIndexes, index].sort((a, b) => a - b);
			}
		} else {
			selectedIterationIndexes = selectedIterationIndexes.filter((i) => i !== index);
		}
	}

	function handleSetIterationDisplayMode(index: number, mode: IterationDisplayMode) {
		iterationDisplayModes = {
			...iterationDisplayModes,
			[index]: mode
		};
	}

	function handleSetAllReferenceOnly() {
		const modes: Record<number, IterationDisplayMode> = {};
		stateHistory.forEach((_, index) => {
			modes[index] = 'reference';
		});
		iterationDisplayModes = modes;
	}

	function getIterationLabel(index: number): string {
		return iterationNames[index] && iterationNames[index].trim().length > 0
			? iterationNames[index]
			: `Iteration ${index + 1}`;
	}

</script>

<BaseLayout showLeftSidebar={true} showRightSidebar={true} bottomPanelTitle="History">
	{#snippet leftSidebar()}
		<div class="relative h-full">
			<Button
				onclick={() => (isLeftSidebarCollapsed = true)}
				variant="outline"
				size="icon"
				class="absolute -right-4 top-1/2 z-20 h-8 w-8 -translate-y-1/2 bg-white"
				aria-label="Hide left panel"
				title="Hide left panel"
			>
				&lt;
			</Button>

			{#if problem}
				<div class="h-full pointer-events-none">
					<AppSidebar
						{problem}
						preferenceTypes={[PREFERENCE_TYPES.ReferencePoint]}
						showNumSolutions={false}
						numSolutions={previewSolutions.length > 0 ? previewSolutions.length : 1}
						typePreferences={PREFERENCE_TYPES.ReferencePoint}
						preferenceValues={previewPreferenceValues}
						objectiveValues={previewObjectiveValues}
						lastIteratedPreference={previewPreferenceValues}
						onPreferenceChange={handlePreviewPreferenceChange}
						onIterate={handlePreviewIterate}
						isFinishButton={false}
					/>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No problem data available for history
				</div>
			{/if}
		</div>
	{/snippet}

	{#snippet explorerControls()}
		<div class="relative h-full flex-row flex items-center px-4">
			<SegmentedControl
				bind:value={mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' },
					{ value: 'history', label: 'History' }
				]}
				class="mr-10"
			/>
		</div>
	{/snippet}

	{#snippet visualizationArea(height)}
		{#if problem}
			<div class="relative h-full">
				<Button
					onclick={() => (isLeftSidebarCollapsed = false)}
					variant="outline"
					size="icon"
					class="fixed left-1 top-1/2 z-30 h-8 w-8 -translate-y-1/2 bg-white"
					aria-label={isLeftSidebarCollapsed ? 'Show left panel' : 'Hide left panel'}
					title={isLeftSidebarCollapsed ? 'Show left panel' : 'Hide left panel'}
					hidden={!isLeftSidebarCollapsed}
				>
					&gt;
				</Button>

				<Button
					onclick={() => (isRightSidebarCollapsed = false)}
					variant="outline"
					size="icon"
					class="fixed right-1 top-1/2 z-30 h-8 w-8 -translate-y-1/2 bg-white"
					aria-label={isRightSidebarCollapsed ? 'Show right panel' : 'Hide right panel'}
					title={isRightSidebarCollapsed ? 'Show right panel' : 'Hide right panel'}
					hidden={!isRightSidebarCollapsed}
				>
					&lt;
				</Button>

				<Resizable.PaneGroup direction="horizontal" class="h-full">
					<Resizable.Pane defaultSize={100} minSize={40} class="h-full">
						<VisualizationsPanelHistory
							{height}
							iterations={historyIterationsForPlot}
							dimensions={historyDimensions}
						/>
					</Resizable.Pane>
				</Resizable.PaneGroup>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No problem data available for history.
			</div>
		{/if}
	{/snippet}

	{#snippet numericalValues()}
		{#if problem && previewState && previewSolutions.length > 0}
			<div class="h-full overflow-auto p-3">
				<table class="w-full text-sm">
					<thead>
						<tr class="border-b bg-gray-50">
							<th class="px-2 py-2 text-left font-semibold">Solution</th>
							{#each problem.objectives as obj}
								<th class="px-2 py-2 text-right font-semibold">{obj.symbol}</th>
							{/each}
						</tr>
					</thead>
					<tbody>
						{#each previewSolutions as solution, idx}
							<tr class="border-b border-gray-100">
								<td class="px-2 py-2">{solution.name?.trim() || `Solution #${idx + 1}`}</td>
								{#each problem.objectives as obj}
									{@const raw = solution.objective_values?.[obj.symbol]}
									{@const value = Array.isArray(raw) ? raw[0] : raw}
									<td class="px-2 py-2 text-right font-mono">{value ?? '-'}</td>
								{/each}
							</tr>
						{/each}
					</tbody>
				</table>
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No iteration preview selected.
			</div>
		{/if}
	{/snippet}

	{#snippet rightSidebar()}
		<div>
			{#if hasRightSidebarContent}
				<div class="relative h-full">
					<Button
						onclick={() => (isRightSidebarCollapsed = true)}
						variant="outline"
						size="icon"
						class="absolute -left-4 top-1/2 z-20 h-8 w-8 -translate-y-1/2 bg-white"
						aria-label="Hide right panel"
						title="Hide right panel"
					>
						&gt;
					</Button>

					<HistorySidebar
						{stateHistory}
						{currentStateIndex}
						{iterationNames}
						{selectedPreviewIndex}
						selectedIterationIndexes={selectedIterationIndexes}
						iterationDisplayModes={iterationDisplayModes}
						onSelectIteration={handleSelectIteration}
						onToggleIterationSelection={handleToggleIterationSelection}
						onSetIterationDisplayMode={handleSetIterationDisplayMode}
						onSetAllReferenceOnly={handleSetAllReferenceOnly}
						{onApplyIteration}
						{onRenameIteration}
					/>
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No details available
				</div>
			{/if}
		</div>
	{/snippet}
</BaseLayout>
