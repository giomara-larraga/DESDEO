import { csvParse } from "d3-dsv";
import type { PageLoad } from './$types';

import {
  parsePopulationRow
} from "$lib/adm/adapters";

import type {
  ADMLog,
  PopulationSolution
} from "$lib/adm/types";

export const load: PageLoad = async ({ fetch }) => {
  const logResponse =
    await fetch("/data/adm_phi_log.json");

  if (!logResponse.ok) throw new Error(`ADM log: HTTP ${logResponse.status}`);

  const rawLog =
    await logResponse.json();

  const log: ADMLog =
    Array.isArray(rawLog)
      ? rawLog[0]
      : rawLog;

  const irveaResponse =
    await fetch(
      "/data/dtlz2_iRVEA_population_history.csv"
    );

  const pbeaResponse =
    await fetch(
      "/data/dtlz2_PBEA_population_history.csv"
    );

  if (!irveaResponse.ok || !pbeaResponse.ok) {
    throw new Error("Unable to load one or both population CSV files");
  }

  const irveaText =
    await irveaResponse.text();

  const pbeaText =
    await pbeaResponse.text();

  const objectiveCount =
    log.problem.objectives;

  const irvea =
    csvParse(irveaText).map(
      (row) =>
        parsePopulationRow(
          row,
          objectiveCount
        )
    );

  const pbea =
    csvParse(pbeaText).map(
      (row) =>
        parsePopulationRow(
          row,
          objectiveCount
        )
    );

  const populationHistory:
    PopulationSolution[] = [
      ...irvea,
      ...pbea
    ];

  return {
    log,
    populationHistory
  };
}