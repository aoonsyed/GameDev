import json

from game.logic.progress import SaveData
from game.logic.skins import DEFAULT_SKIN
from game.storage import SAVE_KEY, Storage


def stats(score=0, gems=0, near=0, mult=1):
    return {"score": score, "gems": gems, "near_misses": near, "best_multiplier": mult, "jumps": score}


# --- SaveData ----------------------------------------------------------------
def test_round_trip():
    save = SaveData(best=42, gems=7, skin="acid", owned=["pulse", "acid"],
                    missions_done=["score_10"], daily_date="2026-10-01", daily_best=9,
                    runs=3, sound=False, shake=False)
    assert SaveData.from_dict(json.loads(json.dumps(save.to_dict()))) == save


def test_from_garbage_gives_defaults():
    for junk in (None, [], "x", 5, {"best": "lots", "gems": -3, "sound": "yes", "owned": "acid"}):
        assert SaveData.from_dict(junk) == SaveData()


def test_from_dict_sanitises_skins():
    save = SaveData.from_dict({"owned": ["acid", "acid", "hacked"], "skin": "hacked"})
    assert save.owned == [DEFAULT_SKIN, "acid"]
    assert save.skin == DEFAULT_SKIN
    assert SaveData.from_dict({"owned": ["acid"], "skin": "acid"}).skin == "acid"


def test_bools_are_not_numbers():
    assert SaveData.from_dict({"best": True}).best == 0


def test_record_run_new_best_and_gems():
    save = SaveData(best=5)
    res = save.record_run(stats(score=8, gems=3))
    assert res.new_best and save.best == 8
    assert save.runs == 1
    assert res.gems_earned == 3 and save.gems == 3
    assert not save.record_run(stats(score=8)).new_best


def test_record_run_completes_missions_once():
    save = SaveData()
    res = save.record_run(stats(score=12))
    assert [m.id for m in res.missions] == ["score_10"]
    assert res.gems_earned == 10
    assert save.record_run(stats(score=12)).missions == []


def test_daily_best_resets_each_day():
    save = SaveData()
    assert save.record_run(stats(score=5), daily="2026-10-01").daily_new_best
    assert not save.record_run(stats(score=3), daily="2026-10-01").daily_new_best
    assert save.daily_best_for("2026-10-01") == 5
    assert save.daily_best_for("2026-10-02") == 0
    assert save.record_run(stats(score=1), daily="2026-10-02").daily_new_best
    assert save.daily_best == 1


def test_normal_runs_leave_daily_alone():
    save = SaveData(daily_date="2026-10-01", daily_best=4)
    save.record_run(stats(score=50))
    assert save.daily_best == 4


# --- Storage -----------------------------------------------------------------
def test_storage_round_trip(tmp_path):
    path = tmp_path / "sub" / "save.json"
    store = Storage(path, web=False)
    assert store.load() == SaveData()
    data = SaveData(best=11, gems=4)
    assert store.save(data)
    assert Storage(path, web=False).load() == data
    assert not path.with_suffix(".tmp").exists()


def test_storage_survives_corrupt_file(tmp_path):
    path = tmp_path / "save.json"
    path.write_text("{not json", encoding="utf-8")
    assert Storage(path, web=False).load() == SaveData()


def test_storage_reports_write_failure(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    assert not Storage(blocker / "save.json", web=False).save(SaveData())


def test_storage_env_override(tmp_path, monkeypatch):
    monkeypatch.setenv("ORBIT_HOP_SAVE", str(tmp_path / "env.json"))
    assert Storage(web=False).path == tmp_path / "env.json"


def test_web_storage_uses_local_storage(monkeypatch):
    """On the web, pygbag exposes the browser through `platform.window`."""
    import platform

    class LocalStorage(dict):
        def getItem(self, k):
            return self.get(k)

        def setItem(self, k, v):
            self[k] = v

    window = type("Window", (), {"localStorage": LocalStorage()})()
    monkeypatch.setattr(platform, "window", window, raising=False)
    store = Storage(web=True)
    assert store.load() == SaveData()
    assert store.save(SaveData(best=3))
    assert SAVE_KEY in window.localStorage
    assert store.load().best == 3
