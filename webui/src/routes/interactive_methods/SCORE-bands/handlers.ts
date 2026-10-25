/** API client for stateful single-user SCORE Bands.
 *
 * Calls the existing SvelteKit /api catch-all proxy, which forwards cookies and
 * authentication refresh. Regenerate the Orval SDK once the Python API is loaded;
 * these small typed wrappers avoid importing nonexistent generated functions now.
 */
import type {
    ProblemInfo,
    SCOREBandsConfig,
    SCOREBandsResult
} from '$lib/gen/endpoints/DESDEOFastAPI';

export type ScoreBandsSavedBand = {
    source_state_id: number;
    cluster_id: number;
    name: string | null;
    preferred_ranges: Record<string, [number, number]>;
};
export type ScoreBandsHistoryItem = {
    state_id: number;
    parent_state_id: number | null;
    action: 'initialize' | 'iterate';
    selected_cluster_id: number | null;
    result: SCOREBandsResult;
};
export type ScoreBandsResponse = {
    response_type: 'score_bands.initialize' | 'score_bands.iterate';
    state_id: number;
    session_id: number;
    result: SCOREBandsResult;
    saved_bands: ScoreBandsSavedBand[];
    history: ScoreBandsHistoryItem[];
};
export type ScoreBandsHistoryResponse = {
    response_type: 'score_bands.history';
    session_id: number;
    state_id: number | null;
    saved_bands: ScoreBandsSavedBand[];
    history: ScoreBandsHistoryItem[];
};
export type ScoreBandsSaveResponse = {
    response_type: 'score_bands.save';
    state_id: number;
    session_id: number;
    saved_bands: ScoreBandsSavedBand[];
};
export type ScoreBandsOptimizationOptions = {
    optimize: boolean;
    algorithm: 'nsga3' | 'rvea';
    algorithm_options?: { number_of_vectors?: number };
};
export type ScoreBandsIterationRequest = {
    problem_id: number;
    session_id: number;
    parent_state_id: number;
    preference: {
        preference_type: 'score_bands.band';
        cluster_id: number;
    };
    optimization_options: ScoreBandsOptimizationOptions;
    scorebands_options?: SCOREBandsConfig | null;
};

const ROOT = '/api/method/score_bands_method';

async function apiRequest<T>(path: string, body?: object): Promise<T> {
    const response = await fetch(`${ROOT}${path}`, {
        method: body === undefined ? 'GET' : 'POST',
        headers: body === undefined ? undefined : { 'Content-Type': 'application/json' },
        body: body === undefined ? undefined : JSON.stringify(body),
        credentials: 'include'
    });
    const payload: unknown = await response.json().catch(() => null);
    if (!response.ok) {
        const detail =
            payload && typeof payload === 'object' && 'detail' in payload
                ? String((payload as { detail: unknown }).detail)
                : `HTTP ${response.status}`;
        throw new Error(detail);
    }
    return payload as T;
}

export function defaultScoreBandsOptions(): SCOREBandsConfig {
    return {
        clustering_algorithm: { name: 'KMeans', n_clusters: 5 },
        distance_formula: 1,
        distance_parameter: 0.05,
        use_absolute_correlations: false,
        include_solutions: false,
        include_medians: true,
        interval_size: 0.25
    };
}

export async function handle_initialize_scorebands(
    problem: ProblemInfo,
    sessionId: number | null = null,
    scorebandsOptions: SCOREBandsConfig = defaultScoreBandsOptions(),
    optimizationOptions: ScoreBandsOptimizationOptions = { optimize: false, algorithm: 'nsga3' }
): Promise<ScoreBandsResponse> {
    return apiRequest<ScoreBandsResponse>('/initialize', {
        problem_id: problem.id,
        session_id: sessionId,
        scorebands_options: scorebandsOptions,
        optimization_options: optimizationOptions
    });
}

export async function handle_iterate_scorebands(
    request: ScoreBandsIterationRequest
): Promise<ScoreBandsResponse> {
    return apiRequest<ScoreBandsResponse>('/iterate', request);
}

export async function handle_save_scorebands(request: {
    problem_id: number;
    session_id: number;
    
    parent_state_id: number;
    preference: { preference_type: 'score_bands.band'; cluster_id: number };
    save: boolean;
    source_state_id?: number | null;
    name?: string | null;
}): Promise<ScoreBandsSaveResponse> {
    return apiRequest<ScoreBandsSaveResponse>('/save', request);
}

export async function handle_scorebands_history(
    problemId: number,
    sessionId: number,
    headStateId?: number
): Promise<ScoreBandsHistoryResponse> {
    const params = new URLSearchParams({
        problem_id: String(problemId),
        session_id: String(sessionId)
    });
    if (headStateId !== undefined) params.set('head_state_id', String(headStateId));
    return apiRequest<ScoreBandsHistoryResponse>(`/history?${params}`);
}
