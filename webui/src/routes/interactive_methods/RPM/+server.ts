/**
 * +server.ts - RPM API Server Endpoint
 * 
 * @description
 * This server endpoint handles RPM (Reference Point Method) API requests, acting as a proxy between
 * the frontend and the backend API.
 * 
 * @endpoints
 * - solve: Performs RPM solve operation based on reference points
 * - save: Saves a solution (optional)
 * 
 * @authentication
 * All endpoints require authentication via refresh_token cookie.
 * 
 * @error_handling
 * Returns standardized JSON responses with success/error fields and appropriate HTTP status codes.
 */
import { json } from '@sveltejs/kit';
import { serverApi as api } from '$lib/api/client';
import type { RequestHandler } from './$types';

export const POST: RequestHandler = async ({ url, request, cookies }) => {
    try {
        const body = await request.json();
        const type = url.searchParams.get('type');
        // Get authentication token from cookies
        const refreshToken = cookies.get('refresh_token');
        if (!refreshToken) {
            return json({ success: false, error: 'No authentication token found' }, { status: 401 });
        }

        let response;
        switch (type) {
            case 'solve':
                response = await handle_solve(body, refreshToken);
                break;

            default:
                return json({ success: false, error: 'Invalid operation type' }, { status: 400 });
        }

        return json(response);

    } catch (error) {
        console.error('Request failed:', error);
        return json({ 
            success: false, 
            error: error instanceof Error ? error.message : 'Unknown error occurred' 
        }, { status: 500 });
    }
};

import type { RPMSolveRequest } from './types';

async function handle_solve(body: RPMSolveRequest, refreshToken: string) {
    const requestBody = {
        problem_id: Number(body.problem_id),
        session_id: null,
        parent_state_id: null,
        preference: body.preference,
        scalarization_options: { rho: 0.1, ...body.scalarization_options },
        solver: null,
        solver_options: null,
    };

    const response = await api.POST('/method/rpm/solve', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });

    // Check if the response has an error
    if (response.error) {
        console.error(`RPM solve API error: ${response.error} (Status: ${response.response?.status})`);
        throw new Error(`RPM solve API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from RPM solve API');
        throw new Error('No data received from RPM solve API');
    }

    return { success: true, data: response.data };
}
