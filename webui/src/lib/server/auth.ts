import { redirect } from '@sveltejs/kit';
import type { Cookies } from '@sveltejs/kit';
import type { components } from '$lib/api/client-types';

type UserPublic = components['schemas']['UserPublic'];
type UserRole = components['schemas']['UserRole'];

const API_BASE_URL = process.env.API_BASE_URL || 'http://localhost:8000';

async function fetchUserWithAccessToken(accessToken: string): Promise<UserPublic | null> {
	const userRes = await fetch(`${API_BASE_URL}/user_info`, {
		headers: {
			Authorization: `Bearer ${accessToken}`
		}
	});

	if (!userRes.ok) {
		return null;
	}

	return (await userRes.json()) as UserPublic;
}

async function refreshAccessToken(cookies: Cookies): Promise<string | null> {
	const refreshToken = cookies.get('refresh_token');
	if (!refreshToken) {
		return null;
	}

	const refreshRes = await fetch(`${API_BASE_URL}/refresh`, {
		method: 'POST',
		headers: {
			Cookie: `refresh_token=${refreshToken}`
		}
	});

	if (!refreshRes.ok) {
		return null;
	}

	const { access_token } = (await refreshRes.json()) as { access_token?: string };
	if (!access_token) {
		return null;
	}

	cookies.set('access_token', access_token, {
		httpOnly: true,
		secure: true,
		sameSite: 'lax',
		path: '/'
	});

	return access_token;
}

export async function requireRole(cookies: Cookies, requiredRole: UserRole): Promise<UserPublic> {
	let accessToken = cookies.get('access_token') ?? null;
	let user = accessToken ? await fetchUserWithAccessToken(accessToken) : null;

	if (!user) {
		accessToken = await refreshAccessToken(cookies);
		if (!accessToken) {
			throw redirect(307, '/home');
		}
		user = await fetchUserWithAccessToken(accessToken);
	}

	if (!user) {
		throw redirect(307, '/home');
	}

	if (user.role !== requiredRole) {
		throw redirect(307, '/dashboard');
	}

	return user;
}
