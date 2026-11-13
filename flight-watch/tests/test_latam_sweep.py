from datetime import date

from flightwatch import config, dates, latam_sweep


def test_rotate_wraps_and_resumes(tmp_path, monkeypatch):
    monkeypatch.setattr(latam_sweep, "STATE", tmp_path / "state.json")
    trips = dates.trip_dates(config.load(), date(2026, 11, 13))
    assert latam_sweep.rotate(trips, 3) == trips[:3]          # sem cursor: começa do início
    latam_sweep.save_cursor(trips[5].outbound.isoformat())
    assert latam_sweep.rotate(trips, 3) == trips[5:8]
    latam_sweep.save_cursor(trips[-1].outbound.isoformat())
    got = latam_sweep.rotate(trips, 3)
    assert got[0].outbound == trips[-1].outbound and got[-1] == trips[1]  # dá a volta
    latam_sweep.save_cursor("2099-01-01")                       # cursor além do fim
    assert latam_sweep.rotate(trips, 2) == trips[:2]
