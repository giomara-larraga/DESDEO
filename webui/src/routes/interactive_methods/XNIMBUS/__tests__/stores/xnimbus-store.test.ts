import { describe, it, expect, beforeEach } from 'vitest';
import { XNimbusStore } from '../../stores/xnimbus-store';

describe('XNimbusStore', () => {
    let store: XNimbusStore;

    beforeEach(() => {
        store = new XNimbusStore();
    });

    describe('preferences', () => {
        it('should update preferences correctly', () => {
            const mockPreferences = {
                bounds: { min: 0, max: 1 },
                aspirationLevels: [0.5, 0.3, 0.7]
            };

            store.setPreferences(mockPreferences);
            expect(store.getPreferences()).toEqual(mockPreferences);
        });

        it('should notify subscribers when preferences change', () => {
            const mockPreferences = {
                bounds: { min: 0, max: 1 },
                aspirationLevels: [0.5, 0.3, 0.7]
            };

            let notified = false;
            store.subscribe((state) => {
                if (state.preferences === mockPreferences) {
                    notified = true;
                }
            });

            store.setPreferences(mockPreferences);
            expect(notified).toBe(true);
        });
    });

    describe('solutions', () => {
        it('should update solutions correctly', () => {
            const mockSolutions = [
                { id: '1', values: [0.5, 0.3, 0.7] },
                { id: '2', values: [0.6, 0.4, 0.8] }
            ];

            store.updateSolutions(mockSolutions);
            expect(store.getSolutions()).toEqual(mockSolutions);
        });

        it('should update current solution when solutions change', () => {
            const mockSolutions = [
                { id: '1', values: [0.5, 0.3, 0.7] },
                { id: '2', values: [0.6, 0.4, 0.8] }
            ];

            store.updateSolutions(mockSolutions);
            expect(store.getCurrentSolution()).toEqual(mockSolutions[0]);

            store.setCurrentSolutionIndex(1);
            expect(store.getCurrentSolution()).toEqual(mockSolutions[1]);
        });
    });

    describe('explanations', () => {
        it('should handle explanation data correctly', () => {
            const mockExplanation = {
                solutionId: '1',
                factors: ['factor1', 'factor2'],
                importance: [0.7, 0.3]
            };

            store.setExplanation('1', mockExplanation);
            expect(store.getExplanation('1')).toEqual(mockExplanation);
        });
    });
});
