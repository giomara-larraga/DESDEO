import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';

import {
	completeLearningPhaseGdmScoreBandsLearningCompletePost
} from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST: RequestHandler = async ({ request, cookies }) => {
	try {
		const refreshToken = cookies.get('refresh_token');
		if (!refreshToken) {
			return json({ error: 'Not authenticated' }, { status: 401 });
		}

		const { group_session_id } = await request.json();

		if (
			typeof group_session_id !== 'number' ||
			!Number.isInteger(group_session_id)
		) {
			return json(
				{
					success: false,
					error: 'Invalid request',
					details: 'group_session_id must be an integer'
				},
				{ status: 400 }
			);
		}

		const response =
			await completeLearningPhaseGdmScoreBandsLearningCompletePost(
				{
					group_session_id
				},
				{
					headers: {
						Authorization: `Bearer  ${refreshToken}`
					}
				}
			);

		return json({
			success: true,
			data: response.data
		});
	} catch (error: any) {
		console.error(
			'Failed to complete SCORE Bands learning phase:',
			error?.response?.data ?? error
		);

		const status =
			error?.response?.status ??
			error?.status ??
			500;

		const details =
			error?.response?.data?.detail ??
			error?.response?.data?.error ??
			error?.message ??
			'Unknown error occurred';

		return json(
			{
				success: false,
				error: 'Failed to complete learning phase',
				details
			},
			{ status }
		);
	}
};