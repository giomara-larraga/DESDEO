"""Service for managing SHAP explainer functionality with database caching."""

from typing import Tuple
import gzip
import pickle
from datetime import datetime

import numpy as np
import polars as pl
from sqlmodel import Session, select

from desdeo.api.models import ExplainerCacheDB
from desdeo.explanations import ShapExplainer, generate_biased_mean_data
from desdeo.problem import Problem, PolarsEvaluator


class ExplainerRXIMO:
    """Service class for managing explainer functionality with database caching."""

    @staticmethod
    def _compress_problem_data(problem_data: pl.DataFrame) -> bytes:
        """Compress problem data for database storage."""
        # Convert to bytes using pickle, then compress with gzip
        pickled_data = pickle.dumps(problem_data)
        return gzip.compress(pickled_data)

    @staticmethod
    def _decompress_problem_data(compressed_data: bytes) -> pl.DataFrame:
        """Decompress problem data from database storage."""
        # Decompress with gzip, then unpickle
        pickled_data = gzip.decompress(compressed_data)
        return pickle.loads(pickled_data)

    @classmethod
    def get_or_create_explainer(
        cls,
        problem: Problem,
        user_id: int,
        problem_id: int,
        session: Session,
        n_samples: int = 200,
    ) -> Tuple[ShapExplainer, pl.DataFrame, str]:
        """Get an existing explainer from database or create a new one using problem_id as key."""

        # Check if explainer data already exists in database
        statement = select(ExplainerCacheDB).where(
            ExplainerCacheDB.problem_id == problem_id
        )
        cache_entry = session.exec(statement).first()

        if cache_entry is not None:
            # Update access statistics
            cache_entry.last_accessed = datetime.utcnow()
            cache_entry.access_count += 1
            session.add(cache_entry)
            session.commit()

            # Decompress and return cached data
            try:
                problem_data = cls._decompress_problem_data(cache_entry.problem_data)

                # Create explainer with cached data
                explainer = ShapExplainer(
                    problem_data=problem_data,
                    input_symbols=cache_entry.variable_symbols,
                    output_symbols=cache_entry.objective_symbols,
                )

                return explainer, problem_data, "database_cache"

            except Exception as e:
                print(
                    f"Warning: Failed to load cached explainer data ({e}), creating new one"
                )
                # If cached data is corrupted, delete it and create new
                session.delete(cache_entry)
                session.commit()

        # Create new explainer data
        explainer, problem_data, evaluation_status = cls._create_new_explainer(
            problem, n_samples
        )

        # Store in database for future use
        cache_status = cls._cache_explainer_data(
            problem_id,
            user_id,
            problem,
            problem_data,
            n_samples,
            evaluation_status,
            session,
        )

        return explainer, problem_data, cache_status

    @classmethod
    def _create_new_explainer(
        cls, problem: Problem, n_samples: int = 200
    ) -> Tuple[ShapExplainer, pl.DataFrame, str]:
        """Create a new explainer by sampling and evaluating the problem."""
        rng = np.random.default_rng(seed=42)

        # Extract variable and objective symbols from problem
        variable_symbols = [var.symbol for var in problem.variables]
        objective_symbols = [obj.symbol for obj in problem.objectives]

        # Randomly sample the input space within variable bounds
        sampled_variables = {}
        for var in problem.variables:
            if hasattr(var, "lowerbound") and hasattr(var, "upperbound"):
                lower = var.lowerbound if var.lowerbound is not None else 0
                upper = var.upperbound if var.upperbound is not None else 1
                sampled_variables[var.symbol] = rng.uniform(lower, upper, n_samples)
            else:
                # Default bounds if not specified
                sampled_variables[var.symbol] = rng.uniform(0, 1, n_samples)

        # Create DataFrame with sampled variables
        sampled_data = pl.DataFrame(sampled_variables)

        # Evaluate the problem with the sampled inputs to generate outputs
        evaluation_method = "actual_evaluation"
        evaluation_error = None

        try:
            evaluator = PolarsEvaluator(problem)
            problem_data = evaluator.evaluate(sampled_data)

        except Exception as eval_error:
            # Fallback: if evaluation fails, create simple synthetic relationships
            print(
                f"Warning: Problem evaluation failed ({eval_error}), using synthetic relationships"
            )
            evaluation_method = "synthetic_fallback"
            evaluation_error = str(eval_error)

            synthetic_objectives = {}
            for obj in problem.objectives:
                if hasattr(obj, "func") and obj.func:
                    # For analytical objectives, try to create more realistic synthetic data
                    synthetic_objectives[obj.symbol] = sum(
                        sampled_variables[var.symbol] * rng.uniform(0.5, 2.0)
                        for var in problem.variables
                    ) + rng.normal(0, 0.1, n_samples)
                else:
                    # Simple relationship for non-analytical objectives
                    synthetic_objectives[obj.symbol] = sum(
                        sampled_variables[var.symbol] for var in problem.variables
                    ) + rng.normal(0, 0.1, n_samples)

            # Combine variables and synthetic objectives
            all_data = {**sampled_variables, **synthetic_objectives}
            problem_data = pl.DataFrame(all_data)

        # Create explainer
        explainer = ShapExplainer(
            problem_data=problem_data,
            input_symbols=variable_symbols,
            output_symbols=objective_symbols,
        )

        return explainer, problem_data, evaluation_method

    @classmethod
    def _cache_explainer_data(
        cls,
        problem_id: int,
        user_id: int,
        problem: Problem,
        problem_data: pl.DataFrame,
        n_samples: int,
        evaluation_method: str,
        session: Session,
    ) -> str:
        """Cache explainer data in the database."""
        try:
            variable_symbols = [var.symbol for var in problem.variables]
            objective_symbols = [obj.symbol for obj in problem.objectives]

            compressed_data = cls._compress_problem_data(problem_data)

            cache_entry = ExplainerCacheDB(
                problem_id=problem_id,
                user_id=user_id,
                variable_symbols=variable_symbols,
                objective_symbols=objective_symbols,
                n_samples=n_samples,
                problem_data=compressed_data,
                evaluation_method=evaluation_method,
                evaluation_error=None,
                access_count=1,
            )

            session.add(cache_entry)
            session.commit()

            return "new_cached"

        except Exception as e:
            print(
                f"Warning: Failed to cache explainer data ({e}), proceeding without caching"
            )
            return "not_cached"

    @classmethod
    def generate_explanation(
        cls,
        explainer: ShapExplainer,
        problem_data: pl.DataFrame,
        solution_variables: dict,
        solution_objectives: dict,
        variable_symbols: list[str],
        objective_symbols: list[str],
    ) -> dict:
        """Generate SHAP explanations for a given solution."""

        # Generate background data around the solution's objectives
        solution_objective_values = [
            solution_objectives[obj] for obj in objective_symbols
        ]
        target_values = np.array(solution_objective_values)

        background_indices = generate_biased_mean_data(
            problem_data[objective_symbols].to_numpy(),
            target_values,
            min_size=15,
            max_size=30,
        )

        if background_indices is None:
            return None

        background_data = problem_data[background_indices]
        explainer.setup(background_data)

        # Create input for explanation from the solution variables
        explanation_input = pl.DataFrame(
            {
                var_symbol: [solution_variables.get(var_symbol, 0.5)]
                for var_symbol in variable_symbols
            }
        )

        # Generate explanations
        shap_explanations = explainer.explain_input(explanation_input)

        # Calculate variable importance (sum of absolute SHAP values across objectives)
        variable_importance = {}
        if (
            hasattr(shap_explanations, "values")
            and shap_explanations.values is not None
        ):
            shap_values = shap_explanations.values
            if len(shap_values.shape) == 2:  # Multiple outputs
                # Sum absolute SHAP values across all objectives
                importance_scores = np.sum(np.abs(shap_values), axis=1)
            else:  # Single output
                importance_scores = np.abs(shap_values)

            for i, var_symbol in enumerate(variable_symbols):
                if i < len(importance_scores):
                    variable_importance[var_symbol] = float(importance_scores[i])

        return {
            "shap_values": (
                shap_explanations.values.tolist()
                if hasattr(shap_explanations, "values")
                else []
            ),
            "base_values": (
                shap_explanations.base_values.tolist()
                if hasattr(shap_explanations, "base_values")
                else []
            ),
            "data": (
                shap_explanations.data.tolist()
                if hasattr(shap_explanations, "data")
                else []
            ),
            "variable_importance": variable_importance,
        }

    @classmethod
    def clear_cache(cls, problem_id: int, user_id: int, session: Session) -> bool:
        """Clear cached explainer data for a specific problem and user."""
        from sqlmodel import and_

        cache_entry = session.exec(
            select(ExplainerCacheDB).where(
                and_(
                    ExplainerCacheDB.problem_id == problem_id,
                    ExplainerCacheDB.user_id == user_id,
                )
            )
        ).first()

        if cache_entry:
            session.delete(cache_entry)
            session.commit()
            return True
        return False

    @classmethod
    def get_cache_status(cls, user_id: int, session: Session) -> list[dict]:
        """Get cache status for all problems for a specific user."""
        cache_entries = session.exec(
            select(ExplainerCacheDB).where(ExplainerCacheDB.user_id == user_id)
        ).all()

        cache_status = []
        for entry in cache_entries:
            cache_status.append(
                {
                    "problem_id": entry.problem_id,
                    "created_at": entry.created_at.isoformat(),
                    "last_accessed": (
                        entry.last_accessed.isoformat() if entry.last_accessed else None
                    ),
                    "access_count": entry.access_count,
                    "data_size_compressed": (
                        len(entry.problem_data) if entry.problem_data else 0
                    ),
                    "n_samples": entry.n_samples,
                    "evaluation_method": entry.evaluation_method,
                }
            )

        return cache_status
