import time
import uuid

import mock
import pytest

pytestmark = [pytest.mark.acceptance, pytest.mark.api, pytest.mark.jobs]


def test_it_gets_jobs(api_client, jobs_endpoint, job_factory, stack):
    # Arrange
    job_id = job_factory()["Id"]
    # Act
    response = api_client.get("{}/{}".format(jobs_endpoint, job_id))
    response_body = response.json()
    # Assert
    assert response.status_code == 200
    assert {
        "Id": job_id,
        "Sk": job_id,
        "Type": "Job",
        "JobStatus": mock.ANY,
        "GSIBucket": mock.ANY,
        "CreatedAt": mock.ANY,
    } == response_body
    assert response.headers.get("Access-Control-Allow-Origin") == stack["APIAccessControlAllowOriginHeader"]


def test_it_handles_unknown_jobs(api_client, jobs_endpoint, stack):
    # Arrange
    job_id = "invalid"
    # Act
    response = api_client.get("{}/{}".format(jobs_endpoint, job_id))
    # Assert
    assert response.status_code == 404
    assert response.headers.get("Access-Control-Allow-Origin") == stack["APIAccessControlAllowOriginHeader"]


def test_it_lists_jobs_by_date(api_client, jobs_endpoint, job_factory, stack, sf_client):
    # Arrange
    job_id_1 = job_factory(job_id=str(uuid.uuid4()), created_at=1576861489)["Id"]
    job_id_2 = job_factory(job_id=str(uuid.uuid4()), created_at=1576861490)["Id"]
    time.sleep(1)  # No item waiter therefore wait for gsi propagation
    execution_arn_1 = "{}:{}".format(stack["StateMachineArn"].replace("stateMachine", "execution"), job_id_1)
    execution_arn_2 = "{}:{}".format(stack["StateMachineArn"].replace("stateMachine", "execution"), job_id_2)
    try:
        # Act
        response = api_client.get(jobs_endpoint)
        response_body = response.json()
        # Assert
        assert response.status_code == 200
        assert {
            "Id": job_id_2,
            "Sk": job_id_2,
            "Type": "Job",
            "JobStatus": mock.ANY,
            "GSIBucket": mock.ANY,
            "CreatedAt": mock.ANY,
        } == response_body["Jobs"][0]
        assert {
            "Id": job_id_1,
            "Sk": job_id_1,
            "Type": "Job",
            "JobStatus": mock.ANY,
            "GSIBucket": mock.ANY,
            "CreatedAt": mock.ANY,
        } == response_body["Jobs"][1]
        assert response.headers.get("Access-Control-Allow-Origin") == stack["APIAccessControlAllowOriginHeader"]
    finally:
        sf_client.stop_execution(executionArn=execution_arn_1)
        sf_client.stop_execution(executionArn=execution_arn_2)


def test_it_lists_job_events_by_date(api_client, jobs_endpoint, job_factory, job_event_factory, stack, sf_client):
    # Arrange
    job_id = str(uuid.uuid4())
    job_id = job_factory(job_id=job_id, created_at=1576861489)["Id"]
    job_event_factory(job_id, "AnEvent", {})
    job_event_factory(job_id, "AnEvent", {})
    execution_arn = "{}:{}".format(stack["StateMachineArn"].replace("stateMachine", "execution"), job_id)
    try:
        # Act
        response = api_client.get("{}/{}/events".format(jobs_endpoint, job_id))
        response_body = response.json()
        # Assert
        assert response.status_code == 200
        assert 2 == len(response_body["JobEvents"])
        assert response.headers.get("Access-Control-Allow-Origin") == stack["APIAccessControlAllowOriginHeader"]
    finally:
        sf_client.stop_execution(executionArn=execution_arn)


def test_it_updates_job_in_response_to_events(job_factory, job_event_factory, job_table, stack, sf_client):
    job_id = job_factory()["Id"]
    execution_arn = "{}:{}".format(stack["StateMachineArn"].replace("stateMachine", "execution"), job_id)
    try:
        job_event_factory(job_id, "FindPhaseFailed", {})
        time.sleep(5)  # No item waiter therefore wait for stream processor
        item = job_table.get_item(Key={"Id": job_id, "Sk": job_id})["Item"]
        assert "FIND_FAILED" == item["JobStatus"]
    finally:
        sf_client.stop_execution(executionArn=execution_arn)


def test_it_locks_job_status_for_failed_jobs(job_factory, job_event_factory, job_table, stack, sf_client):
    job_id = job_factory(JobStatus="FAILED")["Id"]
    execution_arn = "{}:{}".format(stack["StateMachineArn"].replace("stateMachine", "execution"), job_id)
    try:
        job_event_factory(job_id, "JobSucceeded", {})
        time.sleep(5)  # No item waiter therefore wait for stream processor
        item = job_table.get_item(Key={"Id": job_id, "Sk": job_id})["Item"]
        assert "FAILED" == item["JobStatus"]
    finally:
        sf_client.stop_execution(executionArn=execution_arn)
