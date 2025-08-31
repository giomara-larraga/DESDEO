import { describe, it, expect, vi, beforeEach } from 'vitest';
import { XNimbusHandler } from '../../handlers/xnimbus-handlers';
import type { XNimbusStore } from '../../stores/xnimbus-store';
import type { ApiService } from '../../../shared/services/api-service';
import type { PreferenceData, Solution } from '../../types/xnimbus-types';

describe('XNimbusHandler', () => {
    let handler: XNimbusHandler;
    let mockStore: XNimbusStore;
    let mockApiService: ApiService;

    beforeEach(() => {
        // Mock store
        mockStore = {
            setPreferences: vi.fn(),
            updateSolutions: vi.fn(),
            getMethodId: vi.fn().mockReturnValue('test-method-id'),
        } as unknown as XNimbusStore;

        // Mock API service
        mockApiService = {
            updatePreferences: vi.fn(),
            getExplanation: vi.fn(),
        } as unknown as ApiService;

        handler = new XNimbusHandler(mockStore, mockApiService);
    });

    describe('handlePreferenceUpdate', () => {
        it('should update store and call API when preferences change', async () => {
            const mockPreferences: PreferenceData = {
                bounds: { min: 0, max: 1 },
                aspirationLevels: [0.5, 0.3, 0.7]
            };

            const mockResponse = {
                solutions: [
                    { id: '1', values: [0.5, 0.3, 0.7] }
                ] as Solution[]
            };

            mockApiService.updatePreferences = vi.fn().mockResolvedValue(mockResponse);

            await handler.handlePreferenceUpdate(mockPreferences);

            // Verify store was updated
            expect(mockStore.setPreferences).toHaveBeenCalledWith(mockPreferences);
            
            // Verify API was called
            expect(mockApiService.updatePreferences).toHaveBeenCalledWith({
                methodId: 'test-method-id',
                preferences: mockPreferences
            });

            // Verify solutions were updated in store
            expect(mockStore.updateSolutions).toHaveBeenCalledWith(mockResponse.solutions);
        });

        it('should handle API errors gracefully', async () => {
            const mockPreferences: PreferenceData = {
                bounds: { min: 0, max: 1 },
                aspirationLevels: [0.5, 0.3, 0.7]
            };

            mockApiService.updatePreferences = vi.fn().mockRejectedValue(new Error('API Error'));

            await expect(handler.handlePreferenceUpdate(mockPreferences))
                .rejects.toThrow('API Error');

            // Verify store was still updated with preferences
            expect(mockStore.setPreferences).toHaveBeenCalledWith(mockPreferences);
        });
    });

    // Add more test cases for other handler methods
});
