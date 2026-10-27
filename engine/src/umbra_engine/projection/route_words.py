"""Plain French words for a route (#106 card, #107 « Ce qu'on peut faire »), read in its address and its
decorator, never written by a model. A plain shape says it all (a GET on a collection lists, on `{id}` it
shows; a POST creates; a PUT or PATCH changes; a DELETE removes); the common words of sign-up, sign-in,
passwords and « me » name the others. A route behind a superuser or admin dependency says « (admin) »; an
account created with no sign-in says « sans connexion ». Anything else stays unnamed (« »): Claude names
it in #108."""

import re

from umbra_engine.projection.system_purpose import ACCOUNT_TABLES

ME = {"me", "my", "self", "current"}
SIGN_UP = {"signup", "sign-up", "register", "registration"}
SIGN_IN = {"login", "signin", "sign-in", "token", "access-token"}
HEALTH = {"health", "health-check", "healthcheck", "healthz", "ping"}
SIGNING_UP = 0  # what the caller does for himself comes first in the list (#107), as the mock orders it
CALLER = 1  # « me »: his own profile, password, account
OTHERS = 2


def label(verb: str, full: str, owned: bool = False, admin: bool = False, signed_in: bool = True) -> str:
    segments = [s for s in full.lower().split("/") if s]
    statics = [s for s in segments if not s.startswith("{")]
    words = _known(verb, statics)
    shaped = "" if words else _shape(verb, segments, statics, owned)
    found = words or shaped
    if not found:
        return ""
    if admin:
        return f"{found} (admin)"
    if shaped and not signed_in and _account(statics[-1]):
        return f"{found} sans connexion"
    return found


def caller_rank(full: str) -> int:
    statics = [s for s in full.lower().split("/") if s and not s.startswith("{")]
    if SIGN_UP & set(statics):
        return SIGNING_UP
    return CALLER if ME & set(statics) else OTHERS


def _known(verb: str, statics: list[str]) -> str:
    seen = set(statics)
    joined = "/".join(statics)
    if seen & SIGN_UP:
        return "S'inscrire"
    if "password" in joined:
        if "recover" in joined or "forgot" in joined:
            return (
                "Voir le courriel de récupération" if "html" in joined else "Demander un nouveau mot de passe"
            )
        if "reset" in joined:
            return "Choisir un nouveau mot de passe"
        if seen & ME:
            return "Changer son mot de passe"
    if seen & SIGN_IN or any(s.endswith("-token") for s in statics):
        return "Vérifier sa connexion" if "test" in joined else "Se connecter"
    if statics and statics[-1] in HEALTH:
        return "Vérifier que le serveur répond"
    if re.search(r"test-?e?mail", joined):
        return "Envoyer un courriel de test"
    if statics and statics[-1] in ME:
        return {"GET": "Voir son profil", "PUT": "Modifier son profil", "PATCH": "Modifier son profil",
                "DELETE": "Supprimer son compte"}.get(verb, "")  # fmt: skip
    return ""


def _shape(verb: str, segments: list[str], statics: list[str], owned: bool) -> str:
    one = bool(segments) and segments[-1].startswith("{")
    if not statics or (one and len(segments) < 2) or (one and segments[-2].startswith("{")):
        return ""
    many = statics[-1]
    if one and segments[-2] != many or not re.fullmatch(r"[a-z]+s", many):
        return ""
    single = "compte" if _account(many) else many[:-1]
    plural = "comptes" if _account(many) else many
    shapes = {
        ("GET", False): f"Lister {'ses' if owned else 'les'} {plural}", ("GET", True): f"Voir un {single}",
        ("POST", False): f"Créer un {single}", ("PUT", True): f"Modifier un {single}",
        ("PATCH", True): f"Modifier un {single}", ("DELETE", True): f"Supprimer un {single}",
    }  # fmt: skip
    return shapes.get((verb, one), "")


def _account(many: str) -> bool:
    return many.rstrip("s") in ACCOUNT_TABLES
