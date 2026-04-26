<script lang="ts">
	import { ParallelCoordinatesHistory } from '$lib/components/visualizations/parallel-coordinates';

	type DataPoint = Record<string, number>;
	type HistoryIteration = {
		id?: string | number;
		name?: string;
		data: DataPoint[];
		show?: boolean;
		color?: string;
		referencePoint?: DataPoint;
	};

	type HistoryDimension = {
		symbol: string;
		name: string;
		min?: number;
		max?: number;
		direction?: 'min' | 'max';
	};

	interface Props {
		height?: number;
		iterations?: HistoryIteration[];
		dimensions?: HistoryDimension[];
	}

	const { height = undefined, iterations = [], dimensions = [] }: Props = $props();

	let containerElement: HTMLDivElement;
	let containerSize = $state({ width: 0, height: 0 });

	$effect(() => {
		if (!containerElement) return;

		const resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const { width, height } = entry.contentRect;
				containerSize = { width, height };
			}
		});

		resizeObserver.observe(containerElement);
		return () => resizeObserver.disconnect();
	});

	const plotHeight = $derived(height || Math.max(containerSize.height - 16, 10));
	const hasPlottableData = $derived(
		iterations.some((iteration) =>
			(iteration.show ?? true) &&
			((iteration.data && iteration.data.length > 0) || iteration.referencePoint != null)
		)
	);
</script>

<div bind:this={containerElement} class="flex h-full w-full flex-col overflow-hidden p-4">
	{#if dimensions.length > 0 && hasPlottableData}
		<div class="w-full border-gray-200 pb-5" style="height: {plotHeight}px;">
			<ParallelCoordinatesHistory
				{iterations}
				{dimensions}
			/>
		</div>
	{:else}
		<div class="flex h-full items-center justify-center rounded border bg-gray-50 p-8 text-center text-gray-500">
			No history data selected for visualization.
		</div>
	{/if}
</div>