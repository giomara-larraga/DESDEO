import { callNimbusAPI } from '../../routes/interactive_methods/NIMBUS/helper-functions';
import type { Solution, PeriodKey } from '$lib/types';


//  TODO: move the API call to a different path, as the visualization can be used by other methods
export interface MapsResponse {
        years: string[];
        options: Record<string, any>;
        map_json: object;
        map_name: string;
        description: string;
        compensation: number;
}

/**
 * Fetch maps data for UTOPIA visualization for one solution and update Svelte stores.
 */
export async function get_maps(problemId: number, solution: Solution) {
    // Define the expected return type for the maps API


    const result = await callNimbusAPI<MapsResponse>('get_maps', {
        problem_id: problemId,
        solution: solution
    });

    if (result.success && result.data) {
        const data = result.data;
        const map_options = {
            period1: data.options[data.years[0]] || {},
            period2: data.options[data.years[1]] || {},
            period3: data.options[data.years[2]] || {}
        } as Record<PeriodKey, Record<string, any>>;

        const response_map: MapsResponse = {
            years: data.years,
            options: map_options,
            map_json: data.map_json,
            map_name: data.map_name,
            description: data.description,
            compensation: Math.round(data.compensation * 100) / 100
        };
        //yearlist.set(data.years);

        // Apply the formatter function client-side
        for (let year of data.years) {
            if (data.options[year].tooltip.formatterEnabled) {
                data.options[year].tooltip.formatter = function (params: any) {
                    return `${params.name}`;
                };
            }
        }

        return response_map;

        //geoJSON.set(data.map_json);
        //mapName.set(data.map_name);
      //  mapDescription.set(data.description);
        //compensation.set(Math.round(data.compensation * 100) / 100);
    } else {
        console.error('Failed to get maps:', result.error);
        return null;
    }
}
