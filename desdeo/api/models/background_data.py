"""Models for storing explainer background datasets."""

from typing import TYPE_CHECKING

from pydantic import model_validator
from sqlmodel import JSON, Column, Field, Relationship, SQLModel

if TYPE_CHECKING:
    from .problem import ProblemDB


class ProblemBackgroundDatasetLink(SQLModel, table=True):
    """Link table associating problems and background datasets."""

    problem_id: int | None = Field(
        foreign_key="problemdb.id",
        primary_key=True,
        default=None,
    )
    background_dataset_id: int | None = Field(
        foreign_key="backgrounddatasetdb.id",
        primary_key=True,
        default=None,
    )


class BackgroundDatasetBase(SQLModel):
    """Base model for storing background data used by explainers."""

    name: str | None = Field(default=None)
    kind: str = Field(default="rximo_background")
    num_samples: int = Field(gt=0)
    preference_values: dict[str, list[float]] | None = Field(sa_column=Column(JSON), default=None)
    objective_values: dict[str, list[float]] = Field(sa_column=Column(JSON))

    @model_validator(mode="after")
    def validate_sample_shapes(self):
        """Ensure all stored columns have a consistent number of samples."""
        datasets = {
            "preference_values": self.preference_values,
            "objective_values": self.objective_values,
        }

        for dataset_name, dataset in datasets.items():
            if dataset is None:
                continue

            for symbol, values in dataset.items():
                if len(values) != self.num_samples:
                    raise ValueError(f"{dataset_name}.{symbol} has {len(values)} samples, expected {self.num_samples}.")

        return self


class BackgroundDatasetCreateRequest(BackgroundDatasetBase):
    """Request model for creating a background dataset entry."""

    problem_ids: list[int]

    @model_validator(mode="after")
    def validate_problem_ids(self):
        """Ensure at least one unique linked problem is provided."""
        if not self.problem_ids:
            raise ValueError("problem_ids must contain at least one problem id.")

        if len(set(self.problem_ids)) != len(self.problem_ids):
            raise ValueError("problem_ids must not contain duplicates.")

        return self


class BackgroundDatasetInfo(BackgroundDatasetBase):
    """Response model for background dataset entries."""

    id: int
    problem_ids: list[int]


class BackgroundDatasetExplainRequest(SQLModel):
    """Request for explaining a DM reference point with a stored background dataset."""

    problem_id: int
    background_dataset_id: int
    reference_point: dict[str, float]
    target_objective_symbol: str | None = Field(default=None)

    # See `RXIMOExplainRequest.current_solution`: serves both as the
    # SHAP single-point baseline (so each SHAP value captures the
    # aspiration-gap contribution) and as the exact solution fed into
    # `find_rival`'s case-1..9 selection.
    current_solution: dict[str, float] | None = Field(sa_column=Column(JSON), default=None)


class BackgroundDatasetExplainResponse(SQLModel):
    """SHAP explanation response for a single reference point."""

    problem_id: int
    background_dataset_id: int
    input_symbols: list[str]
    output_symbols: list[str]
    reference_point: dict[str, float]
    explained_objective_values: dict[str, float]
    base_values: dict[str, float]
    shap_values: dict[str, dict[str, float]]
    rximo_results: dict[str, dict] | None = Field(sa_column=Column(JSON), default=None)


class BackgroundDatasetDB(BackgroundDatasetBase, table=True):
    """Database model for explainer background datasets."""

    id: int | None = Field(primary_key=True, default=None)

    problems: list["ProblemDB"] = Relationship(
        back_populates="background_datasets",
        link_model=ProblemBackgroundDatasetLink,
    )
