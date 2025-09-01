import { BaseMethodService } from '../../shared/services/api-service';
import type { ApiResponse} from '$lib/types/interactive-method';
import type { StateResponse } from '../types/xnimbus-types';
import type { XNimbusPreference } from '../types/xnimbus-types';

interface InitializeParams {
    problem_id: string;
    session_id: string | null;
    parent_state_id: number | null;
    solver: null; // TODO: check which type to use
}

interface IterateParams {
    problem_id: number;
    session_id: string | null;
    parent_state_id: number | null;
    current_objectives: number[];
    num_desired: number;
    preferences: XNimbusPreference[];
    scalarization_options: null;
    solver: null;
    solver_options: null;
}

interface IntermediateParams {
    problem_id: number;
    session_id: string | null;
    parent_state_id: number | null;
    reference_solution_1: any; //TODO: check type
    reference_solution_2: any; //TODO: check type
    num_desired: number;
    scalarization_options: null;
    solver: null;
    solver_options: null;
}

interface SaveParams {
    problem_id: string;
    session_id: string | null;
    parent_state_id: number | null;
    solutions: any[]; //TODO: check type
}


export class XNimbusService extends BaseMethodService {
    static readonly BASE_PATH = '/api/xnimbus';

    static async initialize(params: InitializeParams): Promise<ApiResponse<StateResponse>> {
        return this.callAPI<StateResponse>('initialize', params);
    }

    static async intermediate(params: IntermediateParams): Promise<ApiResponse<StateResponse>> {
        return this.callAPI<StateResponse>('intermediate', params);
    }

    static async iterate(params: IterateParams): Promise<ApiResponse<StateResponse>> {
        return this.callAPI<StateResponse>('iterate', params);
    }

    static async save(params: SaveParams): Promise<ApiResponse<{ saved_state_id: string }>> {
        return this.callAPI<{ saved_state_id: string }>('save', params);
    }

    protected static async callAPI<T>(endpoint: string, params: any): Promise<ApiResponse<T>> {
        const response = await fetch(`${this.BASE_PATH}/${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(params),
        });

        if (!response.ok) {
            throw new Error(`API call failed: ${response.statusText}`);
        }

        const data = await response.json();
        return {
            success: true,
            data
        };
    }
}