<script lang="ts">
	/**
	 * ParallelCoordinates.svelte
	 * Responsive parallel coordinates plot using D3.
	 *
	 * @author Giomara Larraga <glarragw@jyu.fi>
	 * @author Stina Palomaki <palomakistina@gmail.com> (Multi-selection support, label tooltips)
	 * @created June 2025
	 * @updated April 2026
	 *
	 * Responsibilities:
	 * - render axes and line geometry from the given dimensions and data
	 * - support hover/click interactions and optional brushing
	 * - overlay reference-point related visuals and tooltips
	 * - react to container resizing and prop/state updates
	 */

	import * as d3 from 'd3';
	import { onDestroy, onMount } from 'svelte';

	import { COLOR_PALETTE } from '../utils/colors';

	import { setupAxisBrushing as setupAxisBrushingImpl } from './brushing';
	import { createLineGenerator, createScales, passesFilters } from './chart-utils';
	import {
		attachClickInteraction,
		attachHoverInteractions,
		updateLineVisibility as updateLineVisibilityImpl
	} from './line-interactions';
	import {
		drawGenericReferencePoint as drawGenericReferencePointImpl,
		drawPreferredRanges as drawPreferredRangesImpl,
		drawReferenceSolutions as drawReferenceSolutionsImpl
	} from './reference-renderers';
	import type {
		BrushFilters,
		DataPoint,
		DimensionDefinition,
		ParallelCoordinatesOptions,
		ReferenceData
	} from './types';

	// --- Component Props ---
	// Main data array - each object represents one solution/data point
	export let data: DataPoint[] = [];

	// Dimension definitions - describes each axis with optional constraints
	export let dimensions: DimensionDefinition[] = [];

	// Optional reference data for enhanced visualization
	export let referenceData: ReferenceData | undefined = undefined;

	// Chart configuration options
	export let options: ParallelCoordinatesOptions = {
		showAxisLabels: true,
		highlightOnHover: true,
		strokeWidth: 2,
		opacity: 0.6,
		enableBrushing: true
	};
	// optional map of labels for each data index for tooltip display on hover
	export let lineLabels: { [key: string]: string } = {}; // Map of data index to label
	// Index of currently selected line (null = no selection)
	export let selectedIndex: number | null = null;
	// indexes for the case where multiple lines can be selected
	export let multipleSelectedIndexes: number[] | null = null;

	/**
	 * Helper function to check if a data point is selected
	 * Works with both single selection (selectedIndex) and multi-selection (multipleSelectedIndexes) modes
	 *
	 * @param index - The index of the data point to check
	 * @returns true if the data point is selected, false otherwise
	 */
	function isSelected(index: number): boolean {
		// Check if we're in single or multi-selection mode and if the point is selected
		return (
			(multipleSelectedIndexes === null && index === selectedIndex) ||
			(multipleSelectedIndexes !== null && multipleSelectedIndexes.includes(index))
		);
	}

	// Active brush filters - maps dimension name to [y1, y2] pixel coordinates
	export let brushFilters: BrushFilters = {};

	// Callback functions for parent component communication
	export let onLineSelect: ((index: number | null, data: DataPoint | null) => void) | undefined =
		undefined;
	export let onBrushFilter:
		| ((filters: BrushFilters) => void)
		| undefined = undefined;

	// --- Internal State Variables ---
	let width = 500; // Current container width in pixels
	let height = 400; // Current container height in pixels
	let svg: SVGSVGElement; // Reference to the SVG element
	let container: HTMLDivElement; // Reference to the container div
	let resizeObserver: ResizeObserver; // Observer for container size changes
	let brushes: { [dimension: string]: d3.BrushBehavior<unknown> } = {}; // D3 brush objects per dimension
	let scales: { [key: string]: d3.ScaleLinear<number, number> } = {}; // D3 scales for each dimension
	let tooltip: d3.Selection<HTMLDivElement, unknown, null, undefined>; // Single tooltip for all uses


	// Helper function to add tooltip functionality to a path
	function addTooltip(
		path: d3.Selection<SVGPathElement, any, any, any>,
		label?: string
	) {
		if (!label) return path; // If no label, return path without tooltip

		return path
			.on('mouseover.tooltip', function (event) {
				tooltip.transition().duration(200).style('opacity', 0.9);
				tooltip
					.html(label)
					.style('left', event.pageX + 10 + 'px')
					.style('top', event.pageY - 28 + 'px');
			})
			.on('mouseout.tooltip', function () {
				tooltip.transition().duration(500).style('opacity', 0);
			});
	}


	/**
	 * Handles line selection when user clicks on a data line
	 * Implements single-selection behavior (only one line can be selected)
	 *
	 * @param index - Index of the clicked line in the data array
	 * @param dataPoint - The actual data object for the clicked line
	 */
	function handleLineClick(index: number, dataPoint: DataPoint) {
		// If we're in multi-selection mode
		if (multipleSelectedIndexes !== null) {
			// Let the parent component handle selection/deselection logic
			onLineSelect?.(index, dataPoint);
			return;
		}

		// Single selection mode
		if (selectedIndex === index) {
			// Deselect if already selected
			selectedIndex = null;
			onLineSelect?.(null, null);
		} else {
			// Select new item
			selectedIndex = index;
			onLineSelect?.(index, dataPoint);
		}
	}

	/**
	 * Main function that draws the entire parallel coordinates plot
	 * Orchestrates all the drawing functions and handles the overall layout
	 */
	function drawChart(): void {
		if (!data.length || !dimensions.length) return; // Skip if no data to display

		// Define margins around the chart area
		const margin = { top: 20, right: 40, bottom: 20, left: 40 };
		const innerWidth = width - margin.left - margin.right; // Available width for chart
		const innerHeight = height - margin.top - margin.bottom; // Available height for chart

		// Clear any previous chart content
		d3.select(svg).selectAll('*').remove();

		// Clear brushes object but preserve current filter state
		const currentFilters = { ...brushFilters };
		brushes = {};

		// Create main SVG group with proper positioning
		const svgElement = d3
			.select(svg)
			.attr('width', width)
			.attr('height', height)
			.append('g')
			.attr('transform', `translate(${margin.left}, ${margin.top})`); // Offset by margins

		// Create scales for mapping data values to pixel coordinates
		const newScales = createScales(dimensions, data, innerHeight, margin);
		scales = newScales;

		// Create scale for positioning dimensions horizontally
		const xScale = d3
			.scalePoint()
			.domain(dimensions.map((d) => d.symbol)) // All dimension names
			.range([0, innerWidth]) // Spread across available width
			.padding(0.1); // Small padding between axes

		// Create line generator for drawing data paths
		const line = createLineGenerator(newScales, xScale);

		// Create color scale for axis identification
		const axisColorScale = d3
			.scaleOrdinal<string, string>()
			.domain(dimensions.map((d) => d.symbol))
			.range(COLOR_PALETTE); // Use predefined color palette

		// Draw preferred ranges first (behind everything else)
		drawPreferredRangesImpl(svgElement, newScales, xScale, referenceData?.preferredRanges);

		// Draw axes and labels
		dimensions.forEach((dim) => {
			const x = xScale(dim.symbol)!; // Get x position for this dimension
			const axisColor = axisColorScale(dim.symbol); // Get color for this dimension

			// Draw axis line with tick marks and labels
			svgElement
				.append('g')
				.attr('class', `axis axis-${dim.symbol}`)
				.attr('transform', `translate(${x}, 0)`) // Position at correct x coordinate
				.call(d3.axisLeft(newScales[dim.symbol]).ticks(5)); // Left-aligned axis with 5 ticks

			// Draw axis labels and colored identification squares
			if (options.showAxisLabels) {
				// Colored square for visual identification of each axis
				svgElement
					.append('rect')
					.attr('class', 'axis-color-square')
					.attr('x', x - 20) // Position to the left of the axis
					.attr('y', -18) // Position above the chart area
					.attr('width', 10)
					.attr('height', 10)
					.attr('fill', axisColor) // Use dimension's assigned color
					.attr('stroke', '#333') // Dark border
					.attr('stroke-width', 1)
					.attr('rx', 2) // Rounded corners
					.attr('ry', 2);

				// Axis name with direction indicator
				svgElement
					.append('text')
					.attr('class', 'axis-label')
					.attr('x', x - 5) // Position to the right of the colored square
					.attr('y', -8) // Position just above the chart area
					.attr('text-anchor', 'start') // Left-align text
					.style('font-size', '12px')
					.style('font-weight', 'bold')
					.style('fill', '#333')
					.text(dim.name);

				// Add an arrow if direction is specified
				if (dim.direction) {
					const arrowX = x; // Rough estimate of text width
					svgElement
						.append('path')
						.attr(
							'd',
							dim.direction === 'max'
								? `M${arrowX - 5},8 L${arrowX},0 L${arrowX + 5},8` // Up arrow
								: `M${arrowX - 5},0 L${arrowX},8 L${arrowX + 5},0` // Down arrow
						)
						.attr('fill', '#333')
						.attr('stroke', 'none');
				}
			}
		});

		// Draw previous reference points (light red, multiple)
		if (referenceData?.previousReferencePoints) {
			referenceData.previousReferencePoints.forEach((prevPoint) => {
				drawGenericReferencePointImpl(svgElement, newScales, xScale, line, dimensions, prevPoint, {
					groupClass: `reference-point`,
					color: '#fecaca' // light red color, tailwind red 200
				}, options.strokeWidth, addTooltip);
			});
		}

		// Draw reference visualizations (on top of data lines)
		// Draw current reference point (red)
		drawGenericReferencePointImpl(svgElement, newScales, xScale, line, dimensions, referenceData?.referencePoint, {
			groupClass: 'reference-point',
			color: '#f87171' // Red color, tailwind red 400
		}, options.strokeWidth, addTooltip);

		drawReferenceSolutionsImpl(
			svgElement,
			newScales,
			xScale,
			line,
			dimensions,
			referenceData,
			options.strokeWidth,
			addTooltip
		);

		// Draw main data lines
		const lines = svgElement
			.append('g')
			.attr('class', 'data-lines')
			.selectAll<SVGPathElement, DataPoint>('path')
			.data(data) // Bind data array
			.join('path') // Create path element for each data point
			.attr('d', (d, i) => {
				// Convert data point to line coordinates
				const lineData: [string, number][] = dimensions
					.map((dim) => [dim.symbol, d[dim.symbol]] as [string, number])
					.filter(([, value]) => value !== undefined && value !== null);
				return line(lineData); // Generate SVG path string
			})
			.attr('fill', 'none') // Lines have no fill, only stroke
			.attr('class', (d, i) => `line line-${i}`) // Unique class for each line
			.style('cursor', 'pointer'); // Show pointer cursor to indicate clickability

		const updateVisibleLines = (
			targetLines: d3.Selection<SVGPathElement, DataPoint, SVGGElement, unknown>
		) => {
			updateLineVisibilityImpl(
				targetLines,
				options,
				isSelected,
				(d) => passesFilters(d, brushFilters, scales)
			);
		};

		// Set up brushing for each axis (must be done before line updates)
		dimensions.forEach((dim) => {
			const x = xScale(dim.symbol)!;
			const brush = setupAxisBrushingImpl({
				svgElement,
				dimension: dim.symbol,
				xPos: x,
				innerHeight,
				lines,
				enableBrushing: options.enableBrushing,
				brushFilters,
				onUpdateLines: updateVisibleLines,
				onBrushFilter
			});

			if (brush) {
				brushes[dim.symbol] = brush;
			}
		});

		// Apply initial line styling based on current state
		updateVisibleLines(lines);

		attachHoverInteractions(
			lines,
			options.highlightOnHover,
			options,
			data,
			lineLabels,
			tooltip,
			isSelected,
			(d) => passesFilters(d, brushFilters, scales)
		);

		attachClickInteraction(
			lines,
			(d) => passesFilters(d, brushFilters, scales),
			(index, d) => {
				handleLineClick(index, d);
				updateVisibleLines(lines);
			}
		);

		// Add filter status information at the bottom
		const activeFilters = Object.keys(brushFilters).length;
		if (activeFilters > 0) {
			const visibleLines = data.filter((d) => passesFilters(d, brushFilters, scales)).length;
			svgElement
				.append('text')
				.attr('class', 'filter-info')
				.attr('x', 10)
				.attr('y', innerHeight + 25) // Position below the chart
				.style('font-size', '11px')
				.style('fill', '#666')
				.text(
					`Showing ${visibleLines} of ${data.length} solutions (${activeFilters} filter${activeFilters > 1 ? 's' : ''} active)`
				);
		}
	}

	// --- Lifecycle Management ---

	/**
	 * Component initialization
	 * Sets up responsive behavior and draws initial chart
	 */
	onMount(() => {
		// Create single tooltip for the component
		tooltip = d3.select(container).append('div').attr('class', 'tooltip').style('opacity', 0);

		// Set up responsive behavior using ResizeObserver
		resizeObserver = new ResizeObserver((entries) => {
			for (const entry of entries) {
				const rect = entry.contentRect;
				width = rect.width; // Update width when container resizes
				height = rect.height; // Update height when container resizes
				drawChart(); // Redraw chart with new dimensions
			}
		});
		resizeObserver.observe(container); // Start observing the container
		drawChart(); // Draw initial chart
	});

	/**
	 * Component cleanup
	 * Disconnect observers to prevent memory leaks
	 */
	onDestroy(() => {
		resizeObserver?.disconnect();
	});

	// --- Reactive Updates ---
	// Redraw chart whenever any of these values change
	$: data,
		dimensions,
		options,
		referenceData,
		selectedIndex,
		multipleSelectedIndexes,
		brushFilters,
		width,
		height,
		drawChart();
</script>

<!--
    Responsive container for the parallel coordinates plot.
    Uses aspect ratio to maintain consistent proportions.
-->
<div bind:this={container} style="height: 100%;width: 100%;">
	<svg bind:this={svg} style="width: 100%; height: 100%;" />
</div>

<style>
	/* Axis styling */
	:global(.axis) {
		font-size: 11px;
	}

	:global(.axis path),
	:global(.axis line) {
		fill: none;
		stroke: #000;
		shape-rendering: crispEdges;
	}

	/* Data line animations */
	:global(.line) {
		transition:
			stroke-width 0.2s,
			opacity 0.2s;
	}

	/* Text styling */
	:global(.axis-label) {
		fill: #333;
	}

	:global(.direction-label) {
		fill: #666;
	}

	:global(.selection-title) {
		fill: #333;
	}

	:global(.filter-info) {
		fill: #666;
	}

	/* Colored squares for axis identification */
	:global(.axis-color-square) {
		stroke: #333;
		stroke-width: 1;
		rx: 2;
		ry: 2;
	}

	/* Reference data styling - control interaction */
	:global(.preferred-ranges rect) {
		pointer-events: none;
	}

	:global(.reference-point path) {
		pointer-events: auto;
		cursor: default; /* Shows regular cursor instead of pointer */
	}

	:global(.reference-point circle) {
		pointer-events: auto;
		cursor: default; /* Shows regular cursor instead of pointer */
	}

	/* Allow hover events but prevent clicks */
	:global(.preferred-solutions path),
	:global(.non-preferred-solutions path),
	:global(.other-solutions path) {
		pointer-events: auto;
		cursor: default; /* Shows regular cursor instead of pointer */
	}

	/* Brush styling */
	:global(.brush .selection) {
		fill: #4a90e2;
		opacity: 0.1;
	}

	:global(.brush .handle) {
		fill: #4a90e2;
		stroke: #4a90e2;
		stroke-width: 2;
	}

	/* Brush highlight rectangles */
	:global(.brush-highlight) {
		fill: #4a90e2;
		opacity: 0.2;
		stroke: #4a90e2;
		stroke-width: 2;
		stroke-dasharray: 3, 3;
		pointer-events: none;
		transition: opacity 0.2s ease;
	}

	:global(.brush-highlight:hover) {
		opacity: 0.3;
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
	}
</style>
