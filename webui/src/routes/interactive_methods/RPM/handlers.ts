/**
 * RPM API Client-Side Handlers
 * This module contains functions that handle user interactions and API calls for the Reference Point Method (RPM) in the DESDEO web UI.
 *
 * @author Giomara Larraga <glarragw@jyu.fi>
 */
import {
	solveSolutionsMethodRpmSolvePost,
	saveMethodRpmSavePost,
	deleteSaveMethodRpmDeleteSavePost,
	finalizeNimbusMethodRpmFinalizePost,
	solveNimbusIntermediateMethodRpmIntermediatePost,
	getUtopiaDataUtopiaPost,
	getProblemBackgroundDatasetsBackgroundDataProblemProblemIdGet,
	explainReferencePointMethodRximoExplainPost
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type {
	RPMSolveRequest,
	RPMSaveRequest,
	RPMDeleteSaveRequest,
	RPMFinalizeRequest,
	IntermediateSolutionRequest,
	SolutionInfo,
	BackgroundDatasetInfo,
	RXIMOExplainResponse,
	
} from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo, Solution } from '$lib/types';
import type { Response, ReferencePoint, FinishResponse } from './types';
import { errorMessage, isLoading } from '../../../stores/uiState';

/** Convert a Solution (SolutionReferenceResponse) to a SolutionInfo for API requests. */
function toSolutionInfo(solution: Solution, name?: string | null): SolutionInfo {
	return {
		state_id: solution.state_id,
		solution_index: solution.solution_index ?? 0,
		name: name ?? solution.name
	};
}

/**
 * Handles the generation of intermediate solutions between two selected reference solutions.
 */
export async function handle_intermediate(
	problem: ProblemInfo | null,
	selected_solutions: Solution[],
	num_desired: number
): Promise<Response | null> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return null;
	}
	if (selected_solutions.length !== 2) {
		errorMessage.set('Exactly 2 solutions must be selected for intermediate solutions');
		console.error('Exactly 2 solutions must be selected for intermediate solutions');
		return null;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: IntermediateSolutionRequest = {
			problem_id: problem.id,
			reference_solution_1: toSolutionInfo(selected_solutions[0]),
			reference_solution_2: toSolutionInfo(selected_solutions[1]),
			num_desired: num_desired
		};

		const response = await solveNimbusIntermediateMethodRpmIntermediatePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Intermediate solutions failed with status ${response.status}`);
			console.error('RPM intermediate failed:', response.status);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_intermediate:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Handles a NIMBUS iteration based on user-defined preferences and classifications.
 */
export async function handle_iterate(
	problem: ProblemInfo,
	current_preference: number[],
): Promise<Response | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const preference: ReferencePoint = {
			preference_type: 'reference_point',
			aspiration_levels: problem.objectives.reduce(
				(acc, obj, idx) => {
					acc[obj.symbol] = current_preference[idx];
					return acc;
				},
				{} as Record<string, number>
			)
		};

		const request: RPMSolveRequest = {
			problem_id: problem.id,
			preference: preference
		};

		const response = await solveSolutionsMethodRpmSolvePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Iteration failed with status ${response.status}`);
			console.error('NIMBUS iterate failed:', response.status);
			return null;
		}

		return response.data as unknown as Response;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_iterate:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Saves a solution with an optional user-provided name.
 */
export async function handle_save(
	problem: ProblemInfo | null,
	solution: Solution,
	name: string | undefined
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: RPMSaveRequest = {
			problem_id: problem.id,
			solution_info: [toSolutionInfo(solution, name ?? null)]
		};

		const response = await saveMethodRpmSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Save failed with status ${response.status}`);
			console.error('RPM save failed:', response.status);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_save:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Removes a previously saved solution.
 */
export async function handle_remove_saved(
	problem: ProblemInfo | null,
	solution: Solution
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: RPMDeleteSaveRequest = {
			state_id: solution.state_id,
			solution_index: solution.solution_index ?? 0,
			problem_id: problem.id
		};

		const response = await deleteSaveMethodRpmDeleteSavePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Delete save failed with status ${response.status}`);
			console.error('RPM delete save failed:', response.status);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_remove_saved:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Marks a solution as the final chosen solution for the session.
 */
export async function handle_finish(
	problem: ProblemInfo | null,
	solution: Solution,
	preferences: ReferencePoint
): Promise<boolean> {
	if (!problem) {
		errorMessage.set('No problem selected');
		console.error('No problem selected');
		return false;
	}

	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: RPMFinalizeRequest = {
			problem_id: problem.id,
			solution_info: toSolutionInfo(solution)
		};

		const response = await finalizeNimbusMethodRpmFinalizePost(request);

		if (response.status !== 200) {
			errorMessage.set(`Finalize failed with status ${response.status}`);
			console.error('RPM finalize failed:', response.status);
			return false;
		}

		return true;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in handle_finish:', msg);
		return false;
	} finally {
		isLoading.set(false);
	}
}

/**
 * Fetches map data related to a specific solution for UTOPIA visualization.
 */
export async function get_maps(
	problem: ProblemInfo,
	solution: Solution
): Promise<{
	years: string[];
	options: Record<string, any>;
	map_json: object;
	map_name: string;
	description: string;
	compensation: number;
} | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const response = await getUtopiaDataUtopiaPost({
			problem_id: problem.id,
			solution: toSolutionInfo(solution)
		});

		if (response.status !== 200) {
			errorMessage.set(`Get maps failed with status ${response.status}`);
			console.error('NIMBUS get maps failed:', response.status);
			return null;
		}

		const result = response.data as any;

		if (result) {
			for (const year of result.years) {
				if (result.options[year].tooltip.formatterEnabled) {
					result.options[year].tooltip.formatter = function (params: any) {
						return `${params.name}`;
					};
				}
			}
		}

		return result;
	} catch (error) {
		const msg = error instanceof Error ? error.message : 'Unknown error';
		errorMessage.set(msg);
		console.error('Error in get_maps:', msg);
		return null;
	} finally {
		isLoading.set(false);
	}
}
export async function fetchBackgroundDatasets(
	problem: ProblemInfo,
): Promise<BackgroundDatasetInfo[] | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const response = await getProblemBackgroundDatasetsBackgroundDataProblemProblemIdGet(problem.id);

		if (response.status !== 200) {
			errorMessage.set(`Finalize failed with status ${response.status}`);
			console.error('RPM finalize failed:', response.status);
			return null;
		}
		const data = response.data as unknown as BackgroundDatasetInfo[];

		return data;
	} catch (err) {
		errorMessage.set(err instanceof Error ? err.message : 'Unknown error while fetching background data.');
		return null;
	} finally {
		isLoading.set(false);
	}
}

export async function explainWithRXIMO(
	problemId: number,
	referencePoint: Record<string, number>,
	backgroundDatasetId?: number | null
): Promise<RXIMOExplainResponse | null> {
	// Do NOT set global isLoading here — SHAP computation is slow and runs in the
	// background after iterate completes. Use a separate per-component loading state instead.
	errorMessage.set(null);

	try {
		const payload = {
			problem_id: problemId,
			background_dataset_id: backgroundDatasetId ?? undefined,
			preference: {
				preference_type: 'reference_point',
				aspiration_levels: referencePoint
			} as ReferencePoint
		};

		
		const response = await explainReferencePointMethodRximoExplainPost(payload);


		if (response.status !== 200) {
			errorMessage.set(`RXIMO explanation failed with status ${response.status}`);
			console.error('RXIMO explanation failed:', response.status);
			return null;
		}


		const data = response.data as unknown as RXIMOExplainResponse;
		console.log('RXIMO explanation response:', data);
		return data.shap_values ? data : null;
	} catch (err) {
		errorMessage.set(err instanceof Error ? err.message : 'Unknown error while getting RXIMO explanation.');
		return null;
	}
}
