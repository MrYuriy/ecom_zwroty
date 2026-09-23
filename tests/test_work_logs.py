URL = "/api/work-logs"
DAY = "2026-09-22"


async def test_one_entry_per_day_is_overwritten(client, operator_headers):
    first = await client.put(f"{URL}/{DAY}", json={"minutes": 90}, headers=operator_headers)
    assert first.status_code == 200
    assert first.json() == {"work_date": DAY, "minutes": 90, "author_name": "operator"}

    await client.put(f"{URL}/{DAY}", json={"minutes": 120}, headers=operator_headers)

    listed = (await client.get(URL, headers=operator_headers)).json()
    assert listed["total"] == 1
    assert listed["items"][0]["minutes"] == 120


async def test_unknown_day_is_404_and_minutes_are_validated(client, operator_headers):
    assert (await client.get(f"{URL}/2020-01-02", headers=operator_headers)).status_code == 404
    assert (await client.delete(f"{URL}/2020-01-02", headers=operator_headers)).status_code == 404
    assert (await client.put(f"{URL}/{DAY}", json={"minutes": -5}, headers=operator_headers)).status_code == 422
    assert (await client.put(f"{URL}/{DAY}", json={"minutes": 2000}, headers=operator_headers)).status_code == 422


async def test_entry_is_deleted(client, operator_headers):
    await client.put(f"{URL}/{DAY}", json={"minutes": 30}, headers=operator_headers)
    assert (await client.delete(f"{URL}/{DAY}", headers=operator_headers)).status_code == 204
    assert (await client.get(URL, headers=operator_headers)).json()["total"] == 0


async def test_work_logs_need_a_login(client):
    assert (await client.get(URL)).status_code == 401
    assert (await client.put(f"{URL}/{DAY}", json={"minutes": 10})).status_code == 401
