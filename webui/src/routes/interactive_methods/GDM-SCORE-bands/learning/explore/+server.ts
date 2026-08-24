import { json } from '@sveltejs/kit';
import type {
	RequestHandler
} from '@sveltejs/kit';

import {
	exploreLearningBandGdmScoreBandsLearningExplorePost
} from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST:
	RequestHandler = async ({
		request,
		cookies
	}) => {
	const refreshToken =
		cookies.get('refresh_token');

	if (!refreshToken) {
		return json(
			{
				success: false,
				error: 'Not authenticated'
			},
			{ status: 401 }
		);
	}

	try {
		const {
			group_session_id,
			selected_cluster_id,
			parent_state_id
		} = await request.json();

		const response =
			await exploreLearningBandGdmScoreBandsLearningExplorePost(
				{
					group_session_id,
					selected_cluster_id,
					parent_state_id
				},
				{
					headers: {
						Authorization:
							`Bearer ${refreshToken}`
					}
				}
			);

		if (response.status !== 200) {
			return json(
				{
					success: false,
					error:
						'Failed to explore band',
					details:
						(response.data as any)
							?.detail
				},
				{
					status:
						response.status
				}
			);
		}

		return json({
			success: true,
			data: response.data
		});
	} catch (error: any) {
		console.error(
			'Personal SCORE Bands exploration failed:',
			error?.response?.data ??
				error
		);

		return json(
			{
				success: false,
				error:
					'Failed to explore band',
				details:
					error?.response?.data
						?.detail ??
					error?.message ??
					'Unknown error'
			},
			{
				status:
					error?.response?.status ??
					500
			}
		);
	}
};