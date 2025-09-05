/*Types specific for RPM */

export interface RPMPreference {
    preference_type: "reference_point";
    aspiration_levels: { [key: string]: number };
}

export interface RPMScalarizationOptions {
    [key: string]: string | number | boolean;
}

export interface RPMSolverOptions {
    [key: string]: string | number | boolean;
}

export interface RPMSolveRequest {
    problem_id: number;
    session_id?: number | null;
    parent_state_id?: number | null;
    preference: RPMPreference;
    scalarization_options?: RPMScalarizationOptions | null;
    solver?: string;
    solver_options?: RPMSolverOptions | null;
}

// Type for a single solution
export interface RPMSolution {
    optimal_variables: { [key: string]: number };
    optimal_objectives: { [key: string]: number };
    constraint_values: { [key: string]: number };
    extra_func_values: { [key: string]: number };
    scalarization_values: { [key: string]: number };
    success: boolean;
    message: string;
}

// State returned by the RPM solve endpoint
export interface RPMState {
    solver_results: RPMSolution | RPMSolution[];
    scalarization_options: RPMScalarizationOptions;
    solver: string;
    solver_options: RPMSolverOptions;
}

// Type for objective values in reference points and solutions
export type ObjectiveValues = {
    [key: string]: number;
};