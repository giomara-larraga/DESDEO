import { errorMessage, isLoading } from '../../../stores/uiState';

import type { BackgroundDatasetInfo, RXIMOExplainResponse } from './types';

function getErrorDetail(payload: unknown): string | null {
	if (payload && typeof payload === 'object' && 'detail' in payload) {
		const detail = (payload as { detail?: unknown }).detail;
		if (typeof detail === 'string') {
			return detail;
		}
	}
	return null;
}

export async function fetchBackgroundDatasets(
	problemId: number
): Promise<BackgroundDatasetInfo[] | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const response = await fetch(`/api/background_data/problem/${problemId}`, {
			method: 'GET',
			credentials: 'include'
		});

		if (!response.ok) {
			const payload = await response.json().catch(() => null);
			errorMessage.set(
				getErrorDetail(payload) ?? `Failed to fetch background data (status ${response.status}).`
			);
			return null;
		}

		const data = (await response.json()) as BackgroundDatasetInfo[];
		return data;
	} catch (err) {
		errorMessage.set(err instanceof Error ? err.message : 'Unknown error while fetching background data.');
		return null;
	} finally {
		isLoading.set(false);
	}
}

export async function explainWithRXIMO(
	problemId: number,
	referencePoint: Record<string, number>,
	backgroundDatasetId?: number | null
): Promise<RXIMOExplainResponse | null> {
	isLoading.set(true);
	errorMessage.set(null);

	try {
		const payload = {
			problem_id: problemId,
			background_dataset_id: backgroundDatasetId ?? undefined,
			preference: {
				preference_type: 'reference_point',
				aspiration_levels: referencePoint
			}
		};

		const response = await fetch('/api/method/rximo/explain', {
			method: 'POST',
			headers: { 'Content-Type': 'application/json' },
			credentials: 'include',
			body: JSON.stringify(payload)
		});

		if (!response.ok) {
			const errorPayload = await response.json().catch(() => null);
			errorMessage.set(
				getErrorDetail(errorPayload) ?? `RXIMO explanation failed (status ${response.status}).`
			);
			return null;
		}

		return (await response.json()) as RXIMOExplainResponse;
	} catch (err) {
		errorMessage.set(err instanceof Error ? err.message : 'Unknown error while getting RXIMO explanation.');
		return null;
	} finally {
		isLoading.set(false);
	}
}
