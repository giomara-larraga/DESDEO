import type { PageServerLoad } from './$types';
import { requireRole } from '$lib/server/auth';

export const load: PageServerLoad = async ({ cookies }) => {
	const user = await requireRole(cookies, 'analyst');
	return { user };
};
