// src/lib/types/nimbus.ts
import type { components } from '$lib/api/client-types';
import type { Solution } from '$lib/types/general';

export type ResponseNIMBUS = {
  state_id: number | null;
  previous_preference?: components['schemas']['ReferencePoint'];
  previous_objectives?: Record<string, number>;
  reference_solution_1?: Record<string, number>;
  reference_solution_2?: Record<string, number>;
  current_solutions: Solution[];
  saved_solutions: Solution[];
  all_solutions: Solution[];
};

