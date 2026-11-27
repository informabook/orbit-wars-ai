"""Build the French V5.1 public edition from the canonical V5 and audited tables."""

import argparse
from collections import Counter
import csv
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from textwrap import fill

import matplotlib
matplotlib.use("Agg")
from matplotlib import pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.lines import Line2D
from matplotlib.patches import FancyBboxPatch
import pymupdf as pdf

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
RESULTS = ROOT / "results"
V5 = HERE / "rapport_orbit_wars_v5_post_cloture.pdf"
V51 = HERE / "rapport_orbit_wars_v5_1_edition_publique.pdf"
V5_SHA = "fdf0fc33690978d97d288c4afd49c70e6635f56dec9919ba11176a355db14207"
BLUE, TEAL, AMBER, RED, INK, GRID = "#285085", "#197770", "#a86718", "#af4549", "#172a3f", "#d6e1e9"
COLORS = (BLUE, TEAL, AMBER, RED)
PAPER = "#ffffff"


def table(name):
    with (RESULTS / name).open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def check_sources():
    assert hashlib.sha256(V5.read_bytes()).hexdigest() == V5_SHA
    phase = RESULTS / "phase3"
    manifest = json.loads((phase / "EXPERIMENT_MANIFEST.json").read_text(encoding="utf-8"))
    for item in manifest["tables"]:
        path = phase / item["table"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == item["sha256"], path.name
        assert len(table(path.resolve().relative_to(RESULTS.resolve()))) == item["rows"]
    candidates = table("evolution_candidates.csv")
    matches = table("evolution_matches.csv")
    assert len(candidates) == 52 and len(matches) == 253
    assert Counter(row["status"] for row in matches) == {"OK": 231, "TIMEOUT": 8, "BAD_OUTPUT": 14}


def sheet(number, title, kind, caption, source):
    fig = plt.figure(figsize=(8.2677, 11.6929), facecolor=PAPER)
    fig.text(.085, .948, "ORBIT WARS  /  ANNEXE ILLUSTRÉE DE L’ÉDITION V5.1",
             fontsize=9, color=TEAL, fontweight="bold")
    fig.add_artist(Line2D([.085, .915], [.932, .932], color=GRID, linewidth=1))
    fig.text(.085, .898, f"Figure A{number:02d}  ·  {kind.upper()}", fontsize=9, color=BLUE, fontweight="bold")
    fig.text(.085, .867, fill(title, 44), fontsize=20, color=INK, fontweight="bold", va="top", linespacing=1.23)
    fig.text(.085, .208, "Lecture", color=TEAL, fontsize=11, fontweight="bold")
    fig.text(.085, .184, fill(caption, 94), fontsize=10, va="top", color=INK, linespacing=1.5)
    fig.text(.085, .096, fill("Source : " + source, 112), fontsize=8.1, color=BLUE, va="top", linespacing=1.35)
    fig.add_artist(Line2D([.085, .915], [.061, .061], color=GRID, linewidth=1))
    fig.text(.085, .043, "Florent Schobyn  ·  Rapport historique du 15 juillet 2026  ·  Édition de novembre 2026", fontsize=7.9, color=BLUE)
    fig.text(.915, .043, f"{80+number}", fontsize=9, color=INK, ha="right")
    return fig


def axes(fig, rect=(.14, .31, .73, .44)):
    ax = fig.add_axes(rect)
    ax.grid(axis="y", color=GRID, linewidth=.7)
    ax.set_axisbelow(True)
    ax.spines[["right", "top"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#a6b7c6")
    return ax


def diagram(fig, nodes):
    area = fig.add_axes((.13, .265, .74, .49))
    area.set(xlim=(0, 1), ylim=(0, 1))
    area.axis("off")
    stride = 1 / len(nodes)
    for i, (title, detail) in enumerate(nodes):
        y = 1 - (i + .53) * stride
        height = stride * .69
        area.add_patch(FancyBboxPatch((.03, y - height / 2), .94, height,
                       boxstyle="round,pad=0.006,rounding_size=.015", edgecolor=COLORS[i % 3],
                       facecolor="#f3f7fa", linewidth=1.15))
        area.text(.065, y + height * .16, title, color=INK, weight="bold", fontsize=13, va="center")
        area.text(.065, y - height * .21, detail, color=BLUE, fontsize=9.4, va="center")
        if i:
            top = y + height / 2
            area.annotate("", xy=(.5, top + .004), xytext=(.5, top + stride * .24),
                          arrowprops={"arrowstyle": "-|>", "color": TEAL, "lw": 1.3})


def chronology():
    fig = sheet(1, "Chronologie des traces de recherche", "Jalons documentés",
                "Les dates désignent les traces identifiées dans les archives et la date portée par le rapport. "
                "Elles ne donnent ni les heures de début et de fin des campagnes, ni une durée de calcul.",
                "Inventaire historique des scripts OrbitLab, Intelligent Evolution V6, Beast Lab V16–V18 et rapport V5.")
    diagram(fig, [("16 juin 2026  ·  OrbitLab", "Tournois locaux, instantanés de jeu et analyse des résultats."),
                  ("17 juin 2026  ·  Intelligent Evolution V6", "Finalistes, mutations situationnelles et combinaisons de parents."),
                  ("22 juin 2026  ·  Beast Lab V16 à V18", "Diagnostics par replay, mutations guidées et validation par étapes."),
                  ("15 juillet 2026  ·  Rapport V5", "Synthèse après clôture et comparaison rétrospective du podium.")])
    return fig


def genealogy():
    candidates = table("evolution_candidates.csv")
    observed = {row["name"] for row in candidates}
    generations = sorted({int(row["generation"]) for row in candidates})
    groups = {g: sorted(row["name"] for row in candidates if int(row["generation"]) == g) for g in generations}
    missing = sorted({p for row in candidates for p in json.loads(row["parents_json"]) if p not in observed})
    fig = sheet(2, "Généalogie des 52 candidats observés", "Données archivées",
                f"Une ligne relie un parent explicitement cité à son enfant. {len(missing)} parent(s) cité(s) "
                "ne figurent pas dans la table. Les points sont espacés pour la lecture et ne représentent pas un score.",
                "results/evolution_candidates.csv, champ parents_json. Aucun parent supplémentaire inféré.")
    ax = fig.add_axes((.15, .305, .7, .45))
    pos = {}
    layout = dict(groups)
    if missing:
        layout[-1] = missing
    for g, names in layout.items():
        for i, name in enumerate(names):
            pos[name] = (g, (i + 1) / (len(names) + 1))
    for row in candidates:
        x1, y1 = pos[row["name"]]
        for parent in json.loads(row["parents_json"]):
            x0, y0 = pos[parent]
            ax.plot([x0, x1], [y0, y1], color="#7a98b1", linewidth=.7, alpha=.52, zorder=1)
    for g, names in layout.items():
        ax.scatter([g] * len(names), [pos[name][1] for name in names], s=25,
                   color=COLORS[g % 4], zorder=2)
    ax.set_xticks(list(layout), [f"G{g}\n{len(names)} candidats" if g >= 0 else f"Hors table\n{len(names)} parent(s)" for g, names in layout.items()])
    ax.set_yticks([])
    ax.set_ylim(-.01, 1.01)
    ax.spines[["right", "left", "top"]].set_visible(False)
    return fig


def beast_architecture():
    fig = sheet(3, "Architecture méthodologique de Beast Lab", "Schéma historique",
                "Le schéma représente les opérations du code V18 examiné. L’archive des mesures est associée à "
                "un rapport titré V13. Le numéro de version exact responsable de ce run reste indéterminé.",
                "Scripts Beast Lab V16–V18 et fonctions d’évaluation conservées. Planches conceptuelles originales.")
    diagram(fig, [("Replays locaux", "Chronologies, production, flottes et actions de la place 0."),
                  ("Diagnostics par situation", "Rangs, symétrie, déficit, neutralité et pertes de position."),
                  ("Population guidée", "Familles paramétriques globales et spécifiques au mode 4P."),
                  ("Évaluation échelonnée", "Smoke, Fast, Anti-Mirage, Full et Holdout dans le code."),
                  ("Sélection et export local", "Sorties examinées avec la provenance et les limites du run.")])
    return fig


def guidance():
    fig = sheet(4, "Des erreurs de jeu aux variantes guidées", "Schéma historique",
                "Les règles donnent des hypothèses à tester. Un replay peut porter plusieurs étiquettes. "
                "Les fréquences qui pondèrent la génération comptent les étiquettes retenues. "
                "Le schéma ne mesure aucune efficacité stratégique.",
                "classify_failure_situations, guidance_weight, build_guided_population et mutate_spec_guided, V18.")
    diagram(fig, [("Mesurer la situation", "Écart de flotte ou de production, rang au tour 80, actions en ouverture."),
                  ("Attribuer des étiquettes", "Exemple : grandes neutres libres et retard de production."),
                  ("Pondérer les familles", "Poids historique : max(1, 1 + 6 × proportion d’étiquettes)."),
                  ("Échantillonner puis muter", "Représentants directs, tirages pondérés et exploration aléatoire."),
                  ("Tester sur des paramètres patchables", "Validation avec états terminaux et seeds vérifiés dans l’adaptateur.")])
    return fig


def orbit_counts():
    counts = Counter((row["mode"].upper(), row["status"]) for row in table("phase3/orbitlab_individual_matches.csv"))
    assert sum(counts.values()) == 5800
    fig = sheet(5, "Tentatives locales OrbitLab", "Données archivées",
                "Le journal contient 5 800 enregistrements, dont 1 962 marqués OK et 3 838 marqués ERROR. "
                "Les états terminaux par joueur manquent. OK reprend l’étiquette du journal et ne valide pas le match a posteriori.",
                "results/phase3/orbitlab_individual_matches.csv, agrégation par mode et statut.")
    ax = axes(fig)
    modes = sorted({mode for mode, _ in counts})
    ok = [counts[m, "OK"] for m in modes]
    errors = [counts[m, "ERROR"] for m in modes]
    for offset, values, label, color in ((-.18, ok, "OK enregistré", TEAL), (.18, errors, "ERROR enregistré", AMBER)):
        bars = ax.bar([i+offset for i in range(len(modes))], values, .32, label=label, color=color)
        ax.bar_label(bars, padding=4)
    ax.set_xticks(range(len(modes)), modes)
    ax.set(ylabel="Tentatives enregistrées", ylim=(0, max(ok+errors)*1.18))
    ax.legend(frameon=False)
    return fig


def evolution_attempts():
    matches = table("evolution_matches.csv")
    status = Counter((row["phase"], row["status"]) for row in matches)
    phases = list(dict.fromkeys(row["phase"] for row in matches))
    fig = sheet(6, "Évaluations du journal évolutif", "Données archivées",
                "Le journal relie 52 candidats à 253 tentatives. Il enregistre 8 délais dépassés et 14 sorties invalides. "
                "Le journal utilise ses propres identifiants. Ses tentatives ne s’additionnent pas aux archives OrbitLab.",
                "results/evolution_matches.csv et results/evolution_candidates.csv.")
    ax = axes(fig, (.27, .31, .62, .46))
    ax.grid(False)
    ax.grid(axis="x", color=GRID, linewidth=.7)
    base = [0] * len(phases)
    labels = {"OK": "OK", "TIMEOUT": "Délai dépassé", "BAD_OUTPUT": "Sortie invalide"}
    for state, color in (("OK", BLUE), ("TIMEOUT", RED), ("BAD_OUTPUT", AMBER)):
        values = [status[phase, state] for phase in phases]
        ax.barh(range(len(phases)), values, left=base, label=labels[state], color=color)
        base = [a+b for a,b in zip(base, values)]
    ax.set_yticks(range(len(phases)), [phase.replace("originals_plus_top4", "originaux + top 4").replace("_", " ") for phase in phases])
    ax.invert_yaxis()
    ax.set_xlabel("Tentatives")
    ax.legend(frameon=False, loc="lower right")
    return fig


def ranker():
    points = table("phase3/v14_training_curve.csv")
    fig = sheet(7, "Apprentissage du ranker linéaire V14", "Données archivées",
                "Le meilleur AUC de validation historique vaut 0,886154 selon la métrique approximative du code. "
                "La séparation se faisait au niveau des exemples et pouvait partager des replays. Le coefficient exporté vaut zéro.",
                "results/phase3/v14_training_curve.csv et ranker_v14_summary.json. 131 points, 134 051 exemples.")
    for origin, fields, ylabel in ((.54, ("train_auc", "val_auc"), "AUC ROC approx."),
                                   (.29, ("train_loss", "val_loss"), "Perte pondérée")):
        ax = axes(fig, (.15, origin, .72, .19))
        for name, color, label in zip(fields, (TEAL, AMBER), ("Entraînement", "Validation")):
            ax.plot([int(row["epoch"]) for row in points], [float(row[name]) for row in points], color=color, label=label)
        ax.set(ylabel=ylabel, xlabel="Époque")
        ax.legend(frameon=False, fontsize=8, loc="best")
    return fig


def replay_stats():
    rows = table("phase3/beast_replay_statistics.csv")
    fig = sheet(8, "Résultats des 312 analyses de replays", "Données archivées",
                "Le résultat correspond au point de vue de la place 0. Les égalités sont comptées dans les nuls "
                "même si la place 0 perd face aux ex æquo. La sélection n’établit aucun taux de victoire prospectif.",
                "results/phase3/beast_replay_statistics.csv. Les 193 replays 2P et 119 replays 4P sont comptés séparément.")
    ax = axes(fig)
    modes = ("2P", "4P")
    base = [0, 0]
    outcome = Counter((row["mode"], "draw" if int(row["draw"]) else
                       "p0_strict_win" if int(row["p0_strict_win"]) else "p0_loss") for row in rows)
    for key, label, color in (("p0_strict_win", "Victoire stricte", TEAL), ("draw", "Nul archivé", BLUE), ("p0_loss", "Défaite hors égalités", AMBER)):
        values = [outcome[mode, key] for mode in modes]
        bars = ax.bar(modes, values, bottom=base, label=label, color=color, width=.48)
        ax.bar_label(bars, labels=[str(v) if v else "" for v in values], label_type="center", color="white", fontweight="bold")
        base = [a+b for a,b in zip(base, values)]
    assert base == [193, 119]
    ax.set(ylabel="Replays", ylim=(0, max(base)*1.26))
    ax.legend(frameon=False)
    return fig


def stages():
    records = table("phase3/beast_stage_results.csv")
    fig = sheet(9, "Candidats évalués par étape de Beast Lab", "Données archivées",
                "Les nombres indiquent les lignes récupérées par étape. Tous les deltas combinés Full sont négatifs. "
                "Les raisons de rejet et les décisions individuelles de gate ne sont pas récupérées. Aucun score Holdout n’est attesté.",
                "results/phase3/beast_stage_results.csv. Les points portent les deltas de récompense archivés.")
    ax = axes(fig)
    ax.axhline(0, color=INK, lw=.9)
    steps = ("fast", "anti-mirage", "full")
    captions = []
    for i, stage in enumerate(steps):
        subset = [row for row in records if row["stage"] == stage]
        points = sorted(float(row["combined"]) for row in subset if row["combined"])
        locations = [i + .026*(n - (len(points)-1)/2) for n in range(len(points))]
        ax.scatter(locations, points, s=31, color=COLORS[i], alpha=.83)
        caption = {"fast": "Fast", "anti-mirage": "Anti-Mirage", "full": "Full"}[stage]
        captions.append(f"{caption}\n{len(subset)} évaluations")
    ax.set_xticks(range(3), captions)
    ax.set(xlim=(-.5, 2.5), ylabel="Delta de récompense combiné")
    return fig


def contextual():
    fig = sheet(10, "Politiques distinctes pour les modes 2P et 4P", "Schéma conceptuel",
                "La sélection de paramètres par mode et l’évaluation d’un hybride sont présentes dans les sources. "
                "Dans l’interface publique, le routage se fonde sur le nombre de places prévues au départ. "
                "Le schéma ne relie aucune variante à la soumission Kaggle finale.",
                "Beast Lab V18, build_hybrid_spec. Routage Phase 3 et adaptateurs de reproduction v0.3.1.")
    diagram(fig, [("Séparer les observations par mode", "Récompenses 2P et 4P, tailles d’échantillon et erreurs."),
                  ("Choisir une configuration 2P", "Appliquer les réglages globaux du candidat choisi en duel."),
                  ("Choisir une configuration 4P", "Appliquer les réglages contextuels du candidat choisi en mêlée."),
                  ("Évaluer l’hybride", "Répliquer avec des seeds fixées et des adversaires documentés.")])
    return fig


def cover(page):
    old = "Étudiant en bac 1 informatique, EPL"
    matches = page.search_for(old)
    if len(matches) != 1:
        raise ValueError(f"Expected exactly one original academic line, found {len(matches)}")
    region = matches[0]
    page.add_redact_annot(region, fill=False)
    page.apply_redactions(images=0, graphics=0)
    center = page.rect.width / 2
    inform = "Étudiant en bac 2 informatique, École polytechnique de Louvain (EPL), UCLouvain"
    edition = "Statut académique en novembre 2026 · Édition publique V5.1"
    font = pdf.Font("tiro")
    for value, point, baseline in ((inform, 10.5, region.y0 + 9.5), (edition, 8.25, region.y1 + 7.8)):
        left = center - font.text_length(value, fontsize=point) / 2
        page.insert_text((left, baseline), value, fontsize=point, fontname="tiro", color=(0, 0, 0))
    assert inform in page.get_text() and old not in page.get_text() and "15 juillet 2026" in page.get_text()


def build(destination):
    if destination.resolve() == V5.resolve():
        raise ValueError("Keep the historical V5 PDF unmodified")
    check_sources()
    with TemporaryDirectory(prefix="orbit-v51-") as tmp, pdf.open(V5) as original:
        assert len(original) == 80
        appendix = Path(tmp) / "appendix.pdf"
        metadata = {"Title": "Annexe illustrée du rapport Orbit Wars V5.1",
                    "Author": "Florent Schobyn",
                    "CreationDate": datetime(2026, 11, 27, tzinfo=UTC)}
        with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11, "pdf.fonttype": 42,
                             "text.color": INK, "axes.labelcolor": INK}), PdfPages(appendix, metadata=metadata) as out:
            plots = (chronology, genealogy, beast_architecture, guidance, orbit_counts,
                     evolution_attempts, ranker, replay_stats, stages, contextual)
            for render in plots:
                fig = render()
                out.savefig(fig)
                plt.close(fig)
        cover(original[0])
        with pdf.open(appendix) as extra:
            original.insert_pdf(extra)
        original.save(destination, deflate=True, no_new_id=True)


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("--out", type=Path, default=V51)
    build(cli.parse_args().out)

