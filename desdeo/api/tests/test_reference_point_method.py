"""Tests for Reference Point Method API models and routes."""

import json

import pytest
from fastapi import status
from fastapi.testclient import TestClient
from pydantic import ValidationError

from desdeo.api.models import (
    IntermediateSolutionRequest,
    RPMDeleteSaveRequest,
    RPMDeleteSaveResponse,
    RPMFinalizeRequest,
    RPMFinalizeResponse,
    RPMIntermediateSolutionResponse,
    RPMSaveRequest,
    RPMSaveResponse,
    RPMSolveRequest,
    RPMSolveResponse,
    ReferencePoint,
    SolutionInfo,
)

from .conftest import login, post_json


def test_rpm_request_models_validate_required_fields():
    """RPM request models validate required and optional fields as expected."""
    req = RPMSolveRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={"f_1": 0.4, "f_2": 0.3, "f_3": 0.2}
        ),
    )

    assert req.problem_id == 1
    assert req.session_id is None
    assert req.parent_state_id is None
    assert req.preference.aspiration_levels["f_1"] == 0.4

    with pytest.raises(ValidationError):
        RPMSolveRequest(
            preference=ReferencePoint(
                aspiration_levels={"f_1": 0.4, "f_2": 0.3, "f_3": 0.2}
            )
        )

    save_req = RPMSaveRequest(
        problem_id=1,
        solution_info=[SolutionInfo(state_id=10, solution_index=0, name="candidate")],
    )
    assert len(save_req.solution_info) == 1

    delete_req = RPMDeleteSaveRequest(state_id=10, solution_index=0, problem_id=1)
    assert delete_req.problem_id == 1


def test_rpm_response_models_have_expected_response_types():
    """RPM response models expose the expected fixed response_type fields."""
    solve_response = RPMSolveResponse(
        state_id=1,
        previous_preference=ReferencePoint(
            aspiration_levels={"f_1": 0.5, "f_2": 0.4, "f_3": 0.3}
        ),
        current_solutions=[],
        saved_solutions=[],
        all_solutions=[],
    )
    assert solve_response.response_type == "rpm.solve"

    save_response = RPMSaveResponse(state_id=2)
    assert save_response.response_type == "rpm.save"

    delete_response = RPMDeleteSaveResponse(message="ok")
    assert delete_response.response_type == "rpm.delete_save"


def test_rpm_route_end_to_end_flow(client: TestClient):
    """RPM route flow solve -> save -> intermediate -> finalize -> delete_save works."""
    access_token = login(client)

    solve_request = RPMSolveRequest(
        problem_id=1,
        preference=ReferencePoint(
            aspiration_levels={"f_1": 0.45, "f_2": 0.35, "f_3": 0.25}
        ),
    )

    raw_solve = post_json(
        client, "/method/rpm/solve", solve_request.model_dump(), access_token
    )
    assert raw_solve.status_code == status.HTTP_200_OK

    solve_response: RPMSolveResponse = RPMSolveResponse.model_validate(
        json.loads(raw_solve.content)
    )
    assert solve_response.state_id is not None
    assert solve_response.response_type == "rpm.solve"
    assert len(solve_response.current_solutions) > 0

    save_request = RPMSaveRequest(
        problem_id=1,
        parent_state_id=solve_response.state_id,
        solution_info=[
            SolutionInfo(
                state_id=solve_response.state_id,
                solution_index=0,
                name="saved candidate",
            ),
            # duplicate save for same origin+index updates name instead of creating duplicate
            SolutionInfo(
                state_id=solve_response.state_id,
                solution_index=0,
                name="saved candidate renamed",
            ),
        ],
    )

    raw_save = post_json(
        client, "/method/rpm/save", save_request.model_dump(), access_token
    )
    assert raw_save.status_code == status.HTTP_200_OK

    save_response: RPMSaveResponse = RPMSaveResponse.model_validate(
        json.loads(raw_save.content)
    )
    assert save_response.state_id is not None

    second_solve_request = RPMSolveRequest(
        problem_id=1,
        parent_state_id=save_response.state_id,
        preference=ReferencePoint(
            aspiration_levels={"f_1": 0.55, "f_2": 0.25, "f_3": 0.35}
        ),
    )
    raw_second_solve = post_json(
        client,
        "/method/rpm/solve",
        second_solve_request.model_dump(),
        access_token,
    )
    assert raw_second_solve.status_code == status.HTTP_200_OK

    second_solve_response = RPMSolveResponse.model_validate(
        json.loads(raw_second_solve.content)
    )
    assert len(second_solve_response.saved_solutions) == 1
    assert len(second_solve_response.all_solutions) >= len(
        second_solve_response.current_solutions
    )

    intermediate_request = IntermediateSolutionRequest(
        problem_id=1,
        parent_state_id=second_solve_response.state_id,
        num_desired=1,
        reference_solution_1=SolutionInfo(
            state_id=second_solve_response.state_id, solution_index=0
        ),
        reference_solution_2=SolutionInfo(
            state_id=second_solve_response.state_id, solution_index=1
        ),
    )
    raw_intermediate = post_json(
        client,
        "/method/rpm/intermediate",
        intermediate_request.model_dump(),
        access_token,
    )
    assert raw_intermediate.status_code == status.HTTP_200_OK

    intermediate_response = RPMIntermediateSolutionResponse.model_validate(
        json.loads(raw_intermediate.content)
    )
    assert intermediate_response.response_type == "rpm.intermediate"
    assert len(intermediate_response.current_solutions) == 1

    finalize_request = RPMFinalizeRequest(
        problem_id=1,
        parent_state_id=second_solve_response.state_id,
        solution_info=SolutionInfo(
            state_id=second_solve_response.state_id, solution_index=0
        ),
    )
    raw_finalize = post_json(
        client, "/method/rpm/finalize", finalize_request.model_dump(), access_token
    )
    assert raw_finalize.status_code == status.HTTP_200_OK

    finalize_response: RPMFinalizeResponse = RPMFinalizeResponse.model_validate(
        json.loads(raw_finalize.content)
    )
    assert finalize_response.state_id is not None
    assert finalize_response.response_type == "rpm.finalize"
    assert finalize_response.final_solution.state_id == second_solve_response.state_id

    delete_request = RPMDeleteSaveRequest(
        state_id=solve_response.state_id,
        solution_index=0,
        problem_id=1,
    )
    raw_delete = post_json(
        client, "/method/rpm/delete_save", delete_request.model_dump(), access_token
    )
    assert raw_delete.status_code == status.HTTP_200_OK

    delete_response = RPMDeleteSaveResponse.model_validate(
        json.loads(raw_delete.content)
    )
    assert delete_response.message == "Save deleted."

    # second deletion should fail because the save no longer exists
    raw_delete_again = post_json(
        client, "/method/rpm/delete_save", delete_request.model_dump(), access_token
    )
    assert raw_delete_again.status_code == status.HTTP_404_NOT_FOUND
