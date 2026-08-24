/**
 * Server-side API endpoint for GDM SCORE Bands iteration restart.
 *
 * Route: POST /interactive_methods/GDM-SCORE-bands/restart
 *
 * Author: Giomara Larraga
 * Created: July 2026
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import type { GDMSCOREBandsRestartRequest } from '$lib/gen/endpoints/DESDEOFastAPI';
import { restartScoreBandsGdmScoreBandsRestartPost } from '$lib/gen/endpoints/DESDEOFastAPI';
export const POST: RequestHandler = async ({ request, cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return json({ error: 'Not authenticated' }, { status: 401 });
	}

	try {
		const requestData = await request.json();
		const { group_session_id } = requestData;

		if (
			typeof group_session_id !== 'number'
		) {
			return json(
				{
					error: 'Invalid request',
					details:
						'group_session_id must be a number'
				},
				{ status: 400 }
			);
		}

		const restartRequest:
			GDMSCOREBandsRestartRequest = {
				group_session_id,
			};

		const options: RequestInit = {
			headers: { Authorization: `Bearer ${refreshToken}` }
		};

		const restartResponse = await restartScoreBandsGdmScoreBandsRestartPost(restartRequest, options);

		if (restartResponse.status !== 200) {
			console.error('Restart error:', restartResponse.data);
			return json(
				{
					error: 'Failed to restart iteration',
					details: (restartResponse.data as any)?.detail || 'Restart failed',
					status: restartResponse.status
				},
				{ status: restartResponse.status }
			);
		}

		return json({
			success: true,
			data: restartResponse.data
		});
	} catch (error) {
		const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
		const errorName = error instanceof Error ? error.name : 'Error';

		console.error('Restart error details:', { message: errorMessage, name: errorName });

		return json(
			{ error: 'Server error', details: errorMessage, type: errorName },
			{ status: 500 }
		);
	}
};
