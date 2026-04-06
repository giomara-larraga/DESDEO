import type { Load } from '@sveltejs/kit';
import { getProblemsInfoProblemAllInfoGet } from '$lib/gen/endpoints/DESDEOFastAPI';
import type { ProblemInfo } from '$lib/gen/endpoints/DESDEOFastAPI';

export const load: Load = async () => {
	try {
		const res = await getProblemsInfoProblemAllInfoGet();
		console.log('Problems response:', res);
		if (res.status !== 200) throw new Error(`API returned status ${res.status}`);
		return { problems: res.data satisfies ProblemInfo[] };
	} catch (error) {
		console.error('Failed to fetch problems:', error);
		throw new Error(`Failed to fetch problems: ${error instanceof Error ? error.message : String(error)}`);
	}
};
