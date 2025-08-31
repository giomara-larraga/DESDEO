import { writable } from 'svelte/store';
import type { BaseMethodState, ResponseNIMBUS } from '../types/interactive-method';


export function createMethodStore<T extends BaseMethodState>(initialState: Partial<T> = {}) {
    const defaultState: BaseMethodState = {
        currentState: {} as ResponseNIMBUS,
        problem: null,
        mode: 'iterate',
        selectedType: 'current',
        currentPreference: [],
        selectedIndexes: [0],
        numSolutions: 1,
        selectedObjectives: {}
    };

    return writable({
        ...defaultState,
        ...initialState
    } as T);
}