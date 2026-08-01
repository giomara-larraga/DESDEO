import {
	calculateScoreBandsMethodScoreBandsMethodSolvePost
} from '$lib/gen/endpoints/DESDEOFastAPI';

import type {
	SCOREBandsMethodRequest,
	SCOREBandsMethodResponse
} from '$lib/gen/endpoints/DESDEOFastAPI';

import type { ProblemInfo } from '$lib/types';
import { errorMessage, isLoading } from '../../../stores/uiState';

/**
 * Handles SCORE Bands generation.
 */
export async function handle_initialize_scorebands(
	problem: ProblemInfo
): Promise<SCOREBandsMethodResponse | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const request: SCOREBandsMethodRequest = {
			problem_id: problem.id,
			options: {
				clustering_algorithm: {
					name: 'KMeans',
					n_clusters: 5
				},
				distance_formula: 1,
				distance_parameter: 0.05,
				use_absolute_correlations: false,
				include_solutions: false,
				include_medians: true,
				interval_size: 0.25
			}
		};

		const response =
			await calculateScoreBandsMethodScoreBandsMethodSolvePost(
				request
			);

		if (response.status !== 200) {
			const message =
				`SCORE Bands failed with status ${response.status}`;

			errorMessage.set(message);
			console.error(message);

			return null;
		}

		return response.data;
	} catch (error) {
		const message =
			error instanceof Error
				? error.message
				: 'Unknown SCORE Bands error';

		errorMessage.set(message);
		console.error(
			'Error in handle_initialize_scorebands:',
			error
		);

		return null;
	} finally {
		isLoading.set(false);
	}
}