import { csvParse } from "d3-dsv";
import type { PageLoad } from './$types';

import {
  parsePopulationRow
} from "$lib/adm/adapters";

import type {
  ADMLog,
  PopulationSolution
} from "$lib/adm/types";

export const load: PageLoad = async () => {
  const logResponse =
    await fetch("/data/adm_phi_log.json");

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

  const insgaResponse =
    await fetch(
      "/data/dtlz2_iNSGA-III_population_history.csv"
    );

  const irveaText =
    await irveaResponse.text();

  const insgaText =
    await insgaResponse.text();

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

  const insga =
    csvParse(insgaText).map(
      (row) =>
        parsePopulationRow(
          row,
          objectiveCount
        )
    );

  const populationHistory:
    PopulationSolution[] = [
      ...irvea,
      ...insga
    ];

  return {
    log,
    populationHistory
  };
}