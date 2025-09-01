import type { components } from '$lib/api/client-types';

export interface Solution {
    id: string;
    objectives: Record<string, number>;
    variables: Record<string, number>;
    selected?: boolean;
}
export type ProblemInfo = components['schemas']['ProblemInfo'];

export type MethodMode = 'iterate' | 'final' | 'intermediate';
export type SolutionType = 'current' | 'best' | 'all';
export type PeriodKey = 'period1' | 'period2' | 'period3';

export type ApiResponse<T> = {
    success: boolean;
    data?: T;
    error?: string;
};

export type ResponseNIMBUS = {
		state_id: number | null,
		previous_preference?: components["schemas"]["ReferencePoint"],
    	previous_objectives?: {
			[key: string]: number;
		},
		reference_solution_1?: {
			[key: string]: number;
		},
		reference_solution_2?: {
			[key: string]: number;
		},
		current_solutions: Solution[],
		saved_solutions: Solution[],
		all_solutions: Solution[],
	};

export interface PreferenceData {
    numSolutions: number;
    typePreferences: string;
    preferenceValues: number[];
    objectiveValues: number[];
}

export interface BaseMethodState {
    currentState: ResponseNIMBUS; //TODO:Change to generic response
    problem: ProblemInfo | null;
    mode: MethodMode;
    selectedTypeSolutions: SolutionType;
    currentPreference: number[];
    selectedIndexes: number[];
    numSolutions: number;
    selectedObjectives: Record<string, number>;
}

export interface DialogConfig {
    open: boolean;
    title: string;
    description: string;
    confirmText: string;
    cancelText: string;
    onConfirm: () => void;
    onCancel?: () => void;
	confirmVariant?: "default" | "destructive" | "outline" | "secondary" | "ghost" | "link";
}

export interface BaseMethodHandlers {
    handleIterate: (data: PreferenceData) => Promise<void>;
    handleIntermediate: () => Promise<void>;
    handleFinish: (solution: Solution, index: number) => Promise<void>;
    handleSave: (solution: Solution, name?: string) => Promise<void>;
    handleRemove: (solution: Solution) => Promise<void>;
    handleSolutionTypeChange: (type: SolutionType) => void;
    handlePreferenceChange: (data: PreferenceData) => void;
    handleInitialize: (problemId: number) => Promise<void>;
}