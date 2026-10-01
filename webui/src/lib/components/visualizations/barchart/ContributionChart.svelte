<script lang="ts">
	import { scaleBand, scaleLinear } from 'd3-scale';
	import { formatNumber } from '$lib/helpers';

	type ContributionRow = {
		symbol: string;
		name: string;
		rawValue: number;
		helpScore: number;
		isOwn: boolean;
		isHelpful: boolean;
	};

	interface Props {
		contributions: ContributionRow[];
		suggestedDesiredValueName?: string | null;
		digits?: number;
		showOwnContribution?: boolean;
	}

	let {
		contributions,
		suggestedDesiredValueName = null,
		digits = 2,
		showOwnContribution = false
	}: Props = $props();

	const width = 360;
	const height = 210;

	const margin = {
		top: 28,
		right: 16,
		bottom: 42,
		left: 16
	};

	const plotTop = margin.top;
	const plotBottom = height - margin.bottom;
	const plotLeft = margin.left;
	const plotRight = width - margin.right;

	let rows = $derived.by(() =>
		contributions
			.filter((row) => showOwnContribution || !row.isOwn)
			.toSorted((a, b) => Math.abs(b.helpScore) - Math.abs(a.helpScore))
	);

	let maxMagnitude = $derived.by(() => {
		const maximum = Math.max(...rows.map((row) => Math.abs(row.helpScore)), 0);

		return maximum || 1;
	});

	// Symmetric scale keeps supportive and limiting magnitudes comparable.
	let y = $derived.by(() =>
		scaleLinear().domain([-maxMagnitude, maxMagnitude]).range([plotBottom, plotTop])
	);

	let x = $derived.by(() =>
		scaleBand<string>()
			.domain(rows.map((row) => row.symbol))
			.range([plotLeft, plotRight])
			.padding(0.35)
	);

	let zeroY = $derived(y(0));

	function barY(value: number): number {
		return value >= 0 ? y(value) : zeroY;
	}

	function barHeight(value: number): number {
		return Math.abs(y(value) - zeroY);
	}

	function isSuggested(row: ContributionRow): boolean {
		return suggestedDesiredValueName !== null && row.name === suggestedDesiredValueName;
	}
</script>

<div class="w-full">
	<!-- Direction labels -->

	<svg
		viewBox={`0 0 ${width} ${height}`}
		class="block w-full overflow-visible"
		role="img"
		aria-label="Desired-value contributions to the selected achieved value"
	>
		<!-- Zero baseline -->
		<line x1={plotLeft} x2={plotRight} y1={zeroY} y2={zeroY} stroke="#9ca3af" stroke-width="1" />

		<!-- Subtle upper/lower guides -->
		<line
			x1={plotLeft}
			x2={plotRight}
			y1={plotTop}
			y2={plotTop}
			stroke="#e5e7eb"
			stroke-width="1"
			stroke-dasharray="3 3"
		/>

		<line
			x1={plotLeft}
			x2={plotRight}
			y1={plotBottom}
			y2={plotBottom}
			stroke="#e5e7eb"
			stroke-width="1"
			stroke-dasharray="3 3"
		/>

		{#each rows as row}
			{@const barX = x(row.symbol) ?? 0}
			{@const barWidth = x.bandwidth()}
			{@const suggested = isSuggested(row)}

			<g>
				<title>
					{row.name}: {row.helpScore >= 0 ? 'supportive' : 'limiting'} contribution,
					{formatNumber(Math.abs(row.helpScore), digits)}
					{suggested ? ' — R-XIMO suggested candidate' : ''}
				</title>

				<!-- Contribution bar -->
				<rect
					x={barX}
					y={barY(row.helpScore)}
					width={barWidth}
					height={Math.max(barHeight(row.helpScore), 1)}
					rx="2"
					fill={row.helpScore >= 0 ? '#3b82f6' : '#ef4444'}
					opacity="0.8"
					stroke={suggested ? '#d97706' : 'none'}
					stroke-width={suggested ? 2.5 : 0}
				/>

				<!-- Contribution magnitude -->
				<!-- 				<text
					x={barX + barWidth / 2}
					y={row.helpScore >= 0
						? barY(row.helpScore) - 5
						: barY(row.helpScore) + barHeight(row.helpScore) + 11}
					text-anchor="middle"
					font-size="8"
					font-weight="600"
					fill={row.helpScore >= 0 ? '#1d4ed8' : '#b91c1c'}
				>
					{formatNumber(Math.abs(row.helpScore), digits)}
				</text> -->

				<!-- R-XIMO suggested candidate -->
				{#if suggested}
					<text
						x={barX + barWidth / 2}
						y={zeroY - 4}
						text-anchor="middle"
						font-size="11"
						fill="#d97706"
						font-weight="700"
					>
						★
					</text>
				{/if}

				<!-- Objective symbol -->
				<text
					x={barX + barWidth / 2}
					y={height - 20}
					text-anchor="middle"
					font-size="9"
					font-weight={suggested ? '700' : '500'}
					fill={suggested ? '#b45309' : '#4b5563'}
				>
					{row.name}
				</text>

				<!-- Suggested marker label -->
				{#if suggested}
					<text
						x={barX + barWidth / 2}
						y={height - 8}
						text-anchor="middle"
						font-size="7"
						fill="#b45309"
					>
						suggested
					</text>
				{/if}
			</g>
		{/each}

		<!-- Zero label -->
		<!-- 		<text x={plotRight} y={zeroY - 4} text-anchor="end" font-size="8" fill="#9ca3af"> 0 </text>
 -->
	</svg>

	<div class="mt-1 flex justify-center gap-4 text-[10px] text-gray-500">
		<span>
			<span class="font-semibold text-blue-700">↑</span>
			supportive
		</span>

		<span>
			<span class="font-semibold text-red-700">↓</span>
			limiting
		</span>

		{#if suggestedDesiredValueName}
			<span>
				<span class="font-semibold text-amber-600">★</span>
				R-XIMO suggestion
			</span>
		{/if}
	</div>
</div>
