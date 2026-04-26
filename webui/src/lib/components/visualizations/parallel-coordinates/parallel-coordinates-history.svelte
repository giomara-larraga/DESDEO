<script lang="ts">
	import * as d3 from 'd3';
	import { onDestroy, onMount } from 'svelte';

	import type { DataPoint, DimensionDefinition } from './types';

	type IterationData = {
		id?: string | number;
		name?: string;
		data: DataPoint[];
		show?: boolean;
		color?: string;
		referencePoint?: DataPoint;
	};

	export let iterations: IterationData[] = [];
	export let dimensions: DimensionDefinition[] = [];
	export let iterationColors: string[] | Record<string, string> | null = null;
	export let lineOpacity = 0.55;
	export let lineWidth = 1.8;
	export let showAxisLabels = true;

	let width = 700;
	let height = 420;
	let svg: SVGSVGElement;
	let container: HTMLDivElement;
	let resizeObserver: ResizeObserver;
	let tooltip: d3.Selection<HTMLDivElement, unknown, null, undefined>;

	const markerNames = ['square', 'triangle', 'diamond', 'cross', 'star', 'wye', 'slash'] as const;
	type MarkerName = (typeof markerNames)[number];

	function visibleIterations(): Array<{ iteration: IterationData; originalIndex: number }> {
		return iterations
			.map((iteration, originalIndex) => ({ iteration, originalIndex }))
			.filter(
				({ iteration }) =>
					iteration.show !== false && (iteration.data.length > 0 || iteration.referencePoint != null)
			);
	}

	function getDefaultBlueShade(index: number, total: number): string {
		if (total <= 1) return d3.interpolateBlues(0.65);
		const t = 0.45 + (index / Math.max(1, total - 1)) * 0.45;
		return d3.interpolateBlues(t);
	}

	function resolveIterationColor(iteration: IterationData, index: number, total: number): string {
		if (iteration.color) return iteration.color;

		if (Array.isArray(iterationColors) && iterationColors[index]) {
			return iterationColors[index];
		}

		if (iterationColors && !Array.isArray(iterationColors)) {
			const key = iteration.id != null ? String(iteration.id) : String(index);
			if (iterationColors[key]) return iterationColors[key];
		}

		return getDefaultBlueShade(index, total);
	}

	function markerForIteration(index: number): MarkerName {
		return markerNames[index % markerNames.length];
	}

	function markerPath(marker: MarkerName, size = 38): string {
		const symbolPath = (type: d3.SymbolType, symbolSize: number): string =>
			d3.symbol().type(type).size(symbolSize)() ?? '';

		switch (marker) {
			case 'square':
				return symbolPath(d3.symbolSquare, size);
			case 'triangle':
				return symbolPath(d3.symbolTriangle, size);
			case 'diamond':
				return symbolPath(d3.symbolDiamond, size);
			case 'cross':
				return symbolPath(d3.symbolCross, size);
			case 'star':
				return symbolPath(d3.symbolStar, size + 20);
			case 'wye':
				return symbolPath(d3.symbolWye, size + 10);
			default:
				return symbolPath(d3.symbolCircle, size);
		}
	}

	function isSlashMarker(marker: MarkerName): boolean {
		return marker === 'slash';
	}

	function drawSlashMarker(
		g: d3.Selection<SVGGElement, unknown, null, undefined>,
		x: number,
		y: number,
		color: string
	) {
		g.append('line')
			.attr('x1', x - 4)
			.attr('y1', y + 4)
			.attr('x2', x + 4)
			.attr('y2', y - 4)
			.attr('stroke', color)
			.attr('stroke-width', 2.2)
			.attr('stroke-linecap', 'round');
	}

	function drawChart() {
		if (!svg || dimensions.length === 0) return;

		const series = visibleIterations();
		if (series.length === 0) {
			d3.select(svg).selectAll('*').remove();
			return;
		}

		const margin = { top: 24, right: 40, bottom: 26, left: 40 };
		const innerWidth = Math.max(10, width - margin.left - margin.right);
		const innerHeight = Math.max(10, height - margin.top - margin.bottom);

		const allData: DataPoint[] = [];
		series.forEach(({ iteration }) => {
			allData.push(...iteration.data);
			if (iteration.referencePoint) allData.push(iteration.referencePoint);
		});

		if (allData.length === 0) {
			d3.select(svg).selectAll('*').remove();
			return;
		}

		const xScale = d3
			.scalePoint<string>()
			.domain(dimensions.map((d) => d.symbol))
			.range([0, innerWidth])
			.padding(0.12);

		const yScales: Record<string, d3.ScaleLinear<number, number>> = {};
		dimensions.forEach((dim) => {
			const values = allData.map((d) => d[dim.symbol]).filter((v) => v != null) as number[];
			let domain: [number, number];
			if (dim.min != null && dim.max != null) {
				domain = [dim.min, dim.max];
			} else {
				const ext = d3.extent(values) as [number, number];
				domain = ext && ext[0] != null && ext[1] != null ? ext : [0, 1];
			}
			if (domain[0] === domain[1]) {
				domain = [domain[0] - 1, domain[1] + 1];
			}
			yScales[dim.symbol] = d3.scaleLinear().domain(domain).range([innerHeight, 0]);
		});

		const line = d3
			.line<[string, number]>()
			.x(([k]) => xScale(k) ?? 0)
			.y(([k, v]) => yScales[k](v));

		const root = d3.select(svg);
		root.selectAll('*').remove();

		const g = root
			.attr('width', width)
			.attr('height', height)
			.append('g')
			.attr('transform', `translate(${margin.left}, ${margin.top})`);

		dimensions.forEach((dim) => {
			const x = xScale(dim.symbol) ?? 0;
			const axis = d3.axisLeft(yScales[dim.symbol]).ticks(5);
			g.append('g').attr('transform', `translate(${x},0)`).call(axis);

			if (showAxisLabels) {
				g.append('text')
					.attr('x', x)
					.attr('y', -8)
					.attr('text-anchor', 'middle')
					.style('font-size', '12px')
					.style('font-weight', '600')
					.text(dim.name);
			}
		});

		series.forEach(({ iteration, originalIndex }) => {
			const color = resolveIterationColor(iteration, originalIndex, iterations.length);
			const marker = markerForIteration(originalIndex);
			const iterName = iteration.name ?? `Iteration ${originalIndex + 1}`;

			const iterGroup = g.append('g').attr('class', `iteration-${originalIndex}`);

			iteration.data.forEach((solution, solutionIdx) => {
				const lineData = dimensions
					.map((dim) => [dim.symbol, solution[dim.symbol]] as [string, number])
					.filter(([, v]) => v != null);
				if (lineData.length < 2) return;

				iterGroup
					.append('path')
					.attr('d', line(lineData))
					.attr('fill', 'none')
					.attr('stroke', color)
					.attr('stroke-width', lineWidth)
					.attr('opacity', lineOpacity)
					.on('mouseover', (event) => {
						tooltip.transition().duration(120).style('opacity', 0.95);
						tooltip
							.html(`${iterName}<br/>Solution ${solutionIdx + 1}`)
							.style('left', `${event.pageX + 10}px`)
							.style('top', `${event.pageY - 28}px`);
					})
					.on('mouseout', () => tooltip.transition().duration(240).style('opacity', 0));

				lineData.forEach(([dimKey, val]) => {
					const x = xScale(dimKey) ?? 0;
					const y = yScales[dimKey](val);

					if (isSlashMarker(marker)) {
						drawSlashMarker(iterGroup, x, y, color);
					} else {
						iterGroup
							.append('path')
							.attr('d', markerPath(marker, 34))
							.attr('transform', `translate(${x},${y})`)
							.attr('fill', color)
							.attr('stroke', '#ffffff')
							.attr('stroke-width', 0.7)
							.attr('opacity', 0.95);
					}
				});
			});

			if (iteration.referencePoint) {
				const refLineData = dimensions
					.map((dim) => [dim.symbol, iteration.referencePoint?.[dim.symbol]] as [string, number])
					.filter(([, v]) => v != null);

				if (refLineData.length >= 2) {
					iterGroup
						.append('path')
						.attr('d', line(refLineData))
						.attr('fill', 'none')
						.attr('stroke', color)
						.attr('stroke-width', Math.max(2.8, lineWidth + 1.2))
						.attr('stroke-dasharray', '6,3')
						.attr('opacity', 0.95)
						.on('mouseover', (event) => {
							tooltip.transition().duration(120).style('opacity', 0.95);
							tooltip
								.html(`${iterName}<br/>Reference point`)
								.style('left', `${event.pageX + 10}px`)
								.style('top', `${event.pageY - 28}px`);
						})
						.on('mouseout', () => tooltip.transition().duration(240).style('opacity', 0));

					refLineData.forEach(([dimKey, val]) => {
						const x = xScale(dimKey) ?? 0;
						const y = yScales[dimKey](val);
						iterGroup
							.append('circle')
							.attr('cx', x)
							.attr('cy', y)
							.attr('r', 4.2)
							.attr('fill', '#ffffff')
							.attr('stroke', color)
							.attr('stroke-width', 2.2);
					});
				}
			}
		});
	}

	onMount(() => {
		tooltip = d3.select(container).append('div').attr('class', 'tooltip').style('opacity', 0);

		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				width = entry.contentRect.width;
				height = entry.contentRect.height;
				drawChart();
			}
		});

		resizeObserver.observe(container);
		drawChart();
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		tooltip?.remove();
	});

	$: iterations, dimensions, iterationColors, lineOpacity, lineWidth, showAxisLabels, width, height, drawChart();
</script>

<div bind:this={container} style="height: 100%; width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>

<style>
	:global(.axis path),
	:global(.axis line) {
		fill: none;
		stroke: #000;
		shape-rendering: crispEdges;
	}

	:global(.axis text) {
		font-size: 11px;
	}

	:global(.tooltip) {
		position: absolute;
		padding: 8px;
		background: white;
		border: 1px solid #ddd;
		border-radius: 4px;
		pointer-events: none;
		font-size: 12px;
		box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
		z-index: 10;
	}
</style>
