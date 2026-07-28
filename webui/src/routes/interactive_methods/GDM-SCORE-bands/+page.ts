import type { PageLoad } from './$types';

import {
	getGroupSessionGdmGroupSessionsGroupSessionIdGet,
	getGroupInfoGdmGetGroupInfoPost,
	getProblemProblemProblemIdGet
} from '$lib/gen/endpoints/DESDEOFastAPI';

import type {
	GroupPublic,
	GroupSessionPublic,
	ProblemInfo
} from '$lib/gen/endpoints/DESDEOFastAPI';

type LoadData = {
	refreshToken?: string;
};

type RequestInitWithFetch = RequestInit & {
	fetchImpl: typeof fetch;
};

function getErrorDetail(response: { data?: unknown }): string | undefined {
	const payload = response.data as { detail?: unknown } | undefined;
	return typeof payload?.detail === 'string' ? payload.detail : undefined;
}

export const load: PageLoad<LoadData> = async ({ url, data, fetch }) => {
	const rawGroupSessionId = url.searchParams.get('group_session');

	if (!rawGroupSessionId) {
		throw new Error('No group session ID provided');
	}

	const groupSessionId = Number(rawGroupSessionId);

	if (!Number.isInteger(groupSessionId)) {
		throw new Error('Invalid group session ID');
	}

	const apiRequestOptions = {
		fetchImpl: fetch
	} as RequestInitWithFetch;

	const groupSessionResponse =
		await getGroupSessionGdmGroupSessionsGroupSessionIdGet(
			groupSessionId,
			apiRequestOptions
		);

	if (groupSessionResponse.status !== 200) {
		throw new Error(
			`Failed to fetch group session (status ${groupSessionResponse.status})${
				getErrorDetail(groupSessionResponse)
					? `: ${getErrorDetail(groupSessionResponse)}`
					: ''
			}`
		);
	}

	const groupSession: GroupSessionPublic =
		groupSessionResponse.data;

	const groupResponse =
		await getGroupInfoGdmGetGroupInfoPost({
			group_id: groupSession.group_id
		}, apiRequestOptions);

	if (groupResponse.status !== 200) {
		throw new Error(
			`Failed to fetch group information (status ${groupResponse.status})${
				getErrorDetail(groupResponse)
					? `: ${getErrorDetail(groupResponse)}`
					: ''
			}`
		);
	}

	const problemResponse =
		await getProblemProblemProblemIdGet(
			groupSession.problem_id,
			apiRequestOptions
		);

	if (problemResponse.status !== 200) {
		throw new Error(
			`Failed to fetch problem information (status ${problemResponse.status})${
				getErrorDetail(problemResponse)
					? `: ${getErrorDetail(problemResponse)}`
					: ''
			}`
		);
	}

	return {
		problem: problemResponse.data as ProblemInfo,
		group: groupResponse.data as GroupPublic,
		groupSession,
		refreshToken: data.refreshToken
	};
};