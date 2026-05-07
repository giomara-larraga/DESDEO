<script lang="ts">
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';
	import { Button } from '$lib/components/ui/button/index.js';
	import { openInputDialog } from '$lib/components/custom/dialogs/dialogs';

	type HistoryState = {
		response_type: string;
		current_solutions?: unknown[];
	};

	type IterationDisplayMode = 'both' | 'solutions' | 'reference';

	interface Props {
		stateHistory: HistoryState[];
		currentStateIndex: number;
		iterationNames: Record<number, string>;
		selectedPreviewIndex: number;
		selectedIterationIndexes: number[];
		iterationDisplayModes: Record<number, IterationDisplayMode>;
		onSelectIteration: (index: number) => void;
		onToggleIterationSelection: (index: number, selected: boolean) => void;
		onSetIterationDisplayMode: (index: number, mode: IterationDisplayMode) => void;
		onSetAllReferenceOnly: () => void;
		onApplyIteration: (index: number) => void;
		onRenameIteration: (index: number, name: string) => void;
		ref?: HTMLElement | null;
	}

	let {
		stateHistory,
		currentStateIndex,
		iterationNames,
		selectedPreviewIndex,
		selectedIterationIndexes,
		iterationDisplayModes,
		onSelectIteration,
		onToggleIterationSelection,
		onSetIterationDisplayMode,
		onSetAllReferenceOnly,
		onApplyIteration,
		onRenameIteration,
		ref = null
	}: Props = $props();

	function isIterationSelected(index: number): boolean {
		return selectedIterationIndexes.includes(index);
	}

	function getIterationLabel(index: number): string {
		return iterationNames[index] && iterationNames[index].trim().length > 0
			? iterationNames[index]
			: `Iteration ${index + 1}`;
	}

	function getIterationDisplayMode(index: number): IterationDisplayMode {
		return iterationDisplayModes[index] ?? 'both';
	}

	function displayModeRadioName(index: number): string {
		return `iteration-display-mode-${index}`;
	}

	function renameIteration(index: number) {
		openInputDialog({
			title: 'Rename Iteration',
			description: `Set a custom name for iteration ${index + 1}.`,
			confirmText: 'Save',
			cancelText: 'Cancel',
			initialValue: iterationNames[index] ?? '',
			placeholder: `Iteration ${index + 1}`,
			onConfirm: (name) => onRenameIteration(index, name)
		});
	}
</script>

<Sidebar.Root
	{ref}
	collapsible="none"
	class="top-12 flex h-[calc(100vh-6rem)] min-h-[calc(100vh-3rem)] w-100"
>
	<Sidebar.Header>
		<Sidebar.MenuButton
			size="lg"
			class="data-[state=open]:bg-sidebar-accent data-[state=open]:text-sidebar-accent-foreground"
		>
			<div class="flex flex-col gap-0.5 leading-none">
				<span class="font-semibold">Session Iterations</span>
				<span class="text-primary-500">History preview</span>
			</div>
		</Sidebar.MenuButton>
	</Sidebar.Header>

	<Sidebar.Content class="h-full px-4">
		{#if stateHistory.length > 0}
			<div class="space-y-2 py-2">
				{#each stateHistory as state, index}
					<div class="w-full rounded border px-3 py-2 text-left text-sm transition-colors {selectedPreviewIndex === index ? 'border-blue-500 bg-blue-50 text-blue-900' : 'border-gray-200 bg-white hover:bg-gray-50'}">
						<button type="button" class="w-full text-left" onclick={() => onSelectIteration(index)}>
						<div class="flex items-center justify-between gap-2">
							<div class="flex items-center gap-2 min-w-0">
								<input
									type="checkbox"
									checked={isIterationSelected(index)}
									onclick={(event) => event.stopPropagation()}
									onchange={(event) => {
										const checked = (event.currentTarget as HTMLInputElement).checked;
										onToggleIterationSelection(index, checked);
									}}
								/>
								<span class="truncate font-medium">{getIterationLabel(index)}</span>
							</div>
							<span class="text-[10px] uppercase text-gray-500">{state.response_type}</span>
						</div>
						<div class="mt-1 text-xs text-gray-500">
							{state.current_solutions?.length ?? 0} solution(s)
							{#if index === currentStateIndex}
								• active
							{/if}
						</div>
						</button>
						<fieldset class="mt-2">
							<legend class="text-[11px] text-gray-500">Show</legend>
							<div class="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1">
								<label class="flex items-center gap-1 text-xs text-gray-700">
									<input
										type="radio"
										name={displayModeRadioName(index)}
										value="both"
										checked={getIterationDisplayMode(index) === 'both'}
										onclick={(event) => event.stopPropagation()}
										onchange={() => onSetIterationDisplayMode(index, 'both')}
									/>
									Both
								</label>
								<label class="flex items-center gap-1 text-xs text-gray-700">
									<input
										type="radio"
										name={displayModeRadioName(index)}
										value="solutions"
										checked={getIterationDisplayMode(index) === 'solutions'}
										onclick={(event) => event.stopPropagation()}
										onchange={() => onSetIterationDisplayMode(index, 'solutions')}
									/>
									Solutions
								</label>
								<label class="flex items-center gap-1 text-xs text-gray-700">
									<input
										type="radio"
										name={displayModeRadioName(index)}
										value="reference"
										checked={getIterationDisplayMode(index) === 'reference'}
										onclick={(event) => event.stopPropagation()}
										onchange={() => onSetIterationDisplayMode(index, 'reference')}
									/>
									Reference
								</label>
							</div>
						</fieldset>
						<div class="mt-2 flex items-center justify-end">
							<Button
								variant="ghost"
								size="sm"
								onclick={(event) => {
									event.stopPropagation();
									renameIteration(index);
								}}
							>
								Rename
							</Button>
						</div>
					</div>
				{/each}
			</div>
		{:else}
			<div class="flex h-full items-center justify-center text-gray-500">
				No history available for this session
			</div>
		{/if}
	</Sidebar.Content>

	<Sidebar.Footer>
		<div class="items-right flex justify-end gap-2">
			<Button variant="outline" size="sm" onclick={onSetAllReferenceOnly}>
				Reference For All
			</Button>
			<Button
				variant="secondary"
				size="sm"
				onclick={() => onApplyIteration(selectedPreviewIndex)}
				disabled={selectedPreviewIndex < 0 || selectedPreviewIndex >= stateHistory.length}
			>
				Use This Iteration
			</Button>
		</div>
	</Sidebar.Footer>
	<Sidebar.Rail />
</Sidebar.Root>
