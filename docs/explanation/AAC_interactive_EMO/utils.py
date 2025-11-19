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


def get_experiment_configurations():
    """
    Returns experiment configurations for minimal and complete runs.

    Returns
    -------
    dict
        Dictionary with 'minimal' and 'complete' keys containing problem lists and objective counts
    """
    configurations = {
        "minimal": {
            "dtlz_problems": ["dtlz1", "dtlz2"],
            "wfg_problems": [],
            "objective_counts": [3, 5],
        },
        "complete": {
            "dtlz_problems": [f"dtlz{i}" for i in range(1, 8)],
            "wfg_problems": [f"wfg{i}" for i in range(1, 10)],
            "objective_counts": [3, 5, 7],
        },
    }
    return configurations


def run_single_experiment(
    name: str, n_obj: int, run_adm_func, output_dir: str, counter: int, total: int
):
    """
    Run a single ADM optimization experiment.

    Parameters
    ----------
    name : str
        Problem name (e.g., 'wfg1', 'dtlz2')
    n_obj : int
        Number of objectives
    run_adm_func : callable
        Function to run ADM optimization
    output_dir : str
        Directory to save results
    counter : int
        Current experiment number
    total : int
        Total number of experiments

    Returns
    -------
    bool
        True if successful, False if failed
    """
    import os
    import pandas as pd

    try:
        print(
            f"\n[{counter:2d}/{total}] 🔄 Processing {name.upper()} with {n_obj} objectives..."
        )

        # Create problem instance
        problem = create_problem(name, n_obj)

        # Run ADM optimization
        reference_points = run_adm_func(problem)

        # Save results
        out_path = os.path.join(output_dir, f"{name}_{n_obj}obj_refpoints.csv")
        reference_points.to_csv(out_path, index=False)
        print(f"         Saved {len(reference_points)} reference points → {out_path}")

        return True

    except Exception as e:
        print(f"         Error processing {name} with {n_obj} objectives: {str(e)}")
        return False


def run_experiment_batch(
    problems: list,
    objective_counts: list,
    run_adm_func,
    output_dir: str,
    experiment_type: str = "experiments",
):
    """
    Run a batch of ADM optimization experiments.

    Parameters
    ----------
    problems : list
        List of problem names
    objective_counts : list
        List of objective counts to test
    run_adm_func : callable
        Function to run ADM optimization
    output_dir : str
        Directory to save results
    experiment_type : str
        Type of experiment for display purposes

    Returns
    -------
    dict
        Summary of experiment results
    """
    import time
    import os

    total = len(problems) * len(objective_counts)
    counter = 0
    successful = 0
    failed = 0

    print(f"Starting {experiment_type}...")
    print(
        f"Total experiments: {len(problems)} problems × {len(objective_counts)} objective counts = {total}"
    )
    print("-" * 60)

    start_time = time.time()

    for name in problems:
        for n_obj in objective_counts:
            counter += 1
            success = run_single_experiment(
                name, n_obj, run_adm_func, output_dir, counter, total
            )
            if success:
                successful += 1
            else:
                failed += 1

    elapsed = (time.time() - start_time) / 60

    print(f"\n{experiment_type.capitalize()} completed in {elapsed:.2f} minutes!")
    print(f"Successful: {successful}/{total}")
    if failed > 0:
        print(f"Failed: {failed}/{total}")
    print(f"Results saved to: {os.path.abspath(output_dir)}")

    return {
        "total": total,
        "successful": successful,
        "failed": failed,
        "elapsed_minutes": elapsed,
    }


def get_generated_experiments(output_dir: str):
    """
    Get list of experiments that were successfully generated.

    Parameters
    ----------
    output_dir : str
        Directory containing the results

    Returns
    -------
    list of dict
        List of experiments with keys: 'name', 'n_obj', 'ref_file'
    """
    import os
    import glob

    experiments = []

    # Find all reference point files
    pattern = os.path.join(output_dir, "*_*obj_refpoints.csv")
    ref_files = glob.glob(pattern)

    for ref_file in ref_files:
        filename = os.path.basename(ref_file)
        # Parse filename: {name}_{n_obj}obj_refpoints.csv
        parts = filename.replace("_refpoints.csv", "").split("_")
        if len(parts) >= 2 and parts[-1].endswith("obj"):
            n_obj = int(parts[-1].replace("obj", ""))
            name = "_".join(parts[:-1])

            experiments.append({"name": name, "n_obj": n_obj, "ref_file": ref_file})

    # Sort by name then by n_obj
    experiments.sort(key=lambda x: (x["name"], x["n_obj"]))
    return experiments


def check_iteration_files_exist(
    output_dir: str, name: str, n_obj: int, max_iterations: int = 7
):
    """
    Check which iteration files exist for a given experiment.

    Parameters
    ----------
    output_dir : str
        Directory containing the results
    name : str
        Problem name
    n_obj : int
        Number of objectives
    max_iterations : int
        Maximum number of iterations to check

    Returns
    -------
    dict
        Dictionary with 'nsga3' and 'rvea' keys containing lists of existing iteration numbers
    """
    import os

    existing_iterations = {"nsga3": [], "rvea": []}

    for iteration in range(1, max_iterations + 1):
        nsga3_file = os.path.join(
            output_dir, f"nsga3_iteration_{name}_{n_obj}_{iteration}.csv"
        )
        rvea_file = os.path.join(
            output_dir, f"rvea_iteration_{name}_{n_obj}_{iteration}.csv"
        )

        if os.path.exists(nsga3_file):
            existing_iterations["nsga3"].append(iteration)
        if os.path.exists(rvea_file):
            existing_iterations["rvea"].append(iteration)

    return existing_iterations
