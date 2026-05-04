<script lang="ts">
	import type { ProblemInfo } from '$lib/types';

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

	const width = 330;
	const nearZeroThreshold = 0.005;

	const helpColor = '#2563eb';
	const hurtColor = '#ef4444';
	const darkColor = '#0f172a';

	const contributionTotal = $derived.by(() => {
		return Object.values(shapRow ?? {}).reduce((sum, value) => sum + Number(value ?? 0), 0);
	});

	const waterfallAchieved = $derived(baseline + contributionTotal);
	const totalChange = $derived(waterfallAchieved - baseline);

	const entries = $derived.by(() => {
		return Object.entries(shapRow ?? {})
			.map(([symbol, value]) => ({
				symbol,
				name: label(symbol),
				value: Number(value ?? 0),
				isOwn: normalizeObjectiveSymbol(symbol) === normalizeObjectiveSymbol(selectedOutputSymbol)
			}))
			.sort((a, b) => Math.abs(b.value) - Math.abs(a.value));
	});

	const hasNegative = $derived(entries.some((e) => e.value < 0));

	const margin = $derived.by(() => ({
		top: hasNegative ? 14 : 22,
		right: 28,
		bottom: 46,
		left: 34
	}));

	const strongestPositiveSymbol = $derived.by(() => {
		return entries.filter((e) => e.value > 0).sort((a, b) => b.value - a.value)[0]?.symbol;
	});

	const strongestNegativeSymbol = $derived.by(() => {
		return entries.filter((e) => e.value < 0).sort((a, b) => a.value - b.value)[0]?.symbol;
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
				isStrongestPositive: entry.symbol === strongestPositiveSymbol,
				isStrongestNegative: entry.symbol === strongestNegativeSymbol,
				isNearZero: Math.abs(entry.value) < nearZeroThreshold
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

	const plotWidth = $derived(width - margin.left - margin.right);
	const plotHeight = $derived(height - margin.top - margin.bottom);

	const mismatch = $derived(Math.abs(achieved - waterfallAchieved) > 0.01);

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

    $effect(() => {
	const shapSum = Object.values(shapRow ?? {}).reduce(
		(sum, value) => sum + Number(value ?? 0),
		0
	);

	console.log('Waterfall debug', {
		selectedOutputSymbol,
		baseline,
		shapSum,
		reconstructed: baseline + shapSum,
		achieved,
		difference: achieved - (baseline + shapSum),
		shapRow
	});
});
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

		{#if mismatch}
			<div class="mismatch-note">
				Shown result is reconstructed from the bars.
			</div>
		{/if}
	</div>

	<svg viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Waterfall plot">
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
			{@const topY = y(step.high)}
			{@const bottomY = y(step.low)}
			{@const barH = Math.max(2, bottomY - topY)}

			{#if step.isNearZero}
				<line
					x1={cx - bw / 2}
					x2={cx + bw / 2}
					y1={y(step.end)}
					y2={y(step.end)}
					stroke={step.value >= 0 ? helpColor : hurtColor}
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
					fill={step.value >= 0 ? helpColor : hurtColor}
					opacity={step.isOwn ? 1 : 0.9}
					stroke={step.isStrongestPositive || step.isStrongestNegative ? darkColor : 'transparent'}
					stroke-width={step.isStrongestPositive || step.isStrongestNegative ? 1.25 : 0}
				/>
			{/if}

			{#if step.isStrongestNegative}
				<text x={cx} y={topY - 2} text-anchor="middle" font-size="11">⚠</text>
			{/if}

			{#if step.isStrongestPositive}
				<text x={cx} y={topY - 2} text-anchor="middle" font-size="11">★</text>
			{/if}

			{#if !step.isNearZero}
				<text
					x={cx}
					y={step.value >= 0 ? topY - 4 : bottomY + 12}
					text-anchor="middle"
					font-size="9"
					font-weight={step.isStrongestPositive || step.isStrongestNegative ? '700' : '500'}
					fill="#334155"
				>
					{formatSigned(step.value)}
				</text>
			{/if}

			<text
				x={cx}
				y={height - 22}
				text-anchor="middle"
				font-size="9"
				fill={step.isStrongestPositive || step.isStrongestNegative ? darkColor : '#475569'}
				font-weight={step.isStrongestPositive || step.isStrongestNegative ? '700' : '400'}
			>
				{step.name.length > 7 ? `${step.name.slice(0, 7)}…` : step.name}
			</text>

			{#if step.isOwn}
				<circle cx={cx} cy={height - 13} r="2.5" fill={darkColor} opacity="0.55" />
			{/if}
		{/each}
	</svg>

	<div class="legend">
		<span><i class="positive"></i> Helps</span>
		<span><i class="negative"></i> Hurts</span>
		<span class="legend-symbol">★ strongest help</span>
		<span class="legend-symbol">⚠ strongest limit</span>
	</div>
</div>

<style>
	.waterfall {
		width: 100%;
		border-radius: 0.5rem;
		background: white;
	}

	.result-strip {
		padding: 0.25rem 0.25rem 0.35rem;
	}

	.strip-labels {
		display: flex;
		justify-content: space-between;
		align-items: center;
		font-size: 0.7rem;
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

	.mismatch-note {
		margin-top: 0.2rem;
		text-align: center;
		font-size: 0.65rem;
		color: #94a3b8;
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
		padding: 0.25rem 0.25rem 0;
		font-size: 0.68rem;
		color: #64748b;
	}

	.legend span {
		display: inline-flex;
		align-items: center;
		gap: 0.25rem;
	}

	.legend-symbol {
		color: #475569;
	}

	i {
		display: inline-block;
		width: 0.65rem;
		height: 0.65rem;
		border-radius: 0.15rem;
	}

	.positive {
		background: #2563eb;
	}

	.negative {
		background: #ef4444;
	}
</style>