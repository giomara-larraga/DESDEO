import type {
  ADMLog,
  ADMIteration,
  ReferenceVectorViewModel
} from "$lib/adm/types";

import type { DSVRowString } from "d3-dsv";
import type { PopulationSolution } from "./types";

export function getObjectives(log: ADMLog): string[] {
  return Array.from({ length: log.problem.objectives }, (_, i) => `f${i + 1}`);
}

export function getIteration(log: ADMLog, selectedIteration: number): ADMIteration {
  return (
    log.iterations.find((it) => it.iteration === selectedIteration) ??
    log.iterations[0]
  );
}

export function normalize(values: number[]): number[] {
  const sum = values.reduce((a, b) => a + b, 0);
  return sum === 0 ? values : values.map((v) => v / sum);
}

export function simpleProjection(values: number[]) {
  const w = normalize(values);
  return {
    x: (w[0] ?? 0) + 0.5 * (w[2] ?? 0),
    y: (w[1] ?? 0) + 0.5 * (w[3] ?? 0)
  };
}

export function getReferenceVectorViewData(
  log: ADMLog,
  selectedIteration: number
): ReferenceVectorViewModel[] {
  const iteration = getIteration(log, selectedIteration);

  const assignments = new Map(
    iteration.reference_vector_assignments.map((a) => [
      a.vector_id,
      a.assigned_count
    ])
  );

  const selected = iteration.preference_information.selected_reference_vector;
  const roi = iteration.max_assigned_vector.vector_id;

  return log.reference_vectors.map((vector) => {
    const projection = simpleProjection(vector.direction);

    return {
      id: vector.vector_id,
      weights: normalize(vector.direction),
      assignedSolutions: assignments.get(vector.vector_id) ?? 0,
      selected: vector.vector_id === selected,
      roi: vector.vector_id === roi,
      x: projection.x,
      y: projection.y
    };
  });
}

export function getCurrentPhi(log: ADMLog, selectedIteration: number) {
  const iteration = getIteration(log, selectedIteration);

  return log.methods.map((method) => ({
    method,
    phi: iteration.hypervolume[method].phi_iteration
  }));
}



export function parsePopulationRow(
  row: DSVRowString,
  objectiveCount: number
): PopulationSolution {
  return {
    objectives: Array.from(
      { length: objectiveCount },
      (_, index) =>
        Number(row[`f_${index + 1}`])
    ),

    method: String(row.method),

    adm_iteration:
      Number(row.adm_iteration),

    phase:
      row.phase as
        | "learning"
        | "decision",

    generation_in_iteration:
      Number(row.generation_in_iteration),

    solution_index:
      Number(row.solution_index)
  };
}