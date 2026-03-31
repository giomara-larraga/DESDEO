import createClient from 'openapi-fetch';
import type { paths } from './client-types';
import { auth } from '../../stores/auth';
import { get } from 'svelte/store';
import { browser } from '$app/environment';


const BASE_URL = import.meta.env.VITE_API_URL;

let refreshPromise: Promise<string | null> | null = null;

async function getFreshAccessToken(fetchImpl: typeof fetch): Promise<string | null> {
	if (!refreshPromise) {
		refreshPromise = (async () => {
			const refreshRes = await fetchImpl(`${BASE_URL}/refresh`, {
				method: 'POST',
				credentials: 'include'
			});

			if (!refreshRes.ok) {
				auth.clearAuth();
				return null;
			}

			const { access_token } = await refreshRes.json();
			auth.setAuth(access_token, get(auth).user);
			return access_token;
		})().finally(() => {
			refreshPromise = null;
		});
	}

	return refreshPromise;
}

async function customFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
	const request = new Request(input, {
		...init,
		credentials: init?.credentials ?? 'include'
	});

	const retryRequest = request.clone();
	const headers = new Headers(request.headers);

	const token = get(auth).accessToken;
	if (token && !headers.has('Authorization')) {
		headers.set('Authorization', `Bearer ${token}`);
	}

	const authorizedRequest = new Request(request, { headers });
	let response = await fetch(authorizedRequest);

	if (response.status !== 401) {
		return response;
	}

	const refreshToken = await getFreshAccessToken(fetch);
	if (!refreshToken) {
		return response;
	}

	const retryHeaders = new Headers(retryRequest.headers);
	retryHeaders.set('Authorization', `Bearer ${refreshToken}`);
	const authorizedRetry = new Request(retryRequest, { headers: retryHeaders });

	response = await fetch(authorizedRetry);
	return response;
}

async function serverFetch(input: RequestInfo | URL, init?: RequestInit): Promise<Response> {
	return fetch(input, {
		...init,
		credentials: init?.credentials ?? 'include'
	});
}

export const api = createClient<paths>({
	baseUrl: BASE_URL,
	fetch: customFetch
});

export const serverApi = createClient<paths>({
	baseUrl: browser ? BASE_URL : (process.env.API_BASE_URL || 'http://localhost:8000'),
	fetch: serverFetch
});