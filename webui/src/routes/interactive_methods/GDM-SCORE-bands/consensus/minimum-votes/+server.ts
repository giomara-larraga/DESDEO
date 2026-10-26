import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';

import {
    updateMinimumVotesGdmScoreBandsConsensusUpdateMinimumVotesPost
} from '$lib/gen/endpoints/DESDEOFastAPI';

export const POST: RequestHandler = async ({ request, cookies }) => {
    const refreshToken = cookies.get('refresh_token');

    if (!refreshToken) {
        return json({ error: 'Not authenticated' }, { status: 401 });
    }

    try {
        const { group_session_id, minimum_votes } = await request.json();

        if (
            typeof group_session_id !== 'number' ||
            !Number.isInteger(minimum_votes) ||
            minimum_votes < 1
        ) {
            return json({ error: 'Invalid request' }, { status: 400 });
        }

        const response =
            await updateMinimumVotesGdmScoreBandsConsensusUpdateMinimumVotesPost(
                { group_session_id, minimum_votes },
                {
                    headers: {
                        Authorization: `Bearer ${refreshToken}`
                    }
                }
            );

        if (response.status !== 200) {
            return json(
                {
                    error: 'Failed to update minimum votes',
                    details: (response.data as any)?.detail,
                },
                { status: response.status }
            );
        }

        return json({ success: true, data: response.data });
    } catch (error) {
        return json(
            {
                error: 'Server error',
                details: String(error)
            },
            { status: 500 }
        );
    }
};