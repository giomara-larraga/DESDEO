"""Stateful, single-user SCORE Bands method.

Routes:
  POST /initialize  - resume the latest state, or create the first state
  POST /iterate     - optimize using selected band ranges; save a child state
  POST /save        - save/unsave a band; save a child state
  GET  /history     - restore the current lineage after a reload

The existing /session/new endpoint remains the shared way to create sessions;
/initialize also creates a session when the user has none, for direct navigation.
"""

from typing import Annotated

import polars as pl
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from sqlmodel import Session, select

from desdeo.api.db import get_session
from desdeo.api.models import SCOREBandsMethodState, StateDB
from desdeo.api.models.generic_states import StateKind
from desdeo.api.models.session import InteractiveSessionDB
from desdeo.api.models.user import User
from desdeo.api.routers.user_authentication import get_current_user
from desdeo.api.routers.utils import fetch_problem_with_role_check
from desdeo.api.models.score_bands_method import (
    SCOREBandsBandPreference,
    SCOREBandsMethodHistoryItem,
    SCOREBandsMethodHistoryResponse,
    SCOREBandsMethodInitializeRequest,
    SCOREBandsMethodIterationRequest,
    SCOREBandsMethodResponse,
    SCOREBandsMethodSaveRequest,
    SCOREBandsMethodSaveResponse,
    SCOREBandsOptimizationOptions,
    SCOREBandsSavedBand,
)
from desdeo.emo import algorithms, preference_handling
from desdeo.problem import Problem
from desdeo.tools.score_bands import SCOREBandsConfig, score_json

router = APIRouter(prefix="/method/score_bands_method", tags=["SCORE Bands Method"])

SCORE_KINDS = (
    StateKind.SCORE_BANDS_METHOD_INITIALIZE,
    StateKind.SCORE_BANDS_METHOD_ITERATE,
    StateKind.SCORE_BANDS_METHOD_SAVE,
)


def _problem(user: User, db: Session, problem_id: int):
    problem_db = fetch_problem_with_role_check(user, problem_id, db)
    if problem_db is None:
        raise HTTPException(status_code=404, detail="Problem not found or not accessible.")
    return problem_db


def _session(user: User, db: Session, session_id: int | None, *, create: bool):
    requested = session_id if session_id is not None else user.active_session_id
    found = db.get(InteractiveSessionDB, requested) if requested is not None else None
    if session_id is not None and found is None:
        raise HTTPException(status_code=404, detail="Interactive session not found.")
    if found is not None:
        if found.user_id != user.id:
            raise HTTPException(status_code=403, detail="Interactive session belongs to another user.")
        return found
    if not create:
        raise HTTPException(status_code=400, detail="An active interactive session is required.")

    found = InteractiveSessionDB(user_id=user.id, info="SCORE Bands")
    db.add(found)
    db.flush()
    user.active_session_id = found.id
    db.add(user)
    db.commit()
    db.refresh(found)
    return found


def _latest(db: Session, problem_id: int, session_id: int) -> StateDB | None:
    # Looking only at SCORE states avoids treating another method's state as the parent.
    rows = db.exec(
        select(StateDB)
        .where(StateDB.problem_id == problem_id, StateDB.session_id == session_id)
        .order_by(StateDB.id.desc())
    ).all()
    return next(
        (row for row in rows if row.base_state is not None and row.base_state.kind in SCORE_KINDS),
        None,
    )


def _require_state(db: Session, state_id: int, problem_id: int, session_id: int) -> StateDB:
    row = db.get(StateDB, state_id)
    if (
        row is None
        or row.problem_id != problem_id
        or row.session_id != session_id
        or row.base_state is None
        or row.base_state.kind not in SCORE_KINDS
    ):
        raise HTTPException(status_code=404, detail="SCORE Bands state not found in this session.")
    return row


def _all_history(
    db: Session,
    problem_id: int,
    session_id: int,
) -> list[SCOREBandsMethodHistoryItem]:
    """Return all SCORE Bands generations, including branches."""

    rows = db.exec(
        select(StateDB)
        .where(
            StateDB.problem_id == problem_id,
            StateDB.session_id == session_id,
        )
        .order_by(StateDB.id.asc())
    ).all()

    history = []

    for row in rows:
        if (
            row.base_state is None
            or row.base_state.kind not in SCORE_KINDS
        ):
            continue

        state = row.state

        # Save actions are persisted but are not optimization levels.
        if state.action not in ("initialize", "iterate"):
            continue

        parent_id = None

        if row.parent_id is not None:
            parent = _require_state(
                db,
                row.parent_id,
                problem_id,
                session_id,
            )

            # A generation may have been created after a save state.
            # Follow that save state to its actual generation.
            parent_id = _source_state_id(db, parent)

        history.append(
            SCOREBandsMethodHistoryItem(
                state_id=row.id,
                parent_state_id=parent_id,
                action=state.action,
                selected_cluster_id=state.selected_cluster_id,
                preferred_ranges=state.preferred_ranges,
                result=state.result,
                optimized=bool(
                    (state.optimization_options or {}).get("optimize", False)
                ),
            )
        )

    return history

def _response(db: Session, head: StateDB, session_id: int, *, initialized: bool):
    state = head.state
    return SCOREBandsMethodResponse(
        response_type="score_bands.initialize" if initialized else "score_bands.iterate",
        state_id=head.id,
        session_id=session_id,
        result=state.result,
        saved_bands=[SCOREBandsSavedBand.model_validate(x) for x in _session_saved_bands(db, head.problem_id, session_id)],
        history=_all_history(
            db,
            head.problem_id,
            session_id,
        ),
    )


def _options(problem: Problem, config: SCOREBandsConfig, data: pl.DataFrame) -> SCOREBandsConfig:
    cloned = config.model_copy(deep=True)
    symbols = [obj.symbol for obj in problem.objectives]
    columns = data.columns
    dimensions = cloned.dimensions or [symbol for symbol in symbols if symbol in columns]
    if len(dimensions) < 2 or any(dim not in columns for dim in dimensions):
        raise HTTPException(status_code=422, detail="At least two valid objective dimensions are required.")
    cloned.dimensions = dimensions
    by_symbol = {obj.symbol: obj for obj in problem.objectives}
    if cloned.descriptive_names is None:
        cloned.descriptive_names = {key: by_symbol[key].name for key in dimensions}
    if cloned.units is None:
        cloned.units = {key: by_symbol[key].unit or "" for key in dimensions}
    return cloned


def _is_analytical_problem(problem: Problem) -> bool:
    """Whether all objectives are evaluable analytical functions.

    Data-based objectives require a precomputed discrete representation and
    must not be sent to a continuous evolutionary solver without one.
    """
    objectives = problem.objectives or []
    if len(objectives) < 2:
        return False
    for objective in objectives:
        kind = getattr(objective, "objective_type", "analytical")
        kind = getattr(kind, "value", kind)
        if kind != "analytical" or getattr(objective, "func", None) is None:
            return False
    return bool(problem.get_flattened_variables())


def _discrete_dataset(problem: Problem) -> pl.DataFrame:
    # Only call this when a discrete representation actually exists.
    discrete = problem.discrete_representation
    if discrete is None:
        raise HTTPException(status_code=422, detail="No discrete data were supplied for this problem.")
    values = discrete.objective_values
    if not values or len({len(column) for column in values.values()}) != 1:
        raise HTTPException(status_code=422, detail="Invalid discrete objective columns.")
    return pl.DataFrame(values)


def _solve(
    problem: Problem,
    optimization: SCOREBandsOptimizationOptions,
    ranges: dict[str, tuple[float, float]] | None = None,
    *,
    use_archive: bool = False,
) -> tuple[pl.DataFrame, dict[str, list] | None]:
    """Run an evolutionary solver; no preference for first-front approximation.

    An unpreferenced initialization can use the non-dominated archive, which
    represents more of the discovered Pareto front than the final population.
    We do not couple its objective rows with final-population variable rows.
    """
    if not optimization.optimize:
        raise HTTPException(status_code=422, detail="Evolutionary optimization must be enabled.")
    if not _is_analytical_problem(problem):
        raise HTTPException(
            status_code=422,
            detail="Evolutionary SCORE Bands requires evaluable analytical objective functions and decision variables.",
        )

    options = (
        algorithms.nsga3_options()
        if optimization.algorithm == "nsga3"
        else algorithms.rvea_options()
    )
    if ranges is not None:
        aspirations, reservations = {}, {}
        for objective in problem.objectives:
            symbol = objective.symbol
            if symbol not in ranges:
                raise HTTPException(status_code=422, detail=f"Band lacks range for {symbol}.")
            lower, upper = ranges[symbol]
            if not (float("-inf") < lower <= upper < float("inf")):
                raise HTTPException(status_code=422, detail=f"Invalid bounds for {symbol}.")
            aspirations[symbol] = upper if objective.maximize else lower
            reservations[symbol] = lower if objective.maximize else upper
        options.preference = preference_handling.DesirableRangesOptions(
            aspiration_levels=aspirations,
            reservation_levels=reservations,
        )
    else:
        # First approximation explores the full trade-off space, not one band.
        options.preference = None

    extra = optimization.algorithm_options or {}
    unknown = set(extra) - {"number_of_vectors"}
    if unknown:
        raise HTTPException(status_code=422, detail=f"Unsupported optimization options: {sorted(unknown)}")
    if "number_of_vectors" in extra:
        n = extra["number_of_vectors"]
        if n <= 0:
            raise HTTPException(status_code=422, detail="number_of_vectors must be positive.")
        options.template.selection.reference_vector_options.number_of_vectors = n

    solver, extras = algorithms.emo_constructor(emo_options=options, problem=problem)
    optimized = solver()
    final_outputs = optimized.optimal_outputs
    if not isinstance(final_outputs, pl.DataFrame):
        final_outputs = pl.DataFrame(final_outputs)
    outputs = final_outputs
    variables = getattr(optimized, "optimal_variables", None)

    if use_archive and ranges is None:
        archive = getattr(extras, "archive", None)
        archived = getattr(archive, "solutions", None)
        if archived is not None:
            if not isinstance(archived, pl.DataFrame):
                archived = pl.DataFrame(archived)
            symbols = {obj.symbol for obj in problem.objectives}
            if archived.height > 0 and symbols.issubset(archived.columns):
                outputs = archived
                # Archive entries and last-generation entries have different
                # row counts/order. Only save variables if present in archive.
                variable_symbols = [v.symbol for v in problem.get_flattened_variables()]
                variables = (
                    archived.select(variable_symbols)
                    if variable_symbols and set(variable_symbols).issubset(archived.columns)
                    else None
                )

    dimensions = [obj.symbol for obj in problem.objectives if obj.symbol in outputs.columns]
    if len(dimensions) < 2 or outputs.height == 0:
        raise HTTPException(status_code=422, detail="Evolutionary algorithm generated no usable objective data.")

    if isinstance(variables, pl.DataFrame):
        variables = variables.to_dict(as_series=False)
    elif variables is not None:
        variables = jsonable_encoder(variables)

    # The archive is already non-dominated by design; remove duplicated
    # objective vectors so clustering is not distorted by repeated entries.
    objectives = outputs.select(dimensions).unique(maintain_order=True)
    # When using a final population with decision variables, deduplication
    # would break row correspondence. Preserve the original rows in that case.
    if variables is not None:
        objectives = outputs.select(dimensions)
    return objectives, variables


def _make_state(
    problem: Problem,
    data: pl.DataFrame,
    config: SCOREBandsConfig,
    *,
    action: str,
    selected_cluster_id: int | None = None,
    preferred_ranges: dict[str, tuple[float, float]] | None = None,
    saved_bands: list[dict] | None = None,
    optimization: SCOREBandsOptimizationOptions | None = None,
    variable_values: dict | None = None,
) -> SCOREBandsMethodState:
    options = _options(problem, config, data)
    try:
        result = score_json(data=data.select(options.dimensions), options=options)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    state = SCOREBandsMethodState.from_result(result)
    state.action = action
    state.selected_cluster_id = selected_cluster_id
    state.preferred_ranges = jsonable_encoder(preferred_ranges)
    state.saved_bands = jsonable_encoder(saved_bands or [])
    state.optimization_options = jsonable_encoder(optimization) if optimization else None
    state.objective_values = jsonable_encoder(data.to_dict(as_series=False))
    state.variable_values = jsonable_encoder(variable_values)
    return state


def get_score_bands_state(
    data: pl.DataFrame,
    scorebands_options: SCOREBandsConfig,
    relevant_solution_ids: list[int] | None = None,
):
    """Compatibility helper also used by GDM Learning's private exploration."""
    try:
        result = score_json(data=data, options=scorebands_options)
    except (TypeError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SCOREBandsMethodState.from_result(
        result, relevant_solution_ids=relevant_solution_ids
    ), result


def _session_saved_bands(db: Session, problem_id: int, session_id: int) -> list[dict]:
    """Saved bands belong to the session, not only one exploration branch."""
    latest = _latest(db, problem_id, session_id)
    return list(latest.state.saved_bands) if latest is not None else []


def _source_state_id(db: Session, row: StateDB) -> int:
    """Ignore save-only states when referring to an actual band generation."""
    cursor = row
    while cursor.state.action == "save":
        if cursor.parent_id is None:
            raise HTTPException(status_code=500, detail="Save state has no origin.")
        cursor = db.get(StateDB, cursor.parent_id)
        if cursor is None:
            raise HTTPException(status_code=500, detail="Saved band origin not found.")
    return cursor.id


def _persist(
    db: Session,
    *,
    problem_id: int,
    session_id: int,
    parent_id: int | None,
    state: SCOREBandsMethodState,
    kind: StateKind,
) -> StateDB:
    row = StateDB.create(
        database_session=db,
        problem_id=problem_id,
        session_id=session_id,
        parent_id=parent_id,
        state=state,
        kind=kind,
    )
    try:
        db.add(row)
        db.commit()
        db.refresh(row)
    except Exception:
        db.rollback()
        raise
    return row


@router.post("/initialize")
def initialize_or_get_score_bands_method(
    request: SCOREBandsMethodInitializeRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> SCOREBandsMethodResponse:
    problem_db = _problem(user, db, request.problem_id)
    interactive = _session(user, db, request.session_id, create=True)
    current = _latest(db, problem_db.id, interactive.id)
    if current is not None:
        return _response(db, current, interactive.id, initialized=True)

    problem = Problem.from_problemdb(problem_db)

    # Initialization is not a preference-guided search: either cluster the
    # available discrete Pareto approximation, or generate one from an
    # evaluable analytical problem using an unpreferenced evolutionary run.
    effective_optimization = request.optimization_options.model_copy(deep=True)
    has_discrete = problem.discrete_representation is not None

    if effective_optimization.optimize:
        data, variables = _solve(problem, effective_optimization, use_archive=True)
    elif has_discrete:
        data, variables = _discrete_dataset(problem), None
    elif _is_analytical_problem(problem):
        # Automatically optimize; the UI must not require this checkbox to
        # have been selected for an analytical-only problem.
        effective_optimization.optimize = True
        data, variables = _solve(problem, effective_optimization, use_archive=True)
    else:
        raise HTTPException(
            status_code=422,
            detail=(
                "Cannot initialize SCORE Bands: this problem does not supply "
                "a discrete objective dataset or evaluable analytical objectives."
            ),
        )

    state = _make_state(
        problem, data, request.scorebands_options,
        action="initialize", optimization=effective_optimization,
        variable_values=variables,
    )
    saved = _persist(
        db, problem_id=problem_db.id, session_id=interactive.id,
        parent_id=None, state=state, kind=StateKind.SCORE_BANDS_METHOD_INITIALIZE,
    )
    return _response(db, saved, interactive.id, initialized=True)



def _stored_dataset(
    state: SCOREBandsMethodState,
    cluster_id: int | None = None,
) -> tuple[pl.DataFrame, dict | None]:
    """Recover stored solutions, optionally restricting them to one band."""

    if not state.objective_values:
        raise HTTPException(
            status_code=422,
            detail="This iteration has no stored objective values.",
        )

    data = pl.DataFrame(state.objective_values)

    if data.height != len(state.clusters):
        raise HTTPException(
            status_code=500,
            detail="Stored solutions and cluster assignments do not match.",
        )

    variables = state.variable_values

    if cluster_id is None:
        return data, variables

    selected_indices = [
        index
        for index, assigned_cluster in enumerate(state.clusters)
        if assigned_cluster == cluster_id
    ]

    if not selected_indices:
        raise HTTPException(
            status_code=422,
            detail=f"Band {cluster_id} contains no solutions.",
        )

    mask = pl.Series(
        "selected",
        [cluster == cluster_id for cluster in state.clusters],
    )

    filtered_data = data.filter(mask)

    filtered_variables = None

    if variables is not None:
        if any(len(values) != data.height for values in variables.values()):
            raise HTTPException(
                status_code=500,
                detail="Stored decision variables do not match the objective data.",
            )

        filtered_variables = {
            symbol: [values[index] for index in selected_indices]
            for symbol, values in variables.items()
        }

    return filtered_data, filtered_variables

@router.post("/iterate")
def iterate_score_bands_method(
    request: SCOREBandsMethodIterationRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> SCOREBandsMethodResponse:

    problem_db = _problem(user, db, request.problem_id)

    interactive = _session(
        user,
        db,
        request.session_id,
        create=False,
    )

    parent = (
        _require_state(
            db,
            request.parent_state_id,
            problem_db.id,
            interactive.id,
        )
        if request.parent_state_id is not None
        else _latest(db, problem_db.id, interactive.id)
    )

    if parent is None:
        raise HTTPException(
            status_code=400,
            detail="Initialize SCORE Bands before iterating.",
        )

    # If the latest state is a save operation, use its source generation.
    source_id = _source_state_id(db, parent)

    parent = _require_state(
        db,
        source_id,
        problem_db.id,
        interactive.id,
    )

    parent_state = parent.state

    selected_cluster_id = (
        request.preference.cluster_id
        if request.preference is not None
        else None
    )

    # Extract the selected band's ranges if one was selected.
    ranges = None

    if selected_cluster_id is not None:
        band = parent_state.result.bands.get(selected_cluster_id)

        if band is None:
            raise HTTPException(
                status_code=422,
                detail="Selected band does not exist in the parent state.",
            )

        ranges = {
            symbol: (float(bounds[0]), float(bounds[1]))
            for symbol, bounds in band.items()
        }

    problem = Problem.from_problemdb(problem_db)

    # --------------------------------------------
    # STEP 1: Obtain the solutions to cluster
    # --------------------------------------------

    if request.optimization_options.optimize:
        # Generate NEW solutions.
        data, variables = _solve(
            problem,
            request.optimization_options,
            ranges,
            use_archive=(ranges is None),
        )

    else:
        # Reuse EXISTING solutions.
        data, variables = _stored_dataset(
            parent_state,
            cluster_id=selected_cluster_id,
        )

    # --------------------------------------------
    # STEP 2: Apply clustering configuration
    # --------------------------------------------

    config = (
        request.scorebands_options.model_copy(deep=True)
        if request.scorebands_options is not None
        else parent_state.result.options.model_copy(deep=True)
    )

    # Let SCORE Bands calculate data-appropriate scales.
    # Remove this if the user explicitly needs fixed cross-iteration scales.
    config.scales = None

    # Validate dimension-based clustering.
    if config.clustering_algorithm.name == "DimensionCluster":
        dimension = config.clustering_algorithm.dimension_name

        if dimension not in data.columns:
            raise HTTPException(
                status_code=422,
                detail=f"Clustering objective '{dimension}' is unavailable.",
            )

        if config.dimensions is not None and dimension not in config.dimensions:
            raise HTTPException(
                status_code=422,
                detail="Clustering objective must be an included dimension.",
            )

    # --------------------------------------------
    # STEP 3: Generate SCORE Bands and save state
    # --------------------------------------------

    state = _make_state(
        problem,
        data,
        config,
        action="iterate",
        selected_cluster_id=selected_cluster_id,
        preferred_ranges=ranges,
        saved_bands=_session_saved_bands(
            db,
            problem_db.id,
            interactive.id,
        ),
        optimization=request.optimization_options,
        variable_values=variables,
    )

    created = _persist(
        db,
        problem_id=problem_db.id,
        session_id=interactive.id,
        parent_id=parent.id,
        state=state,
        kind=StateKind.SCORE_BANDS_METHOD_ITERATE,
    )

    return _response(
        db,
        created,
        interactive.id,
        initialized=False,
    )

@router.post("/save")
def save_score_band(
    request: SCOREBandsMethodSaveRequest,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
) -> SCOREBandsMethodSaveResponse:
    problem_db = _problem(user, db, request.problem_id)
    interactive = _session(user, db, request.session_id, create=False)
    head = _latest(db, problem_db.id, interactive.id)

    if head is None:
        raise HTTPException(
            status_code=400,
            detail="Initialize SCORE Bands before saving.",
        )

    # Prevent a stale browser tab from replacing newer saved data.
    if (
        request.parent_state_id is not None
        and request.parent_state_id != head.id
    ):
        raise HTTPException(
            status_code=409,
            detail="Session state has changed. Refresh and try again.",
        )

    # The band may come from an older exploration generation.
    source_id = (
        request.source_state_id
        if request.source_state_id is not None
        else _source_state_id(db, head)
    )

    source = _require_state(
        db,
        source_id,
        problem_db.id,
        interactive.id,
    )

    source_id = _source_state_id(db, source)

    source = _require_state(
        db,
        source_id,
        problem_db.id,
        interactive.id,
    )

    band_id = request.preference.cluster_id
    existing_band = source.state.result.bands.get(band_id)

    if request.save and existing_band is None:
        raise HTTPException(
            status_code=422,
            detail="Selected band is not present in the source state.",
        )

    saved = [
        SCOREBandsSavedBand.model_validate(x)
        for x in _session_saved_bands(
            db,
            problem_db.id,
            interactive.id,
        )
    ]

    if request.save:
        if not any(x.source_state_id == source_id and x.cluster_id == band_id for x in saved):
            saved.append(SCOREBandsSavedBand(
                source_state_id=source_id,
                cluster_id=band_id,
                name=request.name,
                preferred_ranges={k: tuple(v) for k, v in existing_band.items()},
            ))
    else:
        saved = [x for x in saved if not (x.cluster_id == band_id and x.source_state_id == source_id)]

    # Save actions copy visualization/population data but are NOT new optimization levels.
    old = head.state

    state = SCOREBandsMethodState.from_result(old.result)
    state.action = "save"
    state.selected_cluster_id = old.selected_cluster_id
    state.preferred_ranges = old.preferred_ranges
    state.optimization_options = old.optimization_options
    state.objective_values = old.objective_values
    state.variable_values = old.variable_values
    state.saved_bands = jsonable_encoder(saved)

    created = _persist(
        db,
        problem_id=problem_db.id,
        session_id=interactive.id,
        parent_id=head.id,
        state=state,
        kind=StateKind.SCORE_BANDS_METHOD_SAVE,
    )
    return SCOREBandsMethodSaveResponse(
        state_id=created.id, session_id=interactive.id, saved_bands=saved,
    )


@router.get("/history")
def score_bands_method_history(
    problem_id: int,
    user: Annotated[User, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_session)],
    session_id: int | None = None,
    head_state_id: int | None = None,
) -> SCOREBandsMethodHistoryResponse:
    problem_db = _problem(user, db, problem_id)
    interactive = _session(user, db, session_id, create=False)
    head = (
        _require_state(db, head_state_id, problem_db.id, interactive.id)
        if head_state_id is not None
        else _latest(db, problem_db.id, interactive.id)
    )
    if head is None:
        return SCOREBandsMethodHistoryResponse(session_id=interactive.id)
    return SCOREBandsMethodHistoryResponse(
        session_id=interactive.id,
        state_id=head.id,
        saved_bands=[SCOREBandsSavedBand.model_validate(x) for x in _session_saved_bands(db, problem_db.id, interactive.id)],
        history=_all_history(
            db,
            problem_db.id,
            interactive.id,
        ),
    )
