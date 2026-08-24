/**
 * Helper Functions for Single-User SCORE-bands Method
 *
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created December 2025
 *
 * @description
 * Utility functions supporting single-user SCORE-bands interactive method.
 * Contains functions for data transformation, visualization setup, and preference handling.
 *
 * @features
 * - Scale calculation from multiple data sources with fallback priorities
 * - Cluster color generation with consistent palette
 * - Axis styling configuration for visualization
 * - Quantile to interval size conversion utilities
 * - Visualization toggle validation logic
 *
 */

import type { SCOREBandsResult, ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

/**
 * Calculates scales for SCORE-bands visualization with priority fallback system
 * copied from GDM-SCORE-Bands, probably needs updating
 *
 * Priority order:
 * 1. Problem ideal/nadir values (most accurate)
 * 2. API-provided scales (method-specific)
 * 3. Data-derived scales (fallback from bands/medians)
 *
 * @param result SCORE-bands result from API
 * @param problem Problem information containing ideal/nadir values
 * @returns Record mapping axis names to [min, max] scale ranges
 */
/**
 * Calculate axis scales for SCORE bands visualization
 *
 * Determines the min/max range for each axis using a priority order:
 * 1. Problem definition (ideal/nadir from objectives)
 * 2. API-provided scales from result.options.scales
 * 3. Fallback: calculate from actual bands and medians data
 *
 * TODO: When API scales functionality is fully implemented, prioritize using
 * result.options.scales over problem definition. Evaluate if fallback calculation
 * from bands data is still needed or should be removed.
 *
 * @param problem - Problem definition containing objectives with ideal/nadir values
 * @param result - SCORE bands result containing bands data and configuration
 * @returns Record mapping axis name to [min, max] range tuple
 */
export function calculateScales(
	problem: ProblemInfo | null,
	result: SCOREBandsResult
): Record<string, [number, number]> {
	// First, try to use ideal and nadir from problem definition
	const scales: Record<string, [number, number]> = {};
	let allObjectivesHaveScales = true;

	if (!problem) {
		return scales;
	}

	problem.objectives.forEach((objective: any) => {
		const name = objective.symbol || objective.name; // Use symbol if available, otherwise name
		const ideal = objective.ideal;
		const nadir = objective.nadir;
		if (ideal !== undefined && nadir !== undefined) {
			scales[name] = [nadir, ideal];
		} else {
			allObjectivesHaveScales = false;
		}
	});

	// Only use problem scales if ALL objectives have complete ideal/nadir values
	if (allObjectivesHaveScales && Object.keys(scales).length === problem.objectives.length) {
		return scales;
	}

	// Second, try to use scales from API
	if (result.options?.scales) {
		return result.options.scales;
	}

	// Fallback: calculate scales from bands data
	const fallbackScales: Record<string, [number, number]> = {};

	result.ordered_dimensions.forEach((axisName) => {
		let min = Infinity;
		let max = -Infinity;

		// Find min/max across all clusters for this axis
		Object.values(result.bands).forEach((clusterBands) => {
			if (clusterBands[axisName]) {
				const [bandMin, bandMax] = clusterBands[axisName];
				min = Math.min(min, bandMin);
				max = Math.max(max, bandMax);
			}
		});

		// Also check medians for additional range
		Object.values(result.medians).forEach((clusterMedians) => {
			if (clusterMedians[axisName] !== undefined) {
				const median = clusterMedians[axisName];
				min = Math.min(min, median);
				max = Math.max(max, median);
			}
		});

		fallbackScales[axisName] = [min, max];
	});

	return fallbackScales;
}


/**
 * Generates consistent cluster colors using predefined palette
 * Ensures same cluster IDs always get same colors across sessions
 *
 * @param clusterIds Array of cluster IDs to assign colors to
 * @returns Record mapping cluster IDs to hex color strings
 */
export function generateClusterColors(clusterIds: number[]): Record<number, string> {
	const color_palette = [
		'#1f77b4', // Strong blue
		'#ff7f0e', // Vibrant orange
		'#2ca02c', // Strong green
		'#d62728', // Bold red
		'#9467bd', // Purple
		'#8c564b', // Brown
		'#e377c2', // Pink
		'#7f7f7f', // Gray
		'#bcbd22', // Olive/yellow-green
		'#17becf' // Cyan
	];

	const cluster_colors: Record<number, string> = {};

	clusterIds.forEach((clusterId, index) => {
		cluster_colors[clusterId] = color_palette[index % color_palette.length];
	});

	return cluster_colors;
}

/**
 * Generates axis styling options for parallel coordinates visualization
 * Currently applies uniform gray styling - ready for customization
 *
 * @param axisNames Array of axis names
 * @returns Array of styling objects for each axis
 */
export function generateAxisOptions(axisNames: string[]) {
	return axisNames.map((axisName: string) => {
		// Default gray color and solid line for all axes
		return {
			color: '#666666', // Gray for all axes
			strokeWidth: 1,
			strokeDasharray: 'none'
		};
	});
}

/**
 * Validates if bands visualization can be toggled off
 * Prevents deselecting all visualization options simultaneously
 *
 * @param show_bands Current bands visibility state
 * @param show_medians Current medians visibility state
 * @param show_solutions Current solutions visibility state
 * @returns true if bands can be toggled off, false otherwise
 */
export function canToggleBands(
	show_bands: boolean,
	show_medians: boolean,
	show_solutions: boolean
): boolean {
	// Can toggle bands off only if medians or solutions would remain on
	return !show_bands || show_medians || show_solutions;
}

/**
 * Validates if medians visualization can be toggled off
 * Prevents deselecting all visualization options simultaneously
 *
 * @param show_bands Current bands visibility state
 * @param show_medians Current medians visibility state
 * @param show_solutions Current solutions visibility state
 * @returns true if medians can be toggled off, false otherwise
 */
export function canToggleMedians(
	show_bands: boolean,
	show_medians: boolean,
	show_solutions: boolean
): boolean {
	// Can toggle medians off only if bands or solutions would remain on
	return !show_medians || show_bands || show_solutions;
}
