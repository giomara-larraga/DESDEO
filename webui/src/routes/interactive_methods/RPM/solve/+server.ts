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
 * Author: AI Assistant
 * Created: July 2025
 */

import { json } from '@sveltejs/kit';
import type { RequestHandler } from '@sveltejs/kit';
import createClient from 'openapi-fetch';
import type { paths } from '$lib/api/client-types';
import type { components } from '$lib/api/client-types';

/**
 * Create a server-side API client for communicating with the DESDEO backend.
 * 
 * This is separate from the frontend API client because:
 * - Server-side code doesn't have access to VITE_ environment variables
 * - Uses regular NODE_ENV variables (API_URL instead of VITE_API_URL)
 * - Runs in Node.js context, not browser context
 */
const serverApi = createClient<paths>({
  baseUrl: process.env.API_URL || 'http://localhost:8000' // Default to localhost if API_URL not set
});

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
    
    // Debug logging: Log the received request for troubleshooting
    console.log('Received RPM solve request:', JSON.stringify(solveRequest, null, 2));
    console.log('Making API call to /method/rpm/solve');

    /**
     * Forward the request to the backend DESDEO API
     * 
     * Process:
     * - Uses the server-side API client (serverApi)
     * - Includes authentication via Bearer token (refresh token)
     * - Sends the solve request as JSON payload
     */
    const response = await serverApi.POST('/method/rpm/solve', {
      body: solveRequest,
      headers: {
        'Authorization': `Bearer ${refreshToken}`, // Authenticate with refresh token
        'Content-Type': 'application/json'
      }
    });

    // Debug logging: Log the API response details
    console.log('API response status:', response.response?.status);
    console.log('API response data:', response.data);
    console.log('API response error:', response.error);

    /**
     * Handle API response errors
     * If the backend API didn't return data, it indicates an error occurred
     */
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
    console.log('Returning successful response');
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
    
    // Return generic server error to frontend (don't expose internal details)
    return json({ 
        error: 'Server error',
        details: errorMessage,
        type: errorName
    }, { status: 500 });
  }
};

/**
 * Flow Summary:
 * 1. Frontend sends POST request to /interactive_methods/RPM/solve
 * 2. Server checks for valid refresh token in cookies
 * 3. Server parses RPMSolveRequest from request body
 * 4. Server forwards request to DESDEO backend API with authentication
 * 5. Server receives RPMState response from backend
 * 6. Server returns processed response to frontend
 */
