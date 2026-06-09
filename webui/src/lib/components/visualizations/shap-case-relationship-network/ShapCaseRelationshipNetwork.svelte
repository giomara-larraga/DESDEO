<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import * as d3 from 'd3';

	type ObjectiveItem = {
		symbol: string;
		name?: string;
		maximize?: boolean;
	};

	type ObjectiveValue = number | number[] | null | undefined;

	let {
		objectives,
		preferenceValues,
		achievedValues,
		shapValues,
		threshold = 0.0
	}: {
		objectives: ObjectiveItem[];
		preferenceValues: number[];
		achievedValues: Record<string, ObjectiveValue> | null;
		shapValues: Record<string, Record<string, number>> | null;
		threshold?: number;
	} = $props();

	const minWidth = 320;
	const height = 320;
	const boxWidth = 80;
	const boxHeight = 38;

	let svgEl: SVGSVGElement | undefined;
	let activeNodeId = $state<string | null>(null);
	let chartWidth = $state<number>(minWidth);
	let resizeObserver: ResizeObserver | null = null;

	function normalizeSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function toFinite(value: ObjectiveValue): number | null {
		const numeric = Array.isArray(value) ? Number(value[0]) : Number(value);
		return Number.isFinite(numeric) ? numeric : null;
	}

	function formatSigned(value: number): string {
		const abs = Math.abs(value);
		if (value > 0) return `+${abs.toFixed(3)}`;
		if (value < 0) return `-${abs.toFixed(3)}`;
		return '0.000';
	}

	function findShapRow(outputSymbol: string): Record<string, number> {
		if (!shapValues) return {};
		return (
			shapValues[outputSymbol] ??
			shapValues[`z_${outputSymbol}`] ??
			Object.entries(shapValues).find(([key]) => normalizeSymbol(key) === outputSymbol)?.[1] ??
			{}
		);
	}

	function isNodeConnected(nodeId: string, links: Array<{ source: string; target: string }>): boolean {
		if (!activeNodeId) return true;
		if (nodeId === activeNodeId) return true;
		return links.some((link) => link.source === activeNodeId && link.target === nodeId) || links.some((link) => link.target === activeNodeId && link.source === nodeId);
	}

	function renderGraph() {
		if (!svgEl) return;
		const width = chartWidth;
		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();

		if (!objectives.length || !achievedValues || !shapValues) return;

		const leftX = 10;
		const rightX = width - boxWidth - 80;
		const topY = 34;
		const bottomY = height - 54;
		const stepY = objectives.length > 1 ? (bottomY - topY) / (objectives.length - 1) : 0;

		const leftNodes = objectives.map((objective, idx) => {
			const pref = Number(preferenceValues[idx] ?? 0);
			return {
				id: `p_${objective.symbol}`,
				symbol: objective.symbol,
				side: 'left' as const,
				label: `${objective.name ?? objective.symbol} = ${pref.toFixed(3)}`,
				x: leftX,
				y: topY + idx * stepY
			};
		});

		const rightNodes = objectives.map((objective, idx) => {
			const achieved = toFinite(achievedValues[objective.symbol]);
			return {
				id: `a_${objective.symbol}`,
				symbol: objective.symbol,
				side: 'right' as const,
				label: `${objective.name ?? objective.symbol} = ${achieved == null ? 'n/a' : achieved.toFixed(3)}`,
				x: rightX,
				y: topY + idx * stepY
			};
		});

		const nodes = [...leftNodes, ...rightNodes];

		const links: Array<{
			source: string;
			target: string;
			value: number;
			type: 'synergy' | 'conflict';
		}> = [];

		for (const targetObjective of objectives) {
			const shapRow = findShapRow(targetObjective.symbol);
			const targetMaximize = Boolean(targetObjective.maximize);

			for (const inputObjective of objectives) {
				const rawShap = Number(
					shapRow[inputObjective.symbol] ?? shapRow[`z_${inputObjective.symbol}`] ?? 0
				);
				if (!Number.isFinite(rawShap)) continue;

				const helpScore = targetMaximize ? rawShap : -rawShap;
				if (Math.abs(helpScore) <= threshold) continue;

				links.push({
					source: `p_${inputObjective.symbol}`,
					target: `a_${targetObjective.symbol}`,
					value: helpScore,
					type: helpScore >= 0 ? 'synergy' : 'conflict'
				});
			}
		}

		if (links.length === 0) {
			svg
				.append('text')
				.attr('x', width / 2)
				.attr('y', height / 2)
				.attr('text-anchor', 'middle')
				.attr('fill', '#6b7280')
				.attr('font-size', 10)
				.text('No SHAP effects above threshold.');
			return;
		}

		svg
			.append('defs')
			.selectAll('marker')
			.data(['conflict', 'synergy'])
			.join('marker')
			.attr('id', (d) => `shap-arrow-${d}`)
			.attr('viewBox', '0 -5 10 10')
			.attr('markerUnits', 'userSpaceOnUse')
			.attr('refX', 8)
			.attr('refY', 0)
			.attr('markerWidth', 7)
			.attr('markerHeight', 7)
			.attr('orient', 'auto')
			.append('path')
			.attr('d', 'M0,-5L10,0L0,5')
			.attr('fill', (d) => (d === 'conflict' ? '#dc2626' : '#2563eb'));

		const maxAbs = d3.max(links, (d) => Math.abs(d.value)) ?? 1;
		const strokeWidth = d3.scaleLinear().domain([0, maxAbs]).range([1.2, 7]);
		const line = d3
			.line<[number, number]>()
			.x((d) => d[0])
			.y((d) => d[1])
			.curve(d3.curveBasis);

		const byId = new Map(nodes.map((node) => [node.id, node]));
		const anchorRight = (n: { x: number; y: number }) => ({ x: n.x + boxWidth, y: n.y + boxHeight / 2 });
		const anchorLeft = (n: { x: number; y: number }) => ({ x: n.x, y: n.y + boxHeight / 2 });

		svg
			.append('text')
			.attr('x', leftX)
			.attr('y', 18)
			.attr('font-size', 10)
			.attr('font-style', 'italic')
			.attr('fill', '#6b7280')
			.text('preferences');

		svg
			.append('text')
			.attr('x', rightX)
			.attr('y', 18)
			.attr('font-size', 10)
			.attr('font-style', 'italic')
			.attr('fill', '#6b7280')
			.text('achieved values');

		svg
			.append('g')
			.selectAll('path')
			.data(links)
			.join('path')
			.attr('d', (d) => {
				const sNode = byId.get(d.source);
				const tNode = byId.get(d.target);
				if (!sNode || !tNode) return '';
				const s = anchorRight(sNode);
				const t = anchorLeft(tNode);
				const midX = (s.x + t.x) / 2;
				return line([
					[s.x, s.y],
					[midX, s.y],
					[midX, t.y],
					[t.x, t.y]
				]);
			})
			.attr('fill', 'none')
			.attr('stroke', (d) => (d.type === 'conflict' ? '#dc2626' : '#2563eb'))
			.attr('stroke-width', (d) => strokeWidth(Math.abs(d.value)))
			.attr('marker-end', (d) => `url(#shap-arrow-${d.type})`)
			.attr('opacity', (d) => {
				if (!activeNodeId) return 0.92;
				return d.source === activeNodeId || d.target === activeNodeId ? 1 : 0.12;
			});

		svg
			.append('g')
			.selectAll('text')
			.data(links)
			.join('text')
			.attr('x', (d) => {
				const sNode = byId.get(d.source);
				const tNode = byId.get(d.target);
				if (!sNode || !tNode) return 0;
				return (anchorRight(sNode).x + anchorLeft(tNode).x) / 2;
			})
			.attr('y', (d) => {
				const sNode = byId.get(d.source);
				const tNode = byId.get(d.target);
				if (!sNode || !tNode) return 0;
				return (anchorRight(sNode).y + anchorLeft(tNode).y) / 2 - 8;
			})
			.attr('text-anchor', 'middle')
			.attr('font-size', 10)
			.attr('fill', '#111827')
			.attr('opacity', (d) => {
				if (!activeNodeId) return 1;
				return d.source === activeNodeId || d.target === activeNodeId ? 1 : 0.2;
			})
			.text((d) => formatSigned(d.value));

		const nodeGroup = svg
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('transform', (d) => `translate(${d.x}, ${d.y})`)
			.style('cursor', 'pointer')
			.on('click', (_, d) => {
				activeNodeId = activeNodeId === d.id ? null : d.id;
			});

		nodeGroup
			.append('rect')
			.attr('width', boxWidth)
			.attr('height', boxHeight)
			.attr('rx', 8)
			.attr('fill', (d) => {
				if (activeNodeId === d.id) return '#fef3c7';
				return d.side === 'left' ? '#eef2ff' : '#ecfdf5';
			})
			.attr('stroke', (d) => {
				if (activeNodeId === d.id) return '#f59e0b';
				return d.side === 'left' ? '#c7d2fe' : '#a7f3d0';
			})
			.attr('stroke-width', (d) => (activeNodeId === d.id ? 2 : 1.2))
			.attr('opacity', (d) => (isNodeConnected(d.id, links) ? 1 : 0.35));

		nodeGroup
			.append('text')
			.attr('x', boxWidth / 2)
			.attr('y', boxHeight / 2 + 4)
			.attr('text-anchor', 'middle')
			.attr('font-size', 10)
			.attr('font-weight', 600)
			.attr('fill', '#1f2937')
			.attr('pointer-events', 'none')
			.text((d) => d.label);

/* 		const legend = svg.append('g').attr('transform', `translate(${leftX}, ${height - 22})`);

		legend
			.append('line')
			.attr('x1', 0)
			.attr('x2', 36)
			.attr('y1', 0)
			.attr('y2', 0)
			.attr('stroke', '#dc2626')
			.attr('stroke-width', 4);

		legend
			.append('text')
			.attr('x', 46)
			.attr('y', 4)
			.attr('font-size', 10)
			.attr('fill', '#374151')
			.text('conflict');

		legend
			.append('line')
			.attr('x1', 124)
			.attr('x2', 160)
			.attr('y1', 0)
			.attr('y2', 0)
			.attr('stroke', '#2563eb')
			.attr('stroke-width', 4);

		legend
			.append('text')
			.attr('x', 170)
			.attr('y', 4)
			.attr('font-size', 10)
			.attr('fill', '#374151')
			.text('synergy');

		svg
			.append('text')
			.attr('x', Math.max(leftX + 220, width - 250))
			.attr('y', height - 14)
			.attr('font-size', 10)
			.attr('font-style', 'italic')
			.attr('fill', '#6b7280')
			.text('thicker line = stronger SHAP effect'); */
	}

	onMount(() => {
		renderGraph();

		if (!svgEl) return;

		const updateWidth = () => {
			if (!svgEl) return;
			const measured = Math.floor(svgEl.getBoundingClientRect().width);
			if (measured > 0) {
				chartWidth = Math.max(minWidth, measured);
			}
		};

		updateWidth();
		resizeObserver = new ResizeObserver(() => {
			updateWidth();
		});
		resizeObserver.observe(svgEl);
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		resizeObserver = null;
	});

	$effect(() => {
		chartWidth;
		objectives;
		preferenceValues;
		achievedValues;
		shapValues;
		threshold;
		activeNodeId;
		renderGraph();
	});
</script>

<div >
	<div class="mb-2 text-[11px] text-gray-500">
		Click a node to highlight its connected effects.
				{#if activeNodeId}
			<button
				type="button"
				class="rounded bg-gray-100 px-2 py-0.5 text-[11px] text-gray-700 hover:bg-gray-200"
				onclick={() => (activeNodeId = null)}
			>
				Clear focus
			</button>
		{/if}
	</div>
	<svg
		bind:this={svgEl}
		width="100%"
		height={height}
		role="img"
		aria-label="SHAP relationship graph between preferences and achieved values"
	></svg>
</div>
