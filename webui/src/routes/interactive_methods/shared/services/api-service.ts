type ApiResponse<T> = {
    success: boolean;
    data?: T;
    error?: string;
};
export class BaseMethodService {
    protected static async callAPI<T>(endpoint: string, data: Record<string, unknown>): Promise<ApiResponse<T>> {
        try {
            const response = await fetch(`/api/method/${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(data)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();
            return result;
        } catch (error) {
            console.error(`API call failed for ${endpoint}:`, error);
            return {
                success: false,
                error: error instanceof Error ? error.message : 'Unknown error occurred'
            };
        }
    }
}