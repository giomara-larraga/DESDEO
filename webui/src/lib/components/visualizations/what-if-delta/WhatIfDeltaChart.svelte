<script lang="ts">
	type ScenarioDelta = {
		symbol: string;
		name: string;
		delta: number;
		percentDelta: number | null;
		isImprovement: boolean;
	};

	interface Props {
		deltas: ScenarioDelta[];
		selectedObjectiveSymbol: string;
		mode?: 'value' | 'percent';
		valueDigits?: number;
		percentDigits?: number;
		tolerance?: number;
	}

	let {
		deltas,
		selectedObjectiveSymbol,
		mode = 'value',
		valueDigits = 3,
		percentDigits = 2,
		tolerance = 1e-10
	}: Props = $props();

	// Keep the selected objective first, but preserve the order
	// of all remaining objectives.
	let orderedDeltas = $derived.by(() => {
		const selected = deltas.find((delta) => delta.symbol === selectedObjectiveSymbol);

		const rest = deltas.filter((delta) => delta.symbol !== selectedObjectiveSymbol);

		return selected ? [selected, ...rest] : rest;
	});

	function metricValue(delta: ScenarioDelta): number | null {
		if (mode === 'percent') {
			return delta.percentDelta != null && Number.isFinite(delta.percentDelta)
				? delta.percentDelta
				: null;
		}

		return Number.isFinite(delta.delta) ? delta.delta : null;
	}

	let maxAbsValue = $derived.by(() => {
		const values = orderedDeltas
			.map(metricValue)
			.filter((value): value is number => value != null && Number.isFinite(value));

		return Math.max(...values.map((value) => Math.abs(value)), 0);
	});

	function isNoChange(delta: ScenarioDelta): boolean {
		const value = metricValue(delta);

		return value != null && Math.abs(value) <= tolerance;
	}

	function barWidth(delta: ScenarioDelta): number {
		const value = metricValue(delta);

		if (value == null || maxAbsValue === 0 || Math.abs(value) <= tolerance) {
			return 0;
		}

		// Each side of the diverging chart has at most 50%
		// of the available width.
		return Math.min(50, (Math.abs(value) / maxAbsValue) * 50);
	}

	function formatSigned(value: number): string {
		const absolute = Math.abs(value).toFixed(valueDigits);

		if (value > 0) return `+${absolute}`;
		if (value < 0) return `-${absolute}`;

		return Number(0).toFixed(valueDigits);
	}

	function formatSignedPercent(value: number | null): string {
		if (value == null || !Number.isFinite(value)) {
			return 'n/a';
		}

		const absolute = Math.abs(value).toFixed(percentDigits);

		if (value > 0) return `+${absolute}%`;
		if (value < 0) return `-${absolute}%`;

		return `${Number(0).toFixed(percentDigits)}%`;
	}

	function formattedValue(delta: ScenarioDelta): string {
		if (isNoChange(delta)) return 'No change';

		if (mode === 'percent') {
			return formatSignedPercent(delta.percentDelta);
		}

		return formatSigned(delta.delta);
	}
</script>

<div class="w-full">
	<!-- Axis labels -->
	<div class="mb-1 grid grid-cols-[84px_1fr_76px] items-end gap-2 text-[10px] text-gray-400">
		<span>Achieved value</span>

		<div class="grid grid-cols-3">
			<span>Worsened</span>
			<span class="text-center">0</span>
			<span class="text-right">Improved</span>
		</div>

		<span class="text-right">
			{mode === 'percent' ? 'Change (%)' : 'Change'}
		</span>
	</div>

	<div class="space-y-1">
		{#each orderedDeltas as delta}
			{@const value = metricValue(delta)}
			{@const width = barWidth(delta)}
			{@const selected = delta.symbol === selectedObjectiveSymbol}
			{@const unchanged = isNoChange(delta)}

			<div
				class={`grid grid-cols-[84px_1fr_76px] items-center gap-2 rounded px-1 py-1.5 text-sm ${
					selected ? 'bg-blue-50' : ''
				}`}
			>
				<!-- Objective -->
				<div class="min-w-0" title={delta.name}>
					<div class="flex items-center gap-1">
						{#if selected}
							<span class="shrink-0 font-semibold text-blue-700" aria-label="Selected objective">
								◆
							</span>
						{/if}

						<span
							class={`truncate ${
								selected ? 'font-semibold text-gray-900' : 'font-medium text-gray-700'
							}`}
						>
							{delta.name}
						</span>
					</div>
				</div>

				<!-- Diverging bar -->
				<div class="relative h-6">
					<!-- Zero line -->
					<div class="absolute left-1/2 top-0 h-full w-px bg-gray-300" aria-hidden="true"></div>

					{#if value == null}
						<!-- unavailable -->
						<div
							class="absolute left-1/2 top-1/2 w-5 -translate-x-1/2 -translate-y-1/2 border-t border-dashed border-gray-300"
							aria-hidden="true"
						></div>
					{:else if unchanged}
						<!-- Explicit no-change marker -->
						<div
							class="absolute left-1/2 top-1/2 h-2 w-2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-gray-400"
							aria-hidden="true"
						></div>
					{:else if delta.isImprovement}
						<!-- Improvement extends right -->
						<div
							class="absolute left-1/2 top-1/2 h-2.5 -translate-y-1/2 rounded-r bg-[#0C7BDC]"
							style={`width: ${width}%`}
							aria-hidden="true"
						></div>
					{:else}
						<!-- Worsening extends left -->
						<div
							class="absolute right-1/2 top-1/2 h-2.5 -translate-y-1/2 rounded-l bg-[#DC3220]"
							style={`width: ${width}%`}
							aria-hidden="true"
						></div>
					{/if}
				</div>

				<!-- Numeric result -->
				<div
					class={`text-right font-mono text-xs ${
						value == null || unchanged
							? 'text-gray-500'
							: delta.isImprovement
								? 'text-[#0C7BDC]'
								: 'text-[#DC3220]'
					}`}
				>
					{formattedValue(delta)}
				</div>
			</div>
		{/each}
	</div>

	<!-- Legend -->
	<div class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-[10px] text-gray-500">
		<span class="inline-flex items-center gap-1">
			<span class="h-0.5 w-3 bg-[#0C7BDC]" aria-hidden="true"></span>
			Improved
		</span>

		<span class="inline-flex items-center gap-1">
			<span class="h-0.5 w-3 bg-[#DC3220]" aria-hidden="true"></span>
			Worsened
		</span>

		<span class="inline-flex items-center gap-1">
			<span class="h-1.5 w-1.5 rounded-full bg-gray-400" aria-hidden="true"></span>
			No change
		</span>

		<span class="inline-flex items-center gap-1">
			<span class="font-semibold text-blue-700" aria-hidden="true"> ◆ </span>
			Selected objective
		</span>
	</div>
</div>
