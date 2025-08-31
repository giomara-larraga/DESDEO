import type { BaseMethodHandlers, PreferenceData } from '$lib/types/interactive-method';
import type { Solution } from '$lib/types/interactive-method';
import { nimbusStore } from '../stores/xnimbus-store';
import { xnimbusAPI } from '../services/xnimbus-api';

export function createNimbusHandlers(): BaseMethodHandlers {
    return {
        async handleIterate(data: PreferenceData) {
            if (!nimbusStore.problem) {
                console.error('No problem selected');
                return;
            }

            // ...existing preference preparation code...

            const result = await xnimbusAPI.iterate({
                problem_id: nimbusStore.problem.id,
                session_id: null,
                parent_state_id: null,
                current_objectives: nimbusStore.selectedObjectives,
                num_desired: data.numSolutions,
                preference: preference
            });

            // ...existing result handling code...
        },

        // ...update other handlers to use xnimbusAPI...
    };
}