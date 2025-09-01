import type { BaseMethodState, ProblemInfo, ResponseNIMBUS } from '$lib/types/interactive-method';

export interface StateResponse {
    session_id: string;
    state_id: string;
    current_solutions: Array<{
        id: string;
        objective_values: Record<string, number>;
        variables: Record<string, number>;
    }>;
    explanations?: Record<string, XNimbusExplanation>;
}

export interface XNimbusPreference {
    classification: string;
    level: number;
    direction: 'minimize' | 'maximize';
}

export interface XNimbusObjective {
    name: string;
    direction: 'minimize' | 'maximize';
    current_value?: number;
}

export interface XNimbusSolution {
    id: string;
    objectives: Record<string, number>;
    variables: Record<string, number>;
    selected: boolean;
}

export interface XNimbusExplanation {
    solution_id: string;
    factors: string[];
    importance: number[];
    direction: ('minimize' | 'maximize')[];
}

export interface NimbusState extends Omit<BaseMethodState, 'currentState' | 'selectedObjectives'> {
    problem: ProblemInfo | null;
    currentState: ResponseNIMBUS | null;
    currentSession: string | null;
    solutions: XNimbusSolution[];
    selectedObjectives: string[];
    preferences: XNimbusPreference[];
    explanations: Record<string, XNimbusExplanation>;
    currentExplanation: XNimbusExplanation | null;
}
