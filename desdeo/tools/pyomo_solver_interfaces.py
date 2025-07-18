"""Defines solver interfaces for pyomo."""

import itertools

import numpy as np
import pyomo.environ as pyomo
from pydantic import BaseModel, ConfigDict, Field
from pyomo.opt import SolverResults as _pyomo_SolverResults
from pyomo.opt import SolverStatus as _pyomo_SolverStatus
from pyomo.opt import TerminationCondition as _pyomo_TerminationCondition

from desdeo.problem import Problem, PyomoEvaluator, TensorVariable
from desdeo.tools.generics import BaseSolver, SolverError, SolverResults


class BonminOptions(BaseModel):
    """Defines a pydantic model to store and pass options to the Bonmin solver.

    Because Bonmin utilizes many sub-solver, the options specific to Bonmin
    must be prefixed in their name with 'bonmin.{option_name}',
    e.g., `bonmin.integer_tolerance`. For a list of options, see
    https://www.coin-or.org/Bonmin/options_list.html

    Note:
        Not all options are available through this model.
        Please add options as they are needed and make a pull request.
    """

    tol: float = Field(description="Sets the convergence tolerance of ipopt. Defaults to 1e-8.", default=1e-8)
    """Sets the convergence tolerance of ipopt. Defaults to 1e-8."""

    bonmin_integer_tolerance: float = Field(
        description="Numbers within this value of an integer are considered integers. Defaults to 1e-6.", default=1e-6
    )
    """Numbers within this value of an integer are considered integers. Defaults to 1e-6."""

    bonmin_algorithm: str = Field(
        description=(
            "Presets some of the options in Bonmin based on the algorithm choice. Defaults to 'B-BB'. "
            "A good first option to try is 'B-Hyb'."
        ),
        default="B-BB",
    )
    """Presets some of the options in Bonmin based on the algorithm choice. Defaults to 'B-BB'.
    A good first option to try is 'B-Hyb'.
    """

    def asdict(self) -> dict[str, float]:
        """Converts the Pydantic model into a dict so that Bonmin specific options are in the correct format.

        This means that the attributes starting with `bonmin_optionname` will be
        converted to keys in the format `bonmin.optionname` in the returned dict.
        """
        output = {}
        for field_name, _ in BonminOptions.model_fields.items():
            if (rest := field_name.split(sep="_"))[0] == "bonmin":
                # Convert to Bonmin specific format
                output[f"bonmin.{'_'.join(rest[1:])}"] = getattr(self, field_name)
            else:
                # Keep the field as is
                output[field_name] = getattr(self, field_name)

        return output


class IpoptOptions(BaseModel):
    """Defines a pydantic dataclass to pass options to the Ipopt solver.

    For more information and documentation on the options,
    see https://coin-or.github.io/Ipopt/

    Note:
        Not all options are available through this model.
        Please add options as they are needed and make a pull request.
    """

    tol: float = Field(description="The desired relative convergence tolerance. Defaults to 1e-8.", default=1e-8)
    """The desired relative convergence tolerance. Defaults to 1e-8."""

    max_iter: int = Field(description="Maximum number of iterations. Must be >1. Defaults to 3000.", default=3000)
    """Maximum number of iterations. Must be >1. Defaults to 3000."""

    print_level: str = Field(
        description="The verbosity level of the solver's output. Ranges between 0 and 12. Defaults to 5.", default=5
    )
    """The verbosity level of the solver's output. Ranges between 0 and 12."""


class CbcOptions(BaseModel):
    """Defines a pydantic dataclass to pass options to the CBC solver.

    For more information and documentation on the options,
    see https://github.com/coin-or/Cbc

    Note:
        Not all options are available through this model.
        Please add options as they are needed and make a pull request.
    """

    model_config = ConfigDict(frozen=True, populate_by_name=True)

    sec: int = Field(
        description="The maximum amount of time (in seconds) the solver should run. Defaults to 600.", default=600
    )
    """The maximum amount of time (in seconds) the solver should run. Defaults to 600."""

    threads: int = Field(
        description="Number of threads (cores) to use for solving the problem. Defaults to 4.", default=4
    )
    """Number of threads (cores) to use for solving the problem. Defaults to 4."""

    log_level: int = Field(
        alias="logLevel",
        description=(
            "Controls the level of logging output. Values range from 0 (no output) to 5 (very detailed output)."
            " Defaults to 2."
        ),
        default=2,
    )
    """Controls the level of logging output. Values range from 0 (no output) to 5 (very detailed output).
    Defaults to 2.
    """

    max_solutions: int = Field(
        alias="maxSolutions",
        description="Limits the number of feasible solutions found by the solver. Defaults to 10.",
        default=10,
    )
    """Limits the number of feasible solutions found by the solver. Defaults to 10."""

    max_nodes: int = Field(
        alias="maxNodes",
        description="Sets the maximum number of branch-and-bound nodes to explore. Defaults to 1000.",
        default=1000,
    )
    """Sets the maximum number of branch-and-bound nodes to explore. Defaults to 1000."""

    ratio_gap: float = Field(
        alias="ratioGap",
        description=(
            "Sets the relative MIP gap (as a fraction of the optimal solution value) at which the solver will"
            " terminate. Defaults to 0.01."
        ),
        default=0.01,
    )
    """Sets the relative MIP gap (as a fraction of the optimal solution value) at which the solver will terminate.
    Defaults to 0.01.
    """

    absolute_gap: float = Field(
        alias="absoluteGap",
        description=(
            "Sets the absolute MIP gap (an absolute value) at which the solver will terminate.  Defaults to 1.0."
        ),
        default=1.0,
    )
    """Sets the absolute MIP gap (an absolute value) at which the solver will terminate. Defaults to 1.0."""

    solve: str = Field(
        description=(
            "Determines the strategy to use for solving the problem (e.g., 'branchAndCut', 'tree', 'trunk')."
            " Defaults to 'branchAndCut'."
        ),
        default="branchAndCut",
    )
    """Determines the strategy to use for solving the problem (e.g., 'branchAndCut', 'tree', 'trunk').
    Defaults to 'branchAndCut'.
    """

    presolve: int = Field(
        description="Controls the presolve level (0: no presolve, 1: default, 2: aggressive). Defaults to 2.", default=2
    )
    """Controls the presolve level (0: no presolve, 1: default, 2: aggressive). Defaults to 2."""

    feasibility_tolerance: float = Field(
        alias="feasibilityTolerance",
        description="Sets the feasibility tolerance for constraints. Defaults to 1e-6.",
        default=1e-6,
    )
    """Sets the feasibility tolerance for constraints. Defaults to 1e-6."""

    integer_tolerance: float = Field(
        alias="integerTolerance",
        description="Sets the tolerance for integrality of integer variables. Defaults to 1e-5.",
        default=1e-5,
    )
    """Sets the tolerance for integrality of integer variables. Defaults to 1e-5."""


_default_cbc_options = CbcOptions()
"""Defines CBC options with default values."""

_default_bonmin_options = BonminOptions()
"""Defines Bonmin options with default values."""

_default_ipopt_options = IpoptOptions()
"""Defines Ipopt optins with default values."""


def parse_pyomo_optimizer_results(
    opt_res: _pyomo_SolverResults, problem: Problem, evaluator: PyomoEvaluator
) -> SolverResults:
    """Parses pyomo SolverResults into DESDEO SolverResults.

    Args:
        opt_res (SolverResults): the pyomo solver results.
        problem (Problem): the problem being solved.
        evaluator (PyomoEvaluator): the evaluator utilized to get the pyomo solver results.

    Returns:
        SolverResults: DESDEO solver results.
    """
    results = evaluator.get_values()

    variable_values = {}
    for var in problem.variables:
        if isinstance(var, TensorVariable):
            # handle tensor variables
            # 1-indexing in Pyomo...
            values_list = np.zeros(var.shape)
            for indices in itertools.product(*(range(1, dim + 1) for dim in var.shape)):
                values_list[*[idx - 1 for idx in indices]] = results[var.symbol][
                    indices if len(indices) > 1 else indices[0]
                ]
            variable_values[var.symbol] = values_list.tolist()
        else:
            # variable_values = {var.symbol: results[var.symbol] for var in problem.variables}
            variable_values[var.symbol] = results[var.symbol]

    objective_values = {obj.symbol: results[obj.symbol] for obj in problem.objectives}
    constraint_values = (
        {con.symbol: results[con.symbol] for con in problem.constraints} if problem.constraints else None
    )
    extra_func_values = (
        {extra.symbol: results[extra.symbol] for extra in problem.extra_funcs}
        if problem.extra_funcs is not None
        else None
    )
    scalarization_values = (
        {scal.symbol: results[scal.symbol] for scal in problem.scalarization_funcs}
        if problem.scalarization_funcs is not None
        else None
    )
    success = (
        opt_res.solver.status == _pyomo_SolverStatus.ok
        and opt_res.solver.termination_condition == _pyomo_TerminationCondition.optimal
    )
    msg = (
        f"Pyomo solver status is: '{opt_res.solver.status}', with termination condition: "
        f"'{opt_res.solver.termination_condition}'."
    )

    return SolverResults(
        optimal_variables=variable_values,
        optimal_objectives=objective_values,
        constraint_values=constraint_values,
        extra_func_values=extra_func_values,
        scalarization_values=scalarization_values,
        success=success,
        message=msg,
    )


class PyomoBonminSolver(BaseSolver):
    """Creates pyomo solvers that utilize bonmin."""

    def __init__(self, problem: Problem, options: BonminOptions | None = _default_bonmin_options):
        """The solver is initialized with a problem and solver options.

        Suitable for mixed-integer problems. The objective function being minimized
        (target) and the constraint functions must be twice continuously
        differentiable. When the objective functions and constraints are convex, the
        solution is exact. When the objective or any of the constraints, or both,
        are non-convex, then the solution is based on heuristics.

        For more info about bonmin, see: https://www.coin-or.org/Bonmin/

        Note:
            Bonmin must be installed on the system running DESDEO, and its executable
                must be defined in the PATH.

        Args:
            problem (Problem): the problem to be solved.
            options (BonminOptions, optional): options to be passed to the Bonmin solver.
                If `None` is passed, defaults to `_default_bonmin_options` defined in
                this source file. Defaults to `None`.
        """
        if not problem.is_twice_differentiable:
            raise SolverError("Problem must be twice differentiable.")
        self.problem = problem
        self.evaluator = PyomoEvaluator(problem)

        if options is None:
            self.options = _default_bonmin_options
        else:
            self.options = options

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for a given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: the results of the optimization.
        """
        self.evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory("bonmin", tee=True)

        # set solver options
        for key, value in self.options.asdict().items():
            opt.options[key] = value
        opt_res = opt.solve(self.evaluator.model)

        return parse_pyomo_optimizer_results(opt_res, self.problem, self.evaluator)


class PyomoIpoptSolver(BaseSolver):
    """Create a pyomo solver that utilizes Ipopt."""

    def __init__(self, problem: Problem, options: IpoptOptions | None = _default_ipopt_options):
        """The solver is initialized with a problem and solver options.

        Suitable for non-linear, twice differentiable constrained problems.
        The problem may be convex or non-convex.

        For more information, see https://coin-or.github.io/Ipopt/

        Note:
            Ipopt must be installed on the system running DESDEO, and its executable
                must be defined in the PATH.

        Args:
            problem (Problem): the problem being solved.
            options (IpoptOptions, optional): options to be passed to the Ipopt solver.
                If `None` is passed, defaults to `_default_ipopt_options` defined in
                this source file. Defaults to `None`.
        """
        if not problem.is_twice_differentiable:
            raise SolverError("Problem must be twice differentiable.")
        self.problem = problem
        self.evaluator = PyomoEvaluator(problem)

        if options is None:
            self.options = _default_ipopt_options
        else:
            self.options = options

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for a given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: results of the Optimization.
        """
        self.evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory("ipopt", tee=True, options=self.options.model_dump())
        opt_res = opt.solve(self.evaluator.model)
        return parse_pyomo_optimizer_results(opt_res, self.problem, self.evaluator)


class PyomoGurobiSolver(BaseSolver):
    """Creates a pyomo solver that utilized Gurobi."""

    def __init__(self, problem: Problem, options: dict[str, any] | None = None):
        """Creates a pyomo solver that utilizes gurobi.

        You need to have gurobi installed on your system for this to work.

        Suitable for solving mixed-integer linear and quadratic optimization
        problems.

        Args:
            problem (Problem): the problem to be solved.
            options (GurobiOptions): Dictionary of Gurobi parameters to set.
                This is passed to pyomo as is, so it works the same as options
                would for calling pyomo SolverFactory directly.
                See https://www.gurobi.com/documentation/current/refman/parameters.html
                for information on the available options
        """
        self.problem = problem
        self.evaluator = PyomoEvaluator(problem)

        if options is None:
            self.options = {}
        else:
            self.options = options

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for a given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: the results of the optimization.
        """
        self.evaluator.set_optimization_target(target)

        with pyomo.SolverFactory("gurobi", solver_io="python") as opt:
            opt_res = opt.solve(self.evaluator.model)
            return parse_pyomo_optimizer_results(opt_res, self.problem, self.evaluator)


class PyomoCBCSolver(BaseSolver):
    """Create a pyomo solver that utilizes CBC."""

    def __init__(self, problem: Problem, options: CbcOptions | None = _default_cbc_options):
        """The solver is initialized with a problem and solver options.

        Suitable for combinatorial and large-scale mixed-integer linear problems.

        For more information, see https://coin-or.github.io/Ipopt/

        Note:
            CBC must be installed on the system running DESDEO, and its executable
                must be defined in the PATH.

        Args:
            problem (Problem): the problem being solved.
            options (CbcOptions, optional): options to be passed to the CBC solver.
                If `None` is passed, defaults to `_default_cbc_options` defined in
                this source file. Defaults to `None`.
        """
        if not problem.is_linear:
            raise SolverError("Nonlinear problems not supported.")
        self.problem = problem
        self.evaluator = PyomoEvaluator(problem)

        if options is None:
            self.options = _default_cbc_options
        else:
            self.options = options

    def solve(self, target: str) -> SolverResults:
        """Solve the problem for a given target.

        Args:
            target (str): the symbol of the objective function to be optimized.

        Returns:
            SolverResults: results of the Optimization.
        """
        self.evaluator.set_optimization_target(target)

        opt = pyomo.SolverFactory("cbc", tee=True, options=self.options.model_dump())
        opt_res = opt.solve(self.evaluator.model)
        return parse_pyomo_optimizer_results(opt_res, self.problem, self.evaluator)
