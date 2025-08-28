import type { components } from '$lib/api/client-types';

type Solution = components['schemas']['UserSavedSolutionAddress'];

export interface MethodHandlers {
    handleIterate: (data: {
        numSolutions: number;
        typePreferences: string;
        preferenceValues: number[];
        objectiveValues: number[];
    }) => Promise<void>;
    handleIntermediate: () => Promise<void>;
    handleFinish: (solution: Solution, index: number) => Promise<void>;
    handleSave: (solution: Solution, name?: string) => Promise<void>;
    handleRemove: (solution: Solution) => Promise<void>;
    handlePreferenceChange: (data: {
        numSolutions: number;
        typePreferences: string;
        preferenceValues: number[];
        objectiveValues: number[];
    }) => void;
    handleSolutionTypeChange: (type: 'current' | 'best' | 'all') => void;
    handleFinishConfirm: (solution: Solution, index: number) => void;
    handleRemoveConfirm: (solution: Solution) => void;
    handleRename: (solution: Solution) => void;
    handleRenameConfirm: (name: string) => void;
    handleRenameCancel: () => void;
}