export type ADMLog = {
  experiment_id: string;
  problem: {
    name: string;
    objectives: number;
    variables: number;
  };
  methods: string[];
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
  phi_summary: Record<string, any>;
};

export type ReferenceVectorRaw = {
  vector_id: string;
  direction: number[];
};

export type CompositeSolution = {
  solution_id: string;
  method: string;
  objectives: number[];
};

export type ADMIteration = {
  iteration: number;
  phase: "learning" | "decision";
  composite_front: CompositeSolution[];
  preference_information: {
    type: string;
    reference_point: number[];
    selected_reference_vector: string;
    selection_rule: string;
    description: string;
  };
  hypervolume: Record<
    string,
    {
      positive_hypervolume_per_generation: number[];
      negative_hypervolume_per_generation: number[];
      phi_per_generation: number[];
      phi_iteration: number;
    }
  >;
  reference_vector_assignments: {
    vector_id: string;
    assigned_solution_ids: string[];
    assigned_count: number;
  }[];
  max_assigned_vector: {
    vector_id: string;
    assigned_count: number;
  };
};

export type ReferenceVectorViewModel = {
  id: string;
  weights: number[];
  assignedSolutions: number;
  selected: boolean;
  roi: boolean;
  x: number;
  y: number;
};