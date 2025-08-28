<script lang="ts">
	import { BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import { Combobox } from '$lib/components/ui/combobox';
	import Button from '$lib/components/ui/button/button.svelte';
	import type { MethodHandlers } from '$lib/helpers/method-handler';
	import type { components } from '$lib/api/client-types';
	import { TYPE_SOLUTIONS_SHOWN } from '$lib/constants/index.js';
	type Solution = components['schemas']['UserSavedSolutionAddress'];

	export let handlers: MethodHandlers;
	export let mode: 'iterate' | 'final' | 'intermediate' = 'iterate';
	export let problem: any;
	export let selectedSolutions: Solution[] = [];
	export let selectedIndexes: number[] = [];
	export let solutionType: string = 'current';
	export let allowIntermediate: boolean = true;

	// Pass through slots for custom visualization components
	export let visualizationComponent: any;
	export let sidebarComponent: any;
	export let tableComponent: any;

	function handleTypeChange(event: { value: string }) {
		// Type guard to ensure value is a valid SolutionViewType
		if (event.value === 'current' || event.value === 'best' || event.value === 'all') {
			handlers.handleSolutionTypeChange(event.value);
		}
	}
</script>

<BaseLayout showLeftSidebar={!!problem} showRightSidebar={false}>
	{#snippet leftSidebar()}
		{#if problem && mode === 'iterate'}
			<svelte:component
				this={sidebarComponent}
				{problem}
				onPreferenceChange={handlers.handlePreferenceChange}
				onIterate={handlers.handleIterate}
			/>
		{/if}
	{/snippet}

	{#snippet menuRow()}
		{#if allowIntermediate}
			<SegmentedControl
				bind:value={mode}
				options={[
					{ value: 'iterate', label: 'Iterate' },
					{ value: 'intermediate', label: 'Find intermediate' }
				]}
				class="mr-10"
			/>
		{/if}

		<span>View: </span>
		<Combobox
			options={TYPE_SOLUTIONS_SHOWN}
			defaultSelected={solutionType}
			onChange={handleTypeChange}
		/>

		<span
			class="inline-block"
			title={selectedIndexes.length !== 1
				? 'Please select exactly one solution to finish with it.'
				: 'Select final solution and finish'}
		>
			<Button
				onclick={() =>
					selectedIndexes.length === 1 &&
					handlers.handleFinish(selectedSolutions[0], selectedIndexes[0])}
				disabled={selectedIndexes.length !== 1}
				variant="destructive"
				class="ml-10"
			>
				Finish
			</Button>
		</span>
	{/snippet}

	{#snippet topPanel()}
		<svelte:component
			this={visualizationComponent}
			{problem}
			{selectedSolutions}
			{selectedIndexes}
		/>
	{/snippet}

	{#snippet bottomPanel()}
		<svelte:component
			this={tableComponent}
			{problem}
			{selectedSolutions}
			{selectedIndexes}
			onSave={handlers.handleSave}
			onRemove={handlers.handleRemove}
		/>
	{/snippet}
</BaseLayout>
