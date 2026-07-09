<script lang="ts">
	import { onMount } from 'svelte';
	import * as d3 from 'd3';
    import { IMPAIRING_COLOR, IMPROVING_COLOR } from '$lib/constants';

	/**
	 * Component: WhatIfCaseNetwork
	 * Author: Giomara Larraga (glarragw@jyu.fi)
	 * Note: Some parts of this component were fine-tuned with GitHub Copilot.
	 * Created on: May 2026
     * Modified on: May 2026
     * 
	 * Summary:
	 * Renders a directed objective-to-objective network for What-if Cases.
	 * Each edge represents the aggregated effect of impairing one objective on another
	 * across all available cases.
	 *
	 * Parameters:
	 * - objectives: ObjectiveNode[]
	 *   List of problem objectives used to create graph nodes. Each objective provides
	 *   a required symbol (id) and an optional display name.
	 *
	 * - cases: WhatIfCase[]
	 *   List of what-if simulations. Each case defines which objective was impaired and
	 *   the resulting deltas for all objectives.
	 *
	 * - mode: 'value' | 'percent'
	 *   Controls which metric is visualized on edges and labels:
	 *   'value' uses absolute delta, 'percent' uses normalized percent delta.
	 *
	 * Internal visual settings:
	 * - width, height: SVG viewBox dimensions.
	 * - nodeRadius: Radius of each objective node.
	 * - activeNodeSymbol: Optional focus state for highlighting outgoing effects from
	 *   one selected objective.
	 *
	 * Visual encoding:
	 * - Blue solid edge: positive aggregated effect.
	 * - Red dashed edge: negative aggregated effect.
	 * - Edge width: magnitude of effect.
	 * - Node click: toggles focused source objective.
	 *
	 * TODO (pending):
	 * - Add legend UI inside the component (color, line style, and width meaning).
	 * - Add tooltip details per node.
	 * - Add optional responsiveness based on parent container size.
	 */

	/** Graph node representing one objective in the problem. */
	type ObjectiveNode = {
		symbol: string;
		name?: string;
	};

	/**
	 * Change observed for one objective under a what-if case.
	 * `delta` is absolute change and `percentDelta` is normalized change in percent.
	 */
	type CaseDelta = {
		symbol: string;
		delta: number;
		percentDelta: number | null;
	};

	/**
	 * One simulated case where a single objective preference was impaired.
	 * The case stores the resulting changes for all objectives.
	 */
	type WhatIfCase = {
		impairedSymbol: string;
		deltas: CaseDelta[];
	};

	let {
		objectives,
		cases,
		mode = 'value',
		onSelectNode,
		disabledNodeSymbol = null
	}: {
		objectives: ObjectiveNode[];
		cases: WhatIfCase[];
		mode?: 'value' | 'percent';
		onSelectNode?: (symbol: string | null) => void;
		disabledNodeSymbol?: string | null;
	} = $props();

	let containerEl: HTMLDivElement | undefined;

	let width = $state(500);
	let height = $state(220);

	//const width = 500;
	//const height = 200;
	//let height = $state(220);	

	let nodeRadius = $derived(Math.max(22, Math.min(32, height * 0.14)));	
	//let containerEl: HTMLDivElement | null = null;


	let svgEl: SVGSVGElement | undefined;
	let activeNodeSymbol = $state<string | null>(null);

	/** Formats edge labels as signed values based on the selected display mode. */
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

		const padding = nodeRadius/2;

		const centerX = width / 2;
		const centerY = height / 2;

		const availableWidth = Math.max(1, width - padding * 2);
		const availableHeight = Math.max(1, height - padding * 2);

		const ringRadius = Math.min(availableWidth, availableHeight) * 0.42;
		const nodeCount = objectives.length;
		const arrowSize = Math.max(4, Math.min(6, height * 0.018));
		const minStroke = 1.2;
		const maxStroke = Math.max(2.5, Math.min(4.5, height * 0.015));
		const curveOffset = 1.2 * nodeRadius;

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

		// Aggregate links across all cases so each source-target pair is rendered once.
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
		const strokeWidth = d3.scaleLinear()
			.domain([0, maxAbs])
			.range([minStroke, maxStroke]);

		svg
			.append('defs')
			.append('marker')
			.attr('id', 'what-if-arrow')
			.attr('viewBox', '0 -3 6 6')
			.attr('refX', 6)
			.attr('refY', 0)
			.attr('markerWidth', nodeRadius * 0.5)
			.attr('markerHeight', nodeRadius * 0.5)
			.attr('orient', 'auto')
			.attr('markerUnits', 'userSpaceOnUse')
			.append('path')
			.attr('d', 'M0,-3L6,0L0,3')
			.attr('fill', 'context-stroke');

		/*const line = d3
			.line<[number, number]>()
			.x((d) => d[0])
			.y((d) => d[1])
			.curve(d3.curveBasis);*/

		// Offset path endpoints so arrows start/end at node borders instead of node centers.
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

		const visibleLinks = links.filter(
			link => link.source !== disabledNodeSymbol
		);

		linksGroup
			.selectAll('path')
			.data(visibleLinks)
			.join('path')
			.attr('d', (linkDatum) => {
				const source = nodeById.get(linkDatum.source);
				const target = nodeById.get(linkDatum.target);
				if (!source || !target) return '';

				const p = shortenLine(source, target);

				const dx = p.x2 - p.x1;
				const dy = p.y2 - p.y1;
				const norm = Math.hypot(dx, dy) || 1;

				const mx = (p.x1 + p.x2) / 2;
				const my = (p.y1 + p.y2) / 2;

				const curveOffset = Math.max(18, Math.min(38, nodeRadius * 1.2));

				const cx = mx - (dy / norm) * curveOffset;
				const cy = my + (dx / norm) * curveOffset;

				return `M ${p.x1},${p.y1} Q ${cx},${cy} ${p.x2},${p.y2}`;
			})
			.attr('fill', 'none')
			.attr('stroke', (d) => (d.value >= 0 ? IMPROVING_COLOR : IMPAIRING_COLOR))
			.attr('stroke-width', (d) => strokeWidth(Math.abs(d.value)))
			.attr('stroke-dasharray', (d) => (d.value < 0 ? '6 4' : null))
			.attr('marker-end', 'url(#what-if-arrow)')
			// When focused, keep only outgoing effects from the selected source objective prominent.
			.attr('opacity', (d) => {
				if (!activeNodeSymbol) return 0.9;
				return d.source === activeNodeSymbol ? 1 : 0.10;
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
				if (!activeNodeSymbol) return 0;
				return d.source === activeNodeSymbol ? 1 : 0;
			})
			.text((d) => formatSigned(d.value));

		const nodeGroup = svg
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('transform', (d) => `translate(${d.x}, ${d.y})`);

		nodeGroup
			.append('title')
			.text((d) => {
				if (d.id === disabledNodeSymbol) {
						return `${d.label} is the objective you want to improve. Select another objective to explore possible trade-offs.`;
					}
				return '';
			});

		nodeGroup
			.append('circle')
			.attr('r', nodeRadius)
			.attr('fill', (d) => {
				if (d.id === disabledNodeSymbol) return '#dbeafe';
				return d.id === activeNodeSymbol ? '#fef3c7' : 'white';
			})
			.attr('stroke', (d) => {
				if (d.id === disabledNodeSymbol) return '#2563eb';
				return d.id === activeNodeSymbol ? '#f59e0b' : '#111827';
			})
			.attr('opacity', (d) => {
				if (d.id === disabledNodeSymbol) return 0.9;
				if (!activeNodeSymbol) return 1;
				if (d.id === activeNodeSymbol) return 1;

				const hasOutgoing = links.some(
					(link) => link.source === activeNodeSymbol && link.target === d.id
				);

				return hasOutgoing ? 1 : 0.35;
			})
			.style('cursor', (d) => (d.id === disabledNodeSymbol ? 'cursor' : 'pointer'))
			// Clicking a node toggles focus for that objective's outgoing effects.
			.on('click', (_, d) => {
				if (d.id === disabledNodeSymbol) return;

				activeNodeSymbol = activeNodeSymbol === d.id ? null : d.id;
				onSelectNode?.(activeNodeSymbol);
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

	let resizeObserver: ResizeObserver | null = null;

	onMount(() => {
		if (containerEl) {
			resizeObserver = new ResizeObserver(([entry]) => {
				width = entry.contentRect.width;
				height = Math.max(280, Math.min(420, width * 0.9));

				renderGraph();
			});

			resizeObserver.observe(containerEl);
		}

		renderGraph();

		return () => {
			resizeObserver?.disconnect();
		};
	});

	// Re-render when inputs or selection state change.
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
		<!-- <div class="text-xs font-semibold text-gray-700">What if an objective is relaxed?</div> -->
		{#if activeNodeSymbol}
			<button
				type="button"
				class="rounded bg-gray-100 px-2 py-0.5 text-[12px] text-gray-700 hover:bg-gray-200"
				onclick={() => {(activeNodeSymbol = null);onSelectNode?.(null);}}
			>
				Clear focus
			</button>
		{/if}
	</div>
<!-- 	<div class="mb-2 text-[12px] text-gray-500">
		Click an objective to highlight the possible effects of worsening it.
	</div> -->
	<div bind:this={containerEl} class="w-full">
		<svg
			bind:this={svgEl}
			width="100%"
			height={height}
			viewBox={`0 0 ${width} ${height}`}
			preserveAspectRatio="xMidYMid meet"
			role="img"
			aria-label="Shared network graph of What-if Cases effects"
		></svg>
	</div>
</div>
