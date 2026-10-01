<script lang="ts">
	import { scaleLinear } from 'd3-scale';
	import { formatNumber } from '$lib/helpers';

	interface Props {
		objectiveName: string;

		// Desired value used to generate the current presented solution
		desiredValue: number;

		// Achieved value of the current presented solution
		achievedValue: number;

		maximize: boolean;

		ideal?: number | null;
		nadir?: number | null;

		digits?: number;
		tolerance?: number;
	}

	let {
		objectiveName,
		desiredValue,
		achievedValue,
		maximize,
		ideal = null,
		nadir = null,
		digits = 2,
		tolerance = 0.01
	}: Props = $props();

	const width = 340;
	const height = 105;
	const marginLeft = 22;
	const marginRight = 22;
	const axisY = 54;

	let rawDifference = $derived(achievedValue - desiredValue);

	// Positive always means better than desired,
	// independently of minimization/maximization.
	let directionalDifference = $derived(maximize ? rawDifference : -rawDifference);

	let status = $derived.by<'better' | 'worse' | 'met'>(() => {
		if (Math.abs(directionalDifference) <= tolerance) {
			return 'met';
		}

		return directionalDifference > 0 ? 'better' : 'worse';
	});

	let statusText = $derived.by(() => {
		if (status === 'met') return 'Meets desired value';

		return `${formatNumber(Math.abs(rawDifference), digits)} ${status} than desired`;
	});

	let statusColor = $derived.by(() => {
		if (status === 'better') return '#15803d'; // green
		if (status === 'worse') return '#d97706'; // amber
		return '#6b7280'; // gray
	});

	let domain = $derived.by<[number, number]>(() => {
		const values = [desiredValue, achievedValue];

		if (ideal !== null && Number.isFinite(Number(ideal))) {
			values.push(Number(ideal));
		}

		if (nadir !== null && Number.isFinite(Number(nadir))) {
			values.push(Number(nadir));
		}

		let min = Math.min(...values);
		let max = Math.max(...values);

		if (min === max) {
			const padding = Math.max(Math.abs(min) * 0.05, 1);
			min -= padding;
			max += padding;
		}

		const padding = (max - min) * 0.04;

		return [min - padding, max + padding];
	});

	let x = $derived.by(() =>
		scaleLinear()
			.domain(domain)
			.range([marginLeft, width - marginRight])
	);

	let desiredX = $derived(x(desiredValue));
	let achievedX = $derived(x(achievedValue));

	let differenceMidpoint = $derived((desiredX + achievedX) / 2);

	let leftX = $derived(Math.min(desiredX, achievedX));

	let rightX = $derived(Math.max(desiredX, achievedX));

	let markerDistance = $derived(Math.abs(achievedX - desiredX));

	let labelsClose = $derived(markerDistance < 45);

	let achievedLabelAnchor = $derived.by<'start' | 'middle' | 'end'>(() => {
		if (!labelsClose) return 'middle';

		return achievedX >= desiredX ? 'start' : 'end';
	});

	let achievedLabelOffset = $derived.by(() => {
		if (!labelsClose) return 0;

		return achievedX >= desiredX ? 9 : -9;
	});

	let leftLimitLabel = $derived(maximize ? 'Nadir (min)' : 'Ideal (min)');

	let rightLimitLabel = $derived(maximize ? 'Ideal (max)' : 'Nadir (max)');

	let leftLimitValue = $derived.by(() => {
		const idealValue = Number(ideal);
		const nadirValue = Number(nadir);

		if (Number.isFinite(idealValue) && Number.isFinite(nadirValue)) {
			return Math.min(idealValue, nadirValue);
		}

		return domain[0];
	});

	let rightLimitValue = $derived.by(() => {
		const idealValue = Number(ideal);
		const nadirValue = Number(nadir);

		if (Number.isFinite(idealValue) && Number.isFinite(nadirValue)) {
			return Math.max(idealValue, nadirValue);
		}

		return domain[1];
	});
</script>

<div class="w-full">
	<div class="mb-1 flex items-center justify-between">
		<div class="text-xs font-semibold" style={`color: ${statusColor}`}>
			{#if status === 'met'}
				Meets desired value
			{:else}
				{formatNumber(Math.abs(rawDifference), digits)}
				{status === 'better' ? ' better than desired' : ' worse than desired'}
			{/if}
		</div>
	</div>

	<svg
		viewBox={`0 0 ${width} ${height}`}
		class="block w-full overflow-visible"
		role="img"
		aria-label={`Desired and achieved values for ${objectiveName}`}
	>
		<!-- Complete objective scale -->
		<line
			x1={marginLeft}
			x2={width - marginRight}
			y1={axisY}
			y2={axisY}
			stroke="#d1d5db"
			stroke-width="3"
			stroke-linecap="round"
		/>

		<!-- Difference between desired and achieved -->
		{#if status !== 'met'}
			<line
				x1={leftX}
				x2={rightX}
				y1={axisY}
				y2={axisY}
				stroke={statusColor}
				stroke-width="7"
				stroke-linecap="round"
			/>
		{/if}

		<!-- Desired value -->
		<circle cx={desiredX} cy={axisY} r="7" fill="white" stroke="#111827" stroke-width="2.5" />

		<!-- Achieved value -->
		<circle
			cx={achievedX}
			cy={axisY}
			r={status === 'met' ? 4 : 6}
			fill={statusColor}
			stroke="white"
			stroke-width="2"
		/>

		<!-- Desired-value label -->
		<text x={desiredX} y="79" text-anchor="middle" font-size="9" fill="#6b7280"> Desired </text>

		<text x={desiredX} y="92" text-anchor="middle" font-size="10" font-weight="600" fill="#374151">
			{formatNumber(desiredValue, digits)}
		</text>

		<!-- Achieved-value label -->
		<!-- Achieved-value label -->
		<text
			x={achievedX + achievedLabelOffset}
			y="18"
			text-anchor={achievedLabelAnchor}
			font-size="9"
			fill="#6b7280"
		>
			Achieved
		</text>

		<text
			x={achievedX + achievedLabelOffset}
			y="31"
			text-anchor={achievedLabelAnchor}
			font-size="10"
			font-weight="600"
			fill="#374151"
		>
			{formatNumber(achievedValue, digits)}
		</text>
		<!-- Range endpoints -->

		<!-- Left limit -->
		<text x={marginLeft} y="70" text-anchor="start" font-size="8" fill="#6b7280">
			<tspan x={marginLeft} font-weight="600">
				{leftLimitLabel}
			</tspan>

			<tspan x={marginLeft} dy="11" fill="#9ca3af">
				{formatNumber(leftLimitValue, digits)}
			</tspan>
		</text>

		<!-- Right limit -->
		<text x={width - marginRight} y="70" text-anchor="end" font-size="8" fill="#6b7280">
			<tspan x={width - marginRight} font-weight="600">
				{rightLimitLabel}
			</tspan>

			<tspan x={width - marginRight} dy="11" fill="#9ca3af">
				{formatNumber(rightLimitValue, digits)}
			</tspan>
		</text>
	</svg>
</div>
