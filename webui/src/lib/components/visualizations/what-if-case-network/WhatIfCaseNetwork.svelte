<script lang="ts">
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

	import { onMount } from 'svelte';
	import * as d3 from 'd3';
	import { IMPAIRING_COLOR, IMPROVING_COLOR } from '$lib/constants';

	type ObjectiveNode = {
		symbol: string;
		name?: string;
		maximize?: boolean;
	};

	type CaseDelta = {
		symbol: string;
		delta: number;
		percentDelta: number | null;
	};

	type WhatIfCase = {
		impairedSymbol: string;
		impairmentMagnitude: number;
		impairedTargetValue: number;
		deltas: CaseDelta[];
	};

	type LinkDatum = {
		source: string;
		target: string;
		value: number;
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
	let svgEl: SVGSVGElement | undefined;

	let width = $state(500);
	let height = $state(220);

	let nodeRadius = $derived(Math.max(22, Math.min(32, height * 0.14)));

	let activeNodeSymbol = $state<string | null>(null);

	let activeNodeName = $derived.by(() => {
		if (!activeNodeSymbol) return null;

		const objective = objectives.find((objective) => objective.symbol === activeNodeSymbol);

		return objective?.name ?? objective?.symbol ?? null;
	});

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

	function setActiveNode(symbol: string) {
		if (symbol === disabledNodeSymbol) return;

		activeNodeSymbol = activeNodeSymbol === symbol ? null : symbol;

		onSelectNode?.(activeNodeSymbol);
	}

	let activeCaseHasNoChanges = $derived.by(() => {
		if (!activeNodeSymbol) return false;

		const activeCase = cases.find((caseItem) => caseItem.impairedSymbol === activeNodeSymbol);

		if (!activeCase) return false;

		return activeCase.deltas.every((delta) => {
			const value = mode === 'percent' ? Number(delta.percentDelta ?? 0) : Number(delta.delta ?? 0);

			return Math.abs(value) < 1e-10;
		});
	});
	function renderGraph() {
		if (!svgEl) return;

		const svg = d3.select(svgEl);
		svg.selectAll('*').remove();

		if (objectives.length === 0 || cases.length === 0) {
			return;
		}

		const padding = nodeRadius / 2;

		const centerX = width / 2;
		const centerY = height / 2;

		const availableWidth = Math.max(1, width - padding * 2);

		const availableHeight = Math.max(1, height - padding * 2);

		const ringRadius = Math.min(availableWidth, availableHeight) * 0.42;

		const nodeCount = objectives.length;

		const minStroke = 1.2;
		const maxStroke = Math.max(2.5, Math.min(4.5, height * 0.015));

		const nodes = objectives.map((objective, index) => {
			const angle = (2 * Math.PI * index) / nodeCount - Math.PI / 2;

			return {
				id: objective.symbol,
				label: objective.name ?? objective.symbol,
				x: centerX + ringRadius * Math.cos(angle),
				y: centerY + ringRadius * Math.sin(angle)
			};
		});

		const nodeById = new Map(nodes.map((node) => [node.id, node]));

		const objectiveById = new Map(objectives.map((objective) => [objective.symbol, objective]));

		/*
		 * One link represents the achieved-value change
		 * associated with relaxing one desired value.
		 */
		const linkAccumulator = new Map<string, LinkDatum>();

		const activeCase = activeNodeSymbol
			? cases.find((caseItem) => caseItem.impairedSymbol === activeNodeSymbol)
			: null;

		for (const caseItem of cases) {
			for (const delta of caseItem.deltas) {
				const value =
					mode === 'percent' ? Number(delta.percentDelta ?? 0) : Number(delta.delta ?? 0);

				if (!Number.isFinite(value)) continue;
				/*
				 * Do not draw the selected desired value
				 * back onto itself.
				 *
				 * Its resulting achieved-value change is
				 * available in the detailed what-if view.
				 */
				if (caseItem.impairedSymbol === delta.symbol) {
					continue;
				}

				if (!nodeById.has(caseItem.impairedSymbol) || !nodeById.has(delta.symbol)) {
					continue;
				}

				const key = `${caseItem.impairedSymbol}` + `__${delta.symbol}`;

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

		const links = Array.from(linkAccumulator.values());
		if (links.length === 0) return;

		/*
		 * Convert a numerical delta into an
		 * improvement/worsening direction.
		 *
		 * For maximize:
		 *   positive delta = improvement
		 *
		 * For minimize:
		 *   negative delta = improvement
		 */
		function directionalChange(link: LinkDatum): number {
			const objective = objectiveById.get(link.target);

			if (!objective) return link.value;

			return objective.maximize ? link.value : -link.value;
		}

		function isImprovement(link: LinkDatum): boolean {
			return directionalChange(link) > 0;
		}

		/*function directionalChange(link: LinkDatum): number {
			const objective = objectiveById.get(link.target);

			if (!objective) return link.value;

			return objective.maximize ? link.value : -link.value;
		}*/

		function changeStatus(link: LinkDatum): 'improved' | 'worsened' | 'unchanged' {
			if (Math.abs(link.value) < 1e-10) {
				return 'unchanged';
			}

			return directionalChange(link) > 0 ? 'improved' : 'worsened';
		}

		function changeColor(link: LinkDatum): string {
			const status = changeStatus(link);

			if (status === 'improved') {
				return IMPROVING_COLOR;
			}

			if (status === 'worsened') {
				return IMPAIRING_COLOR;
			}

			return '#9ca3af';
		}

		const maxAbs = d3.max(links, (link) => Math.abs(link.value)) || 1;
		const strokeWidth = d3.scaleLinear().domain([0, maxAbs]).range([minStroke, maxStroke]);

		/*
		 * Arrow marker.
		 */
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

		/*
		 * Shorten links so arrows stop at the
		 * node boundary rather than its center.
		 */
		function shortenLine(
			source: {
				x: number;
				y: number;
			},
			target: {
				x: number;
				y: number;
			}
		) {
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

		function linkPath(link: LinkDatum) {
			const source = nodeById.get(link.source);

			const target = nodeById.get(link.target);

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

			return `M ${p.x1},${p.y1} ` + `Q ${cx},${cy} ` + `${p.x2},${p.y2}`;
		}

		/*
		 * The objective currently selected as the
		 * achieved value to improve cannot be used
		 * as the source relaxation.
		 */
		const visibleLinks = links.filter((link) => link.source !== disabledNodeSymbol);

		const linksGroup = svg.append('g');

		const linkPaths = linksGroup
			.selectAll<SVGPathElement, LinkDatum>('path')
			.data(visibleLinks)
			.join('path')
			.attr('d', linkPath)
			.attr('fill', 'none')
			.attr('stroke', (link) => changeColor(link))
			.attr('stroke-width', (link) =>
				changeStatus(link) === 'unchanged' ? 1.5 : strokeWidth(Math.abs(link.value))
			)
			.attr('stroke-dasharray', (link) => {
				const status = changeStatus(link);

				if (status === 'unchanged') return '3 3';
				if (status === 'worsened') return '6 4';

				return null;
			})
			.attr('marker-end', 'url(#what-if-arrow)')
			.attr('opacity', (link) => {
				if (!activeNodeSymbol) {
					// Hide zero-change edges until their scenario
					// is selected, otherwise the overview gets busy.
					return changeStatus(link) === 'unchanged' ? 0 : 0.85;
				}

				return link.source === activeNodeSymbol ? 1 : 0.08;
			});
		/*
		 * Explain each edge on hover.
		 */
		linkPaths.append('title').text((link) => {
			const source = nodeById.get(link.source);

			const target = nodeById.get(link.target);

			const result = isImprovement(link) ? 'improved' : 'worsened';

			return (
				`Relaxing the desired value of ` +
				`${source?.label ?? link.source} ` +
				`changed the achieved value of ` +
				`${target?.label ?? link.target} ` +
				`by ${formatSigned(link.value)} ` +
				`(${result}).`
			);
		});

		/*
		 * Values are shown only for the currently
		 * selected desired value.
		 */
		linksGroup
			.selectAll<SVGTextElement, LinkDatum>('text')
			.data(visibleLinks)
			.join('text')
			.attr('x', (link) => {
				const source = nodeById.get(link.source);

				const target = nodeById.get(link.target);

				if (!source || !target) {
					return 0;
				}

				return (source.x + target.x) / 2;
			})
			.attr('y', (link) => {
				const source = nodeById.get(link.source);

				const target = nodeById.get(link.target);

				if (!source || !target) {
					return 0;
				}

				return (source.y + target.y) / 2 - 9;
			})
			.attr('text-anchor', 'middle')
			.attr('font-size', 11)
			.attr('font-weight', 600)
			.attr('fill', (link) => changeColor(link))
			.attr('opacity', (link) => {
				if (!activeNodeSymbol) {
					return 0;
				}

				return link.source === activeNodeSymbol ? 1 : 0;
			})
			.attr('pointer-events', 'none')
			.text((link) =>
				changeStatus(link) === 'unchanged' ? 'No change' : formatSigned(link.value)
			);

		/*
		 * Objective nodes.
		 *
		 * In the default state, every selectable node
		 * represents a desired value that can be relaxed.
		 *
		 * After selection:
		 * - selected node = relaxed desired value
		 * - connected targets = resulting achieved values
		 */
		const nodeGroup = svg
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('transform', (node) => `translate(${node.x}, ${node.y})`)
			.attr('role', (node) => (node.id === disabledNodeSymbol ? null : 'button'))
			.attr('tabindex', (node) => (node.id === disabledNodeSymbol ? null : 0))
			.attr('aria-label', (node) => {
				if (node.id === disabledNodeSymbol) {
					return `${node.label}: selected ` + `achieved value`;
				}

				return (
					`Desired value of ` +
					`${node.label}. ` +
					`Select to inspect the ` +
					`what-if result when it ` +
					`is relaxed.`
				);
			})
			.style('cursor', (node) => (node.id === disabledNodeSymbol ? 'default' : 'pointer'))
			.on('click', (_, node) => {
				setActiveNode(node.id);
			})
			.on('keydown', (event: KeyboardEvent, node) => {
				if (event.key !== 'Enter' && event.key !== ' ') {
					return;
				}

				event.preventDefault();

				setActiveNode(node.id);
			});

		nodeGroup.append('title').text((node) => {
			if (node.id === disabledNodeSymbol) {
				return (
					`${node.label} is the ` +
					`achieved value currently ` +
					`being explored. Select ` +
					`another desired value to ` +
					`inspect a what-if result.`
				);
			}

			if (node.id === activeNodeSymbol) {
				return `Desired value of ` + `${node.label} selected ` + `for relaxation.`;
			}

			return (
				`Desired value of ` +
				`${node.label}. Select it ` +
				`to inspect what happened ` +
				`when it was relaxed.`
			);
		});

		nodeGroup
			.append('circle')
			.attr('r', nodeRadius)
			.attr('fill', (node) => {
				if (node.id === disabledNodeSymbol) {
					return '#dbeafe';
				}

				if (node.id === activeNodeSymbol) {
					return '#fef3c7';
				}

				return 'white';
			})
			.attr('stroke', (node) => {
				if (node.id === disabledNodeSymbol) {
					return '#2563eb';
				}

				if (node.id === activeNodeSymbol) {
					return '#f59e0b';
				}

				return '#111827';
			})
			.attr('stroke-width', (node) =>
				node.id === activeNodeSymbol || node.id === disabledNodeSymbol ? 2 : 1.5
			)
			.attr('opacity', (node) => {
				if (node.id === disabledNodeSymbol) {
					return 0.95;
				}

				if (!activeNodeSymbol) {
					return 1;
				}

				if (node.id === activeNodeSymbol) {
					return 1;
				}

				const isResultTarget = links.some(
					(link) => link.source === activeNodeSymbol && link.target === node.id
				);

				return isResultTarget ? 1 : 0.3;
			});

		function nodeRoleLabel(nodeId: string): string {
			if (nodeId === disabledNodeSymbol) {
				return ' ◆ ';
			}

			if (nodeId === activeNodeSymbol) {
				return 'relaxed';
			}

			if (!activeNodeSymbol) return '';

			const isTarget = links.some(
				(link) => link.source === activeNodeSymbol && link.target === nodeId
			);

			return isTarget ? 'achieved' : '';
		}

		/*
		 * Objective name.
		 */
		nodeGroup
			.append('text')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'middle')
			.attr('y', (node) => (nodeRoleLabel(node.id) ? -5 : 0))
			.attr('font-weight', 700)
			.attr('font-size', 12)
			.attr('fill', '#111827')
			.attr('pointer-events', 'none')
			.text((node) => (node.id === disabledNodeSymbol ? `${node.label}` : node.label));

		/*
		 * Small semantic role label appears only
		 * after a desired value is selected.
		 */
		nodeGroup
			.append('text')
			.attr('text-anchor', 'middle')
			.attr('dominant-baseline', 'middle')
			.attr('y', 10)
			.attr('font-size', 8)
			.attr('font-weight', 600)
			.attr('fill', (node) => (node.id === activeNodeSymbol ? '#b45309' : '#6b7280'))
			.attr('pointer-events', 'none')
			.text((node) => nodeRoleLabel(node.id));

		nodeGroup
			.filter((node) => node.id === activeNodeSymbol && activeCase != null)
			.append('text')
			.attr('text-anchor', 'middle')
			.attr('y', nodeRadius + 14)
			.attr('font-size', 9)
			.attr('font-weight', 600)
			.attr('fill', '#b45309')
			.attr('pointer-events', 'none')
			.text(`relaxed by ${activeCase?.impairmentMagnitude.toFixed(3)}`);

		nodeGroup
			.filter((node) => node.id === activeNodeSymbol && activeCase != null)
			.append('text')
			.attr('text-anchor', 'middle')
			.attr('y', nodeRadius + 26)
			.attr('font-size', 8)
			.attr('fill', '#6b7280')
			.attr('pointer-events', 'none')
			.text(`desired → ${activeCase?.impairedTargetValue.toFixed(3)}`);
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

	$effect(() => {
		objectives;
		cases;
		mode;
		activeNodeSymbol;
		width;
		height;

		renderGraph();
	});
</script>

<div class="rounded-md border border-gray-200 bg-white p-3">
	<div class="mb-2 flex items-start justify-between gap-3">
		<div class="min-w-0">
			<div class="text-xs font-semibold text-gray-700">
				{#if activeNodeName}
					Relaxed desired value:
					{activeNodeName}
				{:else}
					Select a desired value to relax
				{/if}
			</div>

			<div class="mt-0.5 text-[11px] leading-relaxed text-gray-500">
				{#if activeNodeName}
					Arrows show the resulting changes in the achieved values.
				{:else}
					Each node represents the desired value of an objective.
				{/if}
			</div>
		</div>

		{#if activeNodeSymbol}
			<button
				type="button"
				class="shrink-0 rounded bg-gray-100 px-2 py-0.5 text-[11px] text-gray-700 hover:bg-gray-200"
				onclick={() => {
					activeNodeSymbol = null;
					onSelectNode?.(null);
				}}
			>
				Clear
			</button>
		{/if}
	</div>

	{#if activeCaseHasNoChanges}
		<div class="mb-2 rounded bg-gray-50 px-2 py-1.5 text-[11px] text-gray-600">
			Relaxing this desired value produced no change in the achieved values in this what-if run.
		</div>
	{/if}
	<div bind:this={containerEl} class="w-full">
		<svg
			bind:this={svgEl}
			width="100%"
			{height}
			viewBox={`0 0 ${width} ${height}`}
			preserveAspectRatio="xMidYMid meet"
			role="img"
			aria-label="What-if graph. Nodes represent desired values that can be relaxed. Arrows show resulting changes in achieved values."
		></svg>
	</div>
</div>
