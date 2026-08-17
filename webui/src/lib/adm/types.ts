export type ADMPhase = "learning" | "decision";

export type MethodName = string;


/* =========================================================
   Experiment
   ========================================================= */

export type ADMLog = {
  experiment_id: string;

  problem: {
    name: string;
    objectives: number;
    variables: number;
  };

  methods: MethodName[];

  adm_configuration: {
    learning_iterations: number;
    decision_iterations: number;
    generations_per_iteration: number;
    number_of_reference_vectors: number;
    seed: number;
  };

  initial_reference_point: number[];
  final_nadir: number[];

  reference_vectors: ReferenceVectorRaw[];

  iterations: ADMIteration[];

  phi_summary: Record<string, unknown>;
};


/* =========================================================
   Reference vectors
   ========================================================= */

export type ReferenceVectorRaw = {
  vector_id: string;
  direction: number[];
};

export type ReferenceVectorAssignment = {
  vector_id: string;
  assigned_solution_ids: string[];
  assigned_count: number;
};

export type MaxAssignedVector = {
  vector_id: string;
  assigned_count: number;
};


/* =========================================================
   Solutions
   ========================================================= */

export type CompositeSolution = {
  solution_id: string;
  method: MethodName;
  objectives: number[];
};


/* =========================================================
   ADM preference
   ========================================================= */

export type PreferenceInformation = {
  type: string;

  reference_point: number[];

  selected_reference_vector: string;

  selection_rule: string;

  description?: string;
};


/* =========================================================
   Performance
   ========================================================= */

export type MethodPerformance = {
  positive_hypervolume_per_generation: number[];

  negative_hypervolume_per_generation: number[];

  phi_per_generation: number[];

  phi_iteration: number;
};


/* =========================================================
   Iteration
   ========================================================= */

export type ADMIteration = {
  iteration: number;

  phase: ADMPhase;

  composite_front: CompositeSolution[];

  preference_information: PreferenceInformation;

  hypervolume: Record<
    MethodName,
    MethodPerformance
  >;

  reference_vector_assignments:
    ReferenceVectorAssignment[];

  max_assigned_vector:
    MaxAssignedVector;
};


/* =========================================================
   UI model
   ========================================================= */

export type ReferenceVectorViewModel = {
  id: string;

  weights: number[];

  assignedSolutions: number;

  selected: boolean;

  roi: boolean;

  x: number;
  y: number;
};


/* =========================================================
   Generation-level population history
   ========================================================= */

export type PopulationSolution = {
  objectives: number[];

  method: MethodName;

  adm_iteration: number;

  phase: ADMPhase;

  generation_in_iteration: number;

  solution_index: number;
};