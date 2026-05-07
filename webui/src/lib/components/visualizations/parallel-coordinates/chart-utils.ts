/**
 * Pure helpers for scales, line generation, and brush-based filtering.
 */
import * as d3 from "d3";

import type { BrushFilters, DataPoint, DimensionDefinition, Margin } from "./types";

type LinearScales = { [key: string]: d3.ScaleLinear<number, number> };

export function createScales(
	dimensions: DimensionDefinition[],
	data: DataPoint[],
	innerHeight: number,
	margin: Margin
): LinearScales {
	const newScales: LinearScales = {};

	dimensions.forEach((dim) => {
		const values = data
			.map((d) => d[dim.symbol])
			.filter((v) => v !== undefined && v !== null);

		let domain: [number, number];
		if (dim.min !== undefined && dim.max !== undefined) {
			domain = [dim.min, dim.max];
		} else {
			const extent = d3.extent(values) as [number, number];
			domain = extent || [0, 1];
		}

		newScales[dim.symbol] = d3
			.scaleLinear()
			.domain(domain)
			.range([innerHeight - margin.bottom, margin.top]);
	});

	return newScales;
}

export function createLineGenerator(
	scales: LinearScales,
	xScale: d3.ScalePoint<string>
): d3.Line<[string, number]> {
	return d3
		.line<[string, number]>()
		.x(([dimension]) => xScale(dimension)!)
		.y(([dimension, value]) => scales[dimension](value))
		.curve(d3.curveLinear);
}

export function passesFilters(
	dataPoint: DataPoint,
	brushFilters: BrushFilters,
	scales: LinearScales
): boolean {
	for (const [dimension, [min, max]] of Object.entries(brushFilters)) {
		const value = dataPoint[dimension];
		if (value === undefined || value === null) continue;

		const scale = scales[dimension];
		if (!scale) continue;

		const dataMin = scale.invert(max);
		const dataMax = scale.invert(min);

		if (value < dataMin || value > dataMax) {
			return false;
		}
	}
	return true;
}
