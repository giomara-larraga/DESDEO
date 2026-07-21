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

export const load: PageLoad<LoadData> = async ({ url, data }) => {
	const rawGroupSessionId = url.searchParams.get('group_session');

	if (!rawGroupSessionId) {
		throw new Error('No group session ID provided');
	}

	const groupSessionId = Number(rawGroupSessionId);

	if (!Number.isInteger(groupSessionId)) {
		throw new Error('Invalid group session ID');
	}

	const groupSessionResponse =
		await getGroupSessionGdmGroupSessionsGroupSessionIdGet(
			groupSessionId
		);

	if (groupSessionResponse.status !== 200) {
		throw new Error('Failed to fetch group session');
	}

	const groupSession: GroupSessionPublic =
		groupSessionResponse.data;

	const groupResponse =
		await getGroupInfoGdmGetGroupInfoPost({
			group_id: groupSession.group_id
		});

	if (groupResponse.status !== 200) {
		throw new Error('Failed to fetch group information');
	}

	const problemResponse =
		await getProblemProblemProblemIdGet(
			groupSession.problem_id
		);

	if (problemResponse.status !== 200) {
		throw new Error('Failed to fetch problem information');
	}

	return {
		problem: problemResponse.data as ProblemInfo,
		group: groupResponse.data as GroupPublic,
		groupSession,
		refreshToken: data.refreshToken
	};
};