<script lang="ts">
	import BaseLayout from '$lib/components/custom/method_layout/reworked-layout.svelte';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import { Combobox } from '$lib/components/ui/combobox';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { BaseMethodState, SolutionType } from '$lib/types/interactive-method';
	import type { MethodLayoutProps } from './types';

	export let showLeftSidebar: boolean = true;

	export let handlers: MethodLayoutProps['handlers'];
	export let state: BaseMethodState;
	export let allowIntermediate: MethodLayoutProps['allowIntermediate'] = true;
	export let showRightSidebar: MethodLayoutProps['showRightSidebar'] = false;

	const solutionTypes: { value: SolutionType; label: string }[] = [
		{ value: 'current', label: 'Current solutions' },
		{ value: 'best', label: 'Best solutions' },
		{ value: 'all', label: 'All solutions' }
	];
</script>

<BaseLayout {showLeftSidebar} {showRightSidebar}>
	{#snippet leftSidebar()}
		<slot name="leftSidebar" />
	{/snippet}

	{#snippet menuRow()}
		{#if allowIntermediate}
			<SegmentedControl
				bind:value={state.mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' }
				]}
				class="mr-10"
			/>
		{/if}

		<span>View: </span>
		<Combobox
			options={solutionTypes}
			defaultSelected={state.selectedType}
			onChange={(e) => handlers.handleSolutionTypeChange(e.value as SolutionType)}
		/>

		<slot name="additionalControls" />

		<Button
			onclick={() =>
				state.selectedIndexes.length === 1 &&
				handlers.handleFinish(
					state.currentState.current_solutions[state.selectedIndexes[0]],
					state.selectedIndexes[0]
				)}
			disabled={state.selectedIndexes.length !== 1}
			variant="destructive"
			class="ml-10"
		>
			Finish
		</Button>
	{/snippet}

	{#snippet topPanel()}
		<slot name="visualizationArea" />
	{/snippet}

	{#snippet bottomPanel()}
		<slot name="numericalValues" />
	{/snippet}
</BaseLayout>
