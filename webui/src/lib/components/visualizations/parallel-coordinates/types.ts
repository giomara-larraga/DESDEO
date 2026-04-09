/**
 * Shared types for parallel coordinates rendering and interactions.
 */
export type DataPoint = Record<string, number>;

export type Solution = {
	values: DataPoint;
	label?: string;
};

export type ReferenceData = {
	referencePoint?: Solution;
	previousReferencePoints?: Solution[];
	preferredRanges?: { [key: string]: { min: number; max: number } };
	preferredSolutions?: Solution[];
	nonPreferredSolutions?: Solution[];
	otherSolutions?: Solution[];
};

export type DimensionDefinition = {
	symbol: string;
	name: string;
	min?: number;
	max?: number;
	direction?: "max" | "min";
};

export type ParallelCoordinatesOptions = {
	showAxisLabels: boolean;
	highlightOnHover: boolean;
	strokeWidth: number;
	opacity: number;
	enableBrushing: boolean;
};

export type BrushFilters = { [dimension: string]: [number, number] };

export type Margin = { top: number; bottom: number };
