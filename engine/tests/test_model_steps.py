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
