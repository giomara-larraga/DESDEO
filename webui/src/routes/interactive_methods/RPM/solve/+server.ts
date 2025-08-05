/**
 * Server-side API endpoint for solving optimization problems using the Reference Point Method (RPM).
 * This endpoint acts as a proxy between the frontend and the backend DESDEO API.
 * 
 * Route: POST /interactive_methods/RPM/solve
 * 
 * Purpose:
 * - Receives RPM solve requests from the frontend
 * - Authenticates the request using refresh tokens
 * - Forwards the request to the backend DESDEO API
 * - Returns the optimization results to the frontend
 * 
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';
import { serverApi as api } from '$lib/api/client';
import type { components } from '$lib/api/client-types';


// Type definitions from the OpenAPI schema
type RPMSolveRequest = components['schemas']['RPMSolveRequest'];
type RPMState = components['schemas']['RPMState'];

/**
 * POST handler for RPM solve requests
 * 
 * Expected request body: RPMSolveRequest containing:
 * - problem_id: ID of the optimization problem to solve
 * - preference: Reference point preferences with aspiration levels
 * - scalarization_options: Options for the scalarization function
 * - solver: Solver to use (optional)
 * - solver_options: Options for the solver (optional)
 * - session_id: Optional session identifier
 * - parent_state_id: Optional parent state for iterative solving
 * 
 * Returns: JSON response with RPMState containing optimization results
 */
export const POST: RequestHandler = async ({ request, cookies }) => {
  // Authentication check: Verify that the user has a valid refresh token
  const refreshToken = cookies.get('refresh_token');
  if (!refreshToken) {
    return json({ error: 'Not authenticated' }, { status: 401 });
  }

  try {
    // Parse the incoming RPM solve request from the frontend
    const solveRequest: RPMSolveRequest = await request.json();
    const response = await api.POST('/method/rpm/solve', {
      body: solveRequest,
      headers: {
        'Authorization': `Bearer ${refreshToken}`, 
        'Content-Type': 'application/json'
      }
    });

    if (!response.data) {
      console.error('No data in response:', {
        status: response.response?.status,
        statusText: response.response?.statusText,
        error: response.error
      });
      
      // Return error response to frontend with details from backend
      return json(
        { 
          error: 'Failed to solve problem',
          details: response.error || 'No data returned from API',
          status: response.response?.status
        }, 
        { status: response.response?.status || 500 }
      );
    }

    /**
     * Success case: Return the optimization results to the frontend
     * The response.data contains an RPMState object with:
     * - solver_results: Array of solution vectors with objectives and variables
     * - method: The optimization method used
     * - scalarization_options: Options used for scalarization
     * - Other metadata about the optimization run
     */
    return json({
      success: true,
      data: response.data as RPMState,
      message: 'Problem solved successfully'
    });

  } catch (error) {
    /**
     * Error handling for unexpected errors during processing
     * This could include:
     * - JSON parsing errors
     * - Network errors when calling the backend API
     * - Type conversion errors
     * - Any other unexpected runtime errors
     */
    const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
    const errorName = error instanceof Error ? error.name : 'Error';
    const errorStack = error instanceof Error ? error.stack : undefined;
    
    // Detailed error logging for server-side debugging
    console.error('RPM solve error details:', {
        message: errorMessage,
        stack: errorStack,
        name: errorName
    });
    
    // Return generic server error to frontend
    return json({ 
        error: 'Server error',
        details: errorMessage,
        type: errorName
    }, { status: 500 });
  }
};