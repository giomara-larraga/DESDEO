/**
 * Renderers for preferred ranges, reference points, and reference solution overlays.
 */
import * as d3 from "d3";

import type { DimensionDefinition, ReferenceData, Solution } from "./types";

type LinearScales = { [key: string]: d3.ScaleLinear<number, number> };

type TooltipApplier = (
	path: d3.Selection<SVGPathElement, any, any, any>,
	label?: string
) => d3.Selection<SVGPathElement, any, any, any>;

export function drawPreferredRanges(
	svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
	scales: LinearScales,
	xScale: d3.ScalePoint<string>,
	preferredRanges?: { [key: string]: { min: number; max: number } }
): void {
	if (!preferredRanges) return;

	const rangesGroup = svgElement.append("g").attr("class", "preferred-ranges");

	Object.entries(preferredRanges).forEach(([dimName, range]) => {
		const x = xScale(dimName);
		if (x === undefined || !scales[dimName]) return;

		const yMin = scales[dimName](range.max);
		const yMax = scales[dimName](range.min);

		rangesGroup
			.append("rect")
			.attr("class", `preferred-range-${dimName}`)
			.attr("x", x - 10)
			.attr("y", yMin)
			.attr("width", 20)
			.attr("height", yMax - yMin)
			.attr("fill", "#e6f3ff")
			.attr("stroke", "#4a90e2")
			.attr("stroke-width", 1)
			.attr("opacity", 0.3);
	});
}

export function drawGenericReferencePoint(
	svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
	scales: LinearScales,
	xScale: d3.ScalePoint<string>,
	line: d3.Line<[string, number]>,
	dimensions: DimensionDefinition[],
	pointData: Solution | undefined,
	modifiedOptions: { groupClass: string; color: string },
	strokeWidth: number,
	addTooltip: TooltipApplier
): void {
	if (!pointData) return;

	const referenceGroup = svgElement.append("g").attr("class", modifiedOptions.groupClass);
	const refLineData: [string, number][] = dimensions
		.map((dim) => [dim.symbol, pointData.values[dim.symbol]] as [string, number])
		.filter(([, value]) => value !== undefined && value !== null);

	if (refLineData.length > 0) {
		const path = referenceGroup
			.append("path")
			.datum(refLineData)
			.attr("d", line)
			.attr("fill", "none")
			.attr("stroke", modifiedOptions.color)
			.attr("stroke-width", strokeWidth + 1)
			.attr("stroke-dasharray", "8,4")
			.attr("opacity", 0.8);

		refLineData.forEach(([dimName, value]) => {
			const x = xScale(dimName);
			const y = scales[dimName](value);
			if (x !== undefined && !Number.isNaN(y)) {
				referenceGroup
					.append("circle")
					.attr("cx", x)
					.attr("cy", y)
					.attr("r", 4)
					.attr("fill", modifiedOptions.color)
					.attr("stroke", "#fff")
					.attr("stroke-width", 2)
					.attr("opacity", 0.8);
			}
		});

		addTooltip(path, pointData.label);
	}
}

export function drawReferenceSolutions(
	svgElement: d3.Selection<SVGGElement, unknown, null, undefined>,
	scales: LinearScales,
	xScale: d3.ScalePoint<string>,
	line: d3.Line<[string, number]>,
	dimensions: DimensionDefinition[],
	referenceData: ReferenceData | undefined,
	strokeWidth: number,
	addTooltip: TooltipApplier
): void {
	if (referenceData?.otherSolutions) {
		const otherGroup = svgElement.append("g").attr("class", "other-solutions");

		referenceData.otherSolutions.forEach((solution) => {
			const solutionData: [string, number][] = dimensions
				.map((dim) => [dim.symbol, solution.values[dim.symbol]] as [string, number])
				.filter(([, value]) => value !== undefined && value !== null);

			if (solutionData.length > 0) {
				const path = otherGroup
					.append("path")
					.datum(solutionData)
					.attr("d", line)
					.attr("fill", "none")
					.attr("stroke", "#9ca3af")
					.attr("stroke-width", strokeWidth)
					.attr("stroke-dasharray", "3,3")
					.attr("opacity", 0.6);

				addTooltip(path, solution.label);
			}
		});
	}

	if (referenceData?.preferredSolutions) {
		const preferredGroup = svgElement.append("g").attr("class", "preferred-solutions");
		referenceData.preferredSolutions.forEach((solution) => {
			const solutionData: [string, number][] = dimensions
				.map((dim) => [dim.symbol, solution.values[dim.symbol]] as [string, number])
				.filter(([, value]) => value !== undefined && value !== null);

			if (solutionData.length > 0) {
				const path = preferredGroup
					.append("path")
					.datum(solutionData)
					.attr("d", line)
					.attr("fill", "none")
					.attr("stroke", "#10b981")
					.attr("stroke-width", strokeWidth + 1)
					.attr("stroke-dasharray", "4,2")
					.attr("opacity", 0.6);

				addTooltip(path, solution.label);

				solutionData.forEach(([dimName, value]) => {
					const x = xScale(dimName);
					const y = scales[dimName](value);
					if (x !== undefined && !Number.isNaN(y)) {
						preferredGroup
							.append("polygon")
							.attr("points", `${x},${y - 4} ${x + 4},${y + 3} ${x - 4},${y + 3}`)
							.attr("fill", "#10b981")
							.attr("stroke", "#fff")
							.attr("stroke-width", 1);
					}
				});
			}
		});
	}

	if (referenceData?.nonPreferredSolutions) {
		const nonPreferredGroup = svgElement.append("g").attr("class", "non-preferred-solutions");
		referenceData.nonPreferredSolutions.forEach((solution) => {
			const solutionData: [string, number][] = dimensions
				.map((dim) => [dim.symbol, solution.values[dim.symbol]] as [string, number])
				.filter(([, value]) => value !== undefined && value !== null);

			if (solutionData.length > 0) {
				const path = nonPreferredGroup
					.append("path")
					.datum(solutionData)
					.attr("d", line)
					.attr("fill", "none")
					.attr("stroke", "#e74c3c")
					.attr("stroke-width", strokeWidth + 1)
					.attr("stroke-dasharray", "2,3")
					.attr("opacity", 0.6);

				addTooltip(path, solution.label);

				solutionData.forEach(([dimName, value]) => {
					const x = xScale(dimName);
					const y = scales[dimName](value);
					if (x !== undefined && !Number.isNaN(y)) {
						nonPreferredGroup
							.append("path")
							.attr(
								"d",
								`M${x - 3},${y - 3} L${x + 3},${y + 3} M${x + 3},${y - 3} L${x - 3},${y + 3}`
							)
							.attr("stroke", "#e74c3c")
							.attr("stroke-width", 2);
					}
				});
			}
		});
	}
}
