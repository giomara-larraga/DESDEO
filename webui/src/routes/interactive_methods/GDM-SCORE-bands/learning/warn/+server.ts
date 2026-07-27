import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';

import { warnLearningPhaseGdmScoreBandsLearningWarnPost } from '$lib/gen/endpoints/DESDEOFastAPI';
export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const { group_session_id, message } = await request.json();
		if (typeof group_session_id !== 'number') {
			return json(
				{
					error: 'Invalid request',
					details: 'group_session_id must be a number'
				},
				{ status: 400 }
			);
		}
		const response = await warnLearningPhaseGdmScoreBandsLearningWarnPost(
			{
				group_session_id,
				message
			},
			{
				headers: {
					Authorization: `Bearer  ${refreshToken}`
				}
			}
		);

		if (response.status !== 200) {
			return json(
				{
					error: 'Failed to warn users',
					details: (response.data as any)?.detail || 'No data returned from API',
					status: response.status
				},
				{ status: response.status }
			);
		}

		return json({ success: true, data: response.data });
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		return json({ error: 'Server error', details: errorMessage }, { status: 500 });
	}
};