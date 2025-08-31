import { describe, it, expect } from 'vitest';
import { processExplanationData, calculateImportanceFactors } from '../../utils/explanation-utils';
import type { Solution, ExplanationData } from '../../types/xnimbus-types';

describe('Explanation Utilities', () => {
    describe('processExplanationData', () => {
        it('should process raw explanation data correctly', () => {
            const rawData = {
                factors: ['Cost', 'Time', 'Quality'],
                weights: [0.4, 0.35, 0.25],
                impacts: [1, -1, 1]
            };

            const result = processExplanationData(rawData);

            expect(result).toEqual({
                factors: ['Cost', 'Time', 'Quality'],
                importance: [0.4, 0.35, 0.25],
                direction: ['Positive', 'Negative', 'Positive']
            });
        });

        it('should handle empty data', () => {
            const rawData = {
                factors: [],
                weights: [],
                impacts: []
            };

            const result = processExplanationData(rawData);

            expect(result).toEqual({
                factors: [],
                importance: [],
                direction: []
            });
        });
    });

    describe('calculateImportanceFactors', () => {
        it('should calculate importance factors correctly', () => {
            const solutions: Solution[] = [
                { id: '1', values: [0.5, 0.3, 0.7] },
                { id: '2', values: [0.6, 0.4, 0.8] }
            ];

            const referencePoint = [0.55, 0.35, 0.75];

            const result = calculateImportanceFactors(solutions, referencePoint);

            expect(result).toHaveLength(3);
            expect(result.every(factor => factor >= 0 && factor <= 1)).toBe(true);
            expect(result.reduce((sum, factor) => sum + factor, 0)).toBeCloseTo(1);
        });

        it('should handle single solution case', () => {
            const solutions: Solution[] = [
                { id: '1', values: [0.5, 0.3, 0.7] }
            ];

            const referencePoint = [0.55, 0.35, 0.75];

            const result = calculateImportanceFactors(solutions, referencePoint);

            expect(result).toHaveLength(3);
            expect(result.every(factor => factor >= 0 && factor <= 1)).toBe(true);
        });

        it('should handle edge cases with identical values', () => {
            const solutions: Solution[] = [
                { id: '1', values: [0.5, 0.5, 0.5] },
                { id: '2', values: [0.5, 0.5, 0.5] }
            ];

            const referencePoint = [0.5, 0.5, 0.5];

            const result = calculateImportanceFactors(solutions, referencePoint);

            // Should distribute importance equally
            expect(result).toEqual([1/3, 1/3, 1/3]);
        });
    });
});
