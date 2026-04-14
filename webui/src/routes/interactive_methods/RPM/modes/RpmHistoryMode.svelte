<script lang="ts">
	import { RXIMOLayout as BaseLayout } from '$lib/components/custom/method_layout/index.js';
	import { SegmentedControl } from '$lib/components/custom/segmented-control';
	import Button from '$lib/components/ui/button/button.svelte';

	import type { MethodMode, ProblemInfo } from '$lib/types';

	let {
		mode = $bindable('history' as MethodMode),
		problem,
		hasRightSidebarContent,
		isLeftSidebarCollapsed = $bindable(false),
		isRightSidebarCollapsed = $bindable(false)
	}: {
		mode?: MethodMode;
		problem: ProblemInfo | null;
		hasRightSidebarContent: boolean;
		isLeftSidebarCollapsed?: boolean;
		isRightSidebarCollapsed?: boolean;
	} = $props();
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
				<div>Iterations filter</div>
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
		<div>
			Show solutions per iteration
		</div>
	{/snippet}

	{#snippet numericalValues()}
		<div>
			Show numerical values per iteration
		</div>
	{/snippet}

	{#snippet rightSidebar()}
		<div>
			{#if hasRightSidebarContent && problem}
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
				</div>
			{:else}
				<div class="flex h-full items-center justify-center text-gray-500">
					No explanation available
				</div>
			{/if}
		</div>
	{/snippet}
</BaseLayout>
