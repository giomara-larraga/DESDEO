import { writable, type Writable } from 'svelte/store';
import type { NimbusState} from '../types/xnimbus-types';

function createNimbusStore() {
    const initialState: NimbusState = {
        problem: null,
        currentSession: null,
        currentState: null,
        solutions: [],
        selectedObjectives: [],
        preferences: [],
        explanations: {},
        currentExplanation: null,
        // BaseMethodState properties
        mode: 'iterate',
        selectedTypeSolutions: 'current',
        currentPreference: [],
        selectedIndexes: [],
        numSolutions: 0
    };

    const store: Writable<NimbusState> = writable(initialState);
    const { subscribe, set, update } = store;

    return {
        subscribe,
        update,
        get problem() {
            let currentState: NimbusState | undefined;
            store.subscribe(s => currentState = s)();
            return currentState?.problem ?? null;
        },
        get currentSession() {
            let currentState: NimbusState | undefined;
            store.subscribe(s => currentState = s)();
            return currentState?.currentSession ?? null;
        },
        get currentState() {
            let currentState: NimbusState | undefined;
            store.subscribe(s => currentState = s)();
            return currentState?.currentState ?? null;
        },
        get selectedObjectives() {
            let currentState: NimbusState | undefined;
            store.subscribe(s => currentState = s)();
            return currentState?.selectedObjectives ?? [];
        },
        reset() {
            set(initialState);
        }
    };
}

export const nimbusStore = createNimbusStore();