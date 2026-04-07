<script lang="ts">
	/**
	 * shap-barchart.svelte
	 * --------------------------------
	 * Bar chart showing SHAP values for one selected output objective.
	 *
	 * X axis  = reference-point aspirations (input symbols, e.g. "z_f1")
	 * Y axis  = SHAP value
	 * Color   = red (#C00000) positive, dark-blue (#00008B) negative
	 * Black   = the bar corresponding to the selected objective's own aspiration
	 */
	import * as d3 from 'd3';
	import { onMount, onDestroy } from 'svelte';
	import type { ProblemInfo } from '$lib/types';

	interface Props {
		/** One row of the SHAP matrix: input_symbol → value */
		shapRow: Record<string, number>;
		/** Which output objective is selected (its matching input bar shows in black) */
		selectedOutputSymbol: string;
		problem: ProblemInfo;
	}

	let { shapRow, selectedOutputSymbol, problem }: Props = $props();

	const objNameMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.name ?? o.symbol]))
	);

	const objMaximizeMap = $derived(
		Object.fromEntries(problem.objectives.map((o) => [o.symbol, o.maximize ?? false]))
	);

	const entries = $derived(
		Object.entries(shapRow).map(([inputSym, value]) => {
			const outSym = inputSym.startsWith('z_') ? inputSym.slice(2) : inputSym;
			return {
				inputSym,
				outSym,
				name: objNameMap[outSym] ?? outSym,
				value,
				isSelected: outSym === selectedOutputSymbol
			};
		})
	);

	/** Is the selected objective impaired by its own aspiration? */
	const isImpaired = $derived(() => {
		const maximize = objMaximizeMap[selectedOutputSymbol] ?? false;
		const ownVal = shapRow[`z_${selectedOutputSymbol}`] ?? 0;
		return maximize ? ownVal < 0 : ownVal > 0;
	});

	/** Name of the most helpful lever (aspiration) for the selected objective */
	const bestLeverName = $derived(() => {
		const maximize = objMaximizeMap[selectedOutputSymbol] ?? false;
		if (entries.length === 0) return '';
		// For minimize: most negative SHAP is best; for maximize: most positive
		const sorted = [...entries].sort((a, b) =>
			maximize ? b.value - a.value : a.value - b.value
		);
		return sorted[0].name;
	});

	let svgEl: SVGSVGElement;
	let containerEl: HTMLDivElement;
	let width = $state(280);
	let resizeObserver: ResizeObserver;

	let tooltipX = $state(0);
	let tooltipY = $state(0);
	let tooltipContent = $state('');
	let tooltipVisible = $state(false);

	const H = 185;

	function draw() {
		if (!svgEl || entries.length === 0 || width < 10) return;

		const m = { top: 8, right: 8, bottom: 46, left: 8 };
		const iw = width - m.left - m.right;
		const ih = H - m.top - m.bottom;

		d3.select(svgEl).selectAll('*').remove();

		const g = d3
			.select(svgEl)
			.append('g')
			.attr('transform', `translate(${m.left},${m.top})`);

		const names = entries.map((e) => e.name);
		const vals = entries.map((e) => e.value);

		const x = d3.scaleBand().domain(names).range([0, iw]).padding(0.2);

		const yMin = Math.min(0, d3.min(vals) ?? 0);
		const yMax = Math.max(0, d3.max(vals) ?? 1e-9);
		const y = d3.scaleLinear().domain([yMin, yMax]).range([ih, 0]).nice();

		const _impaired = isImpaired();
		const _best = bestLeverName();

		// Bars
		for (const e of entries) {
			const isOwnImpaired = e.isSelected && _impaired;
			const isBestLever = e.name === _best;
			const fill = isOwnImpaired
				? '#d97706'
				: e.isSelected
					? '#111827'
					: e.value >= 0
						? '#C00000'
						: '#00008B';

			const bx = x(e.name) ?? 0;
			const by = e.value >= 0 ? y(e.value) : y(0);
			const bh = Math.max(1, Math.abs(y(e.value) - y(0)));

			g.append('rect')
				.attr('x', bx)
				.attr('y', by)
				.attr('width', x.bandwidth())
				.attr('height', bh)
				.attr('fill', fill)
				.attr('rx', 2)
				.on('mouseover', (ev: MouseEvent) => {
					tooltipX = ev.pageX;
					tooltipY = ev.pageY;
					const label = e.isSelected ? `${e.name} (own aspiration)` : e.name;
					const warn = isOwnImpaired ? ' ⚠ relaxing this may help' : '';
					const star = isBestLever && !e.isSelected ? ' ★ most helpful aspiration' : '';
					tooltipContent = `${label}: ${e.value.toFixed(3)}${warn}${star}`;
					tooltipVisible = true;
				})
				.on('mousemove', (ev: MouseEvent) => {
					tooltipX = ev.pageX;
					tooltipY = ev.pageY;
				})
				.on('mouseout', () => {
					tooltipVisible = false;
				});

			// Best-lever star glyph above bar
			if (isBestLever) {
				const starY = e.value >= 0 ? by - 3 : by + bh + 10;
				g.append('text')
					.attr('x', bx + x.bandwidth() / 2)
					.attr('y', starY)
					.attr('text-anchor', 'middle')
					.attr('font-size', '11')
					.attr('fill', '#16a34a')
					.attr('pointer-events', 'none')
					.text('★');
			}
		}

		// Zero line
		g.append('line')
			.attr('x1', 0)
			.attr('x2', iw)
			.attr('y1', y(0))
			.attr('y2', y(0))
			.attr('stroke', '#d1d5db')
			.attr('stroke-width', 1);

		// X-axis labels (rotated)
		const ax = g
			.append('g')
			.attr('transform', `translate(0,${ih})`)
			.call(d3.axisBottom(x).tickSize(0));

		ax.select('.domain').remove();
		ax.selectAll<SVGTextElement, string>('text')
			.attr('transform', 'rotate(-35)')
			.style('text-anchor', 'end')
			.attr('dx', '-0.3em')
			.attr('dy', '0.7em')
			.attr('font-size', '9')
			.attr('fill', '#374151')
			.text((d) => (d.length > 10 ? d.slice(0, 9) + '…' : d));

		// Box border
		g.append('rect')
			.attr('x', 0)
			.attr('y', 0)
			.attr('width', iw)
			.attr('height', ih)
			.attr('fill', 'none')
			.attr('stroke', '#e5e7eb')
			.attr('stroke-width', 1);
	}

	$effect(() => {
		void entries;
		void width;
		draw();
	});

	onMount(() => {
		resizeObserver = new ResizeObserver((obs) => {
			for (const o of obs) {
				width = o.contentRect.width;
			}
		});
		resizeObserver.observe(containerEl);
	});

	onDestroy(() => resizeObserver?.disconnect());
</script>

<div bind:this={containerEl} class="relative w-full">
	<svg bind:this={svgEl} style="width:100%; height:{H}px;" />
	{#if isImpaired()}
		<p class="mt-0.5 text-[10px] text-amber-600">
			⚠ This aspiration may be too strict.
			{#if bestLeverName()}
				Most helpful aspiration: <strong>{bestLeverName()}</strong>
				<span class="text-green-700">★</span>
			{/if}
		</p>
	{:else if bestLeverName()}
		<p class="mt-0.5 text-[10px] text-gray-500">
			★ Most helpful aspiration: <span class="font-medium text-green-700">{bestLeverName()}</span>
		</p>
	{/if}
	{#if tooltipVisible}
		<div
			class="pointer-events-none fixed z-50 max-w-48 rounded bg-gray-800 px-2 py-1 text-xs text-white shadow"
			style="left:{tooltipX + 12}px; top:{tooltipY - 32}px;"
		>
			{tooltipContent}
		</div>
	{/if}
</div>
