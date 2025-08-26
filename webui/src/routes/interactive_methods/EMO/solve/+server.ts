/**
 * Server-side API endpoint for solving optimization problems using an EMO (Evolutionary Multi-objective Optimization) method.
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/EMO/solve
 * 
 * Purpose:
 * - Receives EMO solve requests from the frontend
 * - Authenticates the request using refresh tokens
 * - Forwards the request to the backend DESDEO API
 * - Returns the optimization results to the frontend
 * 
 * Author: Giomara Larraga (glarragw@jyu.fi)
 * Created: July 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import { postMethodApi } from '$lib/api/posts';

/**
 * POST handler for EMO solve requests
 * 
 * Expected request body: EMOSolveRequest containing:
 * - problem_id: ID of the optimization problem to solve
 * - method: EMO algorithm to use (e.g., "NSGA3", "RVEA")
 * - preference: User preferences (reference points, preferred ranges, etc.)
 * - max_evaluations: Maximum number of function evaluations
 * - number_of_vectors: Number of solution vectors to generate
 * - use_archive: Whether to use solution archive
 * - session_id: Optional session identifier
 * - parent_state_id: Optional parent state for iterative solving
 * 
 * Returns: JSON response with EMOState containing optimization results
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    const solveRequest = await request.json();
    const response = await postMethodApi('/method/emo/solve', solveRequest, refreshToken);
    if (!response.success) {
      return json({ error: 'Failed to solve problem', details: response.error }, { status: 500 });
    }
    return json({ success: true, data: response.data, message: 'Problem solved successfully' });
  } catch (error) {
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    return json({ error: 'Server error', details: errorMessage }, { status: 500 });
  }
};

/**
 * Flow Summary:
 * 1. Frontend sends POST request to /interactive_methods/EMO/solve
 * 2. Server checks for valid refresh token in cookies
 * 3. Server parses EMOSolveRequest from request body
 * 4. Server forwards request to DESDEO backend API with authentication
 * 5. Server receives EMOState response from backend
 * 6. Server returns processed response to frontend
 */