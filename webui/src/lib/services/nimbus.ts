// src/lib/services/nimbus.ts
import { callNimbusAPI } from '$lib/helpers/nimbus'; // adjust if needed
import type { ResponseNIMBUS as Response } from '$lib/types/nimbus';
import type { Solution } from '$lib/types/general';

export async function initializeNimbus(problem_id: number) {
  return callNimbusAPI<Response>('initialize', {
    problem_id, session_id: null, parent_state_id: null, solver: null
  });
}

export async function iterateNimbus(args: {
  problem_id: number;
  current_objectives: Record<string, number>;
  num_desired: number;
  preference: {
    preference_type: 'reference_point';
    aspiration_levels: Record<string, number>;
  };
}) {
  return callNimbusAPI<Response>('iterate', {
    problem_id: args.problem_id,
    session_id: null,
    parent_state_id: null,
    current_objectives: args.current_objectives,
    num_desired: args.num_desired,
    preference: args.preference
  });
}

export async function intermediateNimbus(args: {
  problem_id: number;
  reference_solution_1: Solution;
  reference_solution_2: Solution;
  num_desired: number;
}) {
  return callNimbusAPI<Response>('intermediate', {
    problem_id: args.problem_id,
    session_id: null,
    parent_state_id: null,
    reference_solution_1: args.reference_solution_1,
    reference_solution_2: args.reference_solution_2,
    num_desired: args.num_desired
  });
}

export async function finishNimbus(args: {
  problem_id: number | undefined; solution: Solution;
}) {
  return callNimbusAPI<{ success: boolean }>('choose', {
    problem_id: args.problem_id, solution: args.solution
  });
}

export async function saveSolution(args: {
  problem_id: number | undefined; solution: Solution & { name?: string };
}) {
  return callNimbusAPI<{ success: boolean }>('save', {
    problem_id: args.problem_id, solutions: [args.solution]
  });
}

export async function removeSavedSolution(args: {
  problem_id: number | undefined; solution: Solution;
}) {
  // endpoint may be mocked / TODO in backend, we keep the call
  return callNimbusAPI<{ success: boolean }>('remove_saved', {
    problem_id: args.problem_id, solutions: [args.solution]
  });
}

export async function getMaps(args: {
  problem_id: number; solution: Solution;
}) {
  return callNimbusAPI<{
    years: string[];
    options: Record<string, any>;
    map_json: object;
    map_name: string;
    description: string;
    compensation: number;
  }>('get_maps', { problem_id: args.problem_id, solution: args.solution });
}
