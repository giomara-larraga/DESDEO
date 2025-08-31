<script lang="ts">
	import * as Resizable from '$lib/components/ui/resizable/index.js';
	import * as Tabs from '$lib/components/ui/tabs/index.js';
	import type { Snippet } from 'svelte';
	import ResizableHandle from '$lib/components/ui/resizable/resizable-handle.svelte';

	interface Props {
		showLeftSidebar?: boolean;
		showRightSidebar?: boolean;
		leftSidebar?: Snippet;
		topPanel?: Snippet;
		bottomPanel?: Snippet;
		rightSidebar?: Snippet;
		menuRow?: Snippet;
	}

	let {
		showLeftSidebar = true,
		showRightSidebar = true,
		leftSidebar,
		topPanel,
		bottomPanel,
		rightSidebar,
		menuRow
	}: Props = $props();

	let horizontalSizes =
		showLeftSidebar && showRightSidebar
			? [20, 60, 20]
			: showLeftSidebar || showRightSidebar
				? [20, 80]
				: [100];
	let verticalSizes = [70, 30]; // top panel & bottom tabs
</script>

<div class="flex h-[calc(100vh-3rem)] w-full flex-col">
	<Resizable.PaneGroup direction="horizontal" class="h-full">
		<!-- Left Sidebar -->
		{#if showLeftSidebar}
			<Resizable.Pane defaultSize={horizontalSizes[0]} minSize={0}>
				{#if leftSidebar}
					{@render leftSidebar()}
				{/if}
			</Resizable.Pane>
			<!--       <Resizable.Handle>
        <button
          class="p-1 text-sm hover:bg-gray-200 rounded"
          on:click={() => showLeftSidebar = false}
        >
          ⏴
        </button>
      </Resizable.Handle> -->
			<Resizable.Handle withHandle />
		{/if}

		<!-- Main Vertical Split -->
		<Resizable.Pane
			defaultSize={horizontalSizes[1]}
			minSize={horizontalSizes[1]}
			class="flex min-h-0 flex-1 flex-col"
		>
			<!-- Fixed Menu Row (NOT resizable) -->
			<div class="flex-shrink-0 border-b bg-gray-50 p-2">
				{#if menuRow}
					{@render menuRow()}
				{:else}
					<span class="font-semibold">Menu</span>
				{/if}
			</div>

			<!-- Resizable Top/Bottom Panel -->
			<Resizable.PaneGroup direction="vertical" class="flex-1">
				<!-- Top Panel: Explorer & Visualization -->
				<Resizable.Pane class="flex min-h-0 flex-col">
					<div class="mx-2 flex-1 overflow-auto rounded border bg-gray-100 p-4">
						{#if topPanel}
							{@render topPanel()}
						{/if}
					</div>
				</Resizable.Pane>

				<Resizable.Handle withHandle />

				<!-- Bottom Panel: Tabs -->
				<Resizable.Pane class="flex min-h-0 flex-col p-2">
					{#if bottomPanel}
						{@render bottomPanel()}
					{:else}
						<div class="p-4">Default bottom panel content</div>
					{/if}
				</Resizable.Pane>
			</Resizable.PaneGroup>
		</Resizable.Pane>

		<!-- Right Sidebar -->
		{#if showRightSidebar}
			<Resizable.Handle withHandle />

			<Resizable.Pane defaultSize={horizontalSizes[horizontalSizes.length - 1]} minSize={0}>
				{#if rightSidebar}
					{@render rightSidebar()}
				{/if}
			</Resizable.Pane>
		{/if}
	</Resizable.PaneGroup>
</div>
