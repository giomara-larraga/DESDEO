<script lang="ts">
	import type { Snippet } from 'svelte';
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';
	import * as Sidebar from '$lib/components/ui/sidebar/index.js';

	import Button from '$lib/components/ui/button/button.svelte';
	import ChevronLeft from '@lucide/svelte/icons/chevron-left';
	import ChevronRight from '@lucide/svelte/icons/chevron-right';

	// Define the interface for your named snippets
	interface Props {
		showLeftSidebar?: boolean;
		showRightSidebar?: boolean;

		isLeftSidebarCollapsed?: boolean;
		isRightSidebarCollapsed?: boolean;

		leftSidebarWidth?: string;
		rightSidebarWidth?: string;

		bottomPanelTitle?: string;
		showBottomPanel?: boolean;
		bottomPanel?: Snippet;
		leftSidebar?: Snippet;
		explorerTitle?: Snippet;
		explorerControls?: Snippet;
		visualizationArea?: Snippet<[number]>;
		tabsList?: Snippet;
		numericalValues?: Snippet;
		savedSolutions?: Snippet;
		rightSidebar?: Snippet;
	}

	let {
		showLeftSidebar = true,
		showRightSidebar = true,

		isLeftSidebarCollapsed = $bindable(false),
		isRightSidebarCollapsed = $bindable(false),

		leftSidebarWidth = 'clamp(16rem, 22vw, 23rem)',
		rightSidebarWidth = 'clamp(19rem, 30vw, 30rem)',
		showBottomPanel = true,

		bottomPanelTitle = 'Numerical values',

		leftSidebar,
		explorerTitle,
		explorerControls,
		visualizationArea,
		tabsList,
		numericalValues,
		savedSolutions,
		bottomPanel,
		rightSidebar
	}: Props = $props();

	let visualizationHeight = $state(0);

	const leftAvailable = $derived(showLeftSidebar && !!leftSidebar);

	const rightAvailable = $derived(showRightSidebar && !!rightSidebar);

	const leftOpen = $derived(leftAvailable && !isLeftSidebarCollapsed);

	const rightOpen = $derived(rightAvailable && !isRightSidebarCollapsed);
</script>

<Sidebar.Provider class="h-[calc(100dvh-3rem)] min-h-0 w-full overflow-hidden">
	<div
		class="method-layout-grid h-full min-h-0 w-full"
		data-left-open={leftOpen ? 'true' : 'false'}
		data-right-open={rightOpen ? 'true' : 'false'}
		style={`
			--method-left-sidebar-width: ${leftSidebarWidth};
			--method-right-sidebar-width: ${rightSidebarWidth};
		`}
	>
		{#if leftAvailable && !leftOpen}
			<Button
				type="button"
				variant="outline"
				size="icon"
				class="absolute top-1/2 left-2 z-[100] h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-md"
				onclick={() => (isLeftSidebarCollapsed = false)}
				aria-label="Show preference panel"
				title="Show preference panel"
			>
				<ChevronRight class="h-4 w-4" />
			</Button>
		{/if}

		{#if rightAvailable && !rightOpen}
			<Button
				type="button"
				variant="outline"
				size="icon"
				class="absolute top-1/2 right-2 z-[100] h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-md"
				onclick={() => (isRightSidebarCollapsed = false)}
				aria-label="Show explanation panel"
				title="Show explanation panel"
			>
				<ChevronLeft class="h-4 w-4" />
			</Button>
		{/if}
		<!-- Left Sidebar: Preferences and Controls -->
		{#if leftAvailable}
			<aside
				class="left-sidebar relative h-full min-h-0"
				class:pointer-events-none={!leftOpen}
				class:invisible={!leftOpen}
			>
				{@render leftSidebar?.()}

				{#if leftOpen}
					<Button
						type="button"
						variant="outline"
						size="icon"
						class="absolute top-1/2 -right-3 z-50 h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-sm"
						onclick={() => (isLeftSidebarCollapsed = true)}
						aria-label="Hide preference panel"
						title="Hide preference panel"
					>
						<ChevronLeft class="h-4 w-4" />
					</Button>
				{/if}
			</aside>
		{/if}

		<Sidebar.Inset
			class="center-area bg-background relative h-full min-h-0 min-w-0 overflow-hidden"
		>
			<div class="flex h-full min-h-0 min-w-0 flex-1 flex-col">
				{#key showBottomPanel}
					<Resizable.PaneGroup direction="vertical" class="h-full min-h-0 w-full flex-1">
						<!-- TOP: SCORE Bands visualization -->
						<Resizable.Pane defaultSize={bottomPanel ? 65 : 50} class="flex min-h-0 flex-col">
							<div class="flex shrink-0 items-center justify-between gap-4 p-3">
								<div class="min-w-0 font-semibold">
									{#if explorerTitle}
										{@render explorerTitle()}
									{:else}
										Solution Explorer
									{/if}
								</div>

								{#if explorerControls}
									<div class="flex shrink-0 items-center gap-2">
										{@render explorerControls()}
									</div>
								{/if}
							</div>

							<div
								class="bg-background mx-2 mb-2 min-h-0 flex-1 overflow-hidden rounded-lg border"
								bind:clientHeight={visualizationHeight}
							>
								<div class="h-full min-h-0 w-full p-2">
									{#if visualizationArea}
										{@render visualizationArea(visualizationHeight)}
									{/if}
								</div>
							</div>
						</Resizable.Pane>

						{#if showBottomPanel}
							<ResizableHandle withHandle />

							<!-- BOTTOM: Generic content, or legacy method tabs -->
							<Resizable.Pane defaultSize={bottomPanel ? 35 : 50} class="flex min-h-0 flex-col">
								{#if bottomPanel}
									<!-- SCORE Bands history graph -->
									<div class="flex h-full min-h-0 flex-col p-2">
										<div class="flex shrink-0 items-center justify-between px-2 py-2">
											<h2 class="text-sm font-semibold">
												{bottomPanelTitle}
											</h2>
										</div>

										<div class="min-h-0 flex-1 overflow-hidden rounded-lg border">
											{@render bottomPanel()}
										</div>
									</div>
								{:else}
									<!-- Original numerical values / saved solutions tabs -->
									<div class="flex h-full min-h-0 flex-col p-2">
										<Tabs.Root value="numerical-values" class="flex h-full min-h-0 flex-col">
											<Tabs.List class="shrink-0">
												{#if tabsList}
													{@render tabsList()}
												{:else}
													<span>{bottomPanelTitle}</span>
												{/if}
											</Tabs.List>

											<Tabs.Content value="numerical-values" class="min-h-0 flex-1 overflow-auto">
												{#if numericalValues}
													{@render numericalValues()}
												{/if}
											</Tabs.Content>

											<Tabs.Content value="saved-solutions" class="min-h-0 flex-1 overflow-auto">
												{#if savedSolutions}
													{@render savedSolutions()}
												{/if}
											</Tabs.Content>
										</Tabs.Root>
									</div>
								{/if}
							</Resizable.Pane>
						{/if}
					</Resizable.PaneGroup>
				{/key}
			</div>
		</Sidebar.Inset>

		<!-- Right Sidebar -->
		{#if rightAvailable}
			<aside
				class="right-sidebar relative h-full min-h-0"
				class:pointer-events-none={!rightOpen}
				class:invisible={!rightOpen}
			>
				{#if rightOpen}
					<Button
						type="button"
						variant="outline"
						size="icon"
						class="absolute top-1/2 -left-3 z-50 h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-sm"
						onclick={() => (isRightSidebarCollapsed = true)}
						aria-label="Hide explanation panel"
						title="Hide explanation panel"
					>
						<ChevronRight class="h-4 w-4" />
					</Button>
				{/if}

				{@render rightSidebar?.()}
			</aside>
		{/if}
	</div>
</Sidebar.Provider>

<style>
	.method-layout-grid {
		position: relative;
		display: grid;

		grid-template-columns:
			var(--left-column-width)
			minmax(0, 1fr)
			var(--right-column-width);

		--left-column-width: 0px;
		--right-column-width: 0px;
	}

	.method-layout-grid[data-left-open='true'] {
		--left-column-width: var(--method-left-sidebar-width);
	}

	.method-layout-grid[data-right-open='true'] {
		--right-column-width: var(--method-right-sidebar-width);
	}

	.left-sidebar {
		grid-column: 1;
		min-width: 0;
		overflow: hidden;
		background: white;
		border-right: 1px solid var(--border-color, #e2e8f0);
	}

	.right-sidebar {
		grid-column: 3;
		min-width: 0;
		overflow: hidden;
		background: white;
		border-left: 1px solid var(--border-color, #e2e8f0);
	}

	.center-area {
		grid-column: 2;
		min-width: 0;
	}

	.method-layout-grid[data-left-open='false'][data-right-open='false'] {
		grid-template-columns: minmax(0, 1fr);
	}

	.method-layout-grid[data-left-open='false'][data-right-open='false'] .center-area {
		grid-column: 1;
	}
</style>
