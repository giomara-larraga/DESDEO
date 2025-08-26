/**
 * +server.ts - NIMBUS API Server Endpoint
 * 
 * @author Stina Palomäki <palomakistina@gmail.com>
 * @created August 2025
 * 
 * @description
 * This server endpoint handles all NIMBUS method API requests, acting as a proxy between
 * the frontend and the backend API. It supports operations like initializing NIMBUS,
 * iterating to find new solutions, generating intermediate solutions, saving solutions,
 * and fetching map data for UTOPIA visualization.
 * 
 * @endpoints
 * - initialize: Initializes a new NIMBUS session with the backend
 * - iterate: Performs a NIMBUS iteration based on user preferences
 * - intermediate: Generates intermediate solutions between two reference solutions
 * - choose: Selects a final solution (TODO: currently not implemented)
 * - save: Saves a solution with a name
 * - remove_saved: Removes a saved solution (TODO: currently not implemented)
 * - get_maps: Retrieves map data for UTOPIA visualization
 * 
 * @authentication
 * All endpoints require authentication via refresh_token cookie.
 * 
 * @error_handling
 * Returns standardized JSON responses with success/error fields and appropriate HTTP status codes.
 */
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { postMethodApi } from '$lib/api/posts';



export const POST: RequestHandler = async ({ url, request, cookies }) => {
    try {
        const body = await request.json();
        const type = url.searchParams.get('type');
        // Get authentication token from cookies
        const refreshToken = cookies.get('refresh_token');
        if (!refreshToken) {
            return json({ success: false, error: 'No authentication token found' }, { status: 401 });
        }

        let endpoint = '';
        let requestBody = body;
        switch (type) {
            case 'initialize':
                endpoint = '/method/nimbus/initialize';
                requestBody = {
                    problem_id: Number(body.problem_id),
                    session_id: body.session_id ? Number(body.session_id) : null,
                    parent_state_id: body.parent_state_id ? Number(body.parent_state_id) : null,
                    solver: body.solver
                };
                break;
            case 'iterate':
                endpoint = '/method/nimbus/solve';
                requestBody = {
                    problem_id: Number(body.problem_id),
                    session_id: body.session_id ? Number(body.session_id) : null,
                    parent_state_id: body.parent_state_id ? Number(body.parent_state_id) : null,
                    current_objectives: body.current_objectives,
                    num_desired: body.num_desired ? Number(body.num_desired) : null,
                    preference: body.preference,
                    scalarization_options: null,
                    solver: null,
                    solver_options: null
                };
                break;
            case 'choose':
                return json({ success: true, message: 'solution chosen!' });
            case 'intermediate':
                endpoint = '/method/nimbus/intermediate';
                requestBody = {
                    problem_id: Number(body.problem_id),
                    session_id: body.session_id ? Number(body.session_id) : null,
                    parent_state_id: body.parent_state_id ? Number(body.parent_state_id) : null,
                    reference_solution_1: body.reference_solution_1,
                    reference_solution_2: body.reference_solution_2,
                    num_desired: body.num_desired ? Number(body.num_desired) : 4,
                    scalarization_options: null,
                    solver: null,
                    solver_options: null
                };
                break;
            case 'save':
                endpoint = '/method/nimbus/save';
                requestBody = {
                    problem_id: body.problem_id,
                    session_id: null,
                    parent_state_id: null,
                    solutions: body.solutions
                };
                break;
            case 'remove_saved':
                return json({ success: false, error: 'solution remove not implemented!' });
            case 'get_maps':
                endpoint = '/utopia/';
                requestBody = {
                    problem_id: Number(body.problem_id),
                    solution: body.solution
                };
                break;
            default:
                return json({ success: false, error: 'Invalid operation type' }, { status: 400 });
        }
        const response = await postMethodApi(endpoint, requestBody, refreshToken);
        return json(response);

    } catch (error) {
        console.error('Request failed:', error);
        return json({ 
            success: false, 
            error: error instanceof Error ? error.message : 'Unknown error occurred' 
        }, { status: 500 });
    }
};