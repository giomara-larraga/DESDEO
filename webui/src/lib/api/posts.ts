// src/lib/api/interactiveMethods.ts
// Generic API request handler for interactive methods (NIMBUS, EMO, etc.)

import { serverApi as api } from './client';

// Use type assertion to bypass strict endpoint typing
export async function postMethodApi(endpoint: string, body: any, refreshToken: string) {
    try {
        // @ts-ignore: Suppress endpoint type error
        const response = await (api as any).POST(endpoint, {
            body,
            headers: {
                'Authorization': `Bearer ${refreshToken}`,
                'Content-Type': 'application/json'
            }
        });

        // Defensive: check for error/data properties
        if (response?.error) {
            console.error(`API error: ${response.error} (Status: ${response.response?.status})`);
            throw new Error(`API error: ${response.error} (Status: ${response.response?.status})`);
        }

        if (!response?.data) {
            console.error('No data received from API');
            throw new Error('No data received from API');
        }

        return { success: true, data: response.data };
    } catch (error) {
        console.error('API request failed:', error);
        return {
            success: false,
            error: error instanceof Error ? error.message : 'Unknown error occurred'
        };
    }
}
