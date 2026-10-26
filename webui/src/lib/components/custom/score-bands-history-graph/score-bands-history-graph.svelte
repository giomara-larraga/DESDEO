<script lang="ts">
	import {
		SvelteFlow,
		Background,
		Controls,
		MiniMap,
		Position,
		type Node,
		type Edge
	} from '@xyflow/svelte';

	import dagre from '@dagrejs/dagre';

	import '@xyflow/svelte/dist/style.css';

	type HistoryItem = {
		state_id: number;
		parent_state_id: number | null;
		action: 'initialize' | 'iterate';
		selected_cluster_id: number | null;
		optimized: boolean;
	};

	type Props = {
		history: HistoryItem[];
		viewedStateId: number | null;
		onSelect: (stateId: number) => void;
	};

	let { history, viewedStateId, onSelect }: Props = $props();

	const NODE_WIDTH = 180;
	const NODE_HEIGHT = 65;
	function buildGraph(
		items: HistoryItem[],
		selectedId: number | null
	): { nodes: Node[]; edges: Edge[] } {
		// --------------------------------------------------
		// 1. Configure Dagre layout (left to right)
		// --------------------------------------------------

		const graph = new dagre.graphlib.Graph();

		graph.setDefaultEdgeLabel(() => ({}));

		graph.setGraph({
			rankdir: 'LR',
			nodesep: 70,
			ranksep: 110
		});

		const NODE_WIDTH = 240;
		const NODE_HEIGHT = 90;

		const ids = new Set(items.map((item) => item.state_id));

		const itemsById = new Map(items.map((item) => [item.state_id, item]));

		// --------------------------------------------------
		// 2. Calculate the level (depth) of each iteration
		// --------------------------------------------------

		const levels = new Map<number, number>();

		function getLevel(stateId: number, visiting = new Set<number>()): number {
			if (levels.has(stateId)) {
				return levels.get(stateId)!;
			}

			const item = itemsById.get(stateId);

			// Initialization is level 0.
			if (!item || item.action === 'initialize') {
				levels.set(stateId, 0);
				return 0;
			}

			if (visiting.has(stateId)) {
				throw new Error('Cycle detected in SCORE Bands history.');
			}

			visiting.add(stateId);

			const parent =
				item.parent_state_id === null ? undefined : itemsById.get(item.parent_state_id);

			const level = parent ? getLevel(parent.state_id, visiting) + 1 : 0;

			visiting.delete(stateId);

			levels.set(stateId, level);

			return level;
		}

		// --------------------------------------------------
		// 3. Number iterations chronologically within level
		// --------------------------------------------------

		const iterationsPerLevel = new Map<number, number>();

		const iterationLabels = new Map<number, string>();

		const chronologicalHistory = [...items].sort((a, b) => a.state_id - b.state_id);

		for (const item of chronologicalHistory) {
			if (item.action === 'initialize') {
				iterationLabels.set(item.state_id, 'Initialization');

				continue;
			}

			const level = getLevel(item.state_id);

			const iterationNumber = (iterationsPerLevel.get(level) ?? 0) + 1;

			iterationsPerLevel.set(level, iterationNumber);

			iterationLabels.set(item.state_id, `${level}.${iterationNumber}`);
		}

		// --------------------------------------------------
		// 4. Create nodes
		// --------------------------------------------------

		const nodes: Node[] = items.map((item) => {
			const id = String(item.state_id);

			const isSelected = item.state_id === selectedId;

			const isRoot = item.action === 'initialize';

			const iterationLabel = iterationLabels.get(item.state_id);

			const operationLabel = item.optimized ? 'Optimization' : 'Reclustering';

			const sourceLabel =
				item.selected_cluster_id === null ? 'All solutions' : `Band ${item.selected_cluster_id}`;

			graph.setNode(id, {
				width: NODE_WIDTH,
				height: NODE_HEIGHT
			});

			return {
				id,

				position: {
					x: 0,
					y: 0
				},

				sourcePosition: Position.Right,
				targetPosition: Position.Left,

				data: {
					label: isRoot
						? 'Initial SCORE Bands\nLevel 0'
						: `Iteration ${iterationLabel}\n${operationLabel}: ${sourceLabel}`
				},

				style: `
                width: ${NODE_WIDTH}px;
                height: ${NODE_HEIGHT}px;

                white-space: pre-line;

                border-radius: 12px;

                border: 2px solid ${isSelected ? '#0d9488' : '#94a3b8'};

                background: ${isSelected ? '#ccfbf1' : '#f8fafc'};

                color: #0f172a;

                font-size: 17px;
                line-height: 1.5;

                font-weight: ${isSelected ? '700' : '600'};

                padding: 16px;

                text-align: center;

                display: flex;
                align-items: center;
                justify-content: center;

                cursor: pointer;
            `
			};
		});

		// --------------------------------------------------
		// 5. Create edges (parent -> child)
		// --------------------------------------------------

		const edges: Edge[] = items
			.filter((item) => item.parent_state_id !== null && ids.has(item.parent_state_id))
			.map((item) => {
				const source = String(item.parent_state_id);
				const target = String(item.state_id);

				graph.setEdge(source, target);

				return {
					id: `edge-${source}-${target}`,
					source,
					target,

					type: 'smoothstep',

					animated: false
				};
			});

		// --------------------------------------------------
		// 6. Calculate node positions
		// --------------------------------------------------

		dagre.layout(graph);

		const positionedNodes: Node[] = nodes.map((node) => {
			const position = graph.node(node.id);

			return {
				...node,

				position: {
					x: position.x - NODE_WIDTH / 2,
					y: position.y - NODE_HEIGHT / 2
				}
			};
		});

		// --------------------------------------------------
		// 7. Return graph
		// --------------------------------------------------

		return {
			nodes: positionedNodes,
			edges
		};
	}
	let graphData = $derived(buildGraph(history, viewedStateId));
</script>

<div class="h-full min-h-0 w-full overflow-hidden">
	<SvelteFlow
		nodes={graphData.nodes}
		edges={graphData.edges}
		fitView
		minZoom={0.2}
		maxZoom={2}
		nodesDraggable={false}
		nodesConnectable={false}
		onnodeclick={({ node }) => {
			onSelect(Number(node.id));
		}}
	>
		<Background />
		<Controls />
		<!-- <MiniMap /> -->
	</SvelteFlow>
</div>
