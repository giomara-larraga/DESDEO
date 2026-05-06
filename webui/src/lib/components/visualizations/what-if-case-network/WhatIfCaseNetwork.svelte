<script lang="ts">
	import { onMount } from 'svelte';
	import * as d3 from 'd3';

	type ObjectiveNode = {
		symbol: string;
		name?: string;
	};

	type CaseDelta = {
		symbol: string;
		delta: number;
		percentDelta: number | null;
	};

	type WhatIfCase = {
		impairedSymbol: string;
		deltas: CaseDelta[];
	};

	let {
		objectives,
		cases,
		mode = 'value'
	}: {
		objectives: ObjectiveNode[];
		cases: WhatIfCase[];
		mode?: 'value' | 'percent';
	} = $props();

	const width = 500;
	const height = 200;
	const nodeRadius = 32;

	let svgEl: SVGSVGElement | undefined;
	let activeNodeSymbol = $state<string | null>(null);

	function formatSigned(value: number): string {
		const abs = Math.abs(value);
		if (mode === 'percent') {
			if (value > 0) return `+${abs.toFixed(2)}%`;
			if (value < 0) return `-${abs.toFixed(2)}%`;
			return '0.00%';
		}
		if (value > 0) return `+${abs.toFixed(3)}`;
		if (value < 0) return `-${abs.toFixed(3)}`;
		return '0.000';
	}

	function renderGraph() {
		if (!svgEl) return;

		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();

		if (objectives.length === 0 || cases.length === 0) return;

		const centerX = width / 2;
		const centerY = height / 2;
		const ringRadius = Math.max(width, height) * 0.34;
		const nodeCount = objectives.length;

		const nodes = objectives.map((objective, idx) => {
			const angle = (2 * Math.PI * idx) / nodeCount - Math.PI / 2;
			return {
				id: objective.symbol,
				label: objective.name ?? objective.symbol,
				x: centerX + ringRadius * Math.cos(angle),
				y: centerY + ringRadius * Math.sin(angle)
			};
		});

		const nodeById = new Map(nodes.map((node) => [node.id, node]));

		const linkAccumulator = new Map<string, { source: string; target: string; value: number }>();

		for (const caseItem of cases) {
			for (const delta of caseItem.deltas) {
				const value = mode === 'percent' ? Number(delta.percentDelta ?? 0) : Number(delta.delta ?? 0);
				if (!Number.isFinite(value) || value === 0) continue;
				if (!nodeById.has(caseItem.impairedSymbol) || !nodeById.has(delta.symbol)) continue;
				if (caseItem.impairedSymbol === delta.symbol) continue;

				const key = `${caseItem.impairedSymbol}__${delta.symbol}`;
				const existing = linkAccumulator.get(key);
				if (existing) {
					existing.value += value;
				} else {
					linkAccumulator.set(key, {
						source: caseItem.impairedSymbol,
						target: delta.symbol,
						value
					});
				}
			}
		}

		const links = Array.from(linkAccumulator.values()).filter((link) => link.value !== 0);
		if (links.length === 0) return;

		const maxAbs = d3.max(links, (link) => Math.abs(link.value)) ?? 1;
		const strokeWidth = d3.scaleLinear().domain([0, maxAbs]).range([1.5, 7]);

		svg
			.append('defs')
			.append('marker')
			.attr('id', 'what-if-arrow')
			.attr('viewBox', '0 -5 10 10')
			.attr('refX', 10)
			.attr('refY', 0)
			.attr('markerWidth', 8)
			.attr('markerHeight', 8)
			.attr('orient', 'auto')
			.append('path')
			.attr('d', 'M0,-5L10,0L0,5')
			.attr('fill', 'currentColor');

		const line = d3
			.line<[number, number]>()
			.x((d) => d[0])
			.y((d) => d[1])
			.curve(d3.curveBasis);

		function shortenLine(source: { x: number; y: number }, target: { x: number; y: number }) {
			const dx = target.x - source.x;
			const dy = target.y - source.y;
			const distance = Math.hypot(dx, dy) || 1;
			const offsetX = (dx / distance) * nodeRadius;
			const offsetY = (dy / distance) * nodeRadius;

			return {
				x1: source.x + offsetX,
				y1: source.y + offsetY,
				x2: target.x - offsetX,
				y2: target.y - offsetY
			};
		}

		const linksGroup = svg.append('g');

		linksGroup
			.selectAll('path')
			.data(links)
			.join('path')
			.attr('d', (linkDatum) => {
				const source = nodeById.get(linkDatum.source);
				const target = nodeById.get(linkDatum.target);
				if (!source || !target) return '';
				const p = shortenLine(source, target);
				const mx = (p.x1 + p.x2) / 2;
				const my = (p.y1 + p.y2) / 2;
				const dx = p.x2 - p.x1;
				const dy = p.y2 - p.y1;
				const norm = Math.hypot(dx, dy) || 1;
				const curveOffset = 28;
				const cx = mx - (dy / norm) * curveOffset;
				const cy = my + (dx / norm) * curveOffset;
				return line([
					[p.x1, p.y1],
					[cx, cy],
					[p.x2, p.y2]
				]);
			})
			.attr('fill', 'none')
			.attr('stroke', (d) => (d.value >= 0 ? '#16a34a' : '#dc2626'))
			.attr('stroke-width', (d) => strokeWidth(Math.abs(d.value)))
			.attr('stroke-dasharray', (d) => (d.value < 0 ? '6 4' : null))
			.attr('marker-end', 'url(#what-if-arrow)')
			.attr('opacity', (d) => {
				if (!activeNodeSymbol) return 0.9;
				return d.source === activeNodeSymbol ? 1 : 0.15;
			});

		linksGroup
			.selectAll('text')
			.data(links)
			.join('text')
			.attr('x', (d) => {
				const s = nodeById.get(d.source);
				const t = nodeById.get(d.target);
				if (!s || !t) return 0;
				return (s.x + t.x) / 2;
			})
			.attr('y', (d) => {
				const s = nodeById.get(d.source);
				const t = nodeById.get(d.target);
				if (!s || !t) return 0;
				return (s.y + t.y) / 2 - 9;
			})
			.attr('text-anchor', 'middle')
			.attr('font-size', 12)
			.attr('fill', '#111827')
			.attr('opacity', (d) => {
				if (!activeNodeSymbol) return 1;
				return d.source === activeNodeSymbol ? 1 : 0.2;
			})
			.text((d) => formatSigned(d.value));

		const nodeGroup = svg
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('transform', (d) => `translate(${d.x}, ${d.y})`);

		nodeGroup
			.append('circle')
			.attr('r', nodeRadius)
			.attr('fill', (d) => (d.id === activeNodeSymbol ? '#fef3c7' : 'white'))
			.attr('stroke', (d) => (d.id === activeNodeSymbol ? '#f59e0b' : '#111827'))
			.attr('stroke-width', (d) => (d.id === activeNodeSymbol ? 2.5 : 2))
			.attr('opacity', (d) => {
				if (!activeNodeSymbol) return 1;
				if (d.id === activeNodeSymbol) return 1;
				const hasOutgoing = links.some(
					(link) => link.source === activeNodeSymbol && link.target === d.id
				);
				return hasOutgoing ? 1 : 0.35;
			})
			.style('cursor', 'pointer')
			.on('click', (_, d) => {
				activeNodeSymbol = activeNodeSymbol === d.id ? null : d.id;
			});

		nodeGroup
			.append('text')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'middle')
			.attr('font-weight', '700')
			.attr('font-size', 12)
			.attr('pointer-events', 'none')
			.text((d) => d.label);
	}

	onMount(() => {
		renderGraph();
	});

	$effect(() => {
		objectives;
		cases;
		mode;
		activeNodeSymbol;
		renderGraph();
	});
</script>

<div class="rounded-md border border-gray-200 bg-white p-3">
	<div class="mb-2 flex items-center justify-between gap-2">
		<div class="text-xs font-semibold text-gray-700">What-if Cases Network</div>
		{#if activeNodeSymbol}
			<button
				type="button"
				class="rounded bg-gray-100 px-2 py-0.5 text-[12px] text-gray-700 hover:bg-gray-200"
				onclick={() => (activeNodeSymbol = null)}
			>
				Clear focus
			</button>
		{/if}
	</div>
	<div class="mb-2 text-[12px] text-gray-500">
		Click a node to highlight its effects across all What-if Cases.
	</div>
	<svg
		bind:this={svgEl}
		width="100%"
		height={height}
		viewBox={`0 0 ${width} ${height}`}
		role="img"
		aria-label="Shared network graph of What-if Cases effects"
	></svg>
</div>
