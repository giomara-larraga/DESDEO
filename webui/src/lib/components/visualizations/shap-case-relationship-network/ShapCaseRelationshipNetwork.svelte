<script lang="ts">
	import { onDestroy, onMount } from 'svelte';
	import * as d3 from 'd3';

	type ObjectiveItem = {
		symbol: string;
		name?: string;
		maximize: boolean;
	};

	type ObjectiveValue = number | number[] | null | undefined;

	type SelectedNetworkNode = {
		side: 'desired' | 'achieved';
		symbol: string;
		name: string;
	};

	type NetworkNode = {
		id: string;
		symbol: string;
		side: 'desired' | 'achieved';
		name: string;
		value: number | null;
		x: number;
		y: number;
	};

	type LinkType = 'supportive' | 'limiting';

	type NetworkLink = {
		source: string;
		target: string;
		value: number;
		type: LinkType;
	};

	let {
		objectives,
		iterationDesiredValues,
		achievedValues,
		shapValues,
		threshold = 0,
		targetObjectiveSymbol = null,
		suggestedDesiredValueSymbol = null,
		showLegend = true,
		onNodeSelect
	}: {
		objectives: ObjectiveItem[];
		iterationDesiredValues: number[];
		achievedValues: Record<string, ObjectiveValue> | null;
		shapValues: Record<string, Record<string, number>> | null;
		threshold?: number;
		targetObjectiveSymbol?: string | null;
		suggestedDesiredValueSymbol?: string | null;
		showLegend?: boolean;
		onNodeSelect?: (node: SelectedNetworkNode | null) => void;
	} = $props();

	const MIN_WIDTH = 420;

	const BOX_WIDTH = 96;
	const BOX_HEIGHT = 44;

	let chartWidth = $state(MIN_WIDTH);
	let height = $state(320);

	let containerEl: HTMLDivElement | null = null;
	let svgEl: SVGSVGElement | undefined;

	let resizeObserver: ResizeObserver | null = null;

	let activeNodeId = $state<string | null>(null);

	let previousTargetObjectiveSymbol = $state<string | null>(null);

	function normalizeSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	function symbolsEqual(a: string | null | undefined, b: string | null | undefined): boolean {
		if (!a || !b) return false;

		return normalizeSymbol(a) === normalizeSymbol(b);
	}

	function toFinite(value: ObjectiveValue): number | null {
		const numeric = Array.isArray(value) ? Number(value[0]) : Number(value);

		return Number.isFinite(numeric) ? numeric : null;
	}

	function formatValue(value: number | null): string {
		if (value == null || !Number.isFinite(value)) {
			return 'n/a';
		}

		return value.toFixed(3);
	}

	function formatSigned(value: number): string {
		const absolute = Math.abs(value);

		if (value > 0) {
			return `+${absolute.toFixed(3)}`;
		}

		if (value < 0) {
			return `-${absolute.toFixed(3)}`;
		}

		return '0.000';
	}

	function truncateLabel(label: string, maximumLength = 14): string {
		if (label.length <= maximumLength) {
			return label;
		}

		return `${label.slice(0, maximumLength - 1)}…`;
	}

	function findShapRow(outputSymbol: string): Record<string, number> {
		if (!shapValues) return {};

		const normalizedOutput = normalizeSymbol(outputSymbol);

		const direct = shapValues[outputSymbol] ?? shapValues[`z_${outputSymbol}`];

		if (direct) return direct;

		const entry = Object.entries(shapValues).find(
			([key]) => normalizeSymbol(key) === normalizedOutput
		);

		return entry?.[1] ?? {};
	}

	function findValueInRecord(
		record: Record<string, ObjectiveValue>,
		symbol: string
	): ObjectiveValue {
		if (symbol in record) {
			return record[symbol];
		}

		if (`z_${symbol}` in record) {
			return record[`z_${symbol}`];
		}

		const normalizedSymbol = normalizeSymbol(symbol);

		const entry = Object.entries(record).find(([key]) => normalizeSymbol(key) === normalizedSymbol);

		return entry?.[1];
	}

	function findShapValue(row: Record<string, number>, symbol: string): number {
		const normalizedSymbol = normalizeSymbol(symbol);

		const direct = row[symbol] ?? row[`z_${symbol}`];

		if (direct != null && Number.isFinite(Number(direct))) {
			return Number(direct);
		}

		const entry = Object.entries(row).find(([key]) => normalizeSymbol(key) === normalizedSymbol);

		const value = Number(entry?.[1]);

		return Number.isFinite(value) ? value : 0;
	}

	function contributionColor(type: LinkType): string {
		return type === 'supportive' ? '#0C7BDC' : '#DC3220';
	}

	function isNodeConnected(nodeId: string, links: NetworkLink[]): boolean {
		if (!activeNodeId) return true;

		if (nodeId === activeNodeId) {
			return true;
		}

		return links.some((link) =>
			link.source === activeNodeId || link.target === activeNodeId
				? link.source === nodeId || link.target === nodeId
				: false
		);
	}

	function isTargetNode(node: NetworkNode): boolean {
		return node.side === 'achieved' && symbolsEqual(node.symbol, targetObjectiveSymbol);
	}

	function isSuggestedNode(node: NetworkNode): boolean {
		return node.side === 'desired' && symbolsEqual(node.symbol, suggestedDesiredValueSymbol);
	}

	function nodeFill(node: NetworkNode): string {
		if (isTargetNode(node)) {
			return '#EFF6FF';
		}

		if (isSuggestedNode(node)) {
			return '#FFFBEB';
		}

		if (activeNodeId === node.id) {
			return '#F9FAFB';
		}

		return '#FFFFFF';
	}

	function nodeStroke(node: NetworkNode): string {
		if (isTargetNode(node)) {
			return '#2563EB';
		}

		if (isSuggestedNode(node)) {
			return '#F59E0B';
		}

		if (activeNodeId === node.id) {
			return '#374151';
		}

		return '#D1D5DB';
	}

	function nodeStrokeWidth(node: NetworkNode): number {
		if (isTargetNode(node) || isSuggestedNode(node)) {
			return 2;
		}

		if (activeNodeId === node.id) {
			return 2;
		}

		return 1.2;
	}

	function nodeMarker(node: NetworkNode): string {
		if (isSuggestedNode(node)) {
			return '★ ';
		}

		if (isTargetNode(node)) {
			return '❤︎ ';
		}

		return '';
	}

	function renderGraph() {
		if (!svgEl) return;

		const width = chartWidth;
		const svg = d3.select(svgEl);

		svg.selectAll('*').remove();

		if (!objectives.length || !achievedValues || !shapValues) {
			return;
		}

		const leftX = 12;
		const rightX = width - BOX_WIDTH - 12;

		const topY = 40;
		const bottomY = height - 56;

		const stepY = objectives.length > 1 ? (bottomY - topY) / (objectives.length - 1) : 0;

		/* ---------------------------------
		 * Nodes
		 * --------------------------------- */

		const desiredNodes: NetworkNode[] = objectives.map((objective, index) => {
			const desired = Number(iterationDesiredValues[index]);

			return {
				id: `p_${objective.symbol}`,
				symbol: objective.symbol,
				side: 'desired',
				name: objective.name ?? objective.symbol,
				value: Number.isFinite(desired) ? desired : null,
				x: leftX,
				y: topY + index * stepY
			};
		});

		const achievedNodes: NetworkNode[] = objectives.map((objective, index) => {
			const raw = findValueInRecord(achievedValues, objective.symbol);

			return {
				id: `a_${objective.symbol}`,
				symbol: objective.symbol,
				side: 'achieved',
				name: objective.name ?? objective.symbol,
				value: toFinite(raw),
				x: rightX,
				y: topY + index * stepY
			};
		});

		const nodes = [...desiredNodes, ...achievedNodes];

		/* ---------------------------------
		 * Contribution links
		 * --------------------------------- */

		const links: NetworkLink[] = [];

		for (const targetObjective of objectives) {
			const shapRow = findShapRow(targetObjective.symbol);

			for (const inputObjective of objectives) {
				const rawShap = findShapValue(shapRow, inputObjective.symbol);

				if (!Number.isFinite(rawShap)) {
					continue;
				}

				/*
				 * Positive helpScore:
				 * supportive contribution.
				 *
				 * Negative helpScore:
				 * limiting contribution.
				 *
				 * For minimized output objectives,
				 * reverse the SHAP sign.
				 */
				const helpScore = targetObjective.maximize ? rawShap : -rawShap;

				if (Math.abs(helpScore) <= threshold) {
					continue;
				}

				links.push({
					source: `p_${inputObjective.symbol}`,
					target: `a_${targetObjective.symbol}`,
					value: helpScore,
					type: helpScore >= 0 ? 'supportive' : 'limiting'
				});
			}
		}

		/* ---------------------------------
		 * Column headings
		 * --------------------------------- */

		svg
			.append('text')
			.attr('x', leftX)
			.attr('y', 17)
			.attr('font-size', 10)
			.attr('font-weight', 600)
			.attr('fill', '#6B7280')
			.text('Desired values');

		svg
			.append('text')
			.attr('x', rightX)
			.attr('y', 17)
			.attr('font-size', 10)
			.attr('font-weight', 600)
			.attr('fill', '#6B7280')
			.text('Achieved values');

		if (links.length === 0) {
			svg
				.append('text')
				.attr('x', width / 2)
				.attr('y', height / 2)
				.attr('text-anchor', 'middle')
				.attr('fill', '#6B7280')
				.attr('font-size', 11)
				.text('No contributions are available.');

			return;
		}

		const maxAbs = d3.max(links, (link) => Math.abs(link.value)) ?? 1;

		const strokeWidth = d3.scaleLinear().domain([0, maxAbs]).range([1.2, 5.5]);

		const byId = new Map(nodes.map((node) => [node.id, node]));

		function anchorRight(node: NetworkNode) {
			return {
				x: node.x + BOX_WIDTH,
				y: node.y + BOX_HEIGHT / 2
			};
		}

		function anchorLeft(node: NetworkNode) {
			return {
				x: node.x,
				y: node.y + BOX_HEIGHT / 2
			};
		}

		function linkPath(link: NetworkLink): string {
			const source = byId.get(link.source);
			const target = byId.get(link.target);

			if (!source || !target) {
				return '';
			}

			const start = anchorRight(source);

			const end = anchorLeft(target);

			const middleX = (start.x + end.x) / 2;

			return [
				`M ${start.x} ${start.y}`,
				`C ${middleX} ${start.y},`,
				`${middleX} ${end.y},`,
				`${end.x} ${end.y}`
			].join(' ');
		}

		function isActiveLink(link: NetworkLink): boolean {
			if (!activeNodeId) {
				return false;
			}

			return link.source === activeNodeId || link.target === activeNodeId;
		}

		/* ---------------------------------
		 * Links
		 * --------------------------------- */

		svg
			.append('g')
			.attr('aria-label', 'Contribution relationships')
			.selectAll('path')
			.data(links)
			.join('path')
			.attr('d', linkPath)
			.attr('fill', 'none')
			.attr('stroke', (link) => contributionColor(link.type))
			.attr('stroke-width', (link) => strokeWidth(Math.abs(link.value)))
			.attr('stroke-linecap', 'round')
			.attr('opacity', (link) => {
				if (!activeNodeId) {
					return 0.18;
				}

				return isActiveLink(link) ? 0.95 : 0.06;
			})
			.each(function (link) {
				d3.select(this)
					.append('title')
					.text(
						`${link.type === 'supportive' ? 'Supportive' : 'Limiting'} contribution: ${formatSigned(link.value)}`
					);
			});

		/* ---------------------------------
		 * Link value labels
		 *
		 * Exact values only appear for the
		 * currently selected node.
		 * --------------------------------- */

		svg
			.append('g')
			.selectAll('text')
			.data(links)
			.join('text')
			.attr('x', (link) => {
				const source = byId.get(link.source);
				const target = byId.get(link.target);

				if (!source || !target) {
					return 0;
				}

				return (anchorRight(source).x + anchorLeft(target).x) / 2;
			})
			.attr('y', (link) => {
				const source = byId.get(link.source);
				const target = byId.get(link.target);

				if (!source || !target) {
					return 0;
				}

				return (anchorRight(source).y + anchorLeft(target).y) / 2 - 7;
			})
			.attr('text-anchor', 'middle')
			.attr('font-size', 9)
			.attr('font-weight', 600)
			.attr('fill', (link) => contributionColor(link.type))
			.attr('stroke', '#FFFFFF')
			.attr('stroke-width', 3)
			.attr('paint-order', 'stroke')
			.attr('pointer-events', 'none')
			.attr('opacity', (link) => (isActiveLink(link) ? 1 : 0))
			.text((link) => formatSigned(link.value));

		/* ---------------------------------
		 * Nodes
		 * --------------------------------- */

		const nodeGroup = svg
			.append('g')
			.selectAll('g')
			.data(nodes)
			.join('g')
			.attr('transform', (node) => `translate(${node.x}, ${node.y})`)
			.attr('opacity', (node) => (isNodeConnected(node.id, links) ? 1 : 0.32))
			.style('cursor', 'pointer')
			.on('click', (_, node) => {
				const isClearing = activeNodeId === node.id;

				if (isClearing) {
					activeNodeId = null;
					onNodeSelect?.(null);
					return;
				}

				activeNodeId = node.id;

				onNodeSelect?.({
					side: node.side,
					symbol: node.symbol,
					name: node.name
				});
			});

		nodeGroup.append('title').text((node) => {
			if (node.side === 'desired') {
				return `Select to see how the desired value for ${node.name} contributed across the achieved values.`;
			}

			return `Select to see which desired values contributed to the achieved value of ${node.name}.`;
		});

		nodeGroup
			.append('rect')
			.attr('width', BOX_WIDTH)
			.attr('height', BOX_HEIGHT)
			.attr('rx', 7)
			.attr('fill', nodeFill)
			.attr('stroke', nodeStroke)
			.attr('stroke-width', nodeStrokeWidth);

		/* Objective name */

		nodeGroup
			.append('text')
			.attr('x', BOX_WIDTH / 2)
			.attr('y', 17)
			.attr('text-anchor', 'middle')
			.attr('font-size', 10)
			.attr('font-weight', 600)
			.attr('fill', '#1F2937')
			.attr('pointer-events', 'none')
			.text((node) => `${nodeMarker(node)}${truncateLabel(node.name)}`);

		/* Desired / achieved numeric value */

		nodeGroup
			.append('text')
			.attr('x', BOX_WIDTH / 2)
			.attr('y', 32)
			.attr('text-anchor', 'middle')
			.attr('font-size', 9)
			.attr('fill', '#6B7280')
			.attr('pointer-events', 'none')
			.text((node) => formatValue(node.value));
	}

	/* ---------------------------------
	 * Keep the selected achieved
	 * objective focused when it changes.
	 * --------------------------------- */

	$effect(() => {
		if (targetObjectiveSymbol === previousTargetObjectiveSymbol) {
			return;
		}

		previousTargetObjectiveSymbol = targetObjectiveSymbol;

		activeNodeId = targetObjectiveSymbol ? `a_${targetObjectiveSymbol}` : null;
	});

	onMount(() => {
		if (targetObjectiveSymbol) {
			activeNodeId = `a_${targetObjectiveSymbol}`;
		}

		const updateSize = () => {
			if (!containerEl) return;

			const measuredWidth = Math.floor(containerEl.getBoundingClientRect().width);

			if (measuredWidth <= 0) {
				return;
			}

			chartWidth = Math.max(MIN_WIDTH, measuredWidth);

			/*
			 * Preserve enough vertical room
			 * for every objective row.
			 */
			const rowBasedHeight = 120 + Math.max(0, objectives.length - 1) * 58;

			const widthBasedHeight = Math.min(440, chartWidth * 0.72);

			height = Math.max(300, rowBasedHeight, widthBasedHeight);
		};

		updateSize();

		resizeObserver = new ResizeObserver(updateSize);

		if (containerEl) {
			resizeObserver.observe(containerEl);
		}
	});

	onDestroy(() => {
		resizeObserver?.disconnect();
		resizeObserver = null;
	});

	$effect(() => {
		chartWidth;
		height;

		objectives;
		iterationDesiredValues;
		achievedValues;
		shapValues;

		threshold;
		activeNodeId;

		targetObjectiveSymbol;
		suggestedDesiredValueSymbol;

		renderGraph();
	});
</script>

<div class="w-full">
	<div bind:this={containerEl} class="overflow-x-auto">
		<svg
			bind:this={svgEl}
			width="100%"
			{height}
			viewBox={`0 0 ${chartWidth} ${height}`}
			preserveAspectRatio="xMidYMid meet"
			role="img"
			aria-label="Contribution relationship graph between desired and achieved values"
			class="block"
		></svg>
	</div>

	{#if showLegend}
		<div
			class="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1.5 text-[11px] text-gray-500"
			aria-label="Contribution relationship legend"
		>
			<span class="inline-flex items-center gap-1.5">
				<span class="h-0.5 w-4 rounded-full bg-[#0C7BDC]" aria-hidden="true"></span>
				Supportive
			</span>

			<span class="inline-flex items-center gap-1.5">
				<span class="h-0.5 w-4 rounded-full bg-[#DC3220]" aria-hidden="true"></span>
				Limiting
			</span>

			<span class="inline-flex items-center gap-1.5">
				<span class="inline-flex items-center gap-0.5" aria-hidden="true">
					<span class="h-px w-3 rounded-full bg-gray-400"></span>
					<span class="h-1 w-3 rounded-full bg-gray-400"></span>
				</span>

				Thicker = larger contribution
			</span>

			{#if suggestedDesiredValueSymbol}
				<span class="inline-flex items-center gap-1">
					<span class="font-semibold text-amber-600" aria-hidden="true"> ★ </span>
					R-XIMO suggestion
				</span>
			{/if}

			{#if targetObjectiveSymbol}
				<span class="inline-flex items-center gap-1">
					<span class="font-semibold text-blue-700" aria-hidden="true"> ❤︎ </span>
					Selected achieved value
				</span>
			{/if}
		</div>
	{/if}
</div>
