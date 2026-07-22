<script lang="ts">
	interface Effect {
		symbol: string;
		name: string;
		value: number;
		maximize?: boolean;
	}

	interface Props {
		effects: Record<string, number>;
		heightPerRow?: number;
		showValues?: boolean;
		valueFormatter?: (value: number) => string;
	}

	let {
		effects,
		heightPerRow = 34,
		showValues = true,
		valueFormatter = defaultValueFormatter
	}: Props = $props();

	let containerWidth = $state(0);

	const margin = {
		top: 12,
		right: 52,
		bottom: 12,
		left: 118
	};

	const minimumChartWidth = 320;

	const chartWidth = $derived(
		Math.max(containerWidth || minimumChartWidth, minimumChartWidth)
	);

	const chartHeight = $derived(
		Math.max(
			margin.top + margin.bottom + effects.length * heightPerRow,
			80
		)
	);

	/*
	 * Convert the raw SHAP effect into a semantic effect:
	 *
	 * Positive semantic value = supports the objective.
	 * Negative semantic value = limits the objective.
	 *
	 * For minimized objectives, decreasing the achieved value is supportive,
	 * so the raw SHAP sign is reversed.
	 */
	const normalizedEffects = $derived(
		effects
			? Object.entries(effects).map(([symbol, value]) => ({
                    symbol,
                    name: symbol,
                    value,
                    semanticValue: value
                }))
            : []
	);

	const maximumAbsoluteEffect = $derived(
		Math.max(
			...normalizedEffects.map((effect) =>
				Math.abs(effect.semanticValue)
			),
			0
		)
	);

	const plotWidth = $derived(
		Math.max(chartWidth - margin.left - margin.right, 80)
	);

	const halfPlotWidth = $derived(plotWidth / 2);

	const centerX = $derived(margin.left + halfPlotWidth);

	function effectWidth(value: number): number {
		if (maximumAbsoluteEffect === 0) return 0;

		return (
			(Math.abs(value) / maximumAbsoluteEffect) *
			halfPlotWidth
		);
	}

	function barX(value: number): number {
		const width = effectWidth(value);

		return value < 0 ? centerX - width : centerX;
	}

	function defaultValueFormatter(value: number): string {
		const absoluteValue = Math.abs(value);

		if (absoluteValue === 0) return '0';

		if (absoluteValue >= 1000) {
			return new Intl.NumberFormat(undefined, {
				notation: 'compact',
				maximumFractionDigits: 1
			}).format(value);
		}

		if (absoluteValue >= 10) {
			return value.toFixed(1);
		}

		return value.toFixed(2);
	}

	function truncateLabel(label: string, maximumLength = 18): string {
		if (label.length <= maximumLength) return label;

		return `${label.slice(0, maximumLength - 1)}…`;
	}

	function valueLabelX(value: number): number {
		const width = effectWidth(value);

		if (value < 0) {
			return centerX - width - 5;
		}

		return centerX + width + 5;
	}

	function valueLabelAnchor(
		value: number
	): 'start' | 'end' {
		return value < 0 ? 'end' : 'start';
	}
</script>

<div class="w-full">
	<div
		class="mb-2 flex flex-wrap items-center justify-between gap-2"
	>
		<div
			class="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs text-gray-500"
			aria-label="Effect direction legend"
		>
			<span class="inline-flex items-center gap-1.5">
				<span
					class="h-2.5 w-2.5 rounded-sm bg-[#0C7BDC]"
					aria-hidden="true"
				></span>
				Supports
			</span>

			<span class="inline-flex items-center gap-1.5">
				<span
					class="h-2.5 w-2.5 rounded-sm bg-[#DC3220]"
					aria-hidden="true"
				></span>
				Limits
			</span>
		</div>

		<span class="text-xs text-gray-400">
			Stronger effects have longer bars
		</span>
	</div>

	<div
		class="w-full overflow-hidden"
		bind:clientWidth={containerWidth}
	>
		{#if normalizedEffects.length === 0}
			<div
				class="flex min-h-24 items-center justify-center rounded-md border border-dashed border-gray-200 px-4 py-6 text-center text-xs text-gray-500"
			>
				No effects are available for this desired value.
			</div>
		{:else}
			<svg
				width="100%"
				height={chartHeight}
				viewBox={`0 0 ${chartWidth} ${chartHeight}`}
				role="img"
				aria-labelledby="desired-effects-title desired-effects-description"
				class="block overflow-visible"
			>
				<title id="desired-effects-title">
					Effects on achieved objective values
				</title>

				<desc id="desired-effects-description">
					A diverging bar chart. Supporting effects extend to the
					right and limiting effects extend to the left.
				</desc>

				<!-- Direction labels -->
				<text
					x={centerX - 8}
					y={9}
					text-anchor="end"
					class="fill-gray-400 text-[10px]"
				>
					Limits
				</text>

				<text
					x={centerX + 8}
					y={9}
					text-anchor="start"
					class="fill-gray-400 text-[10px]"
				>
					Supports
				</text>

				<!-- Central zero line -->
				<line
					x1={centerX}
					x2={centerX}
					y1={margin.top}
					y2={chartHeight - margin.bottom}
					stroke="#D1D5DB"
					stroke-width="1"
				/>

				{#each normalizedEffects as effect, index (effect.symbol)}
					{@const rowCenter =
						margin.top +
						index * heightPerRow +
						heightPerRow / 2}

					{@const barHeight = Math.min(
						18,
						heightPerRow - 8
					)}

					{@const width = effectWidth(
						effect.semanticValue
					)}

					<g>
						<title>
							{effect.name}: {effect.semanticValue > 0
								? 'supports'
								: 'limits'} the achieved objective
							({valueFormatter(effect.semanticValue)}).
							Raw SHAP value:
							{valueFormatter(effect.value)}.
						</title>

						<!-- Objective label -->
						<text
							x={margin.left - 8}
							y={rowCenter}
							dominant-baseline="middle"
							text-anchor="end"
							class="fill-gray-600 text-[11px]"
						>
							{truncateLabel(effect.name)}
						</text>

						<!-- Faint row guide -->
						<line
							x1={margin.left}
							x2={chartWidth - margin.right}
							y1={rowCenter}
							y2={rowCenter}
							stroke="#F3F4F6"
							stroke-width="1"
						/>

						<!-- Effect bar -->
						<rect
							x={barX(effect.semanticValue)}
							y={rowCenter - barHeight / 2}
							width={width}
							height={barHeight}
							rx="3"
							fill={effect.semanticValue >= 0
								? '#0C7BDC'
								: '#DC3220'}
							opacity="0.9"
						/>

						<!-- Zero marker for effects equal to zero -->
						{#if width === 0}
							<circle
								cx={centerX}
								cy={rowCenter}
								r="2"
								fill="#9CA3AF"
							/>
						{/if}

						{#if showValues}
							<text
								x={valueLabelX(effect.semanticValue)}
								y={rowCenter}
								dominant-baseline="middle"
								text-anchor={valueLabelAnchor(
									effect.semanticValue
								)}
								class="fill-gray-500 text-[10px] tabular-nums"
							>
								{valueFormatter(effect.semanticValue)}
							</text>
						{/if}
					</g>
				{/each}
			</svg>
		{/if}
	</div>
</div>