import { BaseMethodService } from '../../shared/services/api-service';
import type { StateResponse, Solution } from '$lib/types/interactive-method';

export class XNimbusService extends BaseMethodService {
    static async iterate(params: IterateParams): Promise<ApiResponse<StateResponse>> {
        return this.callAPI<StateResponse>('iterate', params);
    }

    static async intermediate(params: IntermediateParams): Promise<ApiResponse<StateResponse>> {
        return this.callAPI<StateResponse>('intermediate', params);
    }

    static async choose(problemId: number, solution: Solution): Promise<ApiResponse<void>> {
        return this.callAPI<void>('choose', { problem_id: problemId, solution });
    }

    // Inherits save and removeSaved from BaseMethodService
}