/**
 * Reference data structure for visualization components
 */
export type ReferenceData = {
    referencePoint?: { [key: string]: number };
    previousReferencePoint?: { [key: string]: number };
    preferredRanges?: { [key: string]: { min: number; max: number } };
    preferredSolutions?: Array<{ [key: string]: number }>;
    nonPreferredSolutions?: Array<{ [key: string]: number }>;
};