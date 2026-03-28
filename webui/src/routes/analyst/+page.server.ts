import type { PageServerLoad } from './$types';
import { error } from '@sveltejs/kit';
import { requireRole } from '$lib/server/auth';

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

export const load: PageServerLoad = async ({ cookies, fetch }) => {
	const user = await requireRole(cookies, 'analyst');
	const accessToken = cookies.get('access_token');

	if (!accessToken) {
		throw error(401, 'Missing access token for analyst results request.');
	}

	const response = await fetch(
		`${API_BASE_URL}/analyst/experiment-results/groups?include_action_details=true`,
		{
		headers: {
			Authorization: `Bearer ${accessToken}`
		}
		}
	);

	if (!response.ok) {
		throw error(response.status, 'Failed to load analyst experiment results.');
	}

	const { groups } = (await response.json()) as { groups: unknown[] };

	return { user, groups };
};
