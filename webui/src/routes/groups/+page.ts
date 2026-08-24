import type { PageLoad } from './$types';

import {
	getUserGroupsGdmGroupsGet,
	getGroupSessionsGdmGroupsGroupIdSessionsGet,
	getProblemProblemProblemIdGet
} from '$lib/gen/endpoints/DESDEOFastAPI';

import type {
	GroupPublic,
	GroupSessionPublic,
	ProblemInfo
} from '$lib/gen/endpoints/DESDEOFastAPI';

type GroupSessionRow = {
	group: GroupPublic;
	groupSession: GroupSessionPublic;
	problem: ProblemInfo;
};

export const load: PageLoad = async () => {
	const groupsResponse = await getUserGroupsGdmGroupsGet();

	if (groupsResponse.status !== 200) {
		throw new Error('Failed to fetch groups');
	}

	const groupList: GroupPublic[] = groupsResponse.data;

	const rows = await Promise.all(
		groupList.map(async (group) => {
			const sessionsResponse =
				await getGroupSessionsGdmGroupsGroupIdSessionsGet(group.id);

			if (sessionsResponse.status !== 200) {
				throw new Error(
					`Failed to fetch sessions for group ID ${group.id}`
				);
			}

			return Promise.all(
				sessionsResponse.data.map(
					async (
						groupSession: GroupSessionPublic
					): Promise<GroupSessionRow> => {
						const problemResponse =
							await getProblemProblemProblemIdGet(
								groupSession.problem_id
							);

						if (problemResponse.status !== 200) {
							throw new Error(
								`Failed to fetch problem ${groupSession.problem_id}`
							);
						}

						return {
							group,
							groupSession,
							problem: problemResponse.data
						};
					}
				)
			);
		})
	);

	return {
		groupList,
		sessionRows: rows.flat()
	};
};