import type { ProblemInfo } from '$lib/types';


export 	function findShapRow(
		values: Record<string, Record<string, number>> | null,
		outputSymbol: string
	): Record<string, number> {
		if (!values) return {};
		return (
			values[outputSymbol] ??
			values[`z_${outputSymbol}`] ??
			Object.entries(values).find(([key]) => normalizeObjectiveSymbol(key) === outputSymbol)?.[1] ??
			{}
		);
	}

export function findShapColumn(
        values: Record<string, Record<string, number>> | null,
        inputSymbol: string
    ): Record<string, number> {
        if (!values) return {};
        return (
            Object.fromEntries(
                Object.entries(values).map(([key, row]) => [key, row[inputSymbol] ?? row[`z_${inputSymbol}`]])
            ) ?? {}
        );
    }

	export function normalizeObjectiveSymbol(symbol: string): string {
		return symbol.startsWith('z_') ? symbol.slice(2) : symbol;
	}

	export function isOwnAspiration(inputSymbol: string, outputSymbol: string): boolean {
		return normalizeObjectiveSymbol(inputSymbol) === normalizeObjectiveSymbol(outputSymbol);
	}

	export function displayAspirationName(symbol: string, problem: ProblemInfo): string {
		const normalized = normalizeObjectiveSymbol(symbol);
		const obj = problem.objectives.find((o) => o.symbol === normalized);
		return obj?.name ?? normalized;
	}