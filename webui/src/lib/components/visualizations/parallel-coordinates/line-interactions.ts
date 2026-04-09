/**
 * Shared line styling and interaction handlers for the parallel coordinates plot.
 */
import * as d3 from "d3";

import type { DataPoint, ParallelCoordinatesOptions } from "./types";

type LineSelection = d3.Selection<SVGPathElement, DataPoint, SVGGElement, unknown>;

export function updateLineVisibility(
	lines: LineSelection,
	options: ParallelCoordinatesOptions,
	isSelected: (index: number) => boolean,
	passesFilter: (dataPoint: DataPoint) => boolean
): void {
	lines
		.style("display", (d) => {
			const passes = passesFilter(d);
			return passes ? null : "none";
		})
		.attr("opacity", (d, i) => {
			const passes = passesFilter(d);
			if (!passes) return 0;
			if (isSelected(i)) return 1;
			return options.opacity;
		})
		.attr("stroke", (d, i) => {
			const passes = passesFilter(d);
			if (!passes) return "#93c5fd";
			if (isSelected(i)) return "#3b82f6";
			return "#93c5fd";
		})
		.attr("stroke-width", (d, i) => {
			if (isSelected(i)) return options.strokeWidth + 1;
			return options.strokeWidth;
		});

	lines.each(function (_d, i) {
		if (isSelected(i) && this.parentNode) {
			this.parentNode.appendChild(this);
		}
	});
}

export function attachHoverInteractions(
	lines: LineSelection,
	enabled: boolean,
	options: ParallelCoordinatesOptions,
	data: DataPoint[],
	lineLabels: { [key: string]: string },
	tooltip: d3.Selection<HTMLDivElement, unknown, null, undefined>,
	isSelected: (index: number) => boolean,
	passesFilter: (dataPoint: DataPoint) => boolean
): void {
	if (!enabled) return;

	lines
		.on("mouseover", function (event, d) {
			if (!passesFilter(d)) return;

			const index = data.indexOf(d);
			d3.select(this).attr("stroke-width", options.strokeWidth + 2);

			if (lineLabels[index]) {
				tooltip.transition().duration(200).style("opacity", 0.9);
				tooltip
					.html(lineLabels[index])
					.style("left", `${event.pageX + 10}px`)
					.style("top", `${event.pageY - 28}px`);
			}
		})
		.on("mouseout", function (_event, d) {
			const index = data.indexOf(d);
			d3.select(this).attr(
				"stroke-width",
				isSelected(index) ? options.strokeWidth + 1 : options.strokeWidth
			);
			tooltip.transition().duration(500).style("opacity", 0);
		});
}

export function attachClickInteraction(
	lines: LineSelection,
	passesFilter: (dataPoint: DataPoint) => boolean,
	onLineClicked: (index: number, dataPoint: DataPoint) => void
): void {
	lines.on("click", function (_event, d) {
		if (!passesFilter(d)) return;

		const index = lines.data().indexOf(d);
		onLineClicked(index, d);
	});
}
