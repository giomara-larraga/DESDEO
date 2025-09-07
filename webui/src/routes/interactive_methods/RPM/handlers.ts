import type { ProblemInfo, Solution } from '$lib/types';
import type { Response } from './types';
import { callRPMAPI } from './helper-functions';

// Handler for iteration
export async function handle_iterate(
    problem: ProblemInfo,
    current_preference: number[],
): Promise<Response | null> {
    const preference = {
        preference_type: 'reference_point',
        aspiration_levels: problem.objectives.reduce(
            (acc, obj, idx) => {
                acc[obj.symbol] = current_preference[idx];
                return acc;
            },
            {} as Record<string, number>
        )
    };

    const result = await callRPMAPI<Response>('iterate', {
        problem_id: problem.id,
        session_id: null,
        parent_state_id: null,
        preference: preference
    });

    if (result.success && result.data) {
        return result.data;
    } else {
        console.error('RPM iteration failed:', result.error);
        return null;
    }
}

// Handler for saving a solution
export async function handle_save(
    problem: ProblemInfo | null,
    solution: Solution,
    name: string | undefined
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    // Create a copy of the solution with the name
    const solutionToSave = {
        ...solution,
        name: name ?? null
    };

    interface SaveResponse {
        success: boolean;
    }

    const result = await callRPMAPI<SaveResponse>('save', {
        problem_id: problem.id,
        solution_info: [solutionToSave]
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to save solution:', result.error);
        return false;
    }
}

// Handler for removing a saved solution
export async function handle_remove_saved(
    problem: ProblemInfo | null,
    solution: Solution
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    interface RemoveResponse {
        success: boolean;
    }

    const result = await callRPMAPI<RemoveResponse>('remove_saved', {
        problem_id: problem.id,
        solutions: [solution]
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to remove saved solution:', result.error);
        return false;
    }
}

// Handler for finishing with a solution
export async function handle_finish(
    problem: ProblemInfo | null,
    solution: Solution
): Promise<boolean> {
    if (!problem) {
        console.error('No problem selected');
        return false;
    }

    interface FinishResponse {
        success: boolean;
    }

    const result = await callRPMAPI<FinishResponse>('choose', {
        problem_id: problem.id,
        solution: solution
    });

    if (result.success) {
        return true;
    } else {
        console.error('Failed to save final choice:', result.error);
        return false;
    }
}

// Handler for initializing RPM state
export async function initialize_rpm_state(problem_id: number): Promise<Response | null> {
    const result = await callRPMAPI<Response>('initialize', {
        problem_id: problem_id,
        session_id: null, // Use active session
        parent_state_id: null, // No parent for initialization
        solver: null // Use default solver
    });

    if (result.success && result.data) {
        return result.data;
    } else {
        console.error('RPM initialization failed:', result.error);
        return null;
    }
}

export async function handle_explain(
    problem: ProblemInfo,
    current_preference: number[],
): Promise<Response | null> {
    const preference = {
        preference_type: 'reference_point',
        aspiration_levels: problem.objectives.reduce(
            (acc, obj, idx) => {
                acc[obj.symbol] = current_preference[idx];
                return acc;
            },
            {} as Record<string, number>
        )
    };

    const result = await callRPMAPI<Response>('explain', {
        problem_id: problem.id,
        session_id: null,
        parent_state_id: null,
        preference: preference
    });

    if (result.success && result.data) {
        return result.data;
    } else {
        console.error('RPM explanation failed:', result.error);
        return null;
    }
}