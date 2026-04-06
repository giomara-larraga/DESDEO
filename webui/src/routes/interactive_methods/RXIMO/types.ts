import type { ProblemInfo } from '$lib/types';

export interface BackgroundDatasetInfo {
	id: number;
	problem_ids: number[];
	name?: string | null;
	kind: string;
	num_samples: number;
	preference_values?: Record<string, number[]> | null;
	objective_values: Record<string, number[]>;
}

export interface RXIMOExplainResponse {
	response_type: 'rximo.explain';
	problem_id: number;
	background_dataset_id: number;
	input_symbols: string[];
	output_symbols: string[];
	reference_point: Record<string, number>;
	explained_objective_values: Record<string, number>;
	base_values: Record<string, number>;
	shap_values: Record<string, Record<string, number>>;
}

export interface RXIMOPageData {
	problems: ProblemInfo[];
}
