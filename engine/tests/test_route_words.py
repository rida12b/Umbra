"""#107 (mock prototype.html, ACTIONS_TPL): every route of full-stack-fastapi-template gets plain French
words from its address and its decorator, with no model; a router mounted only in local says so."""

from umbra_engine.projection.card_code import mounts, routes
from umbra_engine.projection.route_words import CALLER, OTHERS, SIGNING_UP, caller_rank, label

# verb, address, behind a superuser dependency, takes the signed-in caller → the mock's words
TEMPLATE = [
    ("GET", "/api/v1/items/", False, True, "Lister ses items"),
    ("POST", "/api/v1/users/signup", False, False, "S'inscrire"),
    ("GET", "/api/v1/users/me", False, True, "Voir son profil"),
    ("PATCH", "/api/v1/users/me", False, True, "Modifier son profil"),
    ("PATCH", "/api/v1/users/me/password", False, True, "Changer son mot de passe"),
    ("DELETE", "/api/v1/users/me", False, True, "Supprimer son compte"),
    ("GET", "/api/v1/users/", True, True, "Lister les comptes (admin)"),
    ("POST", "/api/v1/users/", True, True, "Créer un compte (admin)"),
    ("GET", "/api/v1/users/{user_id}", False, True, "Voir un compte"),
    ("PATCH", "/api/v1/users/{user_id}", True, True, "Modifier un compte (admin)"),
    ("DELETE", "/api/v1/users/{user_id}", True, True, "Supprimer un compte (admin)"),
    ("POST", "/api/v1/login/access-token", False, False, "Se connecter"),
    ("POST", "/api/v1/login/test-token", False, True, "Vérifier sa connexion"),
    ("POST", "/api/v1/password-recovery/{email}", False, False, "Demander un nouveau mot de passe"),
    ("POST", "/api/v1/reset-password/", False, False, "Choisir un nouveau mot de passe"),
    (
        "POST",
        "/api/v1/password-recovery-html-content/{email}",
        True,
        True,
        "Voir le courriel de récupération (admin)",
    ),
    ("POST", "/api/v1/utils/test-email/", True, True, "Envoyer un courriel de test (admin)"),
    ("GET", "/api/v1/utils/health-check/", False, False, "Vérifier que le serveur répond"),
    ("POST", "/api/v1/private/users/", False, False, "Créer un compte sans connexion"),
]


def test_every_template_route_gets_the_mock_words():
    for verb, address, admin, signed_in, words in TEMPLATE:
        owned = address == "/api/v1/items/"
        assert label(verb, address, owned, admin, signed_in) == words, address


def test_what_the_caller_does_for_himself_comes_first():
    assert caller_rank("/api/v1/users/signup") == SIGNING_UP
    assert caller_rank("/api/v1/users/me/password") == CALLER
    assert caller_rank("/api/v1/users/{user_id}") == OTHERS


def test_the_decorator_says_admin_and_the_parameters_say_signed_in():
    text = (
        "@router.get('/', dependencies=[Depends(get_current_active_superuser)])\n"
        "def read_users(session: SessionDep) -> Any:\n    return 1\n\n\n"
        "@router.get('/{user_id}')\n"
        "def read_user_by_id(user_id: int, current_user: CurrentUser) -> Any:\n    return 1\n\n\n"
        "@router.post('/users/')\n"
        "def create_user(user_in: PrivateUserCreate, session: SessionDep) -> Any:\n    return 1\n"
    )
    found = [(r.name, r.admin, r.signed_in) for r in routes(text, True)]
    assert found == [
        ("read_users", True, True),
        ("read_user_by_id", False, True),
        ("create_user", False, False),
    ]


def test_a_router_mounted_only_in_local_says_so():
    text = (
        "api_router.include_router(items.router)\n"
        "if settings.ENVIRONMENT == 'local':\n"
        "    api_router.include_router(private.router)\n"
    )
    assert [(m.target, m.local) for m in mounts(text)] == [("items.router", False), ("private.router", True)]
