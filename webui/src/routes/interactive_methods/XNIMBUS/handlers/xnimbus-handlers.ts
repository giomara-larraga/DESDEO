import type { 
    BaseMethodHandlers, 
    PreferenceData, 
    ProblemInfo,
    ApiResponse,
    ResponseNIMBUS
} from '$lib/types/interactive-method';
import { nimbusStore } from '../stores/xnimbus-store';
import { XNimbusService } from '../services/xnimbus-api';
import type { XNimbusPreference, XNimbusSolution, StateResponse} from '../types/xnimbus-types';
import { error } from '@sveltejs/kit';

export function createNimbusHandlers(): BaseMethodHandlers {
    function validateProblem(): ProblemInfo {
        if (!nimbusStore.problem) {
            throw error(400, 'No problem selected');
        }
        return nimbusStore.problem;
    }

    function preparePreferences(data: PreferenceData): XNimbusPreference[] {
        return data.preferenceValues.map((value, index) => {
            const objective = nimbusStore.problem?.objectives[index];
            if (!objective) {
                throw error(400, `No objective found at index ${index}`);
            }
            
            return {
                classification: data.typePreferences,
                level: value,
                direction: objective.maximize ? 'maximize' : 'minimize'
            };
        });
    }

    function processSolutions(response: ApiResponse<StateResponse>): XNimbusSolution[] {
        if (!response.success || !response.data) {
            return [];
        }

        const solutions = response.data.current_solutions;
        if (!Array.isArray(solutions)) {
            return [];
        }
        
        return solutions.map(solution => ({
            id: solution.id,
            objectives: solution.objective_values,
            variables: solution.variables,
            selected: false
        }));
    }

    return {
        async handleInitialize() {
            const problem = validateProblem();
            
            try {
                const result = await XNimbusService.initialize({
                    problem_id: problem.id.toString()
                });

                if (!result.success || !result.data) {
                    throw error(500, 'Invalid response from server');
                }

                const initialState: ResponseNIMBUS = {
                    state_id: parseInt(result.data.state_id, 10),
                    current_solutions: processSolutions(result),
                    saved_solutions: [],
                    all_solutions: []
                };

                nimbusStore.update((state) => ({
                    ...state,
                    currentState: initialState,
                    mode: 'iterate'
                }));
            } catch (e) {
                console.error('Failed to initialize XNIMBUS:', e);
                throw error(500, 'Failed to initialize XNIMBUS method');
            }
        },

        async handleIterate(data: PreferenceData) {
            const problem = validateProblem();
            
            try {
                const preferences = preparePreferences(data);
                
                const result = await XNimbusService.iterate({
                    problem_id: problem.id,
                    session_id: nimbusStore.currentSession,
                    parent_state_id: nimbusStore.currentState,
                    current_objectives: nimbusStore.selectedObjectives,
                    num_desired: data.numSolutions ?? 3,
                    preferences: preferences
                });

                nimbusStore.update((state) => ({
                    ...state,
                    currentState: result.data?.state_id ?? null,
                    solutions: processSolutions(result.data ?? {}),
                    preferences: preparePreferences(data)
                }));

                // Update explanations if available
                if (result.explanations) {
                    nimbusStore.update((state) => ({
                        ...state,
                        explanations: result.explanations
                    }));
                }
            } catch (e) {
                console.error('Failed to iterate XNIMBUS:', e);
                throw error(500, 'Failed to process XNIMBUS iteration');
            }
        },
    };
}