<script lang="ts">
	/**
	 * ShapWaterfall.svelte
	 * --------------------------------
	 * Waterfall view for one selected SHAP row.
	 *
	 * Bars are classified as improving/impairing using the selected objective
	 * direction (maximize/minimize), matching the other SHAP visualizations.
	 */
	import type { ProblemInfo } from '$lib/types';
	import { COLOR_PALETTE } from '$lib/components/visualizations/utils/colors';

	interface Props {
		shapRow: Record<string, number>;
		selectedOutputSymbol: string;
		problem: ProblemInfo;
		baseline?: number;
		achieved?: number;
		height?: number;
		baselineLabel?: string;
	}

	let {
		shapRow,
		selectedOutputSymbol,
		problem,
		baseline = 0,
		achieved = 0,
		height = 185,
		baselineLabel = 'reference level'
	}: Props = $props();

	function normalizeObjectiveSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function label(symbol: string): string {
		const normalized = normalizeObjectiveSymbol(symbol);
		const obj = problem.objectives.find((o) => o.symbol === normalized);
		return obj?.name ?? normalized;
	}

	function sumContributions(row: Record<string, number> | undefined): number {
		return Object.values(row ?? {}).reduce((sum, value) => sum + Number(value ?? 0), 0);
	}

	const WIDTH = 330;
	const NEAR_ZERO_THRESHOLD = 0.005;
	const MISMATCH_TOLERANCE = 0.01;

	const IMPROVING_COLOR = '#2563eb';
	const IMPAIRING_COLOR = '#ef4444';
	const DARK_COLOR = '#0f172a';

	const objMaximizeMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.maximize ?? false]))
	);

	const selectedOutputMaximize = $derived(
		objMaximizeMap[normalizeObjectiveSymbol(selectedOutputSymbol)] ?? false
	);

	const objectiveColorMap = $derived(
		Object.fromEntries(
			problem.objectives.map((objective, index) => [
				objective.symbol,
				COLOR_PALETTE[index % COLOR_PALETTE.length]
			])
		)
	);

	function isImproving(value: number): boolean {
		return selectedOutputMaximize ? value > 0 : value < 0;
	}

	function objectiveColor(symbol: string): string {
		const normalized = normalizeObjectiveSymbol(symbol);
		return objectiveColorMap[normalized] ?? '#94a3b8';
	}

	const contributionTotal = $derived.by(() => sumContributions(shapRow));

	const waterfallAchieved = $derived(baseline + contributionTotal);
	const totalChange = $derived(waterfallAchieved - baseline);

	const entries = $derived.by(() => {
		return Object.entries(shapRow ?? {})
			.map(([symbol, value]) => ({
				symbol,
				name: label(symbol),
				value: Number(value ?? 0),
				isImproving: isImproving(Number(value ?? 0)),
				isOwn: normalizeObjectiveSymbol(symbol) === normalizeObjectiveSymbol(selectedOutputSymbol)
			}))
			.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
	});

	const hasNegative = $derived(entries.some((e) => e.value < 0));

	const margin = $derived.by(() => ({
		top: hasNegative ? 8 : 12,
		right: 28,
		bottom: 46,
		left: 34
	}));

	const strongestImprovingSymbol = $derived.by(() => {
		return entries.filter((e) => e.isImproving).sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0]
			?.symbol;
	});

	const strongestImpairingSymbol = $derived.by(() => {
		return entries
			.filter((e) => !e.isImproving && Math.abs(e.value) >= NEAR_ZERO_THRESHOLD)
			.sort((a, b) => Math.abs(b.value) - Math.abs(a.value))[0]?.symbol;
	});

	const steps = $derived.by(() => {
		let running = baseline;

		return entries.map((entry) => {
			const start = running;
			const end = running + entry.value;
			running = end;

			return {
				...entry,
				start,
				end,
				low: Math.min(start, end),
				high: Math.max(start, end),
				isStrongestImproving: entry.symbol === strongestImprovingSymbol,
				isStrongestImpairing: entry.symbol === strongestImpairingSymbol,
				isNearZero: Math.abs(entry.value) < NEAR_ZERO_THRESHOLD
			};
		});
	});

	const minY = $derived.by(() => {
		const values = [baseline, waterfallAchieved, ...steps.flatMap((s) => [s.start, s.end])];
		return Math.min(...values);
	});

	const maxY = $derived.by(() => {
		const values = [baseline, waterfallAchieved, ...steps.flatMap((s) => [s.start, s.end])];
		return Math.max(...values);
	});

	const paddedMinY = $derived(minY - Math.abs(maxY - minY || 1) * 0.14);
	const paddedMaxY = $derived(maxY + Math.abs(maxY - minY || 1) * 0.14);

	const plotWidth = $derived(WIDTH - margin.left - margin.right);
	const plotHeight = $derived(height - margin.top - margin.bottom);

	function x(index: number): number {
		const count = Math.max(steps.length, 1);
		return margin.left + (index + 0.5) * (plotWidth / count);
	}

	function barWidth(): number {
		const count = Math.max(steps.length, 1);
		return Math.max(18, Math.min(42, plotWidth / count - 10));
	}

	function y(value: number): number {
		const range = paddedMaxY - paddedMinY || 1;
		return margin.top + ((paddedMaxY - value) / range) * plotHeight;
	}

	function formatSigned(value: number): string {
		const fixed = Math.abs(value).toFixed(2);
		if (value > 0) return `+${fixed}`;
		if (value < 0) return `-${fixed}`;
		return '0.00';
	}
</script>

<div class="waterfall">
	<div class="result-strip">
		<div class="strip-labels">
			<span>{baselineLabel} {baseline.toFixed(2)}</span>
			<strong>result {waterfallAchieved.toFixed(2)}</strong>
		</div>

		<div class="strip-line">
			<span class="start-dot"></span>
			<span class="arrow-line" class:negative={totalChange < 0}></span>
			<span class="end-dot"></span>
		</div>

		<div class="change-badge" class:negative={totalChange < 0}>
			{formatSigned(totalChange)}
		</div>

	</div>

	<svg viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label="Waterfall plot">
		{#each [0, 1, 2] as band}
			<rect
				x={margin.left}
				y={margin.top + (plotHeight / 3) * band}
				width={plotWidth}
				height={plotHeight / 3}
				fill={band % 2 === 0 ? '#fbfdff' : '#ffffff'}
			/>
		{/each}

		{#each steps as step, i}
			{@const bw = barWidth()}
			{@const cx = x(i)}

			{#if i < steps.length - 1}
				<path
					d={`M ${cx + bw / 2} ${y(step.end)} L ${x(i + 1) - bw / 2} ${y(step.end)}`}
					stroke="#64748b"
					stroke-width="1.1"
					stroke-dasharray="3 3"
					opacity="0.55"
					fill="none"
				/>
			{/if}
		{/each}

		{#each steps as step, i}
			{@const bw = barWidth()}
			{@const cx = x(i)}
			{@const axisColor = objectiveColor(step.symbol)}
			{@const shortName = step.name.length > 7 ? `${step.name.slice(0, 7)}…` : step.name}
			{@const topY = y(step.high)}
			{@const bottomY = y(step.low)}
			{@const barH = Math.max(2, bottomY - topY)}
			{@const markerY = step.value >= 0 ? Math.max(margin.top + 8, topY - 17) : Math.max(margin.top + 8, topY - 6)}

			{#if step.isNearZero}
				<line
					x1={cx - bw / 2}
					x2={cx + bw / 2}
					y1={y(step.end)}
					y2={y(step.end)}
					stroke={step.isImproving ? IMPROVING_COLOR : IMPAIRING_COLOR}
					stroke-width="2"
					opacity="0.8"
				/>
			{:else}
				<rect
					x={cx - bw / 2}
					y={topY}
					width={bw}
					height={barH}
					rx="4"
					fill={step.isImproving ? IMPROVING_COLOR : IMPAIRING_COLOR}
					opacity={step.isOwn ? 1 : 0.9}
					stroke={step.isStrongestImproving || step.isStrongestImpairing ? DARK_COLOR : 'transparent'}
					stroke-width={step.isStrongestImproving || step.isStrongestImpairing ? 1.25 : 0}
				/>
			{/if}

			{#if step.isStrongestImpairing}
				<circle cx={cx} cy={markerY} r="6.2" fill="#fff7ed" stroke="#f59e0b" stroke-width="1.1" />
				<text
					x={cx}
					y={markerY + 3.2}
					text-anchor="middle"
					font-size="10"
					font-weight="700"
					fill="#b45309"
				>
					!
				</text>
			{/if}

			{#if step.isStrongestImproving}
				<circle cx={cx} cy={markerY} r="6.2" fill="#eff6ff" stroke="#2563eb" stroke-width="1.1" />
				<text
					x={cx}
					y={markerY + 3.25}
					text-anchor="middle"
					font-size="10"
					font-weight="700"
					fill="#1d4ed8"
				>
					★
				</text>
			{/if}

			{#if !step.isNearZero}
				<text
					x={cx}
					y={step.value >= 0 ? topY - 4 : bottomY + 12}
					text-anchor="middle"
					font-size="10"
					font-weight={step.isStrongestImproving || step.isStrongestImpairing ? '700' : '500'}
					fill="#334155"
				>
					{formatSigned(step.value)}
				</text>
			{/if}

			<rect
				x={cx - 18}
				y={height - 29}
				width="7"
				height="7"
				rx="1.5"
				fill={axisColor}
				stroke="#334155"
				stroke-width="0.5"
			/>

			<text
				x={cx - 8}
				y={height - 22}
				text-anchor="start"
				font-size="0.75rem"
				fill={step.isStrongestImproving || step.isStrongestImpairing ? DARK_COLOR : '#475569'}
				font-weight={step.isStrongestImproving || step.isStrongestImpairing ? '700' : '400'}
			>
				{shortName}
			</text>

			{#if step.isOwn}
				<circle cx={cx} cy={height - 13} r="2.5" fill={DARK_COLOR} opacity="0.55" />
			{/if}
		{/each}
	</svg>

	<div class="legend">
		<span class="legend-item">
			<i class="swatch positive"></i>
			Improving effect
		</span>
		<span class="legend-item">
			<i class="swatch negative"></i>
			Impairing effect
		</span>
		<span class="legend-item legend-item-symbol">
			<i class="marker-star">★</i>
			Strongest improving
		</span>
		<span class="legend-item legend-item-symbol">
			<i class="marker-warning">!</i>
			Strongest impairing
		</span>
	</div>
</div>

<style>
	.waterfall {
		width: 100%;
		border-radius: 0.5rem;
		background: white;
	}

	.result-strip {
		padding: 0.25rem 0.25rem 0.15rem;
	}

	.strip-labels {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.75rem;
		color: #64748b;
	}

	.strip-labels strong {
		color: #0f172a;
	}

	.strip-line {
		display: grid;
		grid-template-columns: auto 1fr auto;
		align-items: center;
		margin-top: 0.15rem;
	}

	.start-dot,
	.end-dot {
		width: 0.45rem;
		height: 0.45rem;
		border-radius: 999px;
		background: #94a3b8;
		z-index: 1;
	}

	.end-dot {
		background: #0f172a;
	}

	.arrow-line {
		height: 0.16rem;
		background: #2563eb;
		position: relative;
	}

	.arrow-line::after {
		content: '';
		position: absolute;
		right: -1px;
		top: 50%;
		transform: translateY(-50%);
		border-left: 0.45rem solid #2563eb;
		border-top: 0.3rem solid transparent;
		border-bottom: 0.3rem solid transparent;
	}

	.arrow-line.negative {
		background: #ef4444;
	}

	.arrow-line.negative::after {
		border-left-color: #ef4444;
	}

	.change-badge {
		width: fit-content;
		margin: 0.25rem auto 0;
		border-radius: 999px;
		background: #dbeafe;
		color: #2563eb;
		padding: 0.1rem 0.75rem;
		font-size: 0.7rem;
		font-weight: 700;
	}

	.change-badge.negative {
		background: #fee2e2;
		color: #ef4444;
	}

	svg {
		width: 100%;
		height: auto;
		display: block;
	}

	.legend {
		display: flex;
		flex-wrap: wrap;
		gap: 0.55rem;
		align-items: center;
		padding: 0.35rem 0.25rem 0;
		font-size: 0.68rem;
		color: #64748b;
	}

	.legend-item {
		display: inline-flex;
		align-items: center;
		gap: 0.35rem;
		padding: 0.18rem 0.48rem;
		border: 1px solid #e2e8f0;
		border-radius: 999px;
		background: #f8fafc;
		color: #475569;
		line-height: 1;
	}

	.legend-item-symbol {
		font-weight: 600;
	}

	.swatch,
	.marker-star,
	.marker-warning {
		display: inline-block;
		flex: 0 0 auto;
}

	.swatch {
		width: 0.65rem;
		height: 0.65rem;
		border-radius: 0.15rem;
		border: 1px solid rgba(51, 65, 85, 0.2);
	}

	.positive {
		background: #2563eb;
	}

	.negative {
		background: #ef4444;
	}

	.marker-star {
		width: 0.95rem;
		height: 0.95rem;
		border-radius: 999px;
		background: #eff6ff;
		border: 1px solid #2563eb;
		text-align: center;
		font-style: normal;
		font-size: 0.72rem;
		font-weight: 700;
		line-height: 0.9rem;
		color: #1d4ed8;
	}

	.marker-warning {
		width: 0.95rem;
		height: 0.95rem;
		border-radius: 999px;
		background: #fff7ed;
		border: 1px solid #f59e0b;
		color: #b45309;
		font-style: normal;
		font-size: 0.72rem;
		font-weight: 700;
		line-height: 0.9rem;
		text-align: center;
	}
</style>