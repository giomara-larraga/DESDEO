import type { MethodHandlers } from '$lib/helpers/method-handler';
import type { components } from '$lib/api/client-types';
import { callNimbusAPI } from './helper-functions';
type Solution = components['schemas']['UserSavedSolutionAddress'];
type ProblemInfo = components['schemas']['ProblemInfo'];
type DialogConfig = {
    open: boolean;
    title: string;
    description: string;
    confirmText: string;
    cancelText: string;
    onConfirm: () => void;
    onCancel?: () => void;
    confirmVariant?: 'default' | 'destructive';
};

type NimbusResponse = {
    state_id: number | null;
    previous_preference?: components["schemas"]["ReferencePoint"];
    previous_objectives?: {
        [key: string]: number;
    };
    reference_solution_1?: {
        [key: string]: number;
    };
    reference_solution_2?: {
        [key: string]: number;
    };
    current_solutions: Solution[];
    saved_solutions: Solution[];
    all_solutions: Solution[];
    selected_solutions_for_intermediate: Solution[];
}

interface NimbusState {
    current_state: NimbusResponse;
    problem: ProblemInfo;
    selected_type_solutions: string;
    current_preference: number[];
    current_num_iteration_solutions: number;
    mode: 'iterate' | 'final' | 'intermediate';
    selected_iteration_index: number[];
    selected_iteration_objectives: Record<string, number>;
    type_preferences: string;
    dialogConfig: DialogConfig;
    inputDialogConfig: {
        open: boolean;
        solution: Solution | null;
        initialName: string;
    };
}

export function createNimbusHandlers(state: NimbusState): MethodHandlers {
    function openDialog(config: Partial<DialogConfig>) {
        state.dialogConfig = {
            ...state.dialogConfig,
            ...config,
            open: true
        };
    }

    return {
        async handleIterate() {
            if (!state.problem) {
                console.error('No problem selected');
                return;
            }

            const preference = {
                preference_type: 'reference_point',
                aspiration_levels: state.problem.objectives.reduce(
                    (acc, obj, idx) => {
                        acc[obj.symbol] = state.current_preference[idx];
                        return acc;
                    },
                    {} as Record<string, number>
                )
            };

            const result = await callNimbusAPI<NimbusResponse>('iterate', {
                problem_id: state.problem.id,
                session_id: null,
                parent_state_id: null,
                current_objectives: state.selected_iteration_objectives,
                num_desired: state.current_num_iteration_solutions,
                preference: preference
            });

            if (result.success && result.data) {
                state.current_state = result.data;
                state.selected_iteration_index = [0];
                state.selected_type_solutions = 'current';
            }
        },
        
        async handleIntermediate() {
            const selected = state.current_state.selected_solutions_for_intermediate;
            if (selected.length !== 2) {
                console.error('Exactly 2 solutions must be selected for intermediate solutions');
                return;
            }

            const result = await callNimbusAPI<NimbusResponse>('intermediate', {
                problem_id: state.problem?.id,
                session_id: null,
                parent_state_id: null,
                reference_solution_1: selected[0],
                reference_solution_2: selected[1],
                num_desired: state.current_num_iteration_solutions
            });

            if (result.success && result.data) {
                state.current_state = result.data;
                state.mode = "iterate";
                state.selected_iteration_index = [0];
                state.selected_type_solutions = 'current';
            }
        },
        
        async handleFinish(solution, index) {
            const result = await callNimbusAPI('choose', {
                problem_id: state.problem?.id,
                solution: solution,
            });

            if (result.success) {
                state.selected_iteration_index = [index];
                state.mode = "final";
            }
        },
        
        async handleSave(solution, name) {
            const solutionToSave = {
                ...solution,
                name: name
            };
            
            const result = await callNimbusAPI('save', {
                problem_id: state.problem?.id,
                solutions: [solutionToSave],
            });

            if (result.success) {
                // Update solution lists in state
                const updateSolutionInList = (list: Solution[]) => 
                    list.map(item => 
                        (item.address_state === solution.address_state && 
                         item.address_result === solution.address_result) 
                            ? solutionToSave 
                            : item
                    );

                state.current_state = {
                    ...state.current_state,
                    current_solutions: updateSolutionInList(state.current_state.current_solutions),
                    saved_solutions: [...state.current_state.saved_solutions, solutionToSave],
                    all_solutions: updateSolutionInList(state.current_state.all_solutions),
                };
            }
        },
        
        async handleRemove(solution) {
            const result = await callNimbusAPI('remove_saved', {
                problem_id: state.problem?.id,
                solutions: [solution],
            });

            if (result.success) {
                // Remove solution from saved solutions
                state.current_state.saved_solutions = state.current_state.saved_solutions.filter(
                    saved => !(saved.address_state === solution.address_state && 
                             saved.address_result === solution.address_result)
                );
            }
        },
        
        handlePreferenceChange(data) {
            state.current_num_iteration_solutions = data.numSolutions;
            state.type_preferences = data.typePreferences;
            state.current_preference = [...data.preferenceValues];
        },

        handleSolutionTypeChange(type) {
            state.selected_type_solutions = type;
            // Reset selections based on new type
            state.selected_iteration_index = [0];
        },

        handleFinishConfirm(solution: Solution, index: number) {
            const solutionName = solution.name || `Solution #${index + 1}`;
            openDialog({
                title: "Confirm Final Choice",
                description: `Are you sure you want to proceed with "${solutionName}" as your final choice?`,
                confirmText: "Yes, Proceed",
                cancelText: "Cancel",
                onConfirm: () => this.handleFinish(solution, index)
            });
        },

        handleRemoveConfirm(solution: Solution) {
            openDialog({
                title: "Remove Saved Solution",
                description: `Are you sure you want to remove ${solution.name || 'this solution'} from saved solutions?`,
                confirmText: "Remove",
                cancelText: "Cancel",
                onConfirm: () => this.handleRemove(solution)
            });
        },

        handleRename(solution: Solution) {
            state.inputDialogConfig = {
                open: true,
                solution: solution,
                initialName: solution.name || ""
            };
        },

        handleRenameConfirm(name: string) {
            if (state.inputDialogConfig.solution) {
                this.handleSave(state.inputDialogConfig.solution, name);
            }
            state.inputDialogConfig.open = false;
            state.inputDialogConfig.solution = null;
        },

        handleRenameCancel() {
            state.inputDialogConfig.open = false;
            state.inputDialogConfig.solution = null;
        }
    };
}