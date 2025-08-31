import { createMethodStore } from '$lib/stores/base-method-store';
import type { BaseMethodState } from '$lib/types/interactive-method';

interface NimbusState extends BaseMethodState {
    hasUtopiaMetadata: boolean;
    mapOptions: Record<string, any>;
    yearlist: string[];
    selectedPeriod: string;
    geoJSON: any;
    mapName: string;
    mapDescription: string;
}

export const nimbusStore = createMethodStore<NimbusState>({
    hasUtopiaMetadata: false,
    mapOptions: {},
    yearlist: [],
    selectedPeriod: 'period1',
    geoJSON: undefined,
    mapName: '',
    mapDescription: ''
});