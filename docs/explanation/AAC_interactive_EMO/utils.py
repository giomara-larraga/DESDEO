from desdeo.problem.testproblems.benchmarks_server import (
    PymooParameters,
    server_problem,
)


def get_dtlz_default_nvar(problem_name: str, n_obj: int) -> int:
    """
    Get the recommended number of variables for a given DTLZ problem and number of objectives.
    Source: pymoo defaults.
    """
    base = {
        "dtlz1": 5,
        "dtlz2": 10,
        "dtlz3": 10,
        "dtlz4": 10,
        "dtlz5": 10,
        "dtlz6": 10,
        "dtlz7": 20,
    }
    k = base.get(problem_name, 10)
    return n_obj + k - 1


def get_wfg_default_nvar(problem_name: str, n_obj: int) -> int:
    """
    WFG problems have n_var = k + l where typically:
      k = 2 * (n_obj - 1)
      l = 20
    """
    k = 2 * (n_obj - 1)
    l = 20
    return k + l


def get_default_ea_parameters(problem_name: str, n_obj: int):
    """
    Returns the default population size, number of generations, and multi-layer
    reference vector configurations for NSGA-III / RVEA depending on the problem
    type and number of objectives.

    The population size is automatically calculated based on the number of reference
    vectors that will be generated from the multi-layer configuration.

    Parameters
    ----------
    problem_name : str
        Name of the problem (e.g. "dtlz1", "wfg2", etc.)
    n_obj : int
        Number of objectives.

    Returns
    -------
    pop_size : int
        Suggested population size (based on number of reference vectors).
        Always an even number.
    n_gen : int
        Suggested number of generations.
    pymoo_layers : list[dict]
        Default multi-layer configuration for reference vectors.
        Each dict contains 'strategy', 'n_partitions', and 'scaling' keys.
    """
    from scipy.special import comb

    problem_name = problem_name.lower()

    # Default generation counts
    dtlz_gen_defaults = {3: 250, 5: 350, 7: 400, 9: 500}

    wfg_gen_defaults = {3: 400, 5: 500, 7: 600, 9: 800}

    # Default multi-layer configurations based on number of objectives
    # Two-layer approach with different scaling factors
    if n_obj == 3:
        # For 3 objectives, use standard das-dennis with two scales
        pymoo_layers = [
            {"strategy": "das-dennis", "n_partitions": 12, "scaling": 1.0},
            {"strategy": "das-dennis", "n_partitions": 12, "scaling": 0.5},
        ]
    elif n_obj == 5:
        # For 5 objectives, use slightly coarser partitions
        pymoo_layers = [
            {"strategy": "das-dennis", "n_partitions": 6, "scaling": 1.0},
            {"strategy": "das-dennis", "n_partitions": 6, "scaling": 0.5},
        ]
    elif n_obj == 7:
        # For 7 objectives, use even coarser partitions
        pymoo_layers = [
            {"strategy": "das-dennis", "n_partitions": 4, "scaling": 1.0},
            {"strategy": "das-dennis", "n_partitions": 4, "scaling": 0.5},
        ]
    elif n_obj >= 9:
        # For 9+ objectives, use minimal partitions
        pymoo_layers = [
            {"strategy": "das-dennis", "n_partitions": 3, "scaling": 1.0},
            {"strategy": "das-dennis", "n_partitions": 3, "scaling": 0.5},
        ]
    else:
        # Fallback for other objective counts
        pymoo_layers = [
            {"strategy": "das-dennis", "n_partitions": 12, "scaling": 1.0},
            {"strategy": "das-dennis", "n_partitions": 12, "scaling": 0.5},
        ]

    # Calculate the number of reference vectors from the layers
    # For das-dennis, the number of vectors per layer is: C(H + M - 1, M - 1)
    # where H is n_partitions and M is n_obj
    total_vectors = 0
    for layer in pymoo_layers:
        if layer["strategy"] == "das-dennis":
            H = layer["n_partitions"]
            # Number of reference vectors in this layer
            n_vectors = int(comb(H + n_obj - 1, n_obj - 1, exact=True))
            total_vectors += n_vectors

    # Set population size equal to or slightly larger than number of reference vectors
    # This ensures each reference vector can have at least one associated solution
    pop_size = total_vectors

    # Ensure population size is always an even number
    # If odd, round up to the next even number
    if pop_size % 2 != 0:
        pop_size += 1

    # Choose generation count based on problem family
    if problem_name.startswith("dtlz"):
        n_gen = dtlz_gen_defaults.get(n_obj, 300)
    elif problem_name.startswith("wfg"):
        n_gen = wfg_gen_defaults.get(n_obj, 500)
    else:
        raise ValueError(f"Unknown problem family: {problem_name}")

    return pop_size, n_gen, pymoo_layers


def get_ideal_nadir(problem_name: str, n_obj: int):
    """
    Returns the ideal and nadir vectors for a DTLZ or WFG problem,
    along with symbols for each objective.

    Parameters
    ----------
    problem_name : str
        Name of the problem, e.g., "dtlz1", "dtlz2", "wfg3", etc.
    n_obj : int
        Number of objectives.

    Returns
    -------
    symbols : list[str]
        Objective symbols, e.g., ["f_1", "f_2", ...].
    ideal_dict : dict
        Mapping from objective symbol to ideal value.
    nadir_dict : dict
        Mapping from objective symbol to nadir value.
    """
    import numpy as np

    symbols = [f"f_{i+1}" for i in range(n_obj)]

    problem_name = problem_name.lower()

    if problem_name.startswith("dtlz"):
        if problem_name == "dtlz1":
            ideal = np.zeros(n_obj)
            nadir = np.full(n_obj, 0.5)
        elif problem_name in ["dtlz2", "dtlz3", "dtlz4", "dtlz5", "dtlz6"]:
            ideal = np.zeros(n_obj)
            nadir = np.ones(n_obj)
        elif problem_name == "dtlz7":
            ideal = np.zeros(n_obj)
            ideal[-1] = 1.0
            nadir = np.ones(n_obj)
            nadir[-1] = 2.0
        else:
            raise ValueError(f"Unknown DTLZ problem: {problem_name}")

    elif problem_name.startswith("wfg"):
        ideal = np.zeros(n_obj)
        # Nadir: 2 * objective index
        nadir = np.array([2 * (i + 1) for i in range(n_obj)])
    else:
        raise ValueError(f"Unknown problem family: {problem_name}")

    ideal_dict = dict(zip(symbols, ideal))
    nadir_dict = dict(zip(symbols, nadir))

    return ideal_dict, nadir_dict


def create_problem(name: str, n_obj: int):
    """Create a Problem instance from the FastAPI server."""
    family = "dtlz" if name.startswith("dtlz") else "wfg"
    n_var = (
        get_dtlz_default_nvar(name, n_obj)
        if family == "dtlz"
        else get_wfg_default_nvar(name, n_obj)
    )
    params = PymooParameters(name=name, n_var=n_var, n_obj=n_obj)
    problem = server_problem(params)
    ideal, nadir = get_ideal_nadir(name, n_obj)
    problem = problem.update_ideal_and_nadir(new_ideal=ideal, new_nadir=nadir)

    print(f"✅ Created {name.upper()} with {n_var} vars and {n_obj} objectives.")
    return problem
