/**
 * D3 brush setup and filter synchronization helpers.
 */
import * as d3 from "d3";

import type { BrushFilters, DataPoint } from "./types";

type LineSelection = d3.Selection<SVGPathElement, DataPoint, SVGGElement, unknown>;

type SetupAxisBrushingArgs = {
	svgElement: d3.Selection<SVGGElement, unknown, null, undefined>;
	dimension: string;
	xPos: number;
	innerHeight: number;
	lines: LineSelection;
	enableBrushing: boolean;
	brushFilters: BrushFilters;
	onUpdateLines: (lines: LineSelection) => void;
	onBrushFilter?: (filters: BrushFilters) => void;
};

export function setupAxisBrushing({
	svgElement,
	dimension,
	xPos,
	innerHeight,
	lines,
	enableBrushing,
	brushFilters,
	onUpdateLines,
	onBrushFilter
}: SetupAxisBrushingArgs): d3.BrushBehavior<unknown> | null {
	if (!enableBrushing) return null;

	const brush = d3
		.brushY()
		.extent([
			[xPos - 10, 0],
			[xPos + 10, innerHeight]
		])
		.on("brush", function (event) {
			const parent = this.parentNode;
			if (!(parent instanceof SVGGElement)) return;
			const brushGroup = d3.select(parent);

			if (event.selection) {
				const [y1, y2] = event.selection as [number, number];

				brushGroup.select(".brush-highlight").remove();
				brushGroup
					.append("rect")
					.attr("class", "brush-highlight")
					.attr("x", xPos - 15)
					.attr("y", y1)
					.attr("width", 30)
					.attr("height", y2 - y1)
					.attr("fill", "#4a90e2")
					.attr("opacity", 0.2)
					.attr("stroke", "#4a90e2")
					.attr("stroke-width", 2)
					.attr("stroke-dasharray", "3,3")
					.style("pointer-events", "none");
			}
		})
		.on("end", function (event) {
			const parent = this.parentNode;
			if (!(parent instanceof SVGGElement)) return;
			const brushGroup = d3.select(parent);

			if (!event.selection) {
				delete brushFilters[dimension];
				brushGroup.select(".brush-highlight").remove();
			} else {
				const [y1, y2] = event.selection as [number, number];
				brushFilters[dimension] = [y1, y2];

				brushGroup.select(".brush-highlight").remove();
				brushGroup
					.append("rect")
					.attr("class", "brush-highlight")
					.attr("x", xPos - 15)
					.attr("y", y1)
					.attr("width", 30)
					.attr("height", y2 - y1)
					.attr("fill", "#4a90e2")
					.attr("opacity", 0.2)
					.attr("stroke", "#4a90e2")
					.attr("stroke-width", 2)
					.attr("stroke-dasharray", "3,3")
					.style("pointer-events", "none");
			}

			onUpdateLines(lines);
			onBrushFilter?.(brushFilters);
		});

	const brushGroup = svgElement
		.append("g")
		.attr("class", `brush brush-${dimension}`)
		.attr("transform", "translate(0, 0)")
		.call(brush);

	brushGroup
		.selectAll(".selection")
		.style("fill", "#4a90e2")
		.style("opacity", 0.15)
		.style("stroke", "#4a90e2")
		.style("stroke-width", 1);

	brushGroup
		.selectAll(".handle")
		.style("fill", "#4a90e2")
		.style("stroke", "#4a90e2")
		.style("stroke-width", 2)
		.style("cursor", "ns-resize");

	if (brushFilters[dimension]) {
		const [y1, y2] = brushFilters[dimension];
		brush.move(brushGroup, [y1, y2]);
	}

	return brush;
}
