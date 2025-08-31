import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/svelte';
import XNimbusSidebar from '../../components/sidebar/xnimbus-sidebar.svelte';
import { xnimbusStore } from '../../stores/xnimbus-store';

// Mock the store
vi.mock('../../stores/xnimbus-store', () => ({
    xnimbusStore: {
        setPreferences: vi.fn(),
        getPreferences: vi.fn(),
        subscribe: vi.fn()
    }
}));

describe('XNimbusSidebar', () => {
    beforeEach(() => {
        vi.clearAllMocks();
    });

    it('should render preference inputs correctly', () => {
        const { getByLabelText } = render(XNimbusSidebar);
        
        // Check if all necessary inputs are rendered
        expect(getByLabelText('Aspiration Level')).toBeTruthy();
        expect(getByLabelText('Upper Bound')).toBeTruthy();
        expect(getByLabelText('Lower Bound')).toBeTruthy();
    });

    it('should update preferences when inputs change', async () => {
        const { getByLabelText } = render(XNimbusSidebar);
        
        const aspirationInput = getByLabelText('Aspiration Level');
        await fireEvent.input(aspirationInput, { target: { value: '0.5' } });

        expect(xnimbusStore.setPreferences).toHaveBeenCalledWith(
            expect.objectContaining({
                aspirationLevels: expect.arrayContaining([0.5])
            })
        );
    });

    it('should validate input ranges', async () => {
        const { getByLabelText, getByText } = render(XNimbusSidebar);
        
        const input = getByLabelText('Aspiration Level');
        await fireEvent.input(input, { target: { value: '2' } });

        // Check if error message is displayed
        expect(getByText('Value must be between 0 and 1')).toBeTruthy();
    });

    it('should display explanation data when available', () => {
        vi.mocked(xnimbusStore.getPreferences).mockReturnValue({
            bounds: { min: 0, max: 1 },
            aspirationLevels: [0.5],
            explanations: {
                factors: ['Factor 1'],
                importance: [0.7]
            }
        });

        const { getByText } = render(XNimbusSidebar);
        expect(getByText('Factor 1')).toBeTruthy();
        expect(getByText('70%')).toBeTruthy();
    });
});
