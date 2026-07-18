import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


async def _create_job(client: AsyncClient) -> int:
    response = await client.post("/api/v1/jobs", json={"title": "Job", "company": "Co"})
    return response.json()["id"]


async def test_create_application_for_job(client: AsyncClient) -> None:
    job_id = await _create_job(client)

    response = await client.post(
        "/api/v1/applications", json={"job_id": job_id, "notes": "Applied via referral"}
    )
    assert response.status_code == 201
    body = response.json()
    assert body["job_id"] == job_id
    assert body["status"] == "draft"


async def test_update_application_status(client: AsyncClient) -> None:
    job_id = await _create_job(client)
    create_response = await client.post("/api/v1/applications", json={"job_id": job_id})
    application_id = create_response.json()["id"]

    update_response = await client.patch(
        f"/api/v1/applications/{application_id}", json={"status": "interview"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["status"] == "interview"


async def test_create_application_invalid_status(client: AsyncClient) -> None:
    job_id = await _create_job(client)
    response = await client.post("/api/v1/applications", json={"job_id": job_id, "status": "not_a_status"})
    assert response.status_code == 422


async def test_delete_application(client: AsyncClient) -> None:
    job_id = await _create_job(client)
    create_response = await client.post("/api/v1/applications", json={"job_id": job_id})
    application_id = create_response.json()["id"]

    delete_response = await client.delete(f"/api/v1/applications/{application_id}")
    assert delete_response.status_code == 204

    get_response = await client.get(f"/api/v1/applications/{application_id}")
    assert get_response.status_code == 404
