/**
 * +server.ts - RPM API Server Endpoint
 * 
 * @author Giomara Larraga <glarragw@jyu.fi>
 * @created September 2025
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
            case 'initialize':
                response = await handle_initialize(body, refreshToken);
                break;
            case 'iterate':
                response = await handle_iterate(body, refreshToken);
                break;
            case 'choose':
                return json({ success: true, message: 'solution chosen!' });
            case 'save':
                response = await handle_save(body, refreshToken);
                break;
            case 'remove_saved':
                return json({ success: false, error: 'solution remove not implemented!' });
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

async function handle_save(body: any, refreshToken: string) {
        const {problem_id, solution_info} = body;
        const session_id = null;
        const parent_state_id = null;
        const requestBody = {
            problem_id,
            session_id,
            parent_state_id,
            solution_info
        }
        const response = await api.POST('/method/rpm/save', {
            body: requestBody,
            headers: {
                'Authorization': `Bearer ${refreshToken}`
            }
        });

        // Check if the response has an error
        if (response.error) {
            console.error(`RPM save API error: ${response.error} (Status: ${response.response?.status})`);
            throw new Error(`RPM save API error: ${response.error} (Status: ${response.response?.status})`);
        }

        if (!response.data) {
            console.error('No data received from RPM save API');
            throw new Error('No data received from RPM save API');
        }

        return { success: true, data: response.data };
}

async function handle_initialize(body: any, refreshToken: string) {
    const { problem_id, session_id, parent_state_id, solver } = body;

    const requestBody = {
        problem_id: Number(problem_id),
        session_id: session_id ? Number(session_id) : null,
        parent_state_id: parent_state_id ? Number(parent_state_id) : null,
        solver
    };

    const response = await api.POST('/method/rpm/get-or-initialize', {
        body: requestBody,
        headers: {
            'Authorization': `Bearer ${refreshToken}`
        }
    });
    
    // Check if the response has an error
    if (response.error) {
        console.error(`RPM initialization API error: ${response.error} (Status: ${response.response?.status})`);
        throw new Error(`RPM initialize API error: ${response.error} (Status: ${response.response?.status})`);
    }

    if (!response.data) {
        console.error('No data received from RPM initialize API');
        throw new Error('No data received from RPM initialize API');
    }

    return { success: true, data: response.data };
}

async function handle_iterate(body: any, refreshToken: string) {
    const { problem_id, session_id, parent_state_id, preference } = body;

    const requestBody = {
        problem_id: Number(problem_id),
        session_id: session_id ? Number(session_id) : null,
        parent_state_id: parent_state_id ? Number(parent_state_id) : null,
        preference,
        scalarization_options: null,
        solver: null,
        solver_options: null
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