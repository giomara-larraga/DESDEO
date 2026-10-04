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

		bottomPanelTitle = 'Numerical values',

		leftSidebar,
		explorerTitle,
		explorerControls,
		visualizationArea,
		tabsList,
		numericalValues,
		savedSolutions,
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
				class="absolute left-2 top-1/2 z-[100] h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-md"
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
				class="absolute right-2 top-1/2 z-[100] h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-md"
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
						class="absolute -right-3 top-1/2 z-50 h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-sm"
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
			class="center-area relative h-full min-h-0 min-w-0 overflow-hidden bg-background"
		>
			<div class="flex h-full min-h-0 min-w-0 flex-1 flex-col">
				<Resizable.PaneGroup direction="vertical" class="h-full min-h-0 w-full flex-1">
					<Resizable.Pane defaultSize={50} class="flex min-h-0 flex-col">
						<!-- Top Panel: Explorer Title and Controls -->
						<div class="flex-shrink-0 p-2">
							<div class="flex flex-row items-center justify-between gap-4 pb-2">
								<div class="font-semibold">
									{#if explorerTitle}
										{@render explorerTitle()}
									{:else}
										Solution Explorer
									{/if}
								</div>
								<div class="flex items-center gap-2">
									{#if explorerControls}
										{@render explorerControls()}
									{/if}
								</div>
							</div>
						</div>
						<!-- Visualization Area -->
						<div
							class="mx-2 min-h-0 flex-1 rounded border bg-gray-100 p-4"
							bind:clientHeight={visualizationHeight}
						>
							<!-- Main Visualization Area -->
							<div class="h-full w-full">
								<div class="grid h-full w-full gap-4 xl:grid-cols-1">
									<div class="h-full flex-1 rounded">
										{#if visualizationArea}
											{@render visualizationArea(visualizationHeight)}
										{/if}
									</div>
								</div>
							</div>
						</div>
					</Resizable.Pane>

					<ResizableHandle />
					<!-- Bottom Panel: Numerical Values and Tables -->
					<Resizable.Pane defaultSize={50} class="flex min-h-0 flex-col">
						<div class="min-h-0 w-full flex-shrink p-2">
							<Tabs.Root value="numerical-values" class="flex h-full flex-shrink flex-col">
								<Tabs.List class="flex-shrink-0">
									{#if tabsList}
										{@render tabsList()}
									{:else}
										<span class="text-black">{bottomPanelTitle}</span>
									{/if}
								</Tabs.List>

								<!-- Numerical Values Tab Content -->
								<Tabs.Content value="numerical-values" class="min-h-0">
									{#if numericalValues}
										{@render numericalValues()}
									{:else}
										<div class="p-4">Default numerical values content</div>
									{/if}
								</Tabs.Content>

								<!-- Saved Solutions Tab Content -->
								<Tabs.Content value="saved-solutions" class="min-h-0 flex-grow">
									{#if savedSolutions}
										{@render savedSolutions()}
									{:else}
										<div class="p-4">Default saved solutions content</div>
									{/if}
								</Tabs.Content>
							</Tabs.Root>
						</div>
					</Resizable.Pane>
				</Resizable.PaneGroup>
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
						class="absolute -left-3 top-1/2 z-50 h-8 w-8 -translate-y-1/2 rounded-full bg-white shadow-sm"
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
</style>
