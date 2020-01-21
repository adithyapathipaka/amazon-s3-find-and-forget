import datetime
import decimal
import json
from types import SimpleNamespace

import mock
import pytest
from mock import patch, ANY

from backend.lambdas.jobs import handlers

pytestmark = [pytest.mark.unit, pytest.mark.api, pytest.mark.jobs]


@patch("backend.lambdas.jobs.handlers.table")
def test_it_retrieves_jobs(table):
    mock_job = {"Id": "test"}
    table.get_item.return_value = {
        "Item": mock_job
    }
    response = handlers.get_job_handler({
        "pathParameters": {"job_id": "test"}
    }, SimpleNamespace())

    assert 200 == response["statusCode"]
    assert mock_job == json.loads(response["body"])
    assert ANY == response["headers"]


@patch("backend.lambdas.jobs.handlers.table")
def test_it_retrieves_returns_job_not_found(table):
    table.get_item.return_value = {}
    response = handlers.get_job_handler({
        "pathParameters": {"job_id": "test"}
    }, SimpleNamespace())

    assert 404 == response["statusCode"]
    assert ANY == response["headers"]


@patch("backend.lambdas.jobs.handlers.table")
def test_it_lists_jobs(table):
    stub = job_stub()
    table.query.return_value = {"Items": [stub]}
    response = handlers.list_jobs_handler({}, SimpleNamespace())
    resp_body = json.loads(response["body"])
    assert 200 == response["statusCode"]
    assert 1 == len(resp_body["Jobs"])
    assert stub == resp_body["Jobs"][0]


@patch("backend.lambdas.jobs.handlers.bucket_count", 3)
@patch("backend.lambdas.jobs.handlers.table")
def test_it_queries_all_gsi_buckets(table):
    stub = job_stub()
    table.query.return_value = {"Items": [stub]}
    handlers.list_jobs_handler({}, SimpleNamespace())
    assert 3 == table.query.call_count


@patch("backend.lambdas.jobs.handlers.Key")
@patch("backend.lambdas.jobs.handlers.table")
def test_it_handles_list_job_start_at_qs(table, k):
    stub = job_stub()
    table.query.return_value = {"Items": [stub]}
    handlers.list_jobs_handler({"queryStringParameters": {"start_at": "12345"}}, SimpleNamespace())
    k.assert_called_with("CreatedAt")
    k().lt.assert_called_with(12345)


@patch("backend.lambdas.jobs.handlers.table")
def test_it_respects_list_job_page_size(table):
    stub = job_stub()
    table.query.return_value = {"Items": [stub for _ in range(0, 3)]}
    handlers.list_jobs_handler({"queryStringParameters": {"page_size": 3}}, SimpleNamespace())
    table.query.assert_called_with(
        IndexName=ANY,
        KeyConditionExpression=ANY,
        ScanIndexForward=ANY,
        Limit=3,
    )


@patch("backend.lambdas.jobs.handlers.bucket_count", 3)
@patch("backend.lambdas.jobs.handlers.table")
def test_it_respects_list_job_page_size_with_multiple_buckets(table):
    table.query.return_value = {"Items": [job_stub() for _ in range(0, 5)]}
    resp = handlers.list_jobs_handler({"queryStringParameters": {"page_size": 5}}, SimpleNamespace())
    assert 3 == table.query.call_count
    assert 5 == len(json.loads(resp["body"])["Jobs"])


@patch("backend.lambdas.jobs.handlers.table")
def test_it_lists_jobs_events(table):
    stub = job_event_stub()
    table.query.return_value = {"Items": [stub]}
    response = handlers.list_job_events_handler({"pathParameters": {"job_id": "test"}}, SimpleNamespace())
    resp_body = json.loads(response["body"])
    assert 200 == response["statusCode"]
    assert 1 == len(resp_body["JobEvents"])
    assert stub == resp_body["JobEvents"][0]


@patch("backend.lambdas.jobs.handlers.table")
def test_it_paginates_jobs_events(table):
    stub = job_event_stub()
    table.query.return_value = {"Items": [stub for _ in range(0, 3)]}
    response = handlers.list_job_events_handler({
        "pathParameters": {"job_id": "test"},
        "queryStringParameters": {"page_size": 3},
    }, SimpleNamespace())
    resp_body = json.loads(response["body"])
    assert 200 == response["statusCode"]
    assert 3 == len(resp_body["JobEvents"])
    assert isinstance(resp_body["NextStart"], int)
    table.query.assert_called_with(
        KeyConditionExpression=mock.ANY,
        ScanIndexForward=False,
        Limit=3,
        FilterExpression=mock.ANY,
        ExpressionAttributeNames=mock.ANY,
        ExpressionAttributeValues=mock.ANY
    )


@patch("backend.lambdas.jobs.handlers.table")
@patch("backend.lambdas.jobs.handlers.Key")
def test_it_handles_job_event_start_at(k, table):
    stub = job_event_stub()
    table.query.return_value = {"Items": [stub]}
    response = handlers.list_job_events_handler({
        "pathParameters": {"job_id": "test"},
        "queryStringParameters": {"start_at": "123456"},
    }, SimpleNamespace())
    resp_body = json.loads(response["body"])
    assert 200 == response["statusCode"]
    assert "NextStart" in resp_body
    k.assert_called_with("Sk")
    k().lt.assert_called_with("123456")


def job_stub(job_id="test", created_at=round(datetime.datetime.utcnow().timestamp()), **kwargs):
    return {"Id": job_id, "Sk": job_id, "CreatedAt": created_at, "Type": "Job", **kwargs}


def job_event_stub(job_id="test", sk=None, **kwargs):
    now = round(datetime.datetime.utcnow().timestamp())
    if not sk:
        sk = "{}#{}".format(str(now), "12345")
    return {"Id": job_id, "Sk": sk, "Type": "JobEvent", "CreatedAt": now, **kwargs}
