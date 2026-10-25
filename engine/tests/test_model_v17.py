"""Study method v1.7 (ADR-0006, #78): what the model now writes so the factory floor can answer « where does
data go » and « what do I change, where », each setting checked against the code it cites."""

import copy
import json
from pathlib import Path

import pytest

from umbra_engine.analysis.method import SCHEMA, UPDATE, study_prompt
from umbra_engine.analysis.model import MAX_SHORT, checked_model, updated_model

FIXTURES = Path(__file__).parent / "fixtures"
WATCHDOG = FIXTURES / "watchdog"
UI_FIXTURES = Path(__file__).parents[2] / "ui" / "test-fixtures"
AUTH = "watchdog_ai/api/middleware/tenant_auth.py"
SCHEMAS = "watchdog_ai/ingestion/schemas.py"


def texts() -> dict[str, str]:
    """The guard-released texts of the Watchdog files (what write_mirror returns)."""
    return {
        p.relative_to(WATCHDOG).as_posix(): p.read_text(encoding="utf-8")
        for p in WATCHDOG.rglob("*")
        if p.is_file()
    }


def answer() -> dict:
    return json.loads((FIXTURES / "watchdog_v17_answer.json").read_text(encoding="utf-8"))


def check(raw: dict, released: dict[str, str] | None = None) -> dict:
    released = texts() if released is None else released
    counts = {path: len(text.splitlines()) for path, text in released.items()}
    return checked_model(raw, counts, {"watchdog_ai"}, texts=released)


def component(model: dict, cid: str) -> dict:
    return next(c for c in model["composants"] if c["id"] == cid)


def with_setting(**row) -> dict:
    """The fixture answer with one setting on auth-tenant, replacing the ones it has."""
    raw = answer()
    base = {
        "nom": "x",
        "code": "X-Tenant-ID",
        "sorte": "entete",
        "valeur": "",
        "effet": "e",
        "fichier": AUTH,
        "lignes": [33, 33],
    }
    next(c for c in raw["composants"] if c["id"] == "auth-tenant")["reglages"] = [base | row]
    return raw


def setting(raw: dict, released: dict[str, str] | None = None) -> dict:
    return component(check(raw, released), "auth-tenant")["reglages"][0]


def test_v17_watchdog_answer_keeps_every_new_field():
    model = check(answer())
    auth = component(model, "auth-tenant")
    header, refusal = auth["reglages"]
    assert (header["code"], header["fichier"], header["lignes"], header["verifie"]) == (
        "X-Tenant-ID",
        AUTH,
        [33, 33],
        True,
    )
    assert (refusal["code"], refusal["verifie"]) == ("401", True)
    assert auth["termes"] == [{"simple": "nom du client", "code": "X-Tenant-ID"}]
    assert auth["entre"] and auth["sort"]
    assert model["donnee"][0]["nom"] == "compte rendu"
    assert {f["nature"] for f in model["flux"]} == {"donnee", "controle"}
    assert [j["id"] for j in model["parcours"] if j["principal"]] == ["envoi-evenement"]
    main = next(j for j in model["parcours"] if j["principal"])
    assert (main["entree"], main["sortie"]) == ("agent-surveille", ["memoire"])
    assert all(b["quand_simple"] and b["alors_simple"] for b in main["branches"][:2])
    assert model["reglages_projet"] and model["pour_changer"]


@pytest.mark.parametrize(
    ("row", "why"),
    [
        ({"lignes": [34, 34]}, "line 34 is the if, not the header"),
        ({"code": "X-Client-ID"}, "the code is not in the line"),
        ({"lignes": [39, 41]}, "past the end of the file"),
        ({"lignes": [200, 201]}, "far past the end"),
        ({"code": "401", "lignes": [1, 40]}, "a citation that wide holds anything"),
        ({"code": ""}, "empty"),
        ({"code": " "}, "blank"),
        ({"code": ":"}, "punctuation only"),
        ({"code": "1", "fichier": SCHEMAS, "lignes": [15, 15]}, "one character"),
        ({"fichier": ".env", "lignes": [3, 3]}, "a file the Secret Guard never releases"),
    ],
)
def test_a_setting_is_verified_only_when_its_literal_code_is_in_the_cited_lines(row, why):
    found = setting(with_setting(**row))
    assert found["verifie"] is False, why
    assert found["code"] == row.get("code", "X-Tenant-ID")  # kept, marked


def test_code_over_several_lines_matches_once_spaces_are_collapsed():
    assert setting(with_setting(code="JSONResponse( status_code=401,", lignes=[35, 36]))["verifie"] is True
    crlf = texts() | {AUTH: texts()[AUTH].replace("\n", "\r\n")}
    assert (
        setting(with_setting(code="JSONResponse( status_code=401,", lignes=[35, 36]), crlf)["verifie"] is True
    )


def test_claude_cannot_mark_its_own_setting_verified():
    model = check(with_setting(verifie=True, lignes=[200, 201]))
    assert component(model, "auth-tenant")["reglages"][0]["verifie"] is False
    counts = {p: len(t.splitlines()) for p, t in texts().items()}
    again = updated_model(model, {}, counts, {"watchdog_ai"}, texts=texts())
    assert component(again, "auth-tenant")["reglages"][0]["verifie"] is False


def test_the_value_is_flagged_when_the_cited_lines_do_not_show_it():
    raw = answer()
    row = next(c for c in raw["composants"] if c["id"] == "schemas")["reglages"][0]
    row["valeur"] = "256"
    wrong = component(check(raw), "schemas")["reglages"][0]
    assert (wrong["verifie"], wrong["valeur_vue"]) == (True, False)
    row["valeur"] = "128"
    assert component(check(raw), "schemas")["reglages"][0]["valeur_vue"] is True


def test_the_literal_check_reads_only_the_released_texts(monkeypatch):
    def refuse(*_args, **_kwargs):
        raise AssertionError("no file may be opened: the Secret Guard already released the texts")

    monkeypatch.setattr("builtins.open", refuse)
    monkeypatch.setattr(Path, "read_text", refuse)
    released = {path: text for path, text in _TEXTS.items()}
    counts = {p: len(t.splitlines()) for p, t in released.items()}
    model = checked_model(copy.deepcopy(_ANSWER), counts, {"watchdog_ai"}, texts=released)
    updated_model(model, {}, counts, {"watchdog_ai"}, texts=released)
    assert component(model, "auth-tenant")["reglages"][0]["verifie"] is True


def test_a_setting_that_only_matches_a_masked_secret_never_verifies():
    released = texts() | {"settings.py": 'API_KEY = "************"\n'}
    raw = with_setting(code='API_KEY = "sk-live-abc123"', fichier="settings.py", lignes=[1, 1])
    model = check(raw, released)
    assert component(model, "auth-tenant")["reglages"][0]["verifie"] is False  # Claude only ever sees the mask


def test_a_project_setting_the_code_never_reads_is_marked_and_not_offered_as_a_lever():
    model = check(answer())
    port, database = model["reglages_projet"]
    assert (port["code"], port["verifie"], port["lu_par_le_code"]) == (
        "APP_PORT=8000",
        True,
        "non",
    )  # no .py reads it
    assert database["lu_par_le_code"] == "non"  # its line is commented out
    lever = next(p for p in model["pour_changer"] if p["reglage"] == "APP_PORT=8000")
    assert (lever["verifie"], lever["motif"]) == (False, "non lu par le code")


def test_a_lever_takes_the_citation_of_the_setting_it_names():
    lever = next(p for p in check(answer())["pour_changer"] if p["composant"] == "auth-tenant")
    assert (lever["fichier"], lever["lignes"], lever["verifie"]) == (AUTH, [33, 33], True)


def test_inside_of_a_part_without_components_is_derived_not_asked():
    raw = answer()
    next(b for b in raw["blocs"] if b["id"] == "docs")["interieur"] = "externe"  # ignored
    inside = {b["id"]: b["interieur"] for b in check(raw)["blocs"]}
    assert (inside["agent-surveille"], inside["operateur"], inside["docs"], inside["outillage"]) == (
        "personne",
    ) * 2 + ("fichiers",) * 2
    assert inside["api"] == ""  # it has components: « Entrer » shows them


def test_a_step_without_component_is_null_only_when_done_by_hand():
    raw = answer()
    steps = raw["parcours"][0]["etapes"]
    steps[0] |= {"composant": None, "manuel": True}
    steps[1] |= {"composant": None, "manuel": False}
    kept = check(raw)["parcours"][0]["etapes"]
    assert kept[0]["composant"] is None
    assert kept[1]["composant"] == ""  # never the text "None"


def test_branch_and_phase_numbers_follow_the_steps_kept():
    step = {"texte": "t", "composant": "auth-tenant", "fichier": AUTH, "lignes": [33, 33]}
    raw = answer()
    raw["parcours"] = [
        {"id": "j", "nom": "J", "principal": True, "etapes": [step, {"composant": "x"}, step, step],
         "branches": [{"quand": "a", "alors": "b", "etape": 3}, {"quand": "c", "alors": "d", "etape": 9}]}
    ]  # fmt: skip
    journey = check(raw)["parcours"][0]
    assert len(journey["etapes"]) == 3
    assert [b["etape"] for b in journey["branches"]] == [2, None]


@pytest.mark.parametrize(
    ("steps", "phases", "kept"),
    [
        (16, [[1, 5], [6, 11], [12, 16]], True),
        (16, [[1, 5], [7, 16]], False),  # a gap, and only 2
        (16, [[1, 5], [6, 10], [10, 16]], False),  # overlap
        (16, [[1, 8], [9, 16]], False),  # 2 phases
        (6, [[1, 2], [3, 4], [5, 6]], False),  # short journey: no phases
    ],
)
def test_phases_are_kept_only_when_they_cover_a_long_journey_in_order(steps, phases, kept):
    step = {"texte": "t", "composant": "auth-tenant"}
    raw = answer()
    raw["parcours"] = [
        {
            "id": "j",
            "nom": "J",
            "etapes": [step] * steps,
            "phases": [{"nom": f"p{i}", "de": a, "a": b} for i, (a, b) in enumerate(phases)],
        }
    ]
    assert bool(check(raw)["parcours"][0]["phases"]) is kept


def ui_model(name: str) -> dict:
    return json.loads((UI_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


@pytest.mark.parametrize(("name", "main"), [("watchdog", "envoi-evenement"), ("justicia", "poser-question")])
def test_without_a_declared_main_journey_the_floor_rule_picks_it(name, main):
    model = checked_model(ui_model(name), _ANY_LINES, set())
    picked = [j for j in model["parcours"] if j["principal"]]
    assert [j["id"] for j in picked] == [main]
    assert picked[0]["principal_deduit"] is True


def test_only_the_first_of_two_declared_main_journeys_stays():
    raw = answer()
    for journey in raw["parcours"]:
        journey["principal"] = True
    assert [j["principal"] for j in check(raw)["parcours"]] == [True] + [False] * (len(raw["parcours"]) - 1)


def test_a_main_journey_returned_by_an_update_wins():
    model = check(answer())
    counts = {p: len(t.splitlines()) for p, t in texts().items()}
    start = next(j for j in model["parcours"] if j["id"] == "demarrage")
    merged = updated_model(
        model, {"parcours": [start | {"principal": True}]}, counts, {"watchdog_ai"}, texts=texts()
    )
    assert [j["id"] for j in merged["parcours"] if j["principal"]] == ["demarrage"]
    assert not next(j for j in merged["parcours"] if j["id"] == "demarrage").get("principal_deduit")


def test_a_part_no_journey_touches_leaves_the_data_zones():
    zones = {b["id"]: b["zone"] for b in check(answer())["blocs"]}
    assert (zones["docs"], zones["outillage"]) == ("atelier", "atelier")
    assert zones["operateur"] == "utilise"  # a journey touches it
    justicia = {b["id"]: b["zone"] for b in checked_model(ui_model("justicia"), _ANY_LINES, set())["blocs"]}
    assert justicia["docs"] == "atelier"  # was « range »


def test_unknown_values_and_too_many_rows_never_break_the_model():
    raw = answer()
    raw["flux"][0]["nature"] = "x"
    auth = next(c for c in raw["composants"] if c["id"] == "auth-tenant")
    auth["reglages"] = [auth["reglages"][0] | {"sorte": "x"}] * 9 + ["not a row"]
    auth["entre"] = ["e"] * 5
    raw["pour_changer"] = [
        {"intention": f"i{n}", "composant": "auth-tenant", "reglage": "X-Tenant-ID"} for n in range(6)
    ]
    raw["pour_changer"].append({"intention": "j", "composant": "docs-x", "reglage": "y"})
    model = check(raw)
    kept = component(model, "auth-tenant")
    assert model["flux"][0]["nature"] == "donnee"
    assert (len(kept["reglages"]), kept["reglages"][0]["sorte"], len(kept["entre"])) == (6, "", 3)
    assert len([p for p in model["pour_changer"] if p["composant"] == "auth-tenant"]) == 3
    assert all(p["composant"] != "docs-x" for p in model["pour_changer"])  # no such component


def test_a_long_effect_is_cut_on_a_word():
    effect = "Le service refuse toute demande qui ne porte pas le nom du client dans son en-tête, même la documentation, et ne garde rien"
    row = setting(with_setting(effet=effect))
    assert len(row["effet"]) <= MAX_SHORT and row["effet"].endswith("…")
    assert effect.startswith(row["effet"][:-1].rstrip()) and effect[len(row["effet"][:-1].rstrip())] == " "


def test_an_update_keeps_the_project_level_sections_and_rechecks_moved_lines():
    model = check(answer())
    counts = {p: len(t.splitlines()) for p, t in texts().items()}
    kept = updated_model(model, {}, counts, {"watchdog_ai"}, texts=texts())
    assert (kept["donnee"], kept["reglages_projet"], kept["pour_changer"]) == (
        model["donnee"],
        model["reglages_projet"],
        model["pour_changer"],
    )
    moved = texts() | {AUTH: "\n\n" + texts()[AUTH]}
    counts = {p: len(t.splitlines()) for p, t in moved.items()}
    again = updated_model(model, {}, counts, {"watchdog_ai"}, texts=moved)
    assert component(again, "auth-tenant")["reglages"][0]["verifie"] is False


def test_an_update_drops_what_points_to_removed_entries_and_keeps_both_kinds_of_flow():
    model = check(answer())
    counts = {p: len(t.splitlines()) for p, t in texts().items()}
    patch = {
        "supprime": {"composants": ["auth-tenant"], "donnee": ["compte rendu"]},
        "flux": [
            {"de": "api", "vers": "memoire", "quoi": "vide la mémoire", "verbe": "vide", "nature": "controle"}
        ],
    }
    merged = updated_model(model, patch, counts, {"watchdog_ai"}, texts=texts())
    assert [p for p in merged["pour_changer"] if p["composant"] == "auth-tenant"] == []
    assert merged["donnee"] == []
    assert {f["nature"] for f in merged["flux"] if (f["de"], f["vers"]) == ("api", "memoire")} == {
        "donnee",
        "controle",
    }


def test_the_prompt_asks_for_every_new_field_and_the_two_reader_rules():
    assert "atelier" in SCHEMA
    for word in ("entre", "sort", "reglages", "termes", "donnee", "reglages_projet", "nature",
                 "principal", "entree", "sortie", "quand_simple", "alors_simple", "etape", "phases", "pour_changer"):  # fmt: skip
        assert f'"{word}"' in SCHEMA, word
    assert all(key in UPDATE for key in ("donnee", "reglages_projet", "pour_changer"))
    prompt = study_prompt()
    assert "donnee.nom" in prompt  # one name for the data in every reader text
    assert "consequence for the user first" in prompt


@pytest.mark.parametrize("name", ["watchdog", "justicia"])
def test_v16_models_load_unchanged(name):
    before = ui_model(name)
    model = checked_model(copy.deepcopy(before), _ANY_LINES, set())
    for section in ("blocs", "composants"):
        for old, new in zip(before[section], model[section], strict=True):
            for key, value in old.items():
                if key not in (
                    "code",
                    "zone",
                ):  # code paths are checked against the map; zone may become atelier
                    assert new[key] == value, (section, old["id"], key)
    assert all(c["reglages"] == [] and c["entre"] == [] for c in model["composants"])
    assert (model["donnee"], model["reglages_projet"], model["pour_changer"]) == ([], [], [])


def test_a_v17_study_answer_stays_close_to_v16_size():
    before = len(json.dumps(ui_model("watchdog"), ensure_ascii=False))
    after = len(json.dumps(check(answer()), ensure_ascii=False))
    ratio = after / before
    print(f"v1.7 / v1.6 model size on Watchdog: {ratio:.2f}")
    assert ratio <= 1.6


class _AnyLines(dict):
    """Line counts for the UI fixtures, whose files are not in the test tree: every cited file fits."""

    def get(self, key, default=None):  # noqa: ARG002
        return 10_000

    def __contains__(self, key) -> bool:
        return True


_ANY_LINES = _AnyLines()
_TEXTS = texts()
_ANSWER = answer()
