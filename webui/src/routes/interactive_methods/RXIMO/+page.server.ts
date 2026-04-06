import { redirect } from '@sveltejs/kit';
import type { ServerLoad } from '@sveltejs/kit';

export const load: ServerLoad = async ({ cookies }) => {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		throw redirect(307, '/home');
	}
	return {};
};
