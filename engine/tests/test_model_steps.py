"""Journey steps keep what the diagram needs: a short action label, conditions and the manual flag."""

from umbra_engine.analysis.model import MAX_ACTION, checked_model

STEP = {
    "texte": "Le hook écrit l'événement.",
    "composant": "journal",
    "touche": ["spool"],
    "conditions": ["plugin installé"],
    "manuel": False,
    "fichier": "hook.py",
    "lignes": [1, 2],
}


def model_with(*steps: dict) -> dict:
    raw = {
        "resume": "r",
        "blocs": [{"id": "spool", "nom": "Spool", "type": "queue", "role": "r"}],
        "parcours": [{"id": "j", "nom": "Journal", "etapes": list(steps)}],
    }
    return checked_model(raw, {"hook.py": 10}, set())


def test_a_step_keeps_its_short_action_label():
    [step] = model_with({**STEP, "action": "Écrit un fichier .json"})["parcours"][0]["etapes"]
    assert step["action"] == "Écrit un fichier .json"
    assert (step["touche"], step["conditions"]) == (["spool"], ["plugin installé"])


def test_a_missing_or_overlong_action_never_breaks_the_model():
    old, long = model_with(STEP, {**STEP, "action": "x" * 500})["parcours"][0]["etapes"]
    assert old["action"] == ""  # a model studied before the label existed
    assert len(long["action"]) == MAX_ACTION


def test_plain_texts_for_readers_who_do_not_code_are_kept():
    raw = {
        "resume": "r",
        "pitch": "Umbra montre comment marche un logiciel.",
        "blocs": [{"id": "spool", "nom": "File", "en_bref": "Garde les événements", "type": "queue"}],
        "parcours": [{"id": "j", "nom": "J", "etapes": [{**STEP, "simple": "Claude note ce qu'il a fait."}]}],
    }
    model = checked_model(raw, {"hook.py": 10}, set())
    assert model["pitch"] == "Umbra montre comment marche un logiciel."
    assert model["blocs"][0]["en_bref"] == "Garde les événements"
    assert model["parcours"][0]["etapes"][0]["simple"] == "Claude note ce qu'il a fait."
