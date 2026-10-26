# Inventaire visuel — maquette « factory floor » (2026-10-25)

Ce fichier est le contrat visuel de la maquette validée. Il vient **uniquement** de quatre captures :

| Capture | Écran-état | Maquette |
|---|---|---|
| `ref-floor-watchdog.png` | **floor** : vue d'ensemble du projet (l'usine) | B |
| `ref-room-api.png` | **room** : après « Entrer » sur la pièce du milieu (Porte d'entrée du service), au repos | B |
| `ref-room-api-playing.png` | **room · lecture** : un trajet est en cours de lecture, étape 1 | B |
| `ref-line-watchdog.png` | **line** : ligne de métro numérotée | A |

Rida a validé **B comme base**, plus **la ligne numérotée de A** (stations, la ligne, la façon de montrer une étape). Les lignes « line » ci-dessous ne gardent que cela ; ce qui, dans A, contredit B est listé en fin de fichier.

> **Règle : l'inventaire fixe la forme, la couleur et la place, pas le texte : le texte vient du modèle.**
> Les textes cités servent seulement à repérer l'élément. Colonne `source` : `modèle` = texte générique venu du modèle du projet ; `attend …` = **fait qui semble lu à la main dans le code** (nom d'en-tête, code HTTP, puce fichier:ligne, nom de classe). Ces lignes ne doivent pas être recopiées en dur : il faut une source dans le modèle.

Fond général : quasi noir (≈ #0d1117), texte principal blanc, texte secondaire gris. Panneau latéral droit ≈ 400 px, séparé par un filet vertical, avec sa propre barre de défilement.

## Tableau

| id | écran-état | élément | forme, couleur, taille, place | source | ticket | écart accepté |
|---|---|---|---|---|---|---|
| V1 | floor | Barre du haut (fil d'Ariane) | Bande pleine largeur ≈ 48 px, filet bas gris. À gauche « **Umbra** / watchdog » (Umbra gras blanc, « / watchdog » gris), puis « L'usine » gras blanc, ≈ 14 px. Rien à droite. | modèle | #75 | |
| V2 | floor | Bloc « Ce que fait ce projet, pour qui » | Libellé petites capitales gris ≈ 11 px, puis paragraphe blanc ≈ 16 px sur 3 lignes, largeur max ≈ 940 px, en haut de la zone centrale. | modèle | #75 | |
| V3 | floor | Ligne « La donnée sur le tapis : » | Libellé gras **jaune-orangé** suivi d'une phrase blanche ≈ 12 px avec le nom de la donnée entre « ». | modèle | #75 | |
| V4 | floor | Puce « même donnée, deux noms » | Petite puce à bord jaune plein ≈ 1 px, texte jaune ≈ 11 px, coins arrondis, en début de 2e ligne sous V3. | modèle | #75 | |
| V5 | floor | « dans le code : EventIn puis EventOut » + puce pointillée | Noms de code en **monospace gras blanc** ; suivis d'une puce à **bord pointillé** gris-blanc « pas encore dans le modèle — lu dans le code ». | attend noms de classes lus dans le code (EventIn / EventOut) | #75 | |
| V6 | floor | Chemin fichier:lignes du schéma | Ligne seule en monospace bleu-gris ≈ 12 px, sous V5 (`…/schemas.py:10, 39`). | attend puce fichier:ligne lue dans le code | #75 | |
| V7 | floor | Légende (2 lignes) | Sous un filet gris horizontal. Ligne 1 : cercle vert vide = Personne ; petit rectangle à barre gauche bleue = Service (pièce) ; carré arrondi orange vide = Base de données ; rectangle pointillé gris = Autour du projet ; **barre jaune épaisse** = Donnée (tapis) ; tirets jaunes = Réponse ; trait gris fin = Contrôle, pas de donnée ; carré rouge plein = Refus. Ligne 2 : carré pointillé = « Lu dans le code, pas encore dans le modèle ». Texte gris clair ≈ 12 px. | modèle (fixe) | #75 | |
| V8 | floor | Carte personne « Personne qui installe et lance » | Carte ≈ 280×80 px, fond vert très sombre, bord vert fin, coins arrondis ≈ 8 px ; icône personne verte au trait à gauche ; titre gras blanc + sous-titre gris. Placée **en haut, centrée au-dessus de la pièce du milieu**, hors du tapis. | modèle | #75 | |
| V9 | floor | Lien de contrôle « démarre » | Trait **gris fin** en équerre, de la carte V8 vers le haut de la pièce du milieu, pointe de flèche grise ; puce gris foncé à bord gris « démarre » posée sur le trait. | modèle | #75 | |
| V10 | floor | Carte d'entrée « Assistant d'IA surveillé » | Grande carte ≈ 180×190 px, fond vert sombre, bord vert, à **gauche**, alignée sur le tapis. En haut à gauche **pastille verte pleine « ▶ ENTRÉE »** (texte sombre, capitales). Icône personne verte, titre gras blanc ≈ 15 px sur 2 lignes, description grise, puis petite ligne grise « Personne · HTTP / JSON ». | modèle ; attend protocole « HTTP / JSON » (lu dans le code) | #75 | |
| V11 | floor | Tapis (donnée) entre les pièces | **Tapis jaune épais (≈ 5-6 px), en tirets serrés**, horizontal, de V10 à la pièce du milieu puis de la pièce au cylindre ; **pointe de flèche jaune pleine** à l'arrivée sur chaque pièce. | modèle (fixe) | #75 | |
| V12 | floor | Étiquette d'action au-dessus du tapis | Puce rectangulaire fond sombre, bord gris fin, texte blanc ≈ 12 px sur 2 lignes (« envoie ses comptes rendus à », « range l'événement dans »), centrée **au-dessus** de chaque tronçon. | modèle | #75 | |
| V13 | floor | Nom de la donnée sous le tapis | Sous chaque tronçon, puce à **bord pointillé** gris, texte gris clair entre « » (« Le compte rendu d'un appel au modèle », « L'événement enregistré »). | modèle | #75 | |
| V14 | floor | Carte pièce « Porte d'entrée du service » | Carte ≈ 290×190 px, fond gris-bleu sombre, **barre bleue épaisse (≈ 4 px) à gauche**, coins arrondis. Titre gras blanc ≈ 15 px, sous-titre gris. Puis **3 machines** en puces à bord gris, chacune avec **numéro dans un cercle à bord orange-jaune** (1, 2, 3) et une petite flèche « → » orange après les deux premières. Puis ligne grise « + Assemblage de l'application (câblage) ». Pied : « 4 machines · 4 étapes ici » gris à gauche, lien **bleu « Entrer › »** à droite. | modèle | #75 | |
| V15 | floor | Cylindre « Mémoire temporaire des événements » (stockage, sortie) | **Forme de cylindre** (ellipse en haut et en bas), ≈ 230×190 px, **bord orange-jaune ≈ 2 px**, fond brun très sombre. Sur le bord haut à gauche : **pastille orange pleine « SORTIE ■ »**. Titre gras blanc, description grise, puis phrase d'avertissement **orange en italique** (« Tout est perdu au redémarrage. »). Pied : « 1 machine · 1 étape ici » + lien orange « Entrer › ». À droite du tapis. | modèle | #75 | |
| V16 | floor | Chemin de réponse | **Tirets jaunes ≈ 2 px** partant du bas de la pièce du milieu, descendant, allant vers la gauche **sous le tapis**, puis remontant jusqu'au bas de V10 avec **pointe de flèche jaune vers le haut**. | modèle (fixe) | #75 | |
| V17 | floor | Étiquette de la réponse | Sous le tronçon horizontal de V16 : « répond à » blanc + **puce jaune à bord jaune « texte du modèle, technique »**, puis 2e ligne dans un cadre pointillé gris : « 201 avec l'EventOut, 401 si l'en-tête manque, ou 422 si le corps est invalide ». | attend codes HTTP et nom EventOut (lus dans le code) | #75 | |
| V18 | floor | Bande « Autour du projet (ne tourne pas) » | Grand cadre **pointillé gris** pleine largeur en bas de la zone centrale, libellé petites capitales gris. Contient 3 cartes **à bord pointillé** côte à côte : titre gras blanc + description grise. La 2e carte a une ligne grise en plus « vérifie « Porte d'entrée du service » — contrôle, pas de donnée ». La 3e (« Réglages du projet ») montre « .env.example et port réel ». | modèle ; attend « .env.example » / port (lus dans le code) | #75 | |
| V19 | floor | Panneau latéral : en-tête « Vous êtes ici » | Petit gris « Vous êtes ici », titre **gras blanc ≈ 20 px** « L'usine (vue d'ensemble) », paragraphe gris ≈ 13 px qui explique le tapis et « Entrer ». | modèle (fixe) | #75 | |
| V20 | floor | Panneau : carte du trajet principal | Titre de section gras blanc « Le trajet sur le tapis ». Carte à bord gris fin : titre gras blanc ; « **Départ :** » et « **Arrivée :** » en **jaune-orangé gras** suivis de texte gris clair ; ligne grise « 5 étapes · 3 cas particuliers ». | modèle | #75 | |
| V21 | floor | Bouton « ▶ Suivre un compte rendu » | Bouton ≈ 195×34 px, **fond jaune-brun sombre, bord jaune**, icône ▶ jaune, texte blanc gras, dans la carte V20 sous les compteurs. | modèle | #75 | |
| V22 | floor | Justification du choix du trajet | Petit texte gris ≈ 11 px sous le bouton (« Choisi car il passe par le plus de composants… »). | modèle | #75 | |
| V23 | floor | Panneau : liste « Les pièces » | Titre de section gras. Une carte par pièce, bord gris fin : titre gras blanc, description gris clair, « N machines · N étapes ici » gris, lien **bleu « Entrer › »** aligné à droite en bas. | modèle | #75 | |
| V24 | floor | Panneau : « Autres trajets » | Titre gras + parenthèse grise plus petite « (un seul trajet à la fois sur le tapis) ». Cartes repliées : « ▸ » + titre gras blanc, description gris clair sur 2 lignes. | modèle | #75 | |
| V25 | room | Barre du haut (fil d'Ariane) + bouton Remonter | « **Umbra** / watchdog », puis « L'usine » **gris** (lien), chevron « › », « Porte d'entrée du service » gras blanc. **À droite** : bouton à bord gris « ‹ Remonter » + « (Échap) » gris plus petit. | modèle | #76 | |
| V26 | room | Bloc projet + donnée + légende | **Identiques à V2–V7** (même place, même taille) : le haut de page ne change pas en entrant dans une pièce. | modèle | #76 | |
| V27 | room | Carte d'entrée réduite | Carte étroite ≈ 125×175 px à **gauche**, fond vert très sombre, **bord pointillé** vert-gris ; icône personne verte + **pastille verte pleine « ▶ ENTRÉE »** sur la même ligne ; texte « depuis **Assistant d'IA surveillé** — envoie ses comptes rendus à » ; lien bleu « Voir la fiche › ». | modèle | #76 | |
| V28 | room | Cadre de la pièce et son titre | Grand cadre arrondi ≈ 665×515 px, fond gris-bleu sombre, **barre bleue épaisse (≈ 4 px) à gauche** sur toute la hauteur. Ligne de titre en haut : nom de la pièce **gras blanc** — sous-titre gris — « · pièce ouverte, la donnée va de gauche à droite » gris plus petit. | modèle | #76 | |
| V29 | room | Bande de câblage | Dans le haut du cadre, rectangle **à bord pointillé** gris pleine largeur. Puce à bord gris, capitales « CÂBLAGE, AU DÉMARRAGE ». Puis « **Assemblage de l'application** — Monte le service et branche ses morceaux · » + chemin `watchdog_ai/main.py` en **monospace bleu**. | modèle ; attend chemin de fichier (lu dans le code) | #76 | |
| V30 | room | Liens de câblage | **Traits gris fins verticaux** du bas de V29 vers le haut des machines 1 et 3, chacun avec une puce gris foncé « câblage ». | modèle (fixe) | #76 | |
| V31 | room | Machines (3 cartes) | Trois cartes ≈ 180×160 px alignées horizontalement, fond sombre, bord gris fin, coins arrondis. En haut : **numéro dans un cercle à bord orange-jaune** + titre **gras blanc ≈ 14 px** sur 2-3 lignes ; description grise. La machine 3 a une ligne grise en plus « aussi à l'étape 5 ». | modèle | #76 | |
| V32 | room | Puces entrée/sortie des machines | En bas de chaque machine, **deux puces à bord pointillé** gris pleine largeur de la carte : en haut, alignée à gauche « → reçoit X » ; en dessous, alignée à droite « rend Y · ou 401 → ». Texte gris clair ≈ 11 px. | attend noms d'en-tête / champs / classes et codes HTTP (X-Tenant-ID, tenant_id, EventIn, EventOut, 401, 422, 201) | #76 | |
| V33 | room | Tapis dans la pièce (au repos) | Tronçons **épais (≈ 6 px) ocre éteint / jaune-brun terne**, avec **pointe de flèche pleine** de même couleur : entrée → machine 1, 1 → 2, 2 → 3, 3 → sortie. Au repos, aucun tronçon n'est jaune vif. | modèle (fixe) | #76 | |
| V34 | room | Numéro d'étape sur le tapis | Petite puce carrée fond sombre bord gris « 4 » posée au-dessus du tronçon machine 3 → sortie. | modèle | #76 | |
| V35 | room | Cartes de refus | Sous les machines 1 et 2 : cartes ≈ 165×90 px, **fond rouge très sombre, bord rouge**, carré rouge plein + titre **rouge gras « refus 401 » / « refus 422 »**, description gris clair. Reliées à leur machine par un **trait vertical en tirets rouge-brun**. (Dans la capture, le texte de « refus 422 » déborde et est coupé.) | modèle ; attend code HTTP dans le titre | #76 | |
| V36 | room | Porte de sortie | À droite du cadre, hors cadre : boîte ≈ 125×170 px **à bord en tirets jaune-orangé**, fond brun sombre. **Pastille orange pleine « SORTIE ■ »** en haut ; texte « vers **Mémoire temporaire des événements** — range l'événement dans » ; puce intérieure à bord gris « 4 · Rangement des événements ». | modèle | #76 | |
| V37 | room | Chemin de réponse dans la pièce | **Tirets jaunes ≈ 2 px** depuis le bas de la machine 3, descente, tronçon horizontal **sous les cartes de refus**, puis remontée hors du cadre jusqu'au bas de la carte d'entrée V27 avec **pointe jaune vers le haut**. | modèle (fixe) | #76 | |
| V38 | room | Étiquette de la réponse | Sur le tronçon bas de V37, cadre pointillé gris : « 5 · répond à Assistant d'IA surveillé » + **puce jaune « texte du modèle, technique »**, 2e ligne « 201 avec l'EventOut, 401…, 422… ». | attend codes HTTP et nom EventOut | #76 | |
| V39 | room | Bande « Autour du projet » | Même forme que V18, **repoussée sous le cadre de la pièce** (visible seulement en haut, il faut défiler). Barre de défilement visible à droite de la zone centrale. | modèle | #76 | |
| V40 | room | Panneau : en-tête de pièce | Petit gris « Vous êtes dans la pièce », titre **gras blanc ≈ 20 px** (nom de la pièce), sous-titre gris. | modèle | #76 | |
| V41 | room | Panneau : titre du trajet | Ligne **gras blanc ≈ 14 px** avec le nom du trajet, au-dessus des boutons. | modèle | #76 | |
| V42 | room | Panneau : boutons du lecteur | Trois boutons côte à côte ≈ 34 px de haut : « ‹ Précédent » **désactivé** (fond gris sombre, texte gris terne) ; « **▶ Lecture** » **fond jaune-brun, bord jaune, texte gras blanc** ; « Suivant › » fond sombre bord gris. | modèle (fixe) | #76 | Remplacé par la barre du bas (V65) — choix Rida 2026-10-25 (lecteur en bas) |
| V43 | room | Panneau : aide clavier | Ligne grise ≈ 12 px sous les boutons : « 5 étapes · cliquez une étape ou « Suivant » · touches ← → ». | modèle (fixe) | #76 | Remplacé par la barre du bas (V65) — choix Rida 2026-10-25 |
| V44 | room | Panneau : titre de groupe par pièce | Petites capitales grises « DANS « PORTE D'ENTRÉE DU SERVICE » » ; un 2e groupe « DANS « MÉMOIRE TEMPORAIRE… » » apparaît plus bas : les étapes sont **groupées par pièce**. | modèle | #76 | |
| V45 | room | Panneau : cartes d'étape | Carte à bord gris fin : **numéro dans un cercle à bord jaune** à gauche, titre gras blanc, texte gris clair, puis chemin **monospace bleu** + « l.28-40 ». | modèle ; attend puce fichier:ligne | #76 | |
| V46 | room | Panneau : blocs de cas particuliers « Si / alors » | Entre les cartes d'étape, bloc **sans cadre, avec barre rouge ≈ 3 px à gauche** : « **Si** … » puis « **alors** … » (mots-clés gras blancs), texte gris clair, **puce jaune « texte du modèle, technique »** en fin de phrase, puis chemin monospace bleu + lignes. | modèle ; attend nom d'en-tête, message d'erreur exact, codes HTTP, noms de champs, puce fichier:ligne | #76 | |
| V47 | room · lecture | Machine active (étape 1) | La machine 1 prend un **bord jaune vif ≈ 3 px avec halo jaune** autour de la carte ; le reste de la carte inchangé. | modèle (fixe) | #77 | |
| V48 | room · lecture | Pastille de la donnée sur la machine active | **Pastille jaune pleine, texte sombre « compte rendu »**, posée à cheval sur le bord haut de la machine active, centrée. | modèle (nom court de la donnée) | #77 | |
| V49 | room · lecture | Tronçon de tapis allumé | Seul le tronçon **entrée → machine 1 passe en jaune vif** (pointe incluse) ; tous les autres tronçons restent ocre éteint comme V33. | modèle (fixe) | #77 | |
| V50 | room · lecture | Machines non actives | Machines 2 et 3 **inchangées** (bord gris), pas de halo. | modèle (fixe) | #77 | |
| V51 | room · lecture | Refus, sortie, réponse pendant l'étape 1 | Cartes de refus, porte de sortie, chemin de réponse et puce « 4 » **inchangés, non allumés** (même la carte « refus 401 » liée à la machine 1 n'est pas allumée). | modèle (fixe) | #77 | |
| V52 | room · lecture | Panneau : aide → compteur d'étape | La ligne V43 devient « **Étape 1 sur 5** · touches ← → ». | modèle (fixe) | #77 | Le compteur d'étape vit dans la barre du bas (V65) — choix Rida 2026-10-25 |
| V53 | room · lecture | Panneau : carte d'étape active | La carte d'étape 1 prend un **bord jaune ≈ 2 px** ; les autres cartes et les blocs « Si / alors » gardent leur aspect V45/V46. | modèle (fixe) | #77 | |
| V54 | room · lecture | Panneau : boutons pendant la lecture | Les trois boutons gardent **le même aspect et le même texte** que V42 (« ‹ Précédent » toujours désactivé à l'étape 1, « ▶ Lecture » n'est pas remplacé par « Pause »). | modèle (fixe) | #77 | Sans objet : lecteur dans la barre du bas — choix Rida 2026-10-25 |
| V55 | room · lecture | Reste de l'écran | Fil d'Ariane, bouton Remonter, bloc projet, légende, bande de câblage, carte d'entrée : **identiques** à l'état repos. | modèle | #77 | |
| V56 | line | La ligne principale | **Ligne jaune pleine, continue, ≈ 6 px**, horizontale, de la personne d'entrée à gauche jusqu'au stockage à droite, traversant le cadre de la pièce ; pas de tirets, pas de pointes de flèche. | modèle (fixe) | #77 | Non repris : le tapis de B (V11/V33) reste — règle « B est la base » (conflit 4) |
| V57 | line | Stations numérotées | Sur la ligne : **disque sombre avec anneau ≈ 3 px**, numéro **blanc gras** au centre, ≈ 26 px de diamètre ; station 1 à **anneau blanc épais**, stations 2-4 à anneau jaune. Espacement régulier. | modèle (numérotation) | #77 | Remplacé par le cercle numéroté dans la machine (V31) — choix Rida 2026-10-25 |
| V58 | line | Étiquette sous chaque station | Sous la station, sur fond sombre : **titre gras blanc = l'action** (« Vérifie le nom du client ») + **ligne grise = la machine** (« Contrôle du nom du client »). | modèle | #77 | Non repris : l'action de l'étape est dans la barre du bas — règle « B est la base » |
| V59 | line | Branche de refus | Sous les stations 1 et 2 : court trait vertical **rouge**, **carré rouge plein** + étiquette **rouge gras « → 401 » / « → 422 »**, puis 2 lignes grises (« Si l'en-tête … manque ou est vide »). | modèle ; attend code HTTP | #77 | Remplacé par la carte rouge (V35) — choix Rida 2026-10-25 |
| V60 | line | Ligne de réponse + station 5 | **Tirets jaunes ≈ 3 px** au-dessus de la ligne : de la station 3 vers le haut, vers la gauche, puis descente vers la personne d'entrée. Sur ce trajet, **station 5 à anneau jaune en pointillés**, étiquette « Confirme la réception » gras + machine en gris. Texte de réponse **italique** posé sur le tirets (« répond à — 201 avec l'EventOut, 401…, 422… »). | modèle ; attend codes HTTP et EventOut | #77 | Non repris : réponse sous le tapis (V16/V37) — règle « B est la base » (conflit 6) |
| V61 | line | Étiquettes d'action et de donnée sur la ligne | Textes **italiques gris-blanc** juste au-dessus de la ligne (« envoie ses comptes rendus à », « range l'événement dans »). Boîte à **bord jaune** « **compte rendu** (dans le code : EventIn) » + ligne jaune « pas encore dans le modèle ». | modèle ; attend nom de classe EventIn | #77 | Non repris : nom de la donnée sous le tapis (V13) — règle « B est la base » |
| V62 | line | Station de câblage hors ligne | Station **anneau blanc, centre vide (point)** sous la ligne, étiquette grise « Assemblage de l'application » ; reliée à la personne « qui installe » par un trait gris-violet fin « démarre » (italique gris) et à la station 1 par un trait sombre. | modèle | #77 | Non repris : câblage en bande (V29) — règle « B est la base » |
| V63 | line | Cas particulier dans le stockage | Depuis la station 4, **trait jaune en pointillés vertical** vers un **petit cercle jaune vide**, texte gris « Si le même event_id est envoyé deux fois ». | modèle ; attend nom de champ event_id | #77 | Non repris : cas particulier dans le panneau (V46) — règle « B est la base » |
| V64 | line | Panneau : liste des stations | Liste verticale : **numéro dans un cercle à bord jaune** ≈ 22 px, titre gras blanc (action) + ligne grise (machine). Encadrée par un bloc « ▶ **Départ** — … » (triangle et mot **verts**, carte bord gris) en haut et « ■ **Arrivée** — … » (carré et mot **orange**) en bas. | modèle | #77 | |
| V65 | line | Barre de lecture en bas | Barre fixe pleine largeur ≈ 60 px en bas de la zone centrale : 3 boutons carrés à bord gris (◀, ▶, ▶\|) puis texte gris « Ligne « … » · 5 étapes. Appuyez sur ▶ ou cliquez une station pour suivre la donnée. » | #77 | | |
| V66 | line | Onglets de lignes | Sous le texte projet : « Lignes : » puis pastilles arrondies, chacune avec **petit trait de couleur** (jaune, violet, rouge), nom du trajet, « N étapes » gris ; l'active a un **bord jaune** et une puce jaune pleine « principale ». | modèle | #77 | Non repris : autres trajets dans le panneau (V24) — règle « B est la base » (conflit 11) |

### Compte par écran-état

| Écran-état | Lignes |
|---|---|
| floor | 24 (V1–V24) |
| room | 22 (V25–V46) |
| room · lecture | 9 (V47–V55) |
| line (A, ligne numérotée seulement) | 11 (V56–V66) |

## Fiche machine (#79) — ajout 2026-10-26

Références : `ref-plate-watchdog.png` (haut de la fiche) et `ref-plate-watchdog-bottom.png` (bas), maquette A, clic sur la station ① « Contrôle du nom du client ». B n'a pas de fiche : la fiche de A est posée dans le panneau de B (« B est la base » pour le reste de l'écran).

| id | écran-état | élément | forme, couleur, taille, place | source | ticket | écart accepté |
|---|---|---|---|---|---|---|
| V67 | plate | Chemin au-dessus du titre | Ligne grise ≈ 13 px : la pièce « Porte d'entrée du service › », puis le nom de la machine. Le bouton « ‹ Plan » de A n'est pas repris : « ‹ Remonter » et le fil d'Ariane du haut (V1) le font déjà. | modèle | #79 | |
| V68 | plate | Titre | Nom de la machine, **gras blanc ≈ 20 px**. | modèle | #79 | |
| V69 | plate | Cases fixes | Six cases toujours dans cet ordre : FAIT, REÇOIT, REND, RÉGLAGES, OÙ, VU DANS. Libellé en **petites capitales grises ≈ 11 px, espacées**, filet gris fin entre deux cases. | fixe | #79 | |
| V70 | plate | Fait | `en_bref` en **gras blanc ≈ 16 px**, puis `role` en gris ≈ 13 px. | modèle | #79 | |
| V71 | plate | Cadre « pas encore dans le modèle — lu dans le code » | Cadre pointillé ambre autour de Reçoit / Rend / Réglages, puce ambre en haut. | — | #79 | Sans objet : depuis v1.7 ces cases viennent du modèle. Une case vide dit « pas encore dans le modèle — relancer l'étude (nouvelle méthode) » (ticket #79). |
| V72 | plate | Reçoit, Rend | Une ligne blanche ≈ 14 px par élément. Dans A, une puce de code et un lien fichier:ligne suivent : le modèle v1.7 n'en donne pas pour `entre`/`sort`, rien n'est inventé. Un refus (« ou un refus… ») est en rouge (ticket). | v1.7 | #79 | |
| V73 | plate | Réglages | Une ligne par réglage, filet entre deux : nom blanc ≈ 14 px à gauche, lien **bleu monospace fichier:ligne** à droite, puis le code exact dans une **puce monospace** sombre, puis l'effet en gris ≈ 12.5 px et la marque ✓ vérifié / ? hypothèse. | v1.7 `reglages` | #79 | Choix Rida 2026-10-26 : ligne de la maquette A, pas le tableau à 6 colonnes du ticket. |
| V74 | plate | Où | Pour chaque `expose` : nom en puce monospace, puis chemin **bleu monospace** + « l.a-b » et **« ✓ vérifié » vert** (sinon « ? non vérifié »). Puis « Fichiers : » gris et les chemins en bleu. | modèle | #79 | |
| V75 | plate | Vu dans | Un bouton à bord gris par étape faite ici : petite barre de couleur à gauche, « nom du trajet · étape N — action ». Clic : le trajet joue depuis cette étape. | calculé | #79 | La barre est jaune pour tous les trajets : le jaune ne veut dire que « donnée » (conflit 1). |

## Conflits entre les maquettes A et B

1. **Jaune = donnée ou trajet ?** Dans B, le jaune veut dire « la donnée sur le tapis » (et l'étape allumée). Dans A, le jaune est la **couleur d'une ligne** (le trajet principal) ; les autres trajets sont violet et rouge. Le jaune garde-t-il le seul sens « donnée / étape allumée » (et la ligne numérotée est toujours jaune, quel que soit le trajet) ? oui / non
2. **Rouge = refus ou trajet ?** Dans B, le rouge veut dire « refus ». Dans A, la ligne « Toute requête sans nom de client est refusée » est aussi rouge. Faut-il interdire le rouge comme couleur de trajet ? oui / non
3. **Violet pour le contrôle ?** Dans B, le contrôle (« démarre ») est un trait **gris** fin. Dans A, il est gris-violet, et le violet est aussi la couleur du trajet « Installer et démarrer ». Le contrôle reste-t-il gris comme dans B ? oui / non
4. **Tapis en tirets avec flèches (B) ou ligne pleine sans flèche (A) ?** Sur la vue floor de B, le tapis est en tirets épais avec pointes de flèche ; dans la pièce, en tronçons pleins avec pointes. A montre une ligne pleine continue sans flèche. Garde-t-on le tapis de B (avec flèches) et pose-t-on seulement les stations numérotées de A dessus ? oui / non
5. **Forme du numéro d'étape.** B : cercle à bord orange-jaune dans les machines et la carte pièce. A : disque sombre à anneau blanc/jaune épais posé **sur la ligne**. Les deux coexistent-ils (numéro sur la machine ET station sur le tapis) ? oui / non
6. **Où est la réponse ?** B place le chemin de réponse **sous** le tapis ; A le place **au-dessus** de la ligne, avec une station 5 en pointillés. On garde le dessous (B) ? oui / non
7. **Forme du refus.** B : carte rouge sous la machine, reliée par des tirets. A : court trait rouge + « → 401 » et texte gris, sans carte. On garde la carte de B ? oui / non
8. **Couleur de « Départ ».** B : « Départ : » en jaune-orangé. A : « ▶ Départ » en vert (« Arrivée » est orange dans les deux). Départ reste jaune-orangé comme B ? oui / non
9. **Place de la pastille « ENTRÉE ».** B : au-dessus du titre (floor) ou à côté de l'icône (room). A : sous le nom de la personne. On garde la place de B ? oui / non
10. **Où est le lecteur ?** B : boutons « Précédent / Lecture / Suivant » dans le panneau latéral. A : barre fixe en bas de la zone centrale. Le lecteur reste dans le panneau (B) et la barre de A est abandonnée ? oui / non
11. **Choix du trajet.** B : « Autres trajets » repliés dans le panneau, « un seul trajet à la fois ». A : onglets de couleur en haut de page. On garde le panneau de B ? oui / non
12. **Bord pointillé : un ou plusieurs sens ?** Dans B, le pointillé veut dire à la fois « lu dans le code, pas encore dans le modèle » (V5, légende), « autour du projet » (V18), les puces entrée/sortie des machines (V32), la bande de câblage (V29) et la carte d'entrée réduite (V27). Dans A, le cadre de la pièce lui-même est en tirets blancs. Faut-il réserver le pointillé gris à un seul sens ? oui / non
13. **Marque « pas encore dans le modèle ».** B : puce à bord pointillé gris. A : texte jaune sous une boîte à bord jaune plein. On garde la puce pointillée grise de B ? oui / non
14. **Cylindre de stockage.** B : bord orange-jaune, fond brun. A : bord jaune, fond noir, station 4 posée sur la ligne au-dessus du cylindre. On garde le cylindre de B, avec la station 4 sur le tapis juste avant ? oui / non
15. **Nom de la zone hors flux.** B : « Autour du projet (ne tourne pas) », 3 cartes pointillées. A : « Atelier — à côté du flux », 2 cartes à bord plein, et la légende de A ajoute « Atelier (hors flux) » et « Correspondance ». On garde le nom et la légende de B ? oui / non
16. **Jaune pour « texte du modèle, technique ».** Dans B, cette puce est jaune alors que le jaune est aussi la donnée et l'étape allumée. Faut-il lui donner une autre couleur ? oui / non
17. **Bleu pour la pièce et pour les liens.** Dans B, le bleu marque à la fois la barre gauche d'une pièce (service), les liens « Entrer › » et les chemins de fichier. Acceptable ? oui / non

## Réponses de Rida (2026-10-25)

Règle générale : **B est la base** ; de A on garde seulement le mouvement de la ligne (le tronçon actif qui s'allume, V49) et la liste des étapes avec Départ / Arrivée (V64).
- Conflit 1 (jaune) : **oui, tapis jaune comme B** ; l'étape en cours = jaune vif + halo, les autres tronçons ocre éteint (V47-V49).
- Conflit 10 (lecteur) : **barre fixe en bas (A)** ; le lecteur du panneau (V42, V43, V52, V54) n'est pas repris.
- Conflit 7 (refus) : **grande carte rouge (B)**, V35.
- Conflit 5 (numéros) : **cercle numéroté dans la machine (B)**, V31 ; pas de station sur la ligne (V57).
- Conflits 2, 3, 4, 6, 8, 9, 11, 13, 14, 15 : réglés par la règle « B est la base ».
- Conflit 12 (pointillé à plusieurs sens), 16 (jaune de « texte du modèle »), 17 (bleu) : gardés comme dans B.
- V35 : le texte coupé de « refus 422 » est un défaut de la maquette, pas à recopier.
- V55 (2026-10-26, #77) : **OK Rida** — pendant la lecture, « Échap : arrêter le chemin » remplace « ‹ Remonter (Échap) » (Échap arrête le trajet, ticket #77 point 8). Écran réel validé côte à côte (« oui »).

## Attribution

Éléments de la maquette : 66, attribués : 66, sans ticket : 0. Floor #75 (V1-V24), pièce #76 (V25-V46), lecture #77 (V47-V66).
