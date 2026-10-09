# -*- coding: utf-8 -*-
"""
================================================================================
 SMARTSKILLS — Application RH de gestion de la formation et des compétences
 SmartFactory (entreprise fictive) — Projet universitaire — Données 100% fictives
================================================================================
 Fichier unique, sans dépendance externe (bibliothèque standard Python uniquement).

 Lancement :
     python smartskills.py
 Puis ouvrir http://localhost:8090 dans le navigateur.
 Comptes de démonstration (mot de passe commun : demo) :
     sf-1002  salarié   (Camille D.)
     sf-1015  manager   (Karim B., équipe Maintenance)
     sf-2001  DRH/Formation (Nadia L.)
     sf-9001  administrateur (Admin Technique)

 Persistance : les données sont sauvegardées dans smartskills_data.json
 (créé à côté du script). POST /api/reset restaure les données de démonstration.

 Avertissement RGPD : application de démonstration pédagogique. Aucune donnée
 réelle n'est traitée. L'authentification est simplifiée et ne convient pas à la
 production (voir l'écran « Documentation » dans l'application).
================================================================================
"""

import json
import os
import re
import sys
import uuid
import hashlib
from datetime import date, datetime, timedelta
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

VERSION = "1.0.0"
HOST = "localhost"
PORT = 8090
DATA_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "smartskills_data.json")
TODAY = date(2026, 10, 9)          # date de référence de la démonstration
YEAR = 2026

# -----------------------------------------------------------------------------
# Échelle de niveaux (utilisée par l'autoévaluation et les référentiels)
# -----------------------------------------------------------------------------
LEVELS = {
    1: "Débutant — notions très limitées, besoin d'accompagnement permanent",
    2: "Notions de base — sait faire des tâches simples avec aide ponctuelle",
    3: "Autonome — réalise les tâches du poste sans assistance",
    4: "Avancé — maîtrise solide, capable de former et d'analyser",
    5: "Expert — référence interne, conçoit et améliore les pratiques",
}

# -----------------------------------------------------------------------------
# SEED — Données fictives de démonstration
# -----------------------------------------------------------------------------

def seed_data():
    """Construit le jeu de données de démonstration (totalement fictif)."""
    d = {}

    # ----- Services -----------------------------------------------------------
    d["services"] = [
        {"id": "SVC-01", "nom": "Production"},
        {"id": "SVC-02", "nom": "Maintenance"},
        {"id": "SVC-03", "nom": "Qualité"},
        {"id": "SVC-04", "nom": "Méthodes & Ingénierie"},
        {"id": "SVC-05", "nom": "Logistique"},
        {"id": "SVC-06", "nom": "IT & Data"},
    ]

    # ----- Métiers (parcours types) ------------------------------------------
    d["metiers"] = [
        {"id": "MET-01", "nom": "Technicien de maintenance", "service_id": "SVC-02",
         "competences_cibles": {
            "CPT-01": 4, "CPT-02": 3, "CPT-03": 3, "CPT-05": 2, "CPT-09": 2,
            "CPT-16": 3, "CPT-17": 2},
         "competences_critiques": ["CPT-01", "CPT-02"],
         "parcours": [
            {"etape": 1, "titre": "Fondamentaux maintenance",
             "objectif": "Atteindre l'autonomie (niveau 3) en mécanique et électrique",
             "formations": ["FOR-01", "FOR-02"]},
            {"etape": 2, "titre": "Maintenance avancée & prédictive",
             "objectif": "Maîtriser le diagnostic, la GMAO et la maintenance prédictive",
             "formations": ["FOR-03", "FOR-04"]},
            {"etape": 3, "titre": "Industrie 4.0 appliquée à la maintenance",
             "objectif": "Intégrer capteurs, jumeau numérique et cybersécurité OT",
             "formations": ["FOR-05", "FOR-12"]}],
         "formations_obligatoires": [{"formation_id": "FOR-06", "validite_mois": 36}]},
        {"id": "MET-02", "nom": "Opérateur de production", "service_id": "SVC-01",
         "competences_cibles": {
            "CPT-07": 3, "CPT-08": 2, "CPT-09": 3, "CPT-15": 2, "CPT-16": 3},
         "competences_critiques": ["CPT-09"],
         "parcours": [
            {"etape": 1, "titre": "Bonnes pratiques de production",
             "objectif": "Sécurité, 5S et qualité à la source (niveau 3)",
             "formations": ["FOR-06", "FOR-07"]},
            {"etape": 2, "titre": "Amélioration continue opérateur",
             "objectif": "Contribuer aux cercles de qualité et à la résolution de problèmes",
             "formations": ["FOR-08"]},
            {"etape": 3, "titre": "Vers un rôle d'opérateur polyvalent / leader de quart",
             "objectif": "Polyvalence sur lignes et encadrement informel",
             "formations": ["FOR-15"]}],
         "formations_obligatoires": [{"formation_id": "FOR-06", "validite_mois": 36}]},
        {"id": "MET-03", "nom": "Responsable d'équipe", "service_id": None,
         "competences_cibles": {
            "CPT-14": 4, "CPT-15": 4, "CPT-09": 3, "CPT-18": 3},
         "competences_critiques": ["CPT-14"],
         "parcours": [
            {"etape": 1, "titre": "Fondamentaux du management d'équipe",
             "objectif": "Pilotage opérationnel, entretiens, animation (niveau 3)",
             "formations": ["FOR-15"]},
            {"etape": 2, "titre": "Management de la performance",
             "objectif": "Fixer des objectifs, mesurer, accompagner (niveau 4)",
             "formations": ["FOR-16"]}],
         "formations_obligatoires": []},
        {"id": "MET-04", "nom": "Ingénieur méthodes", "service_id": "SVC-04",
         "competences_cibles": {
            "CPT-13": 4, "CPT-18": 4, "CPT-07": 3, "CPT-10": 2, "CPT-11": 3},
         "competences_critiques": ["CPT-13", "CPT-18"],
         "parcours": [
            {"etape": 1, "titre": "Amélioration des processus industriels",
             "objectif": "Lean, études de temps et industrialisation (niveau 4)",
             "formations": ["FOR-07", "FOR-08"]},
            {"etape": 2, "titre": "Données & simulation au service des méthodes",
             "objectif": "Exploiter les données de production et simuler (niveau 3)",
             "formations": ["FOR-10", "FOR-11"]}],
         "formations_obligatoires": []},
        {"id": "MET-05", "nom": "Technicien qualité", "service_id": "SVC-03",
         "competences_cibles": {
            "CPT-07": 4, "CPT-08": 4, "CPT-10": 3, "CPT-09": 2, "CPT-16": 2},
         "competences_critiques": ["CPT-08", "CPT-10"],
         "parcours": [
            {"etape": 1, "titre": "Socle qualité industrielle",
             "objectif": "Maîtrise SPC et gestion des non-conformités (niveau 4)",
             "formations": ["FOR-09", "FOR-08"]},
            {"etape": 2, "titre": "Audit & système qualité",
             "objectif": "Auditer un processus selon ISO 9001 (niveau 3)",
             "formations": ["FOR-17"]}],
         "formations_obligatoires": [{"formation_id": "FOR-06", "validite_mois": 36}]},
        {"id": "MET-06", "nom": "Analyste de données industrielles", "service_id": "SVC-06",
         "competences_cibles": {
            "CPT-11": 4, "CPT-12": 3, "CPT-13": 4, "CPT-19": 2, "CPT-05": 2},
         "competences_critiques": ["CPT-11", "CPT-13"],
         "parcours": [
            {"etape": 1, "titre": "Socle data industriel",
             "objectif": "SQL, Python et visualisation appliqués à l'industrie (niveau 4)",
             "formations": ["FOR-10", "FOR-11"]},
            {"etape": 2, "titre": "Analyse avancée & prédictif",
             "objectif": "Modèles prédictifs de maintenance et de qualité (niveau 4)",
             "formations": ["FOR-18", "FOR-05"]},
            {"etape": 3, "titre": "Sécurisation des données industrielles",
             "objectif": "Cybersécurité OT/IT et gouvernance des données (niveau 2)",
             "formations": ["FOR-12", "FOR-19"]}],
         "formations_obligatoires": []},
    ]

    # ----- Compétences ---------------------------------------------------------
    d["competences"] = [
        {"id": "CPT-01", "nom": "Maintenance mécanique", "theme": "Maintenance",
         "critique": True,  "description": "Diagnostic et intervention sur les équipements mécaniques (roulements, transmissions, hydraulique)."},
        {"id": "CPT-02", "nom": "Maintenance électrique & automatismes", "theme": "Maintenance",
         "critique": True,  "description": "Lecture de schémas électriques, dépannage et automates (API/ASI)."},
        {"id": "CPT-03", "nom": "Maintenance prédictive", "theme": "Maintenance",
         "critique": False, "description": "Analyse vibratoire, thermographie, surveillance d'état."},
        {"id": "CPT-04", "nom": "GMAO & gestion des interventions", "theme": "Maintenance",
         "critique": False, "description": "Saisie et exploitation des ordres de travail dans la GMAO."},
        {"id": "CPT-05", "nom": "Robotique & automatisation", "theme": "Production",
         "critique": True,  "description": "Paramétrage et supervision de cellules robotisées."},
        {"id": "CPT-06", "nom": "Pilotage des lignes de production", "theme": "Production",
         "critique": False, "description": "Suivi des indicateurs de ligne (TRS, cadence, qualité)."},
        {"id": "CPT-07", "nom": "Lean & amélioration continue", "theme": "Méthodes",
         "critique": False, "description": "5S, gaspillages, Kaizen, A3."},
        {"id": "CPT-08", "nom": "SPC — contrôle statistique des procédés", "theme": "Qualité",
         "critique": True,  "description": "Cartes de contrôle, capabilité, échantillonnage."},
        {"id": "CPT-09", "nom": "Sécurité & prévention des risques", "theme": "Transverse",
         "critique": True,  "description": "Règles de sécurité industrielle, permis de travail, analyse de risques."},
        {"id": "CPT-10", "nom": "Gestion des non-conformités & 8D", "theme": "Qualité",
         "critique": True,  "description": "Mise en œuvre de la démarche 8D et actions correctives."},
        {"id": "CPT-11", "nom": "Analyse de données (Python/SQL)", "theme": "Data & IA",
         "critique": True,  "description": "Extraction, nettoyage et analyse de données avec Python et SQL."},
        {"id": "CPT-12", "nom": "Tableaux de bord & visualisation", "theme": "Data & IA",
         "critique": False, "description": "Conception de tableaux de bord décisionnels."},
        {"id": "CPT-13", "nom": "Statistiques appliquées à l'industrie", "theme": "Data & IA",
         "critique": True,  "description": "Tests, régression, séries temporelles appliqués aux données de production."},
        {"id": "CPT-14", "nom": "Management d'équipe", "theme": "Transverse",
         "critique": False, "description": "Animation, entretiens, gestion des conflits, développement des talents."},
        {"id": "CPT-15", "nom": "Leadership opérationnel", "theme": "Transverse",
         "critique": False, "description": "Priorisation, prise de décision en situation d'incertitude, transmission."},
        {"id": "CPT-16", "nom": "Méthodologie projet", "theme": "Transverse",
         "critique": False, "description": "Planification, pilotage et restitution de projets."},
        {"id": "CPT-17", "nom": "Jumeau numérique & capteurs IoT", "theme": "Data & IA",
         "critique": False, "description": "Instrumentation, flux de données terrain et jumeau numérique."},
        {"id": "CPT-18", "nom": "Cybersécurité industrielle (OT)", "theme": "Cybersécurité",
         "critique": True,  "description": "Protection des systèmes opérationnels, segmentation, incidents OT."},
        {"id": "CPT-19", "nom": "Gouvernance & qualité des données", "theme": "Data & IA",
         "critique": False, "description": "Fiabilisation, traçabilité et partage responsable des données."},
    ]

    # ----- Prestataires --------------------------------------------------------
    d["prestataires"] = [
        {"id": "PRE-01", "nom": "Académie SmartFactory (interne)", "type": "Interne",
         "contact": "formation@smartfactory-demo.fr", "note_qualite": 4.2},
        {"id": "PRE-02", "nom": "IFM Industries Formation", "type": "Externe",
         "contact": "contact@ifm-industries-demo.fr", "note_qualite": 4.5},
        {"id": "PRE-03", "nom": "ProForma Digital", "type": "Externe",
         "contact": "hello@proforma-demo.fr", "note_qualite": 4.0},
        {"id": "PRE-04", "nom": "Centre Expert Maintenance", "type": "Externe",
         "contact": "info@cem-demo.fr", "note_qualite": 4.3},
    ]

    # ----- Formations ----------------------------------------------------------
    def F(fid, titre, theme, format_, duree, cout, pre_id, niveau, descriptif,
          objectifs, competences, prerequis, evaluation, public):
        return {"id": fid, "titre": titre, "theme": theme, "format": format_,
                "duree_h": duree, "cout": cout, "prestataire_id": pre_id, "niveau": niveau,
                "description": descriptif, "objectifs": objectifs,
                "competences": competences, "prerequis": prerequis,
                "evaluation": evaluation, "public_cible": public}

    d["formations"] = [
        F("FOR-01", "Fondamentaux de la maintenance mécanique", "Maintenance", "Présentiel",
          28, 1450, "PRE-04", 1,
          "Initiation au diagnostic et aux interventions mécaniques courantes sur machines industrielles.",
          ["Identifier les composants mécaniques usuels (roulements, courroies, réducteurs)",
           "Réaliser un démontage / remontage simple en respectant la sécurité",
           "Remplir un rapport d'intervention complet"],
          ["CPT-01", "CPT-09"], [],
          "Contrôle pratique sur banc d'essai + quiz de fin de formation.",
          "Techniciens de maintenance, opérateurs polyvalents"),
        F("FOR-02", "Électrotechnique & automatismes pour la maintenance", "Maintenance", "Blended",
          35, 1980, "PRE-04", 2,
          "Lecture de schémas électriques, dépannage des armoires et prise en main d'automates.",
          ["Lire et tracer un schéma électrique industriel",
           "Diagnostiquer une panne sur automate (API/ASI)",
           "Intervenir en sécurité sur une armoire basse tension"],
          ["CPT-02", "CPT-09"], [],
          "Étude de cas fil rouge + évaluation pratique en atelier.",
          "Techniciens de maintenance avec bases électriques"),
        F("FOR-03", "Maintenance prédictive : vibratoire & thermographie", "Maintenance", "Présentiel",
          21, 2200, "PRE-04", 3,
          "Méthodes de surveillance d'état pour anticiper les pannes.",
          ["Planifier une campagne vibratoire sur un équipement critique",
           "Interpréter un thermogramme et détecter une anomalie",
           "Formuler une recommandation d'intervention argumentée"],
          ["CPT-03", "CPT-01"], [{"type": "competence", "id": "CPT-01", "niveau_min": 2,
                                   "libelle": "Maintenance mécanique niveau ≥ 2"}],
          "Mise en situation sur équipements instrumentés.",
          "Techniciens de maintenance confirmés"),
        F("FOR-04", "Maîtriser la GMAO et les ordres de travail", "Maintenance", "E-learning",
          14, 620, "PRE-01", 1,
          "Saisie, suivi et analyse des données de maintenance dans l'outil GMAO.",
          ["Saisir un ordre de travail complet et conforme",
           "Exploiter les indicateurs GMAO (coût, MTBF)"],
          ["CPT-04"], [],
          "Quiz en ligne noté (seuil de validation : 75 %).", "Tous techniciens maintenance"),
        F("FOR-05", "Jumeau numérique & capteurs IoT industriels", "Data & IA", "Blended",
          28, 2450, "PRE-03", 3,
          "Instrumenter une ligne et exploiter son jumeau numérique.",
          ["Choisir des capteurs adaptés à un équipement",
           "Connecter un flux de données terrain vers la plateforme",
           "Construire une vue jumeau simplifiée d'un poste"],
          ["CPT-17", "CPT-05"], [{"type": "competence", "id": "CPT-02", "niveau_min": 2,
                                   "libelle": "Automatismes niveau ≥ 2"}],
          "Projet de groupe évalué en fin de parcours.",
          "Techniciens maintenance, ingénieurs méthodes, analystes data"),
        F("FOR-06", "Sécurité industrielle & permis de travail (obligatoire)", "Transverse", "Présentiel",
          7, 380, "PRE-01", 1,
          "Rappel des règles de sécurité, analyse de risques et permis de travail. Formation obligatoire pour les métiers exposés.",
          ["Appliquer les règles de consignation et de permis de travail",
           "Participer à une analyse de risques (5M / arbre des causes)"],
          ["CPT-09"], [],
          "QCM obligatoire (seuil : 80 %) + observation en situation réelle.",
          "Tous salariés des sites industriels"),
        F("FOR-07", "Lean manufacturing pour les équipes terrain", "Méthodes", "Présentiel",
          21, 1350, "PRE-02", 2,
          "Les fondamentaux du lean appliqués aux ateliers.",
          ["Identifier les 8 gaspillages sur son poste",
           "Déployer un chantier 5S complet",
           "Rédiger un A3 simple"],
          ["CPT-07", "CPT-15"], [],
          "Chantier 5S réalisé en atelier et évalué par le formateur.",
          "Opérateurs, techniciens, responsables d'équipe"),
        F("FOR-08", "Résolution de problèmes & démarche 8D", "Qualité", "Blended",
          14, 980, "PRE-02", 2,
          "Méthodologie structurée pour traiter les problèmes récurrents.",
          ["Structurer un problème avec le 5 Pourquoi et l'Ishikawa",
           "Rédiger un rapport 8D complet et suivi"],
          ["CPT-10", "CPT-07"], [],
          "Étude de cas chiffrée + soutenance du rapport 8D.",
          "Techniciens qualité, opérateurs, méthodes"),
        F("FOR-09", "SPC : contrôle statistique des procédés en pratique", "Qualité", "Présentiel",
          28, 1750, "PRE-02", 3,
          "Mettre en œuvre le SPC sur les procédés critiques de SmartFactory.",
          ["Construire et interpréter des cartes de contrôle (Xbar-R, p)",
           "Calculer et suivre la capabilité d'un procédé",
           "Décider d'une action corrective fondée sur les données"],
          ["CPT-08", "CPT-13"], [{"type": "competence", "id": "CPT-13", "niveau_min": 2,
                                   "libelle": "Statistiques niveau ≥ 2"}],
          "Exercices sur données de production réelles (fictives) + examen final.",
          "Techniciens qualité, ingénieurs méthodes"),
        F("FOR-10", "Python & SQL pour l'analyse de données industrielles", "Data & IA", "E-learning",
          35, 1290, "PRE-03", 2,
          "Socle data : extraire, nettoyer et analyser les données de production.",
          ["Interroger une base SQL multi-tables",
           "Nettoyer un jeu de données avec pandas",
           "Produire une analyse descriptive commentée"],
          ["CPT-11", "CPT-13"], [],
          "Projets notés à chaque module (moyenne ≥ 12/20).", "Tous salariés, aucun prérequis technique"),
        F("FOR-11", "Tableaux de bord décisionnels (Power BI / dashboards)", "Data & IA", "Blended",
          14, 890, "PRE-03", 2,
          "Concevoir des tableaux de bord clairs pour le pilotage.",
          ["Choisir les indicateurs adaptés à une décision",
           "Construire un tableau de bord interactif lisible",
           "Présenter une analyse à un non-spécialiste"],
          ["CPT-12", "CPT-11"], [{"type": "formation", "id": "FOR-10", "libelle": "Avoir suivi « Python & SQL pour l'analyse de données »"}],
          "Dashboard livré et présenté en soutenance.",
          "Analystes, méthodes, responsables d'équipe"),
        F("FOR-12", "Cybersécurité OT : protéger les systèmes industriels", "Cybersécurité", "Présentiel",
          21, 2600, "PRE-03", 3,
          "Spécificités de la sécurité des environnements opérationnels (OT).",
          ["Cartographier les flux OT/IT d'un site",
           "Mettre en œuvre une segmentation réseau industrielle",
           "Simuler et traiter un incident OT"],
          ["CPT-18", "CPT-09"], [{"type": "competence", "id": "CPT-02", "niveau_min": 3,
                                   "libelle": "Automatismes niveau ≥ 3"}],
          "Jeux de rôle incident + évaluation écrite.",
          "Maintenance, IT & Data, méthodes — profils techniques confirmés"),
        F("FOR-13", "Initiation à l'IA générative au travail (usage responsable)", "Data & IA", "E-learning",
          7, 450, "PRE-03", 1,
          "Utiliser les assistants IA courants de façon efficace et conforme.",
          ["Formuler des prompts utiles pour ses tâches",
           "Vérifier les réponses et identifier les limites",
           "Respecter la confidentialité des données d'entreprise"],
          ["CPT-19", "CPT-12"], [],
          "Auto-évaluation de fin de module (pas de note éliminatoire).",
          "Tous salariés"),
        F("FOR-14", "Gestion de projet pour non-specialistes (PMP simplifié)", "Transverse", "Blended",
          21, 1150, "PRE-02", 2,
          "Les bases du pilotage de projet appliquées aux projets industriels.",
          ["Rédiger un cahier des charges simple",
           "Construire un planning réaliste avec dépendances",
           "Piloter les risques et alimenter un comité de suivi"],
          ["CPT-16", "CPT-15"], [],
          "Étude de cas projet évaluée + retour du formateur.",
          "Tous salariés amenés à porter des projets"),
        F("FOR-15", "Manager une équipe de production : les fondamentaux", "Management", "Présentiel",
          35, 2900, "PRE-02", 2,
          "Prendre en main l'encadrement d'une équipe terrain.",
          ["Conduire un entretien individuel structuré",
           "Animer une réunion de quart efficace",
           "Gérer un conflit opérationnel"],
          ["CPT-14", "CPT-15"], [],
          "Mises en situation filmées et débriefées + évaluation 360° simplifiée.",
          "Responsables d'équipe, leaders de quart"),
        F("FOR-16", "Management de la performance & développement des talents", "Management", "Présentiel",
          21, 2400, "PRE-02", 3,
          "Aller plus loin : objectifs, feedback et plan de développement.",
          ["Fixer des objectifs SMART avec son équipe",
           "Construire un plan de développement individuel",
           "Mener un entretien de développement"],
          ["CPT-14", "CPT-16"], [{"type": "formation", "id": "FOR-15", "libelle": "Avoir suivi « Manager une équipe de production »"}],
          "Plan de développement présenté en soutenance.",
          "Responsables d'équipe confirmés"),
        F("FOR-17", "Auditeur interne ISO 9001 : préparer et mener un audit", "Qualité", "Présentiel",
          28, 2100, "PRE-02", 3,
          "Mener un audit de processus selon la norme ISO 9001.",
          ["Préparer un plan d'audit de processus",
           "Mener un entretien d'audit et collecter des preuves",
           "Rédiger un rapport d'audit avec constats gradués"],
          ["CPT-10", "CPT-07"], [{"type": "competence", "id": "CPT-10", "niveau_min": 3,
                                   "libelle": "Gestion des non-conformités niveau ≥ 3"}],
          "Audit simulé croisé entre participants.", "Techniciens qualité confirmés"),
        F("FOR-18", "Prédiction de pannes : machine learning appliqué à la maintenance", "Data & IA", "Blended",
          28, 2350, "PRE-03", 3,
          "Construire un premier modèle prédictif sur données de maintenance.",
          ["Préparer des données de pannes pour la modélisation",
           "Entraîner et évaluer un modèle de classification simple",
           "Interpréter les résultats avec prudence (limites du modèle)"],
          ["CPT-13", "CPT-11", "CPT-03"], [{"type": "formation", "id": "FOR-10", "libelle": "Avoir suivi « Python & SQL pour l'analyse de données »"}],
          "Notebook final évalué + présentation des résultats.",
          "Analystes data, ingénieurs méthodes, techniciens maintenance confirmés"),
        F("FOR-19", "Gouvernance des données industrielles : qualité & partage responsable", "Data & IA", "E-learning",
          14, 780, "PRE-01", 2,
          "Fiabiliser et partager les données dans le respect des règles internes.",
          ["Appliquer les règles de qualité des données (complétude, cohérence)",
           "Documenter un flux de données métier",
           "Identifier les contraintes RGPD liées aux données d'activité"],
          ["CPT-19", "CPT-12"], [],
          "Quiz final noté (seuil : 70 %).", "Analystes, IT & Data, méthodes"),
        F("FOR-20", "Robotique collaborative : prise en main et sécurité Cobot", "Production", "Présentiel",
          21, 2750, "PRE-04", 3,
          "Programmer et sécuriser une cellule avec bras collaboratif.",
          ["Paramétrer un cobot pour une tâche de manutention",
           "Appliquer les règles de sécurité spécifiques aux cobots",
           "Diagnostiquer une anomalie de trajectoire"],
          ["CPT-05", "CPT-09"], [{"type": "competence", "id": "CPT-02", "niveau_min": 3,
                                   "libelle": "Automatismes niveau ≥ 3"}],
          "Évaluation pratique en cellule cobot.",
          "Maintenance, méthodes — profils automatismes confirmés"),
    ]

    # ----- Sessions -------------------------------------------------------------
    def S(sid, fid, debut, fin, capacite, inscrits, lieu):
        return {"id": sid, "formation_id": fid, "date_debut": debut.isoformat(),
                "date_fin": fin.isoformat(), "capacite": capacite,
                "places_insnees": inscrits, "lieu": lieu}

    d["sessions"] = [
        S("SES-01", "FOR-01", date(2026, 11, 2),  date(2026, 11, 13), 8, 5, "Site Nord — Atelier A"),
        S("SES-02", "FOR-02", date(2026, 11, 16), date(2026, 12, 4), 8, 7, "Site Nord — Salle T2"),
        S("SES-03", "FOR-03", date(2026, 12, 8),  date(2026, 12, 18), 6, 6, "Site Sud — Atelier B"),
        S("SES-04", "FOR-04", date(2026, 11, 1),  date(2026, 11, 15), 20, 9, "E-learning (plateforme)"),
        S("SES-05", "FOR-05", date(2027, 1, 11),  date(2027, 1, 22), 10, 4, "Site Nord — Labo Data"),
        S("SES-06", "FOR-06", date(2026, 11, 5),  date(2026, 11, 9), 25, 18, "Tous sites — salles de formation"),
        S("SES-07", "FOR-07", date(2026, 11, 30), date(2026, 12, 11), 12, 8, "Site Sud — Atelier C"),
        S("SES-08", "FOR-08", date(2026, 11, 9),  date(2026, 11, 20), 15, 6, "Blended : Site Nord + e-learning"),
        S("SES-09", "FOR-09", date(2027, 1, 18),  date(2027, 1, 30), 10, 5, "Site Sud — Salle Q1"),
        S("SES-10", "FOR-10", date(2026, 11, 4),  date(2026, 11, 27), 30, 12, "E-learning (plateforme)"),
        S("SES-11", "FOR-11", date(2026, 12, 1),  date(2026, 12, 11), 15, 7, "Blended : Site Nord + e-learning"),
        S("SES-12", "FOR-12", date(2027, 2, 1),   date(2027, 2, 11), 8, 3, "Site Nord — Salle InfoSec"),
        S("SES-13", "FOR-13", date(2026, 11, 2),  date(2026, 11, 6), 50, 21, "E-learning (plateforme)"),
        S("SES-14", "FOR-14", date(2026, 12, 7),  date(2026, 12, 18), 15, 9, "Blended : Site Sud + e-learning"),
        S("SES-15", "FOR-15", date(2027, 1, 4),   date(2027, 1, 16), 10, 6, "Site Nord — Salle M1"),
        S("SES-16", "FOR-16", date(2027, 2, 8),   date(2027, 2, 18), 10, 2, "Site Nord — Salle M1"),
        S("SES-17", "FOR-17", date(2026, 12, 14), date(2026, 12, 24), 8, 5, "Site Sud — Salle Q2"),
        S("SES-18", "FOR-18", date(2027, 1, 25),  date(2027, 2, 5), 12, 6, "Blended : Site Nord + e-learning"),
        S("SES-19", "FOR-19", date(2026, 11, 16), date(2026, 11, 30), 25, 10, "E-learning (plateforme)"),
        S("SES-20", "FOR-20", date(2027, 2, 15),  date(2027, 2, 25), 6, 2, "Site Sud — Cellule Cobot"),
    ]

    # ----- Salariés (fictifs) ---------------------------------------------------
    def E(eid, nom, metier_id, svc_id, manager_id, niveaux, objectif=None, recrutement="2019-06-01"):
        return {"id": eid, "nom": nom + " (démonstration)", "metier_id": metier_id,
                "service_id": svc_id, "manager_id": manager_id, "routage": None,
                "autoevaluation": niveaux, "objectif_evolution": objectif,
                "date_embauche": recrutement}

    d["salaries"] = [
        # Managers (1 par équipe de démo)
        E("sf-1015", "Karim B.", "MET-03", "SVC-02", None,
          {"CPT-14": 4, "CPT-15": 4, "CPT-09": 3, "CPT-18": 2},
          objectif="Responsable maintenance site"),
        E("sf-1021", "Sofia M.", "MET-03", "SVC-01", None,
          {"CPT-14": 3, "CPT-15": 3, "CPT-09": 4, "CPT-07": 3}),
        E("sf-1027", "Julien P.", "MET-03", "SVC-03", None,
          {"CPT-14": 3, "CPT-15": 3, "CPT-09": 3, "CPT-10": 3}),
        E("sf-1033", "Awa T.", "MET-03", "SVC-06", None,
          {"CPT-14": 4, "CPT-15": 3, "CPT-09": 2, "CPT-11": 3}),
        # Équipe Maintenance (manager sf-1015)
        E("sf-1001", "Thomas R.", "MET-01", "SVC-02", "sf-1015",
          {"CPT-01": 4, "CPT-02": 3, "CPT-03": 2, "CPT-04": 3, "CPT-09": 3, "CPT-16": 2},
          objectif="Chef d'équipe maintenance"),
        E("sf-1002", "Camille D.", "MET-01", "SVC-02", "sf-1015",
          {"CPT-01": 3, "CPT-02": 2, "CPT-03": 1, "CPT-04": 3, "CPT-09": 2, "CPT-16": 1},
          objectif="Technicien maintenance prédictive"),
        E("sf-1003", "Mehdi K.", "MET-01", "SVC-02", "sf-1015",
          {"CPT-01": 3, "CPT-02": 4, "CPT-03": 2, "CPT-04": 2, "CPT-09": 3, "CPT-18": 1},
          objectif="Spécialiste cybersécurité OT"),
        E("sf-1004", "Léa V.", "MET-01", "SVC-02", "sf-1015",
          {"CPT-01": 2, "CPT-02": 2, "CPT-03": 1, "CPT-04": 2, "CPT-09": 2},
          recrutement="2024-03-01"),
        E("sf-1005", "Hugo S.", "MET-01", "SVC-02", "sf-1015",
          {"CPT-01": 5, "CPT-02": 4, "CPT-03": 4, "CPT-04": 4, "CPT-09": 4, "CPT-17": 2},
          objectif="Ingénieur méthodes maintenance"),
        # Équipe Production (manager sf-1021)
        E("sf-1010", "Nadia F.", "MET-02", "SVC-01", "sf-1021",
          {"CPT-07": 3, "CPT-08": 2, "CPT-09": 4, "CPT-15": 2, "CPT-16": 2}),
        E("sf-1011", "Pablo G.", "MET-02", "SVC-01", "sf-1021",
          {"CPT-07": 2, "CPT-08": 1, "CPT-09": 3, "CPT-15": 2}, recrutement="2025-01-15"),
        E("sf-1012", "Inès C.", "MET-02", "SVC-01", "sf-1021",
          {"CPT-07": 3, "CPT-08": 3, "CPT-09": 3, "CPT-15": 3, "CPT-05": 1},
          objectif="Opératrice polyvalente / leader de quart"),
        E("sf-1013", "David L.", "MET-02", "SVC-01", "sf-1021",
          {"CPT-07": 2, "CPT-08": 2, "CPT-09": 2, "CPT-15": 1}),
        E("sf-1014", "Yasmine H.", "MET-02", "SVC-01", "sf-1021",
          {"CPT-07": 3, "CPT-08": 2, "CPT-09": 3, "CPT-15": 2, "CPT-16": 2},
          objectif="Responsable d'équipe de production"),
        # Équipe Qualité (manager sf-1027)
        E("sf-1020", "Marc O.", "MET-05", "SVC-03", "sf-1027",
          {"CPT-07": 3, "CPT-08": 4, "CPT-10": 4, "CPT-09": 3, "CPT-16": 3},
          objectif="Auditeur interne certifié"),
        E("sf-1022", "Elif A.", "MET-05", "SVC-03", "sf-1027",
          {"CPT-07": 2, "CPT-08": 3, "CPT-10": 3, "CPT-09": 2, "CPT-16": 1},
          recrutement="2024-09-01"),
        E("sf-1023", "Rachid Z.", "MET-05", "SVC-03", "sf-1027",
          {"CPT-07": 3, "CPT-08": 4, "CPT-10": 3, "CPT-09": 3, "CPT-16": 2},
          objectif="Chef de service qualité"),
        E("sf-1024", "Clara W.", "MET-05", "SVC-03", "sf-1027",
          {"CPT-07": 2, "CPT-08": 2, "CPT-10": 2, "CPT-09": 2}, recrutement="2025-06-01"),
        # Équipe Méthodes (manager : DRH déléguée sf-2001 pour la démo)
        E("sf-1030", "Antoine D.", "MET-04", "SVC-04", "sf-2001",
          {"CPT-13": 4, "CPT-18": 2, "CPT-07": 4, "CPT-10": 2, "CPT-11": 3},
          objectif="Responsable industrialisation"),
        E("sf-1031", "Fatou S.", "MET-04", "SVC-04", "sf-2001",
          {"CPT-13": 3, "CPT-18": 2, "CPT-07": 3, "CPT-10": 2, "CPT-11": 2},
          objectif="Data analyst industrielle"),
        E("sf-1032", "Lucas M.", "MET-04", "SVC-04", "sf-2001",
          {"CPT-13": 3, "CPT-18": 1, "CPT-07": 3, "CPT-10": 1, "CPT-11": 2},
          recrutement="2025-02-01"),
        # Équipe IT & Data (manager sf-1033)
        E("sf-1040", "Sarah N.", "MET-06", "SVC-06", "sf-1033",
          {"CPT-11": 4, "CPT-12": 4, "CPT-13": 4, "CPT-19": 3, "CPT-05": 1},
          objectif="Data scientist maintenance prédictive"),
        E("sf-1041", "Omar B.", "MET-06", "SVC-06", "sf-1033",
          {"CPT-11": 3, "CPT-12": 3, "CPT-13": 3, "CPT-19": 2, "CPT-18": 2},
          objectif="Ingénieur cybersécurité industrielle"),
        E("sf-1042", "Pauline E.", "MET-06", "SVC-06", "sf-1033",
          {"CPT-11": 3, "CPT-12": 2, "CPT-13": 2, "CPT-19": 2}, recrutement="2025-04-01"),
        E("sf-1043", "Ibrahim T.", "MET-06", "SVC-06", "sf-1033",
          {"CPT-11": 4, "CPT-12": 3, "CPT-13": 3, "CPT-19": 3, "CPT-17": 2}),
        # Logistique (rattachés au manager production pour la démo)
        E("sf-1050", "Marie J.", "MET-02", "SVC-05", "sf-1021",
          {"CPT-07": 2, "CPT-08": 1, "CPT-09": 3, "CPT-15": 2}),
        E("sf-1051", "Bilal R.", "MET-02", "SVC-05", "sf-1021",
          {"CPT-07": 2, "CPT-08": 1, "CPT-09": 2, "CPT-15": 1}, recrutement="2024-11-01"),
        # DRH / Formation
        E("sf-2001", "Nadia L.", None, "SVC-06", None,
          {"CPT-16": 4, "CPT-11": 3}, objectif=None),
        # Administrateur technique
        E("sf-9001", "Admin Technique", None, "SVC-06", None, {}),
    ]

    # ----- Rôles utilisateurs ----------------------------------------------------
    d["roles"] = {
        "sf-1002": "salarie", "sf-1001": "salarie", "sf-1003": "salarie",
        "sf-1004": "salarie", "sf-1005": "salarie", "sf-1010": "salarie",
        "sf-1011": "salarie", "sf-1012": "salarie", "sf-1013": "salarie",
        "sf-1014": "salarie", "sf-1020": "salarie", "sf-1022": "salarie",
        "sf-1023": "salarie", "sf-1024": "salarie", "sf-1030": "salarie",
        "sf-1031": "salarie", "sf-1032": "salarie", "sf-1040": "salarie",
        "sf-1041": "salarie", "sf-1042": "salarie", "sf-1043": "salarie",
        "sf-1050": "salarie", "sf-1051": "salarie",
        "sf-1015": "manager", "sf-1021": "manager", "sf-1027": "manager",
        "sf-1033": "manager",
        "sf-2001": "drh",
        "sf-9001": "admin",
    }

    # ----- Budgets annuels (par service) -----------------------------------------
    d["budgets"] = [
        {"service_id": "SVC-01", "annee": YEAR, "montant": 120000},
        {"service_id": "SVC-02", "annee": YEAR, "montant": 150000},
        {"service_id": "SVC-03", "annee": YEAR, "montant": 90000},
        {"service_id": "SVC-04", "annee": YEAR, "montant": 100000},
        {"service_id": "SVC-05", "annee": YEAR, "montant": 60000},
        {"service_id": "SVC-06", "annee": YEAR, "montant": 110000},
    ]

    # ----- Demandes d'inscription --------------------------------------------------
    def REQ(rid, eid, fid, statut, cree_le, session_id=None, historique=None):
        return {"id": rid, "salarie_id": eid, "formation_id": fid,
                "session_id": session_id, "statut": statut,
                "date_creation": cree_le.isoformat(), "historique": historique or []}

    d["demandes"] = [
        REQ("DEM-001", "sf-1002", "FOR-03", "en_attente", date(2026, 10, 2),
            session_id="SES-03",
            historique=[{"date": date(2026, 10, 2).isoformat(), "action": "demande_creee",
                         "par": "sf-1002", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-002", "sf-1003", "FOR-12", "en_attente", date(2026, 9, 28),
            session_id="SES-12",
            historique=[{"date": date(2026, 9, 28).isoformat(), "action": "demande_creee",
                         "par": "sf-1003", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-003", "sf-1004", "FOR-02", "en_attente", date(2026, 10, 6),
            session_id="SES-02",
            historique=[{"date": date(2026, 10, 6).isoformat(), "action": "demande_creee",
                         "par": "sf-1004", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-004", "sf-1012", "FOR-15", "approuvee", date(2026, 9, 15),
            session_id="SES-15",
            historique=[{"date": date(2026, 9, 15).isoformat(), "action": "demande_creee",
                         "par": "sf-1012", "detail": "Demande envoyée à la validation"},
                        {"date": date(2026, 9, 20).isoformat(), "action": "approuvee",
                         "par": "sf-1021", "motif": "Cohérent avec l'objectif de leader de quart."}]),
        REQ("DEM-005", "sf-1014", "FOR-15", "en_attente", date(2026, 10, 7),
            session_id="SES-15",
            historique=[{"date": date(2026, 10, 7).isoformat(), "action": "demande_creee",
                         "par": "sf-1014", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-006", "sf-1022", "FOR-09", "en_attente", date(2026, 10, 5),
            session_id="SES-09",
            historique=[{"date": date(2026, 10, 5).isoformat(), "action": "demande_creee",
                         "par": "sf-1022", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-007", "sf-1031", "FOR-10", "inscrite", date(2026, 9, 10),
            session_id="SES-10",
            historique=[{"date": date(2026, 9, 10).isoformat(), "action": "demande_creee",
                         "par": "sf-1031", "detail": "Demande envoyée à la validation"},
                        {"date": date(2026, 9, 14).isoformat(), "action": "approuvee",
                         "par": "sf-2001", "motif": "Socle data indispensable au plan de développement."},
                        {"date": date(2026, 9, 25).isoformat(), "action": "inscrite",
                         "par": "sf-2001", "detail": "Inscrit(e) à la session du 04/11/2026"}]),
        REQ("DEM-008", "sf-1041", "FOR-12", "approuvee", date(2026, 9, 30),
            session_id="SES-12",
            historique=[{"date": date(2026, 9, 30).isoformat(), "action": "demande_creee",
                         "par": "sf-1041", "detail": "Demande envoyée à la validation"},
                        {"date": date(2026, 10, 5).isoformat(), "action": "approuvee",
                         "par": "sf-1033", "motif": "Priorité cybersécurité OT sur le plan de l'année."}]),
        REQ("DEM-009", "sf-1011", "FOR-07", "refusee", date(2026, 9, 22),
            session_id="SES-07",
            historique=[{"date": date(2026, 9, 22).isoformat(), "action": "demande_creee",
                         "par": "sf-1011", "detail": "Demande envoyée à la validation"},
                        {"date": date(2026, 9, 25).isoformat(), "action": "refusee",
                         "par": "sf-1021", "motif": "Période de forte charge sur la ligne B ; à reprogrammer au T4."}]),
        REQ("DEM-010", "sf-1043", "FOR-05", "en_attente", date(2026, 10, 8),
            session_id="SES-05",
            historique=[{"date": date(2026, 10, 8).isoformat(), "action": "demande_creee",
                         "par": "sf-1043", "detail": "Demande envoyée à la validation"}]),
        REQ("DEM-011", "sf-1020", "FOR-17", "approuvee", date(2026, 9, 18),
            session_id="SES-17",
            historique=[{"date": date(2026, 9, 18).isoformat(), "action": "demande_creee",
                         "par": "sf-1020", "detail": "Demande envoyée à la validation"},
                        {"date": date(2026, 9, 24).isoformat(), "action": "approuvee",
                         "par": "sf-1027", "motif": "Aligné sur l'objectif auditeur interne."}]),
        REQ("DEM-012", "sf-1050", "FOR-13", "en_attente", date(2026, 10, 8),
            session_id="SES-13",
            historique=[{"date": date(2026, 10, 8).isoformat(), "action": "demande_creee",
                         "par": "sf-1050", "detail": "Demande envoyée à la validation"}]),
    ]

    # ----- Réalisations de formation (historique validé) ----------------------------
    def RAL(rid, eid, fid, debut, fin, heures_prevues, heures_reelles, validee=True, attestation=None):
        return {"id": rid, "salarie_id": eid, "formation_id": fid,
                "date_debut": debut.isoformat(), "date_fin": fin.isoformat(),
                "heures_prevues": heures_prevues, "heures_reelles": heures_reelles,
                "validee": validee, "attestation_id": attestation}

    d["realisations"] = [
        RAL("RAL-01", "sf-1001", "FOR-01", date(2026, 3, 2), date(2026, 3, 13), 28, 28,
            attestation="AT-2026-0001"),
        RAL("RAL-02", "sf-1001", "FOR-06", date(2026, 4, 6), date(2026, 4, 8), 7, 7,
            attestation="AT-2026-0002"),
        RAL("RAL-03", "sf-1002", "FOR-06", date(2026, 4, 6), date(2026, 4, 8), 7, 7,
            attestation="AT-2026-0003"),
        RAL("RAL-04", "sf-1002", "FOR-04", date(2026, 5, 4), date(2026, 5, 18), 14, 12,
            attestation="AT-2026-0004"),
        RAL("RAL-05", "sf-1003", "FOR-02", date(2026, 2, 9), date(2026, 3, 6), 35, 35,
            attestation="AT-2026-0005"),
        RAL("RAL-06", "sf-1005", "FOR-03", date(2026, 4, 27), date(2026, 5, 8), 21, 21,
            attestation="AT-2026-0006"),
        RAL("RAL-07", "sf-1010", "FOR-07", date(2026, 3, 9), date(2026, 3, 20), 21, 21,
            attestation="AT-2026-0007"),
        RAL("RAL-08", "sf-1010", "FOR-06", date(2026, 4, 6), date(2026, 4, 8), 7, 7,
            attestation="AT-2026-0008"),
        RAL("RAL-09", "sf-1014", "FOR-08", date(2026, 5, 11), date(2026, 5, 22), 14, 14,
            attestation="AT-2026-0009"),
        RAL("RAL-10", "sf-1020", "FOR-09", date(2026, 2, 16), date(2026, 2, 28), 28, 28,
            attestation="AT-2026-0010"),
        RAL("RAL-11", "sf-1023", "FOR-09", date(2026, 2, 16), date(2026, 2, 28), 28, 25,
            attestation="AT-2026-0011"),
        RAL("RAL-12", "sf-1030", "FOR-14", date(2026, 5, 4), date(2026, 5, 15), 21, 21,
            attestation="AT-2026-0012"),
        RAL("RAL-13", "sf-1040", "FOR-10", date(2026, 3, 2), date(2026, 3, 25), 35, 35,
            attestation="AT-2026-0013"),
        RAL("RAL-14", "sf-1040", "FOR-11", date(2026, 6, 1), date(2026, 6, 11), 14, 14,
            attestation="AT-2026-0014"),
        RAL("RAL-15", "sf-1043", "FOR-10", date(2026, 3, 2), date(2026, 3, 25), 35, 35,
            attestation="AT-2026-0015"),
        RAL("RAL-16", "sf-1043", "FOR-19", date(2026, 7, 6), date(2026, 7, 17), 14, 14,
            attestation="AT-2026-0016"),
        RAL("RAL-17", "sf-1051", "FOR-06", date(2026, 4, 6), date(2026, 4, 8), 7, 7,
            attestation="AT-2026-0017"),
        RAL("RAL-18", "sf-1024", "FOR-06", date(2026, 4, 6), date(2026, 4, 8), 7, 5,
            validee=False),  # assiduité insuffisante : non validée, pas d'attestation
        RAL("RAL-19", "sf-1031", "FOR-13", date(2026, 6, 8), date(2026, 6, 12), 7, 7,
            attestation="AT-2026-0018"),
        RAL("RAL-20", "sf-1041", "FOR-10", date(2026, 3, 2), date(2026, 3, 25), 35, 35,
            attestation="AT-2026-0019"),
    ]

    # ----- Attestations ---------------------------------------------------------------
    d["attestations"] = [
        {"id": aid, "realisation_id": rid, "date_emission": date(2026, 3, 20).isoformat(),
         "statut": "emise"}
        for aid, rid in [("AT-2026-0001", "RAL-01"), ("AT-2026-0002", "RAL-02"),
                         ("AT-2026-0003", "RAL-03"), ("AT-2026-0004", "RAL-04"),
                         ("AT-2026-0005", "RAL-05"), ("AT-2026-0006", "RAL-06"),
                         ("AT-2026-0007", "RAL-07"), ("AT-2026-0008", "RAL-08"),
                         ("AT-2026-0009", "RAL-09"), ("AT-2026-0010", "RAL-10"),
                         ("AT-2026-0011", "RAL-11"), ("AT-2026-0012", "RAL-12"),
                         ("AT-2026-0013", "RAL-13"), ("AT-2026-0014", "RAL-14"),
                         ("AT-2026-0015", "RAL-15"), ("AT-2026-0016", "RAL-16"),
                         ("AT-2026-0017", "RAL-17"), ("AT-2026-0018", "RAL-19"),
                         ("AT-2026-0019", "RAL-20")]
    ]

    # ----- Évaluations à chaud -----------------------------------------------------------
    def EV(eid, fid, notes, commentaire=""):
        return {"salarie_id": eid, "formation_id": fid, "notes": notes,
                "commentaire": commentaire, "date": date(2026, 3, 20).isoformat(),
                "type": "chaud"}

    d["evaluations"] = [
        EV("sf-1001", "FOR-01", {"satisfaction": 5, "contenu": 4, "pertinence": 5,
                                  "animation": 4, "utilite": 5, "reutilisation": 5},
           "Très bon atelier, beaucoup de pratique."),
        EV("sf-1002", "FOR-04", {"satisfaction": 4, "contenu": 4, "pertinence": 4,
                                 "animation": 3, "utilite": 4, "reutilisation": 4},
           "E-learning efficace mais un peu long."),
        EV("sf-1005", "FOR-03", {"satisfaction": 5, "contenu": 5, "pertinence": 5,
                                 "animation": 5, "utilite": 4, "reutilisation": 5}),
        EV("sf-1010", "FOR-07", {"satisfaction": 4, "contenu": 4, "pertinence": 4,
                                 "animation": 5, "utilite": 4, "reutilisation": 4},
           "Le chantier 5S a été très concret."),
        EV("sf-1020", "FOR-09", {"satisfaction": 5, "contenu": 5, "pertinence": 5,
                                 "animation": 4, "utilite": 5, "reutilisation": 5}),
        EV("sf-1030", "FOR-14", {"satisfaction": 4, "contenu": 4, "pertinence": 3,
                                 "animation": 4, "utilite": 4, "reutilisation": 4},
           "Certaines parties peu adaptées au contexte industriel."),
        EV("sf-1040", "FOR-10", {"satisfaction": 5, "contenu": 5, "pertinence": 5,
                                 "animation": 4, "utilite": 5, "reutilisation": 5},
           "Données de production très parlantes."),
        EV("sf-1043", "FOR-19", {"satisfaction": 4, "contenu": 4, "pertinence": 4,
                                 "animation": 4, "utilite": 4, "reutilisation": 4}),
    ]

    # ----- Évaluation à froid (30-90 jours après) ------------------------------------------
    d["evaluations_froides"] = [
        {"salarie_id": "sf-1001", "formation_id": "FOR-01",
         "utilisation_acquis": 5, "difficultes": "Accès limité aux outillages de mesure.",
         "commentaire": "J'applique les procédures de diagnostic au quotidien.",
         "date": date(2026, 6, 1).isoformat()},
        {"salarie_id": "sf-1040", "formation_id": "FOR-10",
         "utilisation_acquis": 5, "difficultes": "Aucune difficulté majeure.",
         "commentaire": "Python/SQL utilisés sur les rapports hebdomadaires.",
         "date": date(2026, 6, 15).isoformat()},
        {"salarie_id": "sf-1030", "formation_id": "FOR-14",
         "utilisation_acquis": 3, "difficultes": "Difficile de dégager du temps pour le suivi des projets.",
         "commentaire": "Méthodes utiles mais application partielle à ce stade.",
         "date": date(2026, 8, 1).isoformat()},
    ]

    # ----- Compétences validées par un évaluateur (reconnaissance) ---------------------------
    d["competences_validees"] = [
        {"salarie_id": "sf-1005", "competence_id": "CPT-03", "niveau": 4,
         "justification": "Validé par l'évaluateur après chantier vibratoire 2026.",
         "date": date(2026, 5, 10).isoformat(), "par": "sf-1015"},
        {"salarie_id": "sf-1040", "competence_id": "CPT-13", "niveau": 4,
         "justification": "Projet de prévision des arrêts — soutenance validée.",
         "date": date(2026, 6, 20).isoformat(), "par": "sf-1033"},
        {"salarie_id": "sf-1020", "competence_id": "CPT-10", "niveau": 4,
         "justification": "Campagne 8D menée en autonomie sur le site Sud.",
         "date": date(2026, 7, 5).isoformat(), "par": "sf-1027"},
    ]

    # ----- Paramètres configurables (alertes) --------------------------------------------------
    d["parametres"] = {
        "delai_attente_jours": 7,
        "seuil_session_pleine_pct": 80,
        "seuil_budget_pct": 90,
        "validite_obligatoire_mois_defaut": 36,
        "seuil_couverture_critique": 2.5,
    }

    # ----- Notifications ---------------------------------------------------------------------------
    d["notifications"] = [
        {"id": "NTF-001", "destinataire": "sf-1012",
         "message": "Votre demande « Manager une équipe de production » a été approuvée par Sofia M.",
         "date": date(2026, 9, 20).isoformat(), "lue": False},
        {"id": "NTF-002", "destinataire": "sf-1011",
         "message": "Votre demande « Lean manufacturing pour les équipes terrain » a été refusée. Motif : période de forte charge sur la ligne B.",
         "date": date(2026, 9, 25).isoformat(), "lue": False},
        {"id": "NTF-003", "destinataire": "sf-1031",
         "message": "Vous êtes inscrit(e) à la session « Python & SQL » du 04/11/2026.",
         "date": date(2026, 9, 25).isoformat(), "lue": False},
        {"id": "NTF-004", "destinataire": "sf-1041",
         "message": "Votre demande « Cybersécurité OT » a été approuvée par Awa T.",
         "date": date(2026, 10, 5).isoformat(), "lue": False},
    ]

    # ----- Scénarios de simulation --------------------------------------------------------------------
    d["scenarios"] = [
        {"id": "SCN-01", "nom": "Déploiement Industrie 4.0 (hypothèse T+2 ans)",
         "description": "Hypothèse : montée en service des cellules robotisées et du jumeau numérique sur les deux sites.",
         "ajustements": {"CPT-05": 1, "CPT-17": 2, "CPT-18": 1, "CPT-11": 1},
         "contrainte_budget_pct": None},
        {"id": "SCN-02", "nom": "Automatisation des lignes d'emballage (hypothèse T+1 an)",
         "description": "Hypothèse : automatisation de 3 lignes, besoin accru en robotique et maintenance prédictive.",
         "ajustements": {"CPT-05": 2, "CPT-03": 1, "CPT-02": 1},
         "contrainte_budget_pct": None},
        {"id": "SCN-03", "nom": "Priorité cybersécurité industrielle (hypothèse T+1 an)",
         "description": "Hypothèse : durcissement des exigences de sécurité OT après audit externe.",
         "ajustements": {"CPT-18": 2, "CPT-19": 1},
         "contrainte_budget_pct": None},
        {"id": "SCN-04", "nom": "Renforcement data & analyse (hypothèse T+2 ans)",
         "description": "Hypothèse : généralisation de l'analyse prédictive qualité et maintenance.",
         "ajustements": {"CPT-11": 2, "CPT-13": 1, "CPT-12": 1},
         "contrainte_budget_pct": None},
        {"id": "SCN-05", "nom": "Contrainte budgétaire sévère (hypothèse)",
         "description": "Hypothèse : le budget de formation est réduit de 30 % par rapport à l'année en cours.",
         "ajustements": {"CPT-18": 1, "CPT-11": 1},
         "contrainte_budget_pct": -30},
    ]

    d["compteurs"] = {"demande": 12, "realisation": 20, "attestation": 19,
                      "notification": 4, "session": 20}
    return d

# -----------------------------------------------------------------------------
# Persistance
# -----------------------------------------------------------------------------

def load_data():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if isinstance(data, dict) and "formations" in data and "salaries" in data:
                return data
        except Exception:
            pass
    return seed_data()

def save_data(data):
    try:
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=1)
    except Exception as e:
        print("[SmartSkills] Avertissement : impossible d'écrire la sauvegarde :", e)

# -----------------------------------------------------------------------------
# Helpers métier
# -----------------------------------------------------------------------------

def by_id(coll, key):
    return {x["id"]: x for x in coll}

def find(coll, key, id_):
    for x in coll:
        if x[key] == id_:
            return x
    return None

def fmt_date(iso):
    try:
        y, m, dd = iso.split("-")
        return f"{dd}/{m}/{y}"
    except Exception:
        return iso

def fmt_euro(x):
    return f"{x:,.0f} €".replace(",", " ")

STATUTS_DEMANDE = {
    "brouillon": "Brouillon", "en_attente": "En attente de validation",
    "approuvee": "Approuvée", "refusee": "Refusée",
    "inscrite": "Inscrit(e) en session", "terminee": "Terminée",
    "annulee": "Annulée",
}

# Transitions autorisées (règle de cohérence des statuts)
TRANSITIONS = {
    "brouillon": {"en_attente", "annulee"},
    "en_attente": {"approuvee", "refusee", "annulee"},
    "approuvee": {"inscrite", "annulee"},
    "refusee": set(),
    "inscrite": {"terminee", "annulee"},
    "terminee": set(),
    "annulee": set(),
}

EV_CHAUD_KEYS = ["satisfaction", "contenu", "pertinence", "animation", "utilite", "reutilisation"]
EV_CHAUD_LABELS = {
    "satisfaction": "Satisfaction globale",
    "contenu": "Qualité du contenu",
    "pertinence": "Pertinence pour le poste",
    "animation": "Qualité de l'animation",
    "utilite": "Utilité perçue des acquis",
    "reutilisation": "Intention de réutiliser les connaissances",
}

# -----------------------------------------------------------------------------
# Logique métier : budgets
# -----------------------------------------------------------------------------

def budget_service(data, service_id, annee=YEAR):
    b = find(data["budgets"], "service_id", service_id)
    if b and b.get("annee") == annee:
        return b["montant"]
    return 0

def couts_demandes(data, statuts, service_id=None):
    """Somme des coûts des demandes aux statuts donnés (option : un service)."""
    total = 0.0
    for dem in data["demandes"]:
        if dem["statut"] not in statuts:
            continue
        sal = find(data["salaries"], "id", dem["salarie_id"])
        if service_id and (not sal or sal["service_id"] != service_id):
            continue
        for_ = find(data["formations"], "id", dem["formation_id"])
        if for_:
            total += for_["cout"]
    return total

def couts_realisations(data, service_id=None, debut_iso=None, fin_iso=None):
    """Coût des formations terminées (réalisations validées uniquement)."""
    total = 0.0
    for r in data["realisations"]:
        if not r.get("validee"):
            continue
        sal = find(data["salaries"], "id", r["salarie_id"])
        if service_id and (not sal or sal["service_id"] != service_id):
            continue
        if debut_iso and r["date_fin"] < debut_iso:
            continue
        if fin_iso and r["date_debut"] > fin_iso:
            continue
        for_ = find(data["formations"], "id", r["formation_id"])
        if for_:
            total += for_["cout"]
    return total

def budget_state(data, service_id=None):
    """
    Règles métier (documentées) :
      - budget_total   : enveloppe annuelle allouée au service ;
      - budget_engage  : coûts des demandes approuvées ou inscrites (non terminées)
                         → réservation, pas encore dépense ;
      - budget_consomme: coûts des réalisations validées (formations terminées) ;
      - budget_restant : total − engagé − consommé.
    """
    if service_id:
        total = budget_service(data, service_id)
        engage = couts_demandes(data, {"approuvee", "inscrite"}, service_id)
        consomme = couts_realisations(data, service_id)
    else:
        total = sum(b["montant"] for b in data["budgets"] if b.get("annee") == YEAR)
        engage = couts_demandes(data, {"approuvee", "inscrite"})
        consomme = couts_realisations(data)
    return {"total": total, "engage": engage, "consomme": consomme,
            "restant": max(total - engage - consomme, 0.0),
            "taux_utilisation_pct": round(100.0 * (engage + consomme) / total, 1) if total else 0.0}

# -----------------------------------------------------------------------------
# Logique métier : compétences & écarts
# -----------------------------------------------------------------------------

def niveaux_effectifs(data, sal):
    """
    Niveau retenu par compétence = max(autoévaluation déclarée, niveau validé
    par un évaluateur). Règle : une compétence déclarée n'est pas considérée
    comme validée ; ici on affiche le meilleur des deux et on distingue les sources.
    """
    out = {}
    for cpt_id, niv in (sal.get("autoevaluation") or {}).items():
        out[cpt_id] = {"declare": niv, "valide": None, "retenu": niv,
                       "source": "Autoévaluation du salarié (déclarée)"}
    for cv in data["competences_validees"]:
        if cv["salarie_id"] == sal["id"]:
            cur = out.setdefault(cv["competence_id"],
                                 {"declare": None, "valide": None, "retenu": 0,
                                  "source": "—"})
            cur["valide"] = cv["niveau"]
            if (cur["retenu"] or 0) < cv["niveau"]:
                cur["retenu"] = cv["niveau"]
                cur["source"] = f"Validée par évaluateur le {fmt_date(cv['date'])}"
    return out

def ecarts_salarie(data, sal):
    """Écarts niveau retenu vs niveau cible du métier (≥ 0)."""
    metier = find(data["metiers"], "id", sal.get("metier_id"))
    if not metier:
        return []
    eff = niveaux_effectifs(data, sal)
    ecarts = []
    for cpt_id, cible in metier["competences_cibles"].items():
        actuel = (eff.get(cpt_id) or {}).get("retenu") or 0
        if cible - actuel > 0:
            cpt = find(data["competences"], "id", cpt_id)
            ecarts.append({"competence_id": cpt_id,
                           "nom": cpt["nom"] if cpt else cpt_id,
                           "actuel": actuel, "cible": cible,
                           "ecart": cible - actuel,
                           "critique": bool(cpt and cpt.get("critique"))})
    ecarts.sort(key=lambda e: (-e["ecart"], not e["critique"]))
    return ecarts

def formations_terminées(data, sal_id):
    return [r for r in data["realisations"] if r["salarie_id"] == sal_id and r.get("validee")]

def prerequis_ok(data, sal, formation):
    """Vérifie les prérequis (compétence ≥ niveau ou formation suivie)."""
    eff = niveaux_effectifs(data, sal)
    term = {r["formation_id"] for r in formations_terminées(data, sal["id"])}
    res = []
    for pre in formation.get("prerequis", []):
        if pre["type"] == "competence":
            cur = (eff.get(pre["id"]) or {}).get("retenu") or 0
            ok = cur >= pre["niveau_min"]
            cpt = find(data["competences"], "id", pre["id"])
            res.append({"ok": ok, "libelle": pre["libelle"],
                        "detail": f"Niveau actuel : {cur} / requis : {pre['niveau_min']}"
                                  if cpt else pre["libelle"]})
        elif pre["type"] == "formation":
            ok = pre["id"] in term
            for_ = find(data["formations"], "id", pre["id"])
            res.append({"ok": ok, "libelle": pre["libelle"],
                        "detail": (f"Formation « {for_['titre'] if for_ else pre['id']} » "
                                   + ("suivie ✓" if ok else "non suivie ✗"))})
    return res

def prochaine_session(data, formation_id):
    ses = [s for s in data["sessions"] if s["formation_id"] == formation_id]
    if not ses:
        return None
    ses.sort(key=lambda s: s["date_debut"])
    return min((s for s in ses if s["places_insnees"] < s["capacite"]),
               key=lambda s: s["date_debut"], default=ses[0])

# -----------------------------------------------------------------------------
# Moteur de recommandation (explicable, pondérations documentées)
# -----------------------------------------------------------------------------

RECO_PONDERATIONS = {
    "ecart_competence": 12.0,
    "competence_critique": 4.0,
    "objectif_evolution": 8.0,
    "formation_obligatoire": 15.0,
    "session_disponible": 3.0,
}

def recommandations(data, sal, duree_max_h=None, budget_max=None):
    """
    Score par formation (transparent) :
      + 12 × somme des écarts réduits (écart = niveau cible − niveau actuel)
      + 4  si la formation développe une compétence critique du métier
      + 8  si elle développe une compétence utile à l'objectif d'évolution déclaré
      + 15 si formation obligatoire pour le métier et non encore validée
      + 3  si une session avec place est disponible prochainement
    Exclusions : formations déjà terminées. Signalement (non-exclusion) :
    prérequis manquants, durée > disponible, coût > budget restant.
    """
    metier = find(data["metiers"], "id", sal.get("metier_id"))
    ecarts = {e["competence_id"]: e for e in ecarts_salarie(data, sal)}
    term_ids = {r["formation_id"] for r in formations_terminées(data, sal["id"])}

    # Compétences utiles à l'objectif d'évolution : si un métier correspond à
    # l'objectif déclaré (correspondance simple par mots-clés), on prend son référentiel.
    obj_cpts = set()
    if sal.get("objectif_evolution"):
        for m in data["metiers"]:
            for mot in re.findall(r"[a-zàâéèêëîïôöûùüç'-]{5,}", m["nom"].lower()):
                if mot in sal["objectif_evolution"].lower():
                    obj_cpts |= set(m["competences_cibles"].keys())

    obligatoires = set()
    if metier:
        for fo in metier.get("formations_obligatoires", []):
            # obligatoire non validée si jamais terminée ou terminée hors validité (simplifié : jamais)
            if fo["formation_id"] not in term_ids:
                obligatoires.add(fo["formation_id"])

    budget_dispo = budget_max
    if budget_dispo is None:
        bs = budget_state(data, sal.get("service_id"))
        budget_dispo = bs["restant"]

    results = []
    for f in data["formations"]:
        if f["id"] in term_ids:
            continue
        score = 0.0
        pourquoi = []
        # 1) écarts de compétences
        gap_sum = 0
        cpts_traites = []
        for cpt_id in f["competences"]:
            e = ecarts.get(cpt_id)
            if e and e["ecart"] > 0:
                gain = min(e["ecart"], 2)  # une formation ne comble pas tout l'écart
                pts = RECO_PONDERATIONS["ecart_competence"] * gain
                score += pts
                gap_sum += gain
                cpts_traites.append((e, gain))
        if cpts_traites:
            detail = ", ".join(f"{e['nom']} (écart {e['ecart']}, réduit de ~{g})"
                               for e, g in sorted(cpts_traites,
                                                  key=lambda x: -x[1]))
            pourquoi.append(f"Réduit les écarts sur : {detail}")
        # 2) compétence critique
        if any(ecarts.get(c, {}).get("critique") for c in f["competences"]):
            score += RECO_PONDERATIONS["competence_critique"]
            pourquoi.append("Développe une compétence critique du référentiel du poste.")
        # 3) objectif d'évolution
        if obj_cpts and any(c in obj_cpts for c in f["competences"]):
            score += RECO_PONDERATIONS["objectif_evolution"]
            pourquoi.append("Contribue à l'objectif d'évolution déclaré."
                            + (f" (« {sal['objectif_evolution']} »)" if sal.get("objectif_evolution") else ""))
        # 4) obligatoire
        if f["id"] in obligatoires:
            score += RECO_PONDERATIONS["formation_obligatoire"]
            pourquoi.append("Formation obligatoire pour votre métier, non encore validée.")
        if not pourquoi:
            continue  # aucune raison de recommander
        # 5) session disponible
        ses = prochaine_session(data, f["id"])
        if ses and ses["places_insnees"] < ses["capacite"]:
            score += RECO_PONDERATIONS["session_disponible"]
        else:
            ses = None
        # Signalements (ne suppriment pas la recommandation : contrôle humain)
        alertes = []
        pres = prerequis_ok(data, sal, f)
        pres_manquants = [p for p in pres if not p["ok"]]
        if pres_manquants:
            alertes.append("Prérequis à acquérir : " + "; ".join(p["libelle"]
                         for p in pres_manquants))
        if duree_max_h and f["duree_h"] > duree_max_h:
            alertes.append(f"Durée ({f['duree_h']} h) supérieure au temps disponible indiqué ({duree_max_h} h).")
        if budget_dispo is not None and f["cout"] > budget_dispo:
            alertes.append(f"Coût ({fmt_euro(f['cout'])}) supérieur au budget restant du service ({fmt_euro(budget_dispo)}).")

        # Alternatives : autres formations développant les mêmes compétences principales
        alt_ids = []
        for c in f["competences"][:1]:
            for g in data["formations"]:
                if g["id"] != f["id"] and g["id"] not in term_ids and c in g["competences"]:
                    alt_ids.append(g["id"])
        alt_ids = alt_ids[:3]

        results.append({
            "formation_id": f["id"], "titre": f["titre"], "score": round(score, 1),
            "pourquoi": pourquoi,
            "competences_developpees": [find(data["competences"], "id", c)["nom"]
                                        for c in f["competences"]],
            "ecarts_reduits": [{"nom": e["nom"], "ecart": e["ecart"]}
                               for e, _ in sorted(cpts_traites, key=lambda x: -x[1])],
            "duree_h": f["duree_h"], "cout": f["cout"], "format": f["format"],
            "prerequis": pres, "alertes": alertes,
            "session_prochaine": (f"{fmt_date(ses['date_debut'])} — {ses['lieu']}"
                                  f" ({ses['capacite'] - ses['places_insnees']} place(s) restante(s))"
                                  if ses else "Aucune session avec place disponible à court terme"),
            "alternatives": [find(data["formations"], "id", a)["titre"] for a in alt_ids],
        })
    results.sort(key=lambda r: -r["score"])
    return {"salarie_id": sal["id"], "ponderations": RECO_PONDERATIONS,
            "recommandations": results[:10]}

# -----------------------------------------------------------------------------
# Cartographie des compétences stratégiques
# -----------------------------------------------------------------------------

def cartographie(data):
    rows = []
    for cpt in data["competences"]:
        # population concernée : salariés dont la compétence figure dans le référentiel d'un métier
        concernes = [s for s in data["salaries"] if s.get("metier_id") and
                     cpt["id"] in (find(data["metiers"], "id", s["metier_id"]) or {}).get("competences_cibles", {})]
        effs = [niveaux_effectifs(data, s).get(cpt["id"], {}).get("retenu") or 0 for s in concernes]
        n = len(effs)
        moy = round(sum(effs) / n, 2) if n else 0.0
        rares = sum(1 for e in effs if e >= 3)
        # écart moyen vs cibles des métiers concernés
        cibles = []
        for s in concernes:
            m = find(data["metiers"], "id", s["metier_id"])
            cibles.append(m["competences_cibles"][cpt["id"]])
        ecart_moyen = round(sum((c - a) for c, a in zip(cibles, effs)) / n, 2) if n else 0.0
        rows.append({
            "competence_id": cpt["id"], "nom": cpt["nom"], "theme": cpt["theme"],
            "critique": cpt.get("critique", False),
            "effectif_concerne": n, "moyenne_niveau": moy,
            "personnes_autonome_plus": rares,
            "taux_autonome_pct": round(100.0 * rares / n, 1) if n else 0.0,
            "ecart_moyen_vs_cible": ecart_moyen,
            "rare": bool(n > 0 and rares <= max(1, int(0.2 * n))),
        })
    rows.sort(key=lambda r: (not r["critique"], -r["ecart_moyen_vs_cible"]))
    return rows

# -----------------------------------------------------------------------------
# Simulation d'anticipation des besoins (estimations, pas de prédictions)
# -----------------------------------------------------------------------------

def simulation(data, scenario_id, budget_reduction_pct=None):
    scn = find(data["scenarios"], "id", scenario_id)
    if not scn:
        return {"erreur": "Scénario inconnu"}
    ajust = dict(scn.get("ajustements") or {})
    red = budget_reduction_pct if budget_reduction_pct is not None \
        else (scn.get("contrainte_budget_pct") or 0)

    # cibles de base : référentiels des métiers ; le scénario les augmente
    cibles_scenario = {}
    for cpt_id, delta in ajust.items():
        cibles_scenario[cpt_id] = delta

    lignes = []
    formations_suggerees = set()
    cout_estime = 0.0
    for cpt in data["competences"]:
        if cpt["id"] not in cibles_scenario:
            continue
        delta = cibles_scenario[cpt["id"]]
        concernes = [s for s in data["salaries"] if s.get("metier_id") and
                     cpt["id"] in (find(data["metiers"], "id", s["metier_id"]) or {}).get("competences_cibles", {})]
        effs = [niveaux_effectifs(data, s).get(cpt["id"], {}).get("retenu") or 0 for s in concernes]
        cibles_base = [(find(data["metiers"], "id", s["metier_id"])["competences_cibles"][cpt["id"]])
                       for s in concernes]
        n = len(effs)
        moy_actuel = round(sum(effs) / n, 2) if n else 0.0
        moy_cible_scen = round(sum(c + delta for c in cibles_base) / n, 2) if n else delta
        ecart = round(moy_cible_scen - moy_actuel, 2)
        affectes = sum(1 for a, c in zip(effs, cibles_base) if a < c + delta)
        # formations à envisager : celles qui développent la compétence (top coût-efficacité simple)
        f_sugg = sorted((f for f in data["formations"] if cpt["id"] in f["competences"]),
                        key=lambda f: f["cout"] / max(f["duree_h"], 1))[:3]
        for f in f_sugg:
            formations_suggerees.add(f["id"])
        if affectes > 0 and f_sugg:
            # estimation : coût de la formation la moins chère × nb d'affectés (hypothèse) 
            cout_estime += min(f["cout"] for f in f_sugg) * affectes
        lignes.append({
            "competence_id": cpt["id"], "nom": cpt["nom"], "delta_cible": delta,
            "effectif_concerne": n, "moyenne_actuelle": moy_actuel,
            "cible_scenario": moy_cible_scen, "ecart_scenario": ecart,
            "salaries_affectes": affectes,
            "formations_suggerees": [f["titre"] for f in f_sugg],
        })
    lignes.sort(key=lambda l: -l["ecart_scenario"])

    budget_actuel = budget_state(data)["total"]
    budget_scenario = round(budget_actuel * (1 + red / 100.0)) if red else budget_actuel
    return {
        "scenario": {"id": scn["id"], "nom": scn["nom"], "description": scn["description"]},
        "reduction_budget_pct": red,
        "budget_annuel_actuel": budget_actuel,
        "budget_scenario_estime": budget_scenario,
        "cout_formation_estime": round(cout_estime),
        "lignes": lignes,
        "formations_a_envisager": sorted({f["id"] for f in data["formations"]
                                          if f["id"] in formations_suggerees}),
        "avertissement": ("Ces projections sont des ESTIMATIONS fondées sur des hypothèses "
                          "explicitement déclarées, pas des prédictions certaines. Elles servent "
                          "au dialogue de pilotage et doivent être arbitrées par la DRH."),
    }

# -----------------------------------------------------------------------------
# Équité d'accès à la formation
# -----------------------------------------------------------------------------

def equite_acces(data):
    rows = []
    for svc in data["services"]:
        effectif = sum(1 for s in data["salaries"] if s["service_id"] == svc["id"])
        formes = {r["salarie_id"] for r in data["realisations"]
                  if r.get("validee") and
                  (find(data["salaries"], "id", r["salarie_id"]) or {}).get("service_id") == svc["id"]}
        taux = round(100.0 * len(formes) / effectif, 1) if effectif else 0.0
        heures = sum(r.get("heures_reelles") or 0 for r in data["realisations"]
                     if r.get("validee") and
                     (find(data["salaries"], "id", r["salarie_id"]) or {}).get("service_id") == svc["id"])
        rows.append({"service_id": svc["id"], "nom": svc["nom"], "effectif": effectif,
                     "salaries_formes": len(formes), "taux_acces_pct": taux,
                     "heures_reelles": heures,
                     "prudence": effectif < 5})
    rows.sort(key=lambda r: -r["taux_acces_pct"])
    return {"lignes": rows,
            "avertissement": ("Indicateur de répartition uniquement : il ne sert pas à pénaliser "
                              "des salariés ou des équipes. Interpréter avec prudence lorsque "
                              "les effectifs sont faibles (< 5).")}

# -----------------------------------------------------------------------------
# Alertes et automatisations (règles configurables)
# -----------------------------------------------------------------------------

def alertes(data, role="drh", user_id=None):
    p = data["parametres"]
    out = []
    # 1) demandes en attente depuis trop longtemps
    for dem in data["demandes"]:
        if dem["statut"] != "en_attente":
            continue
        age = (TODAY - date.fromisoformat(dem["date_creation"])).days
        sal = find(data["salaries"], "id", dem["salarie_id"])
        for_ = find(data["formations"], "id", dem["formation_id"])
        if role == "manager" and sal and sal.get("manager_id") != user_id:
            continue
        if age > p["delai_attente_jours"]:
            out.append({"type": "attente_trop_longue", "gravite": "haute",
                        "message": (f"Demande {dem['id']} de {sal['nom'] if sal else dem['salarie_id']} "
                                    f"(« {for_['titre'] if for_ else '?'} ») en attente depuis {age} jours "
                                    f"(seuil configuré : {p['delai_attente_jours']} j)."),
                        "lien": f"#/demandes?focus={dem['id']}"})
    # 2) sessions bientôt complètes
    for s in data["sessions"]:
        occ = 100.0 * s["places_insnees"] / s["capacite"] if s["capacite"] else 0
        if occ >= p["seuil_session_pleine_pct"] and s["date_debut"] > TODAY.isoformat():
            for_ = find(data["formations"], "id", s["formation_id"])
            out.append({"type": "session_presque_pleine", "gravite": "moyenne",
                        "message": (f"Session « {for_['titre'] if for_ else s['formation_id']} » du "
                                    f"{fmt_date(s['date_debut'])} à {int(occ)} % de remplissage "
                                    f"({s['capacite'] - s['places_insnees']} place(s) restante(s))."),
                        "lien": "#/catalogue"})
    # 3) formations obligatoires arrivant à échéance / non suivies
    for met in data["metiers"]:
        for fo in met.get("formations_obligatoires", []):
            for s in data["salaries"]:
                if s.get("metier_id") != met["id"]:
                    continue
                term = [r for r in data["realisations"]
                        if r["salarie_id"] == s["id"] and r["formation_id"] == fo["formation_id"]
                        and r.get("validee")]
                if not term:
                    out.append({"type": "obligatoire_non_suivie", "gravite": "haute",
                                "message": (f"{s['nom']} ({met['nom']}) n'a pas encore validé la formation "
                                            f"obligatoire « {find(data['formations'], 'id', fo['formation_id'])['titre']} ».", ),
                                "lien": "#/demandes"})
                else:
                    derniere = max(r["date_fin"] for r in term)
                    limite = (date.fromisoformat(derniere) + timedelta(days=fo["validite_mois"] * 30))
                    if limite < TODAY and role == "drh":
                        out.append({"type": "obligatoire_expires", "gravite": "haute",
                                    "message": (f"Formation obligatoire de {s['nom']} expirée le "
                                                f"{fmt_date(derniere)} (validité {fo['validite_mois']} mois) — à réorganiser.", ),
                                    "lien": "#/demandes"})
    # 4) budget proche du plafond
    for b in data["budgets"]:
        bs = budget_state(data, b["service_id"])
        if bs["taux_utilisation_pct"] >= p["seuil_budget_pct"]:
            svc = find(data["services"], "id", b["service_id"])
            out.append({"type": "budget_plafond", "gravite": "haute",
                        "message": (f"Budget {svc['nom']} : {bs['taux_utilisation_pct']} % utilisé "
                                    f"(seuil d'alerte : {p['seuil_budget_pct']} %). Reste {fmt_euro(bs['restant'])}.", ),
                        "lien": "#/tableau-de-bord"})
    # 5) compétences critiques insuffisamment couvertes
    for row in cartographie(data):
        if row["critique"] and row["effectif_concerne"] > 0 and \
                row["taux_autonome_pct"] < p["seuil_couverture_critique"] * 20:
            out.append({"type": "competence_critique", "gravite": "moyenne",
                        "message": (f"Compétence critique « {row['nom']} » : seulement "
                                    f"{row['taux_autonome_pct']} % des salariés concernés sont autonomes ou plus "
                                    f"(écart moyen vs cible : {row['ecart_moyen_vs_cible']})."),
                        "lien": "#/cartographie"})
    out.sort(key=lambda a: {"haute": 0, "moyenne": 1}.get(a["gravite"], 2))
    return out

# -----------------------------------------------------------------------------
# Tableau de bord — indicateurs (formules documentées)
# -----------------------------------------------------------------------------

def tableau_bord(data, service_id=None, theme=None, format_=None,
                 debut_iso=None, fin_iso=None):
    def _dans_periode(iso_date):
        if debut_iso and iso_date < debut_iso:
            return False
        if fin_iso and iso_date > fin_iso:
            return False
        return True

    def _filtre_form(for_):
        if theme and for_["theme"] != theme:
            return False
        if format_ and for_["format"] != format_:
            return False
        return True

    # Réalisations dans le périmètre
    rals = []
    for r in data["realisations"]:
        if not r.get("validee"):
            continue
        sal = find(data["salaries"], "id", r["salarie_id"])
        for_ = find(data["formations"], "id", r["formation_id"])
        if service_id and (not sal or sal["service_id"] != service_id):
            continue
        if not _filtre_form(for_):
            continue
        if not (_dans_periode(r["date_fin"]) or _dans_periode(r["date_debut"])):
            continue
        rals.append((r, sal, for_))

    salaries_formes = {r["salarie_id"] for r, _, _ in rals}
    effectif_ref = sum(1 for s in data["salaries"]
                       if (not service_id or s["service_id"] == service_id)
                       and s.get("metier_id"))  # effectif de référence : salariés opérationnels
    heures = sum(r.get("heures_reelles") or 0 for r, _, _ in rals)
    nb_formations_suivies = len(rals)

    bs = budget_state(data, service_id)

    # taux de validation des demandes (périmètre, sur la période de création)
    val = refu = 0
    for dem in data["demandes"]:
        sal = find(data["salaries"], "id", dem["salarie_id"])
        if service_id and (not sal or sal["service_id"] != service_id):
            continue
        if not _dans_periode(dem["date_creation"]):
            continue
        for_ = find(data["formations"], "id", dem["formation_id"])
        if not _filtre_form(for_):
            continue
        if dem["statut"] in ("approuvee", "inscrite", "terminee"):
            val += 1
        elif dem["statut"] == "refusee":
            refu += 1
    taux_validation = round(100.0 * val / (val + refu), 1) if (val + refu) else None

    # répartitions
    par_theme, par_format = {}, {}
    for r, sal, for_ in rals:
        par_theme[for_["theme"]] = par_theme.get(for_["theme"], 0) + 1
        par_format[for_["format"]] = par_format.get(for_["format"], 0) + 1
    couts_par_service = {}
    for r, sal, for_ in rals:
        if sal:
            svc = find(data["services"], "id", sal["service_id"])
            nom = svc["nom"] if svc else sal["service_id"]
            couts_par_service[nom] = round(couts_par_service.get(nom, 0) + for_["cout"])

    # compétences les plus demandées (via demandes de formation)
    cpt_demandees = {}
    for dem in data["demandes"]:
        if dem["statut"] == "brouillon":
            continue
        sal = find(data["salaries"], "id", dem["salarie_id"])
        if service_id and (not sal or sal["service_id"] != service_id):
            continue
        for_ = find(data["formations"], "id", dem["formation_id"])
        for c in for_["competences"]:
            cpt_demandees[c] = cpt_demandees.get(c, 0) + 1
    top_cpts = sorted(((find(data["competences"], "id", c)["nom"], n)
                       for c, n in cpt_demandees.items()), key=lambda x: -x[1])[:6]

    # plus grands écarts (cartographie filtrée si service donné → simplifié : global)
    carto = cartographie(data)
    top_ecarts = [(r["nom"], r["ecart_moyen_vs_cible"]) for r in carto if r["effectif_concerne"] > 0][:6]

    return {
        "perimetre": {"service_id": service_id, "theme": theme, "format": format_,
                      "debut": debut_iso, "fin": fin_iso},
        "budget": bs,
        "salaries_formes": len(salaries_formes),
        "effectif_reference": effectif_ref,
        "taux_acces_pct": round(100.0 * len(salaries_formes) / effectif_ref, 1) if effectif_ref else 0.0,
        "heures_reelles": heures,
        "formations_suivies": nb_formations_suivies,
        "taux_validation_pct": taux_validation,
        "par_theme": par_theme, "par_format": par_format,
        "couts_par_service": couts_par_service,
        "competences_demandees": top_cpts, "plus_grands_ecarts": top_ecarts,
        "definitions": {
            "budget_total": "Enveloppe annuelle de formation allouée au périmètre (somme des budgets annuels par service).",
            "budget_engage": "Coût des demandes approuvées ou inscrites, non terminées : réservation budgétaire, pas encore dépense.",
            "budget_consomme": "Coût des formations terminées avec réalisation validée (heures réellement effectuées).",
            "budget_restant": "budget_total − budget_engage − budget_consomme.",
            "taux_acces_pct": "Salariés distincts ayant suivi ≥ 1 formation dans la période ÷ effectif de référence × 100.",
            "taux_validation_pct": "Demandes approuvées (approuvée/inscrite/terminée) ÷ (approuvées + refusées) × 100, sur la période.",
            "heures_reelles": "Somme des heures effectivement réalisées (après validation de la réalisation), distinctes des heures prévues.",
        },
    }

# -----------------------------------------------------------------------------
# Chatbot « SmartSkills Assistant » — réponses prédéfinies + recherche catalogue
# (mode démonstration : AUCUN modèle d'IA externe n'est connecté)
# -----------------------------------------------------------------------------

CHATBASE = [
    (r"\b(comment|comment\s+faire|demander)\b.*\b(formation|inscription)\b|demande de formation",
     "Pour demander une formation : 1) ouvrez « Catalogue » ; 2) choisissez une formation et sa session ; "
     "3) cliquez sur « Demander l'inscription ». Votre demande passe au statut « En attente » et votre manager "
     "est notifié. Vous suivez son évolution dans « Mes demandes » et recevez une notification à chaque changement."),
    (r"auto-?evaluation|évaluer mes compétences|auto eval",
     "L'autoévaluation se trouve dans l'écran « Autoévaluation ». Notez-vous de 1 à 5 sur chaque compétence de "
     "votre référentiel (1 = débutant … 5 = expert). Attention : c'est une DÉCLARATION, pas une mesure objective. "
     "Elle sert de support au dialogue avec votre manager, qui peut ensuite valider certaines compétences."),
    (r"statut|brouillon|en attente|approuv|refus|inscri|termin|annul",
     "Les statuts d'une demande sont : Brouillon → En attente de validation → Approuvée ou Refusée → Inscrit(e) en "
     "session → Terminée (ou Annulée à tout moment avant la fin). Chaque décision du manager est motivée et "
     "conservée dans l'historique de la demande."),
    (r"recommand|parcours|suggér|sugger",
     "L'écran « Recommandations » propose des formations expliquées : écarts de compétences vs votre référentiel, "
     "compétences critiques, objectif d'évolution déclaré, prérequis et budget. C'est une aide à la décision : le "
     "choix final revient toujours à vous, votre manager et la DRH."),
    (r"attestation|certificat",
     "Une attestation est générée automatiquement quand une formation est terminée ET validée (assiduité "
     "suffisante). Retrouvez-la dans « Mes attestations » — elle est téléchargeable. Rappel : ce sont des "
     "attestations de démonstration, non officielles."),
    (r"budget|coût|cout|combien",
     "Le budget est visible dans le tableau de bord (DRH) : total, engagé (demandes approuvées/inscrites), "
     "consommé (formations terminées validées) et restant. Un manager vérifie le budget prévisionnel avant de "
     "valider une demande."),
    (r"rgpd|données? personnelles|confidentialité|vie privée",
     "SmartSkills ne traite que des données fictives de démonstration. En production, les règles RGPD sont "
     "documentées dans l'écran « Documentation » : finalités, conservation, droits d'accès/rectification et "
     "mesures de sécurité."),
    (r"obligatoire|expir",
     "Certaines formations sont obligatoires pour des métiers exposés (ex. sécurité industrielle). L'écran "
     "« Alertes » signale les obligations non suivies ou expirées, et votre manager est informé."),
    (r"quiz|évaluation à chaud|satisfaction",
     "Après chaque formation, un court questionnaire à chaud mesure satisfaction, pertinence et intention de "
     "réutilisation. Les résultats agrégés aident le service Formation ; ils ne mesurent PAS l'impact à long "
     "terme (voir l'évaluation à froid, 30-90 jours après)."),
    (r"simulation|anticip|futur|scénario",
     "Le module « Simulation » (DRH) permet de tester des hypothèses (Industrie 4.0, automatisation, cybersécurité, "
     "contrainte budgétaire…) et d'estimer les écarts de compétences résultants. Ce sont des estimations pour le "
     "pilotage, pas des prédictions."),
    (r"bonjour|salut|hello|coucou",
     "Bonjour ! Je suis SmartSkills Assistant (mode démonstration : réponses prédéfinies + recherche dans le "
     "catalogue). Posez-moi une question sur les formations, vos demandes, l'autoévaluation ou le budget."),
]

def chatbot(data, question, user_id=None):
    q = (question or "").lower()
    # 1) recherche dans le catalogue
    mots = re.findall(r"[a-zàâéèêëîïôöûùüç]{4,}", q)
    if mots and not any(k in q for k in ["comment", "pourquoi", "statut"]):
        hits = []
        for f in data["formations"]:
            texte = (f["titre"] + " " + f["description"] + " " + f["theme"] + " " +
                     " ".join((find(data["competences"], "id", c) or {"nom": ""})["nom"]
                               for c in f["competences"])).lower()
            score = sum(1 for m in mots if m in texte)
            if score >= 2 or (len(mots) == 1 and mots[0] in f["titre"].lower()):
                hits.append((score, f))
        if hits:
            hits.sort(key=lambda x: -x[0])
            rep = "J'ai trouvé dans le catalogue :\n"
            for sc, f in hits[:4]:
                ses = prochaine_session(data, f["id"])
                rep += (f"• {f['titre']} — {f['format']}, {f['duree_h']} h, {fmt_euro(f['cout'])}"
                        + (f" ; prochaine session : {fmt_date(ses['date_debut'])}" if ses else "") + "\n")
            rep += "Ouvrez « Catalogue » pour le détail et demander l'inscription. Si ma réponse est incertaine, " \
                   "demandez à la DRH (sf-2001)."
            return {"reponse": rep, "confiance": "moyenne",
                    "limite": "Recherche textuelle simple dans le catalogue fictif."}
    # 2) base de réponses prédéfinies
    for pattern, reponse in CHATBASE:
        if re.search(pattern, q):
            return {"reponse": reponse, "confiance": "haute",
                    "limite": "Réponse prédéfinie (mode démo, sans modèle d'IA externe)."
                              " Je ne prends aucune décision RH : en cas de question complexe, "
                              "adressez-vous à la DRH."}
    return {"reponse": ("Je ne suis pas certain de comprendre votre question (mes capacités sont limitées au "
                        "mode démonstration). Essayez par ex. « comment demander une formation », « statuts d'une "
                        "demande », ou le titre d'une formation. Pour toute question complexe : DRH (sf-2001)."),
            "confiance": "faible",
            "limite": "Assistant basé sur des réponses prédéfinies et une recherche dans le catalogue. "
                      "Aucun modèle d'IA externe n'est connecté."}

# -----------------------------------------------------------------------------
# Attestations — génération
# -----------------------------------------------------------------------------

def creer_attestation(data, realisation):
    n = data["compteurs"]["attestation"] + 1
    aid = f"AT-{realisation['date_fin'][:4]}-{n:04d}"
    att = {"id": aid, "realisation_id": realisation["id"],
           "date_emission": TODAY.isoformat(), "statut": "emise"}
    data["attestations"].append(att)
    data["compteurs"]["attestation"] = n
    return att

def html_attestation(data, att):
    r = find(data["realisations"], "id", att["realisation_id"])
    sal = find(data["salaries"], "id", r["salarie_id"])
    f = find(data["formations"], "id", r["formation_id"])
    pre = find(data["prestataires"], "id", f["prestataire_id"])
    cpts = [find(data["competences"], "id", c)["nom"] for c in f["competences"]]
    metier = find(data["metiers"], "id", sal.get("metier_id"))
    svc_nom = (find(data["services"], "id", sal.get("service_id")) or {"nom": "—"})["nom"]
    logo = ("<svg width='72' height='72' viewBox='0 0 100 100'>"
            "<rect x='5' y='5' width='90' height='90' rx='18' fill='#0b3d66'/>"
            "<path d='M25 62 L42 40 L55 55 L75 30' stroke='#f5a623' stroke-width='7' fill='none' stroke-linecap='round' stroke-linejoin='round'/>"
            "<circle cx='75' cy='30' r='6' fill='#4cc9f0'/></svg>")
    return f"""<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<title>Attestation {att['id']} — SmartSkills (démonstration)</title>
<style>
 body{{font-family:'Segoe UI',Arial,sans-serif;background:#eef2f7;margin:0;padding:40px;}}
 .page{{max-width:760px;margin:auto;background:#fff;border-radius:10px;box-shadow:0 8px 30px rgba(11,61,102,.15);padding:48px;position:relative;overflow:hidden;}}
 .bande{{position:absolute;top:0;left:0;right:0;background:#0b3d66;color:#fff;padding:10px 48px;font-size:12px;letter-spacing:.14em;text-transform:uppercase;}}
 .head{{display:flex;gap:20px;align-items:center;margin:34px 0 8px;}}
 h1{{margin:6px 0 0;color:#0b3d66;font-size:26px;}}
 .sub{{color:#5a6b7d;font-size:14px;}}
 .body{{margin-top:26px;font-size:15px;line-height:1.75;color:#22303c;}}
 table{{width:100%;border-collapse:collapse;margin:18px 0;}}
 td{{padding:9px 12px;border-bottom:1px solid #e3e9f0;font-size:14px;}}
 td:first-child{{color:#5a6b7d;width:42%;}}
 .demo{{margin-top:30px;background:#fff7e8;border:1.5px dashed #f5a623;border-radius:8px;padding:12px 16px;font-size:12.5px;color:#7a5b12;}}
 .sign{{display:flex;justify-content:space-between;margin-top:40px;font-size:13.5px;color:#22303c;}}
 .stamp{{width:150px;text-align:center;border:1.5px solid #0b3d66;border-radius:8px;padding:10px 6px;color:#0b3d66;font-size:11.5px;letter-spacing:.06em;}}
 @media print{{body{{background:#fff;padding:0;}}.page{{box-shadow:none;border-radius:0;}}}}
</style></head><body>
<div class="page">
 <div class="bande">SmartFactory — Service Formation &amp; Développement des compétences</div>
 <div class="head">{logo}
  <div><h1>Attestation de formation</h1>
  <div class="sub">Application SmartSkills v{VERSION} — document de démonstration</div></div></div>
 <div class="body">
  <p>Nous attestons que</p>
  <p style="font-size:17px"><strong>{sal['nom']}</strong><br>
  <span class="sub">Identifiant salarié (fictif) : {sal['id'].upper()} — Métier : {metier['nom'] if metier else '—'} — Service : {svc_nom}</span></p>
  <p>a suivi et terminé la formation suivante, avec réalisation validée :</p>
  <table>
   <tr><td>Titre de la formation</td><td><strong>{f['titre']}</strong></td></tr>
   <tr><td>Prestataire</td><td>{pre['nom'] if pre else '—'}</td></tr>
   <tr><td>Dates</td><td>du {fmt_date(r['date_debut'])} au {fmt_date(r['date_fin'])}</td></tr>
   <tr><td>Durée effectivement réalisée</td><td>{r['heures_reelles']} h (prévues : {r['heures_prevues']} h)</td></tr>
   <tr><td>Format</td><td>{f['format']}</td></tr>
   <tr><td>Compétences / objectifs pédagogiques</td><td>{', '.join(cpts)}</td></tr>
   <tr><td>Objectifs pédagogiques</td><td>{'<br>'.join('• ' + o for o in f['objectifs'])}</td></tr>
   <tr><td>Date d'émission</td><td>{fmt_date(att['date_emission'])}</td></tr>
   <tr><td>Identifiant unique d'attestation</td><td><strong>{att['id']}</strong></td></tr>
  </table>
  <div class="demo">⚠ ATTESTATION DE DÉMONSTRATION — Ce document est généré par l'application pédagogique
  SmartSkills (projet universitaire). Il ne constitue pas un certificat officiel. Toutes les données
  (salarié, formation, dates) sont fictives.</div>
  <div class="sign">
   <div>Le Service Formation &amp; Développement<br>SmartFactory (entité fictive)</div>
   <div class="stamp">SMARTFACTORY<br>SERVICE FORMATION<br>{att['id']}</div>
  </div>
 </div>
</div></body></html>"""

# -----------------------------------------------------------------------------
# Serveur HTTP + API
# -----------------------------------------------------------------------------

SESSIONS = {}   # token -> user_id (mémoire vive uniquement)

ROLES = {"salarie", "manager", "drh", "admin"}

class Handler(BaseHTTPRequestHandler):
    server_version = "SmartSkills/" + VERSION

    # ---------- utilitaires ----------
    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _html(self, html, code=200):
        body = html.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _body(self):
        try:
            n = int(self.headers.get("Content-Length", 0))
            raw = self.rfile.read(n) if n else b"{}"
            return json.loads(raw.decode("utf-8") or "{}")
        except Exception:
            return {}

    def _user(self):
        cookie = self.headers.get("Cookie", "")
        m = re.search(r"ss_token=([a-f0-9]{16,})", cookie)
        if m and SESSIONS.get(m.group(1)):
            uid = SESSIONS[m.group(1)]
            sal = find(DATA["salaries"], "id", uid)
            if sal:
                return {"id": uid, "role": DATA["roles"].get(uid, "salarie"), "nom": sal["nom"]}
        return None

    def _need(self, *roles):
        u = self._user()
        if not u:
            self._json({"erreur": "Non authentifié."}, 401)
            return None, None
        if roles and u["role"] not in roles:
            self._json({"erreur": f"Accès refusé : rôle « {u['role']} » non autorisé."}, 403)
            return None, None
        return u, None

    def log_message(self, fmt, *args):
        pass  # silence du journal (mode démo)

    # ---------- GET ----------
    def do_GET(self):
        url = urlparse(self.path)
        p = url.path
        q = {k: v[0] for k, v in parse_qs(url.query).items()}
        try:
            if p == "/":
                return self._html(PAGE_HTML)
            if p == "/api/state":
                u = self._user()
                if not u:
                    return self._json({"connecte": False, "comptes_demo": [
                        {"id": "sf-1002", "nom": "Camille D. — salarié(e) (Maintenance)"},
                        {"id": "sf-1015", "nom": "Karim B. — manager (équipe Maintenance)"},
                        {"id": "sf-2001", "nom": "Nadia L. — DRH / Service Formation"},
                        {"id": "sf-9001", "nom": "Admin Technique — administrateur"}]})
                return self._json(self.state_public(u))
            if p == "/api/dashboard":
                u, err = self._need("drh", "admin")
                if not u:
                    return
                return self._json(tableau_bord(DATA, q.get("service"), q.get("theme"),
                                                q.get("format"), q.get("debut"), q.get("fin")))
            if p == "/api/recommandations":
                u, err = self._need()
                if not u:
                    return
                sal = find(DATA["salaries"], "id", u["id"])
                duree = int(q["duree"]) if q.get("duree") else None
                budg = float(q["budget"]) if q.get("budget") else None
                return self._json(recommandations(DATA, sal, duree, budg))
            if p == "/api/simulation":
                u, err = self._need("drh", "admin")
                if not u:
                    return
                red = int(q["reduction"]) if q.get("reduction") else None
                return self._json(simulation(DATA, q.get("scenario", "SCN-01"), red))
            if p == "/api/cartographie":
                u, err = self._need("drh", "admin")
                if not u:
                    return
                return self._json(cartographie(DATA))
            if p == "/api/equite":
                u, err = self._need("drh", "admin")
                if not u:
                    return
                return self._json(equite_acces(DATA))
            if p == "/api/alertes":
                u, err = self._need()
                if not u:
                    return
                return self._json(alertes(DATA, u["role"], u["id"]))
            if p.startswith("/api/attestation/"):
                u, err = self._need()
                if not u:
                    return
                aid = p.rsplit("/", 1)[-1]
                att = find(DATA["attestations"], "id", aid)
                if not att:
                    return self._json({"erreur": "Attestation introuvable."}, 404)
                r = find(DATA["realisations"], "id", att["realisation_id"])
                sal_ok = (u["role"] in ("drh", "admin") or
                          r["salarie_id"] == u["id"] or
                          (find(DATA["salaries"], "id", r["salarie_id"]) or {}).get("manager_id") == u["id"])
                if not sal_ok:
                    return self._json({"erreur": "Accès refusé : attestation d'un tiers."}, 403)
                html = html_attestation(DATA, att)
                body = html.encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Disposition",
                                 f'attachment; filename="{aid}_SmartSkills_demo.html"')
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if p == "/api/chat":
                u, err = self._need()
                if not u:
                    return
                return self._json(chatbot(DATA, q.get("q", ""), u["id"]))
            if p == "/api/export":
                u, err = self._need("drh", "admin")
                if not u:
                    return
                body = json.dumps(DATA, ensure_ascii=False, indent=1).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Disposition",
                                 "attachment; filename=smartskills_export_demo.json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if p == "/api/indicateurs-definitions":
                u = self._user()
                if not u:
                    return self._json({"erreur": "Non authentifié."}, 401)
                return self._json(tableau_bord(DATA)["definitions"])
            return self._json({"erreur": "Route inconnue : " + p}, 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._json({"erreur": f"Erreur interne : {e}"}, 500)

    # ---------- POST ----------
    def do_POST(self):
        global DATA
        url = urlparse(self.path)
        p = url.path
        body = self._body()
        try:
            if p == "/api/login":
                uid, pwd = body.get("id", ""), body.get("password", "")
                sal = find(DATA["salaries"], "id", uid.strip().lower())
                if not sal or DATA["roles"].get(uid.strip().lower()) is None:
                    return self._json({"erreur": "Identifiant inconnu."}, 401)
                if pwd != "demo":
                    return self._json({"erreur": "Mot de passe incorrect (démo : « demo »)."}, 401)
                token = uuid.uuid4().hex
                SESSIONS[token] = uid.strip().lower()
                self.send_response(200)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Set-Cookie", f"ss_token={token}; Path=/; HttpOnly; SameSite=Lax")
                payload = json.dumps({"ok": True}, ensure_ascii=False).encode("utf-8")
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)
                return
            if p == "/api/logout":
                cookie = self.headers.get("Cookie", "")
                m = re.search(r"ss_token=([a-f0-9]{16,})", cookie)
                if m:
                    SESSIONS.pop(m.group(1), None)
                return self._json({"ok": True})

            u, err = self._need()
            if not u:
                return
            sal = find(DATA["salaries"], "id", u["id"])

            # ----- demande : création -------------------------------------
            if p == "/api/demande/create":
                fid, sid = body.get("formation_id"), body.get("session_id")
                statut = body.get("statut", "en_attente")
                for_ = find(DATA["formations"], "id", fid)
                if not for_:
                    return self._json({"erreur": "Formation inconnue."}, 400)
                if statut not in ("brouillon", "en_attente"):
                    return self._json({"erreur": "Statut de création invalide."}, 400)
                # contrôle doublon : un seul dossier ouvert par salarié + formation
                for dem in DATA["demandes"]:
                    if dem["salarie_id"] == u["id"] and dem["formation_id"] == fid \
                            and dem["statut"] in ("brouillon", "en_attente", "approuvee", "inscrite"):
                        return self._json({"erreur": f"Une demande active existe déjà pour cette formation ({dem['id']})."}, 409)
                # contrôle capacité de session
                if sid:
                    ses = find(DATA["sessions"], "id", sid)
                    if not ses or ses["formation_id"] != fid:
                        return self._json({"erreur": "Session inconnue ou non associée à cette formation."}, 400)
                    if ses["places_insnees"] >= ses["capacite"]:
                        return self._json({"erreur": "Cette session est complète : choisissez une autre session."}, 409)
                n = DATA["compteurs"]["demande"] + 1
                dem = {"id": f"DEM-{n:03d}", "salarie_id": u["id"], "formation_id": fid,
                       "session_id": sid, "statut": statut,
                       "date_creation": TODAY.isoformat(),
                       "historique": [{"date": TODAY.isoformat(),
                                       "action": "demande_creee", "par": u["id"],
                                       "detail": ("Brouillon enregistré." if statut == "brouillon"
                                                   else "Demande envoyée à la validation du manager.")}]}
                DATA["demandes"].append(dem)
                DATA["compteurs"]["demande"] = n
                save_data(DATA)
                return self._json({"ok": True, "demande_id": dem["id"]})

            # ----- demande : transition de statut ---------------------------
            if p.startswith("/api/demande/") and p.endswith("/transition"):
                did = p.split("/")[3]
                dem = find(DATA["demandes"], "id", did)
                if not dem:
                    return self._json({"erreur": "Demande introuvable."}, 404)
                nouveau = body.get("statut")
                motif = (body.get("motif") or "").strip()
                for_ = find(DATA["formations"], "id", dem["formation_id"])
                # permissions
                if u["role"] == "salarie":
                    if dem["salarie_id"] != u["id"]:
                        return self._json({"erreur": "Accès refusé : demande d'un tiers."}, 403)
                    autorises = {"annulee", "en_attente"}  # annuler la sienne, ou soumettre un brouillon
                elif u["role"] == "manager":
                    sal_dem = find(DATA["salaries"], "id", dem["salarie_id"])
                    if not sal_dem or sal_dem.get("manager_id") != u["id"]:
                        return self._json({"erreur": "Cette demande ne concerne pas votre équipe."}, 403)
                    autorises = {"approuvee", "refusee", "annulee"}
                else:  # drh / admin
                    autorises = {"approuvee", "refusee", "inscrite", "terminee", "annulee"}
                if nouveau not in TRANSITIONS.get(dem["statut"], set()):
                    return self._json({"erreur": f"Transition impossible : « {STATUTS_DEMANDE[dem['statut']]} » → « {STATUTS_DEMANDE.get(nouveau, nouveau)} »."}, 409)
                if nouveau not in autorises:
                    return self._json({"erreur": f"Votre rôle ne permet pas le passage à « {STATUTS_DEMANDE.get(nouveau, nouveau)} »."}, 403)
                if nouveau in ("approuvee", "refusee") and not motif:
                    return self._json({"erreur": "Le motif de la décision est obligatoire (équité et traçabilité)."}, 400)
                # inscription : session obligatoire avec place
                if nouveau == "inscrite":
                    sid = body.get("session_id") or dem["session_id"]
                    ses = find(DATA["sessions"], "id", sid) if sid else None
                    if not ses or ses["formation_id"] != dem["formation_id"]:
                        return self._json({"erreur": "Une session valide est requise pour inscrire."}, 400)
                    if ses["places_insnees"] >= ses["capacite"]:
                        return self._json({"erreur": "Session complète : choisissez une autre session."}, 409)
                    dem["session_id"] = sid
                # terminée : heures réalisées obligatoires, attestation si conditions remplies
                realisation = None
                if nouveau == "terminee":
                    heures = body.get("heures_reelles")
                    try:
                        heures = int(heures)
                    except (TypeError, ValueError):
                        return self._json({"erreur": "Les heures réellement effectuées sont obligatoires."}, 400)
                    prevues = for_["duree_h"]
                    if heures < 0 or heures > prevues * 1.2:
                        return self._json({"erreur": f"Heures incohérentes (prévues : {prevues} h)."}, 400)
                    n = DATA["compteurs"]["realisation"] + 1
                    validee = heures >= prevues * 0.8   # règle : ≥ 80 % d'assiduité
                    realisation = {"id": f"RAL-{n:02d}", "salarie_id": dem["salarie_id"],
                                   "formation_id": dem["formation_id"],
                                   "date_debut": (find(DATA["sessions"], "id", dem["session_id"]) or {}).get("date_debut", TODAY.isoformat()),
                                   "date_fin": TODAY.isoformat(),
                                   "heures_prevues": prevues, "heures_reelles": heures,
                                   "validee": validee, "attestation_id": None}
                    DATA["realisations"].append(realisation)
                    DATA["compteurs"]["realisation"] = n
                    if validee:
                        att = creer_attestation(DATA, realisation)
                        realisation["attestation_id"] = att["id"]
                # application de la transition
                dem["statut"] = nouveau
                dem["historique"].append({"date": TODAY.isoformat(), "action": nouveau,
                                          "par": u["id"],
                                          "motif": motif or None,
                                          "detail": (f"Inscrit(e) à la session {dem['session_id']}."
                                                     if nouveau == "inscrite" else
                                                     f"Formation terminée : {realisation['heures_reelles']} h réalisées, "
                                                     + (f"validée — attestation {realisation['attestation_id']} émise."
                                                        if realisation and realisation["validee"]
                                                        else "non validée (assiduité < 80 %), pas d'attestation."))
                                          if nouveau == "terminee" else None})
                # réservation de place à l'inscription
                if nouveau == "inscrite":
                    ses = find(DATA["sessions"], "id", dem["session_id"])
                    ses["places_insnees"] += 1
                # notification au salarié
                sal_dem = find(DATA["salaries"], "id", dem["salarie_id"])
                ntf = DATA["compteurs"]["notification"] + 1
                libelles = {"approuvee": f"a été approuvée par {u['nom']}",
                            "refusee": f"a été refusée. Motif : {motif}",
                            "inscrite": f"— vous êtes inscrit(e) en session.",
                            "terminee": (f"— terminée. " + (f"Attestation {realisation['attestation_id']} disponible." if realisation and realisation["validee"] else "Réalisation non validée (assiduité insuffisante).")),
                            "annulee": f"a été annulée.",
                            "en_attente": f"a été envoyée à la validation de votre manager."}
                DATA["notifications"].append({
                    "id": f"NTF-{ntf:03d}", "destinataire": dem["salarie_id"],
                    "message": f"Votre demande « {for_['titre']} » ({dem['id']}) {libelles[nouveau]}",
                    "date": TODAY.isoformat(), "lue": False})
                DATA["compteurs"]["notification"] = ntf
                save_data(DATA)
                return self._json({"ok": True, "statut": nouveau,
                                   "attestation_id": realisation["attestation_id"] if realisation else None})

            # ----- autoévaluation --------------------------------------------
            if p == "/api/autoevaluation":
                niveaux = body.get("niveaux") or {}
                for k, v in niveaux.items():
                    if not find(DATA["competences"], "id", k):
                        return self._json({"erreur": f"Compétence inconnue : {k}"}, 400)
                    try:
                        v = int(v)
                        if not 1 <= v <= 5:
                            raise ValueError
                    except (TypeError, ValueError):
                        return self._json({"erreur": f"Niveau invalide pour {k} : doit être un entier de 1 à 5."}, 400)
                sal.setdefault("autoevaluation", {}).update(niveaux)
                sal["autoevaluation"] = dict(sorted(sal["autoevaluation"].items()))
                save_data(DATA)
                return self._json({"ok": True,
                                   "rappel": "Ces niveaux sont des DÉCLARATIONS : ils ne constituent pas une mesure objective de performance. Votre manager peut en discuter et valider certaines compétences."})

            # ----- évaluation à chaud -----------------------------------------
            if p == "/api/evaluation":
                fid = body.get("formation_id")
                notes = body.get("notes") or {}
                for k in EV_CHAUD_KEYS:
                    try:
                        v = int(notes.get(k))
                        if not 1 <= v <= 5:
                            raise ValueError
                    except (TypeError, ValueError):
                        return self._json({"erreur": f"Note manquante ou invalide : {EV_CHAUD_LABELS[k]} (1 à 5)."}, 400)
                # doit exister une réalisation terminée récente pour ce salarié + formation
                ok = any(r["salarie_id"] == u["id"] and r["formation_id"] == fid and r.get("validee")
                         for r in DATA["realisations"])
                if not ok:
                    return self._json({"erreur": "Aucune réalisation validée trouvée pour cette formation."}, 409)
                deja = any(e["salarie_id"] == u["id"] and e["formation_id"] == fid for e in DATA["evaluations"])
                if deja:
                    return self._json({"erreur": "Vous avez déjà évalué cette formation."}, 409)
                DATA["evaluations"].append({"salarie_id": u["id"], "formation_id": fid,
                                            "notes": {k: int(notes[k]) for k in EV_CHAUD_KEYS},
                                            "commentaire": (body.get("commentaire") or "").strip()[:500],
                                            "date": TODAY.isoformat(), "type": "chaud"})
                save_data(DATA)
                return self._json({"ok": True,
                                   "rappel": "Merci. Cette évaluation à chaud mesure la satisfaction immédiate ; elle ne mesure ni l'acquisition réelle des connaissances, ni l'impact professionnel à long terme (évaluation à froid prévue 30-90 jours après)."})

            # ----- évaluation à froide ------------------------------------------
            if p == "/api/evaluation_froide":
                fid = body.get("formation_id")
                try:
                    util = int(body.get("utilisation_acquis"))
                    if not 1 <= util <= 5:
                        raise ValueError
                except (TypeError, ValueError):
                    return self._json({"erreur": "« Utilisation des acquis » : note de 1 à 5 obligatoire."}, 400)
                ok = any(r["salarie_id"] == u["id"] and r["formation_id"] == fid and r.get("validee")
                         for r in DATA["realisations"])
                if not ok:
                    return self._json({"erreur": "Aucune réalisation validée trouvée pour cette formation."}, 409)
                DATA["evaluations_froides"].append({
                    "salarie_id": u["id"], "formation_id": fid, "utilisation_acquis": util,
                    "difficultes": (body.get("difficultes") or "").strip()[:300],
                    "commentaire": (body.get("commentaire") or "").strip()[:500],
                    "date": TODAY.isoformat()})
                save_data(DATA)
                return self._json({"ok": True, "rappel": "Suivi à froid enregistré : il complète l'évaluation à chaud sans la remplacer."})

            # ----- validation d'une compétence par un évaluateur -----------------
            if p == "/api/competence_validee":
                if u["role"] not in ("manager", "drh", "admin"):
                    return self._json({"erreur": "Seul un manager, la DRH ou l'administrateur peut valider une compétence."}, 403)
                sal_id = body.get("salarie_id")
                cpt_id = body.get("competence_id")
                try:
                    niv = int(body.get("niveau"))
                    if not 1 <= niv <= 5:
                        raise ValueError
                except (TypeError, ValueError):
                    return self._json({"erreur": "Niveau de validation invalide (1 à 5)."}, 400)
                sal_v = find(DATA["salaries"], "id", sal_id)
                if not sal_v:
                    return self._json({"erreur": "Salarié inconnu."}, 400)
                if u["role"] == "manager" and sal_v.get("manager_id") != u["id"]:
                    return self._json({"erreur": "Ce salarié ne fait pas partie de votre équipe."}, 403)
                if not find(DATA["competences"], "id", cpt_id):
                    return self._json({"erreur": "Compétence inconnue."}, 400)
                motif = (body.get("justification") or "").strip()
                if not motif:
                    return self._json({"erreur": "La justification est obligatoire pour une validation de compétence."}, 400)
                DATA["competences_validees"].append({
                    "salarie_id": sal_id, "competence_id": cpt_id, "niveau": niv,
                    "justification": motif[:300], "date": TODAY.isoformat(), "par": u["id"]})
                save_data(DATA)
                return self._json({"ok": True,
                                   "rappel": "Compétence validée. Une validation par évaluateur est plus forte qu'une simple déclaration, mais reste un point de vue professionnel : elle s'inscrit dans le dialogue salarié/manager."})

            # ----- notifications ----------------------------------------------
            if p == "/api/notification/lire":
                ntf = find(DATA["notifications"], "id", body.get("id"))
                if ntf and (ntf["destinataire"] == u["id"] or u["role"] in ("drh", "admin")):
                    ntf["lue"] = True
                    save_data(DATA)
                    return self._json({"ok": True})
                return self._json({"erreur": "Notification introuvable ou non autorisée."}, 403)

            # ----- administration : catalogue, sessions, paramètres ------------------
            if p == "/api/formation/add":
                if u["role"] not in ("drh", "admin"):
                    return self._json({"erreur": "Accès refusé."}, 403)
                req = ["titre", "theme", "format", "duree_h", "cout", "prestataire_id",
                       "niveau", "description", "objectifs", "competences"]
                for k in req:
                    if not body.get(k):
                        return self._json({"erreur": f"Champ obligatoire manquant : {k}"}, 400)
                n = max(int(f["id"].split("-")[1]) for f in DATA["formations"]) + 1
                fid = f"FOR-{n:02d}"
                DATA["formations"].append({
                    "id": fid, "titre": body["titre"][:120], "theme": body["theme"],
                    "format": body["format"], "duree_h": int(body["duree_h"]),
                    "cout": float(body["cout"]), "prestataire_id": body["prestataire_id"],
                    "niveau": int(body["niveau"]), "description": body["description"][:500],
                    "objectifs": [o for o in body["objectifs"] if o][:8],
                    "competences": body["competences"], "prerequis": [],
                    "evaluation": (body.get("evaluation") or "À définir par le prestataire.")[:300],
                    "public_cible": (body.get("public_cible") or "Tous salariés")[:200]})
                save_data(DATA)
                return self._json({"ok": True, "formation_id": fid})

            if p == "/api/session/add":
                if u["role"] not in ("drh", "admin"):
                    return self._json({"erreur": "Accès refusé."}, 403)
                for k in ("formation_id", "date_debut", "date_fin", "capacite", "lieu"):
                    if not body.get(k):
                        return self._json({"erreur": f"Champ obligatoire manquant : {k}"}, 400)
                n = DATA["compteurs"]["session"] + 1
                DATA["sessions"].append({"id": f"SES-{n:02d}", "formation_id": body["formation_id"],
                                         "date_debut": body["date_debut"], "date_fin": body["date_fin"],
                                         "capacite": int(body["capacite"]), "places_insnees": 0,
                                         "lieu": body["lieu"][:120]})
                DATA["compteurs"]["session"] = n
                save_data(DATA)
                return self._json({"ok": True, "session_id": f"SES-{n:02d}"})

            if p == "/api/parametres":
                if u["role"] not in ("drh", "admin"):
                    return self._json({"erreur": "Accès refusé."}, 403)
                for k, v in body.items():
                    if k in DATA["parametres"]:
                        try:
                            DATA["parametres"][k] = float(v) if "." in str(v) else int(v)
                        except (TypeError, ValueError):
                            return self._json({"erreur": f"Valeur invalide pour {k}"}, 400)
                save_data(DATA)
                return self._json({"ok": True, "parametres": DATA["parametres"]})

            if p == "/api/reset":
                if u["role"] != "admin":
                    return self._json({"erreur": "Seul l'administrateur peut réinitialiser les données."}, 403)
                DATA = seed_data()
                save_data(DATA)
                return self._json({"ok": True, "message": "Données de démonstration restaurées."})

            return self._json({"erreur": "Route inconnue : " + p}, 404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return self._json({"erreur": f"Erreur interne : {e}"}, 500)

    # ---------- état public (filtré selon le rôle) ----------------------------
    def state_public(self, u):
        sal = find(DATA["salaries"], "id", u["id"])
        role = u["role"]
        if role == "salarie":
            visibles = [u["id"]] + [d["salarie_id"] for d in DATA["demandes"]]
            salaries_visibles = [sal]
            demandes_visibles = [d for d in DATA["demandes"] if d["salarie_id"] == u["id"]]
            realisations_visibles = [r for r in DATA["realisations"] if r["salarie_id"] == u["id"]]
            notifs = [n for n in DATA["notifications"] if n["destinataire"] == u["id"]]
        elif role == "manager":
            equipe_ids = {u["id"]} | {s["id"] for s in DATA["salaries"]
                                      if s.get("manager_id") == u["id"]}
            salaries_visibles = [s for s in DATA["salaries"] if s["id"] in equipe_ids]
            demandes_visibles = [d for d in DATA["demandes"]
                                 if find(DATA["salaries"], "id", d["salarie_id"], ) and
                                 find(DATA["salaries"], "id", d["salarie_id"]).get("manager_id") == u["id"]]
            realisations_visibles = [r for r in DATA["realisations"] if r["salarie_id"] in equipe_ids]
            notifs = [n for n in DATA["notifications"] if n["destinataire"] == u["id"]]
        else:
            salaries_visibles = DATA["salaries"]
            demandes_visibles = DATA["demandes"]
            realisations_visibles = DATA["realisations"]
            notifs = [n for n in DATA["notifications"] if n["destinataire"] == u["id"]]

        out = {
            "connecte": True, "user": {"id": u["id"], "role": role, "nom": sal["nom"]},
            "version": VERSION, "date_demo": TODAY.isoformat(),
            "services": DATA["services"], "metiers": DATA["metiers"],
            "competences": DATA["competences"], "prestataires": DATA["prestataires"],
            "formations": DATA["formations"], "sessions": DATA["sessions"],
            "salaries": salaries_visibles, "demandes": demandes_visibles,
            "realisations": realisations_visibles,
            "attestations": [a for a in DATA["attestations"] if
                             (role in ("drh", "admin") or
                              (find(DATA["realisations"], "id", a["realisation_id"]) or {}).get("salarie_id") == u["id"])],
            "evaluations": DATA["evaluations"] if role in ("drh", "admin") else
                           [e for e in DATA["evaluations"] if e["salarie_id"] == u["id"]],
            "evaluations_froides": DATA["evaluations_froides"] if role in ("drh", "admin") else
                                   [e for e in DATA["evaluations_froides"] if e["salarie_id"] == u["id"]],
            "competences_validees": ([cv for cv in DATA["competences_validees"]
                                      if (role in ("drh", "admin") or
                                          cv["salarie_id"] == u["id"] or
                                          cv["salarie_id"] in {s['id'] for s in salaries_visibles})]),
            "budgets": DATA["budgets"] if role in ("drh", "admin") else None,
            "parametres": DATA["parametres"] if role in ("drh", "admin") else None,
            "scenarios": DATA["scenarios"] if role in ("drh", "admin") else None,
            "notifications": notifs,
            "budget_state": budget_state(DATA, sal.get("service_id") if role == "salarie" else None),
            "levels": LEVELS,
        }
        return out

# -----------------------------------------------------------------------------
# Point d'entrée
# -----------------------------------------------------------------------------

DATA = load_data()

def main():
    global HOST, PORT
    if "--port" in sys.argv:
        try:
            PORT = int(sys.argv[sys.argv.index("--port") + 1])
        except (IndexError, ValueError):
            print("[SmartSkills] Option --port invalide.")
            return
    if "--host" in sys.argv:
        HOST = sys.argv[sys.argv.index("--host") + 1]
    print("=" * 68)
    print(" SMARTSKILLS — SmartFactory (démonstration, données fictives) v" + VERSION)
    print("=" * 68)
    print(f" Serveur : http://{HOST}:{PORT}")
    print(" Comptes de démonstration (mot de passe : demo) :")
    print("   sf-1002  salarié(e)     — Camille D. (Maintenance)")
    print("   sf-1015  manager        — Karim B. (équipe Maintenance)")
    print("   sf-2001  DRH/Formation  — Nadia L.")
    print("   sf-9001  administrateur — Admin Technique")
    print(" Arrêt : Ctrl+C")
    print("=" * 68)
    save_data(DATA)
    httpd = ThreadingHTTPServer((HOST, PORT), Handler)
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[SmartSkills] Arrêt du serveur.")

# (PAGE_HTML est défini plus bas ; le point d'entrée se trouve en fin de fichier)

# -----------------------------------------------------------------------------
# Front-end : SPA intégrée (HTML + CSS + JS, aucune dépendance externe)
# -----------------------------------------------------------------------------

PAGE_HTML = """<!DOCTYPE html>
<html lang="fr"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>SmartSkills — SmartFactory (démonstration)</title>
<style>
:root{
 --bleu:#0b3d66; --bleu2:#125a94; --orange:#f5a623; --fond:#eef2f7;
 --carte:#ffffff; --texte:#22303c; --gris:#5a6b7d; --bord:#dde5ee;
 --ok:#1e8e5a; --warn:#c77414; --err:#c0392b; --info:#2563eb;
}
*{box-sizing:border-box} body{margin:0;font-family:'Segoe UI',Arial,sans-serif;background:var(--fond);color:var(--texte);font-size:14.5px}
a{color:var(--bleu2);text-decoration:none} a:hover{text-decoration:underline}
h2{color:var(--bleu);margin:0 0 4px;font-size:21px} h3{color:var(--bleu);font-size:16px;margin:18px 0 8px}
.small{font-size:12.5px;color:var(--gris)} .mono{font-family:Consolas,monospace;font-size:12.5px}
.bande-demo{background:#fff7e8;border-bottom:1.5px dashed var(--orange);color:#7a5b12;padding:6px 18px;font-size:12.5px;text-align:center}
/* barre du haut */
.topbar{background:var(--bleu);color:#fff;display:flex;align-items:center;gap:14px;padding:0 18px;height:56px;position:sticky;top:0;z-index:50}
.logo{display:flex;align-items:center;gap:10px;font-weight:700;font-size:17px;letter-spacing:.02em}
.logo svg{flex:none}
.topbar .spacer{flex:1}
.chip{background:rgba(255,255,255,.14);border-radius:20px;padding:4px 12px;font-size:12.5px}
.bell{position:relative;cursor:pointer;font-size:19px}
.bell .badge{position:absolute;top:-6px;right:-8px;background:var(--orange);color:#3a2a00;border-radius:50%;font-size:10.5px;padding:1px 5px;font-weight:700}
.btn{display:inline-block;border:none;border-radius:7px;padding:8px 14px;font-size:13.5px;cursor:pointer;background:var(--bleu2);color:#fff;transition:.15s}
.btn:hover{filter:brightness(1.1)} .btn.sec{background:#e7edf4;color:var(--texte)} .btn.ok{background:var(--ok)}
.btn.err{background:var(--err)} .btn.warn{background:var(--warn)} .btn.mini{padding:4px 9px;font-size:12px;border-radius:6px}
.btn[disabled]{opacity:.5;cursor:not-allowed}
/* layout */
.layout{display:flex;min-height:calc(100vh - 84px)}
.nav{width:232px;background:#fff;border-right:1px solid var(--bord);padding:14px 10px;flex:none}
.nav a{display:flex;gap:9px;align-items:center;padding:9px 12px;border-radius:8px;color:var(--texte);font-size:13.8px;margin-bottom:2px}
.nav a:hover{background:#f0f4f9;text-decoration:none}
.nav a.actif{background:var(--bleu);color:#fff}
.nav .grp{font-size:10.5px;text-transform:uppercase;letter-spacing:.1em;color:var(--gris);padding:12px 12px 4px}
.main{flex:1;padding:22px 26px;max-width:1280px}
/* cartes & tableaux */
.carte{background:var(--carte);border:1px solid var(--bord);border-radius:10px;padding:16px 18px;margin-bottom:14px;box-shadow:0 1px 3px rgba(11,61,102,.05)}
.grille{display:grid;gap:12px} .g2{grid-template-columns:repeat(auto-fit,minmax(320px,1fr))}
.g3{grid-template-columns:repeat(auto-fit,minmax(240px,1fr))} .g4{grid-template-columns:repeat(auto-fit,minmax(190px,1fr))}
.kpi{background:#fff;border:1px solid var(--bord);border-radius:10px;padding:13px 15px}
.kpi .v{font-size:21px;font-weight:700;color:var(--bleu)} .kpi .t{font-size:12.5px;color:var(--gris);margin-top:2px}
.kpi .d{font-size:11px;color:#8b98a6;margin-top:5px;line-height:1.4}
table.tbl{width:100%;border-collapse:collapse;background:#fff;border-radius:8px;overflow:hidden}
table.tbl th{background:#f2f6fa;text-align:left;padding:9px 11px;font-size:12px;text-transform:uppercase;letter-spacing:.05em;color:var(--gris);border-bottom:2px solid var(--bord)}
table.tbl td{padding:9px 11px;border-bottom:1px solid #edf1f6;font-size:13.5px;vertical-align:top}
table.tbl tr:hover td{background:#f8fafc}
.badge{display:inline-block;border-radius:12px;padding:2.5px 10px;font-size:11.5px;font-weight:600;white-space:nowrap}
.b-brouillon{background:#eef1f5;color:#4a5866} .b-en_attente{background:#fff3dd;color:#9a6200}
.b-approuvee{background:#e2f4ea;color:#176b43} .b-refusee{background:#fdeaea;color:#a02c1e}
.b-inscrite{background:#e3edfb;color:#1d4f9c} .b-terminee{background:#e8eaf6;color:#3949ab}
.b-annulee{background:#f5e6f5;color:#8e24aa}
.b-critique{background:#fdeaea;color:#a02c1e} .b-rare{background:#fff3dd;color:#9a6200}
.tag{display:inline-block;background:#eef2f7;border-radius:6px;padding:2px 8px;font-size:11.5px;color:var(--gris);margin:1px 2px 1px 0}
/* formulaires */
input,select,textarea{font:inherit;padding:8px 10px;border:1px solid var(--bord);border-radius:7px;background:#fff;width:100%}
label{font-size:12.5px;color:var(--gris);display:block;margin-bottom:3px;font-weight:600}
.fld{margin-bottom:11px} .ligne{display:flex;gap:10px;flex-wrap:wrap;align-items:end}
.ligne>div{flex:1;min-width:140px}
/* modale */
.modale-fond{position:fixed;inset:0;background:rgba(10,30,50,.55);display:none;align-items:flex-start;justify-content:center;z-index:100;padding:30px 16px;overflow:auto}
.modale-fond.ouverte{display:flex}
.modale{background:#fff;border-radius:12px;max-width:860px;width:100%;padding:22px 24px;max-height:88vh;overflow:auto}
.modale .x{float:right;cursor:pointer;font-size:20px;color:var(--gris)}
/* alertes */
.alerte{border-radius:8px;padding:10px 14px;margin-bottom:8px;font-size:13.5px;border-left:4px solid}
.a-haute{background:#fdeaea;border-color:var(--err)} .a-moyenne{background:#fff7e8;border-color:var(--warn)}
/* chat */
.chat-box{height:420px;overflow:auto;background:#f6f9fc;border:1px solid var(--bord);border-radius:10px;padding:14px}
.msg{max-width:78%;padding:9px 13px;border-radius:12px;margin-bottom:9px;font-size:13.5px;line-height:1.5;white-space:pre-wrap}
.msg.user{margin-left:auto;background:var(--bleu);color:#fff;border-bottom-right-radius:3px}
.msg.bot{background:#fff;border:1px solid var(--bord);border-bottom-left-radius:3px}
.msg .conf{display:block;font-size:10.5px;color:var(--gris);margin-top:5px;font-style:italic}
/* barre de progression */
.barre{height:9px;background:#e6ecf3;border-radius:5px;overflow:hidden;margin-top:4px}
.barre i{display:block;height:100%;background:var(--bleu2);border-radius:5px}
.pastille{display:inline-block;width:10px;height:10px;border-radius:50%;margin-right:5px}
/* login */
.login-fond{min-height:calc(100vh - 40px);display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,#0b3d66 0%,#125a94 55%,#1c74b8 100%)}
.login{background:#fff;border-radius:14px;padding:34px 36px;width:460px;box-shadow:0 20px 60px rgba(0,0,0,.3)}
.login h1{margin:0;color:var(--bleu);font-size:24px} .login .sub{color:var(--gris);font-size:13px;margin:6px 0 18px}
.cpt-demo{display:flex;align-items:center;gap:10px;border:1.5px solid var(--bord);border-radius:9px;padding:10px 12px;margin-bottom:8px;cursor:pointer}
.cpt-demo:hover{border-color:var(--bleu2);background:#f4f8fc}
.cpt-demo.sel{border-color:var(--orange);background:#fffaf0}
.doc h3{margin-top:22px;border-left:4px solid var(--orange);padding-left:10px}
footer{padding:14px 26px;color:var(--gris);font-size:12px;border-top:1px solid var(--bord);background:#fff;margin-top:20px}
@media (max-width:900px){.nav{display:none} .main{padding:16px}}
</style></head><body>
<div class="bande-demo">⚠ <strong>Application de démonstration pédagogique</strong> — SmartFactory est une entreprise fictive ; toutes les données, identifiants et montants sont inventés. Aucune donnée personnelle réelle n'est traitée.</div>

<!-- ÉCRAN DE CONNEXION -->
<div id="ecran-login" class="login-fond" style="display:none">
 <div class="login">
  <div class="logo" style="margin-bottom:14px"><svg width="38" height="38" viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90" rx="18" fill="#0b3d66"/><path d="M25 62 L42 40 L55 55 L75 30" stroke="#f5a623" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="75" cy="30" r="6" fill="#4cc9f0"/></svg> SmartSkills</div>
  <h1>Espace Formation &amp; Compétences</h1>
  <div class="sub">SmartFactory — Service Formation et Développement des compétences (démonstration)</div>
  <label>Compte de démonstration</label>
  <div id="liste-comptes"></div>
  <div class="fld" style="margin-top:12px"><label>Mot de passe (démo : <span class="mono">demo</span>)</label>
   <input id="login-pwd" type="password" value="demo"></div>
  <button class="btn" style="width:100%;padding:11px" onclick="faireLogin()">Se connecter</button>
  <div id="login-err" class="small" style="color:var(--err);margin-top:8px"></div>
 </div>
</div>

<!-- COQUILLE DE L'APPLICATION -->
<div id="app" style="display:none">
 <div class="topbar">
  <div class="logo"><svg width="30" height="30" viewBox="0 0 100 100"><rect x="5" y="5" width="90" height="90" rx="18" fill="#ffffff22"/><path d="M25 62 L42 40 L55 55 L75 30" stroke="#f5a623" stroke-width="7" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="75" cy="30" r="6" fill="#4cc9f0"/></svg> SmartSkills <span class="chip">SmartFactory</span></div>
  <div class="spacer"></div>
  <div class="chip" id="top-role"></div>
  <div class="chip" id="top-user"></div>
  <div class="bell" onclick="ouvrirNotifs()" title="Notifications">🔔<span class="badge" id="nb-notifs" style="display:none">0</span></div>
  <button class="btn mini sec" onclick="deconnexion()">Déconnexion</button>
 </div>
 <div class="layout">
  <nav class="nav" id="nav"></nav>
  <div class="main" id="contenu"></div>
 </div>
 <footer>SmartSkills v<span id="f-version"></span> — projet universitaire, données fictives — date de démonstration : <span id="f-date"></span>. Les recommandations sont des aides à la décision : le pouvoir de décision et de contestation revient toujours aux salariés, managers et DRH.</footer>
</div>

<!-- MODALE GÉNÉRIQUE -->
<div class="modale-fond" id="modale-fond"><div class="modale" id="modale"></div></div>

<script>
/* ============================ état & utilitaires ============================ */
let S = null, cptDemoSel = null;
const $id = s => document.getElementById(s);
const esc = s => String(s==null?"":s).replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;").replace(/"/g,"&quot;");
function fmtD(iso){ if(!iso) return "—"; const p=iso.split("-"); return p[2]+"/"+p[1]+"/"+p[0]; }
function fmtE(x){ return x==null?"—":(Math.round(x*10)/10).toLocaleString("fr-FR").replace(/,/g," ")+" €"; }
const STATUTS = {brouillon:"Brouillon", en_attente:"En attente", approuvee:"Approuvée", refusee:"Refusée",
 inscrite:"Inscrit(e)", terminee:"Terminée", annulee:"Annulée"};
async function api(path, opts={}){
 const r = await fetch(path, {method: opts.method||"GET", headers:{"Content-Type":"application/json"},
  body: opts.body?JSON.stringify(opts.body):undefined});
 let j; try{ j = await r.json(); }catch(e){ j = {erreur:"Réponse inattendue du serveur."}; }
 if(!r.ok && !j.erreur) j.erreur = "Erreur HTTP "+r.status;
 return j;
}
async function post(path, body){ const j = await api(path, {method:"POST", body: body||{}});
 if(j.erreur){ alert(j.erreur); } return j; }
const findF = id => S.formations.find(f=>f.id===id);
const findC = id => S.competences.find(c=>c.id===id);
const findS = id => S.salaries.find(s=>s.id===id);
const findM = id => S.metiers.find(m=>m.id===id);
const findSvc = id => (S.services.find(x=>x.id===id)||{nom:"—"}).nom;
const findPre = id => (S.prestataires.find(x=>x.id===id)||{nom:"—"}).nom;
const findSE = id => S.sessions.find(s=>s.id===id);
function sessionsDe(fid){ return S.sessions.filter(s=>s.formation_id===fid).sort((a,b)=>a.date_debut<b.date_debut?-1:1); }
function mesRealisations(){ return S.realisations.filter(r=>r.salarie_id===S.user.id); }
function equipesManager(){ return S.salaries.filter(s=>s.manager_id===S.user.id); }

/* ============================ navigation ============================ */
function navItems(role){
 const N=[];
 if(role==="salarie"){
  N.push({g:"Mon espace"}, {h:"#/accueil",t:"🏠 Accueil"},{h:"#/catalogue",t:"📚 Catalogue de formation"},
   {h:"#/demandes",t:"📋 Mes demandes"},{h:"#/suivi",t:"📈 Suivi de mes formations"},
   {h:"#/autoevaluation",t:"✅ Autoévaluation des compétences"},{h:"#/recommandations",t:"✨ Recommandations personnalisées"},
   {h:"#/evaluations",t:"⭐ Évaluer mes formations"},{h:"#/attestations",t:"🎓 Mes attestations"});
  N.push({g:"Aide & infos"},{h:"#/assistant",t:"💬 SmartSkills Assistant"},{h:"#/documentation",t:"📖 Documentation"});
 } else if(role==="manager"){
  N.push({g:"Ma équipe"}, {h:"#/accueil",t:"🏠 Accueil"},{h:"#/demandes",t:"📋 Demandes de l'équipe"},
   {h:"#/equipe",t:"👥 Besoins & compétences de l'équipe"},{h:"#/suivi",t:"📈 Formations de l'équipe"});
  N.push({g:"Ressources"},{h:"#/catalogue",t:"📚 Catalogue"},{h:"#/parcours",t:"🧭 Parcours par métier"},
   {h:"#/alertes",t:"🔔 Alertes"},{h:"#/assistant",t:"💬 Assistant"},{h:"#/documentation",t:"📖 Documentation"});
 } else if(role==="drh"){
  N.push({g:"Pilotage"}, {h:"#/accueil",t:"🏠 Accueil"},{h:"#/tableau-de-bord",t:"📊 Tableau de bord PDC"},
   {h:"#/cartographie",t:"🗺 Cartographie des compétences"},{h:"#/simulation",t:"🔮 Anticipation des besoins"},
   {h:"#/equite",t:"⚖ Équité d'accès à la formation"},{h:"#/alertes",t:"🔔 Alertes & règles"});
  N.push({g:"Gestion"}, {h:"#/demandes",t:"📋 Toutes les demandes"},{h:"#/catalogue-admin",t:"➕ Catalogue (ajouts)"},
   {h:"#/evaluations",t:"⭐ Évaluations agrégées"},{h:"#/attestations",t:"🎓 Attestations"});
  N.push({g:"Ressources"},{h:"#/catalogue",t:"📚 Catalogue"},{h:"#/parcours",t:"🧭 Parcours par métier"},
   {h:"#/assistant",t:"💬 Assistant"},{h:"#/documentation",t:"📖 Documentation"});
 } else {
  N.push({g:"Administration"}, {h:"#/accueil",t:"🏠 Accueil"},{h:"#/tableau-de-bord",t:"📊 Tableau de bord"},
   {h:"#/alertes",t:"🔔 Alertes & règles"},{h:"#/catalogue-admin",t:"➕ Catalogue (ajouts)"},
   {h:"#/documentation",t:"📖 Documentation"});
 }
 return N;
}
function afficherNav(){
 const r = S.user.role, items = navItems(r);
 let h=""; for(const it of items){ if(it.g) h+=`<div class=grp>${it.g}</div>`;
  else h+=`<a href=${it.h} data-h=${it.h}>${it.t}</a>`; }
 $id("nav").innerHTML = h;
}

/* ============================ login / logout ============================ */
async function init(){
 const st = await api("/api/state");
 if(st.connecte){ S = st; afficherApp(); } else { afficherLogin(st.comptes_demo); }
}
function afficherLogin(comptes){
 $id("ecran-login").style.display="flex";
 $id("liste-comptes").innerHTML = comptes.map(c=>
  `<div class="cpt-demo" data-id="${c.id}" onclick="selCpt('${c.id}',this)"><span>👤</span><div><strong>${esc(c.id)}</strong><br><span class=small>${esc(c.nom)}</span></div></div>`).join("");
}
function selCpt(id, el){ cptDemoSel=id; document.querySelectorAll(".cpt-demo").forEach(x=>x.classList.remove("sel")); el.classList.add("sel"); }
async function faireLogin(){
 const id = cptDemoSel || (document.querySelector(".cpt-demo")||{}).dataset?.id;
 if(!id){ $id("login-err").textContent="Choisissez un compte de démonstration."; return; }
 const j = await api("/api/login", {method:"POST", body:{id, password:$id("login-pwd").value}});
 if(j.erreur){ $id("login-err").textContent=j.erreur; return; }
 S = await api("/api/state"); afficherApp(); location.hash = "#/accueil";
}
async function deconnexion(){ await api("/api/logout", {method:"POST"}); location.reload(); }
function afficherApp(){
 $id("ecran-login").style.display="none"; $id("app").style.display="block";
 const r=S.user.role, lib={salarie:"Salarié(e)",manager:"Manager",drh:"DRH / Formation",admin:"Administrateur"};
 $id("top-role").textContent = lib[r]||r; $id("top-user").textContent = S.user.nom;
 $id("f-version").textContent = S.version; $id("f-date").textContent = fmtD(S.date_demo);
 afficherNav(); majNotifs(); render(); window.addEventListener("hashchange", render);
}

/* ============================ notifications ============================ */
function mesNotifs(){ return S.notifications.filter(n=>n.destinataire===S.user.id || (S.user.role==="drh"&&false)); }
function majNotifs(){ const nb = mesNotifs().filter(n=>!n.lue).length; const b=$id("nb-notifs");
 b.style.display = nb?"inline-block":"none"; b.textContent=nb; }
async function ouvrirNotifs(){
 const ns = mesNotifs().slice().reverse();
 let h = `<div class=x onclick="fermerModale()">✕</div><h2>Notifications</h2>`;
 if(!ns.length) h += `<p class=small>Aucune notification.</p>`;
 for(const n of ns){ h += `<div class=carte style="margin-bottom:8px;padding:10px 14px"><div>${esc(n.message)} <span class=small>— ${fmtD(n.date)}</span></div>
  ${n.lue?"":`<button class="btn mini sec" onclick="(async()=>{await post('/api/notification/lire',{id:'${n.id}'});S=await api('/api/state');majNotifs();ouvrirNotifs();})()">Marquer comme lue</button>`}</div>`; }
 ouvrirModale(h);
}
function ouvrirModale(html){ $id("modale").innerHTML = html; $id("modale-fond").classList.add("ouverte"); }
function fermerModale(){ $id("modale-fond").classList.remove("ouverte"); }
$id && document.addEventListener("click", e=>{ if(e.target.id==="modale-fond") fermerModale(); });

/* ============================ routage ============================ */
function render(){
 const h = location.hash || "#/accueil";
 document.querySelectorAll(".nav a").forEach(a=>a.classList.toggle("actif", a.dataset.h===h));
 const C = $id("contenu");
 try{
  if(h==="#/accueil") vAccueil(C);
  else if(h==="#/catalogue") vCatalogue(C);
  else if(h==="#/demandes") vDemandes(C);
  else if(h==="#/suivi") vSuivi(C);
  else if(h==="#/autoevaluation") vAutoEval(C);
  else if(h==="#/recommandations") vReco(C);
  else if(h==="#/evaluations") vEvals(C);
  else if(h==="#/attestations") vAttests(C);
  else if(h==="#/tableau-de-bord") vDash(C);
  else if(h==="#/cartographie") vCarto(C);
  else if(h==="#/simulation") vSimu(C);
  else if(h==="#/equite") vEquite(C);
  else if(h==="#/alertes") vAlertes(C);
  else if(h==="#/catalogue-admin") vAdminCat(C);
  else if(h==="#/parcours") vParcours(C);
  else if(h==="#/equipe") vEquipe(C);
  else if(h==="#/assistant") vAssistant(C);
  else if(h==="#/documentation") vDocs(C);
  else C.innerHTML = `<div class=carte><h2>Page introuvable</h2><a href="#/accueil">Retour à l'accueil</a></div>`;
 }catch(e){ C.innerHTML = `<div class=carte><h2>Erreur d'affichage</h2><pre class=mono>${esc(e.message)}</pre></div>`; }
}

/* ============================ accueil ============================ */
function vAccueil(C){
 const r=S.user.role, sal=findS(S.user.id);
 let h = `<h2>Bonjour ${esc(S.user.nom)} 👋</h2><p class=small>Vous êtes connecté(e) en tant que <strong>${r}</strong>. Date de démonstration : ${fmtD(S.date_demo)}.</p>`;
 if(r==="salarie"){
  const mes = S.demandes.filter(d=>d.salarie_id===S.user.id);
  const enAtt = mes.filter(d=>d.statut==="en_attente").length;
  const rals = mesRealisations();
  h += `<div class="grille g4">
   <div class=kpi><div class=v>${mes.length}</div><div class=t>Demandes de formation</div><div class=d>Ensemble de vos demandes (tous statuts).</div></div>
   <div class=kpi><div class=v>${enAtt}</div><div class=t>En attente de validation</div><div class=d>Demandes en cours d'examen par votre manager.</div></div>
   <div class=kpi><div class=v>${rals.filter(x=>x.validee).length}</div><div class=t>Formations terminées & validées</div><div class=d>Réalisations validées (heures réellement effectuées).</div></div>
   <div class=kpi><div class=v>${rals.reduce((a,x)=>a+(x.heures_reelles||0),0)} h</div><div class=t>Heures réalisées</div><div class=d>Heures effectivement suivies, distinctes des heures prévues.</div></div></div>`;
  const eco = ecartsLocaux(sal);
  if(eco.length){ h += `<div class=carte><h3>Vos principaux écarts de compétences (déclarés vs cible du poste)</h3>
   <p class=small>Basé sur votre autoévaluation et les validations d'évaluateur. Support de dialogue avec votre manager — pas une mesure objective.</p>`;
   for(const e of eco.slice(0,4)){ h += `<div style="margin-bottom:8px"><strong>${esc(e.nom)}</strong> <span class=small>— niveau actuel ${e.actuel} / cible ${e.cible}</span>
    <div class=barre><i style="width:${Math.round(100*e.actuel/5)}%"></i></div></div>`; }
   h += `<p style="margin-top:10px"><a href="#/autoevaluation">Voir l'autoévaluation complète →</a> · <a href="#/recommandations">Recommandations →</a></p></div>`; }
 } else if(r==="manager"){
  const eq = equipesManager();
  const att = S.demandes.filter(d=>d.statut==="en_attente").length;
  h += `<div class="grille g3">
   <div class=kpi><div class=v>${eq.length}</div><div class=t>Salariés dans mon équipe</div></div>
   <div class=kpi><div class=v>${att}</div><div class=t>Demandes en attente de ma décision</div><div class=d>Chaque décision (approbation ou refus) doit être motivée.</div></div>
   <div class=kpi><div class=v>${S.realisations.filter(x=>eq.some(s=>s.id===x.salarie_id)&&x.validee).length}</div><div class=t>Formations validées de l'équipe</div></div></div>`;
  h += `<div class=carte><p><a href="#/demandes">Traiter les demandes →</a> · <a href="#/equipe">Besoins de compétences de l'équipe →</a></p></div>`;
 } else {
  const bs = S.budget_state;
  h += `<div class="grille g4">
   <div class=kpi><div class=v>${fmtE(bs.total)}</div><div class=t>Budget annuel total (2026)</div><div class=d>Somme des enveloppes allouées par service.</div></div>
   <div class=kpi><div class=v>${fmtE(bs.consomme)}</div><div class=t>Budget consommé</div><div class=d>Formations terminées et validées uniquement.</div></div>
   <div class=kpi><div class=v>${fmtE(bs.restant)}</div><div class=t>Budget restant</div><div class=d>Total − engagé − consommé.</div></div>
   <div class=kpi><div class=v>${S.salaries.length}</div><div class=t>Salariés (effectif de démo)</div><div class=d>Échantillon fictif — l'entreprise réelle compte 5 000 salariés.</div></div></div>`;
  h += `<div class=carte><p><a href="#/tableau-de-bord">Tableau de bord PDC →</a> · <a href="#/cartographie">Cartographie des compétences →</a> · <a href="#/simulation">Simulation d'anticipation →</a></p></div>`;
 }
 C.innerHTML = h;
}
/* écart local (miroir du moteur côté serveur, pour l'affichage) */
function niveauxEff(sal){ const out={}; for(const k in (sal.autoevaluation||{})) out[k]={d:sal.autoevaluation[k],v:null};
 for(const cv of S.competences_validees){ if(cv.salarie_id===sal.id){ const o=out[cv.competence_id]||(out[cv.competence_id]={d:null,v:null}); o.v=cv.niveau; } }
 return out; }
function ecartsLocaux(sal){ const m=findM(sal.metier_id); if(!m) return [];
 const eff=niveauxEff(sal), out=[];
 for(const [cid,cible] of Object.entries(m.competences_cibles)){ const e=eff[cid];
  const retenu=Math.max(e?e.d||0:0, e?e.v||0:0); if(cible-retenu>0) out.push({competence_id:cid,nom:findC(cid).nom,actuel:retenu,cible,ecart:cible-retenu}); }
 return out.sort((a,b)=>b.ecart-a.ecart); }

/* ============================ catalogue ============================ */
function vCatalogue(C){
 const themes=[...new Set(S.formations.map(f=>f.theme))].sort();
 const fmts=["Présentiel","E-learning","Blended"];
 C.innerHTML = `<h2>Catalogue de formation</h2><p class=small>Recherche textuelle et filtres combinables. ${S.formations.length} formations (données fictives).</p>
 <div class=carte><div class=ligne>
  <div style="flex:2"><label>Recherche</label><input id="f-rech" placeholder="titre, compétence, thème…" oninput="filtreCat()"></div>
  <div><label>Thème</label><select id="f-theme" onchange="filtreCat()"><option value="">Tous</option>${themes.map(t=>`<option>${t}</option>`).join("")}</select></div>
  <div><label>Format</label><select id="f-fmt" onchange="filtreCat()"><option value="">Tous</option>${fmts.map(t=>`<option>${t}</option>`).join("")}</select></div>
  <div><label>Durée max (h)</label><input id="f-dur" type="number" min="0" oninput="filtreCat()"></div>
  <div><label>Coût max (€)</label><input id="f-cout" type="number" min="0" oninput="filtreCat()"></div>
  <div><label>Prestataire</label><select id="f-pre" onchange="filtreCat()"><option value="">Tous</option>${S.prestataires.map(p=>`<option value="${p.id}">${esc(p.nom)}</option>`).join("")}</select></div>
  <div><label>Niveau</label><select id="f-niv" onchange="filtreCat()"><option value="">Tous</option><option value="1">1 — Initiation</option><option value="2">2 — Intermédiaire</option><option value="3">3 — Avancé</option></select></div>
  <div><label>Compétence visée</label><select id="f-cpt" onchange="filtreCat()"><option value="">Toutes</option>${S.competences.map(c=>`<option value="${c.id}">${esc(c.nom)}</option>`).join("")}</select></div>
  <div style="flex:0"><label>Session disponible</label><select id="f-ses" onchange="filtreCat()"><option value="">Indifférent</option><option value="1">Avec place</option><option value="0">Complète acceptée</option></select></div>
 </div></div><div id="cat-results"></div>`;
 filtreCat();
}
function listeFiltree(){
 const rech=($id("f-rech")?.value||"").toLowerCase(), th=$id("f-theme")?.value, fm=$id("f-fmt")?.value,
 dur=+$id("f-dur")?.value||0, cout=+$id("f-cout")?.value||0, pre=$id("f-pre")?.value,
 niv=$id("f-niv")?.value, cpt=$id("f-cpt")?.value, ses=$id("f-ses")?.value;
 return S.formations.filter(f=>{
  const texte=(f.titre+" "+f.description+" "+f.theme+" "+f.competences.map(c=>findC(c).nom).join(" ")).toLowerCase();
  if(rech && !texte.includes(rech)) return false;
  if(th && f.theme!==th) return false; if(fm && f.format!==fm) return false;
  if(dur && f.duree_h>dur) return false; if(cout && f.cout>cout) return false;
  if(pre && f.prestataire_id!==pre) return false; if(niv && String(f.niveau)!==niv) return false;
  if(cpt && !f.competences.includes(cpt)) return false;
  const ss=sessionsDe(f.id);
  if(ses==="1" && !ss.some(s=>s.places_insnees<s.capacite)) return false;
  if(ses==="0" && ss.some(s=>s.places_insnees<s.capacite) && !ss.every(s=>s.places_insnees>=s.capacite)) return false;
  return true; });
}
function carteFormation(f){
 const ss=sessionsDe(f.id), dispo=ss.filter(s=>s.places_insnees<s.capacite);
 return `<div class=carte style="margin-bottom:10px">
  <div style="display:flex;justify-content:space-between;gap:12px"><div>
   <h3 style="margin:0">${esc(f.titre)}</h3>
   <div class=small>${esc(f.theme)} · ${f.format} · ${f.duree_h} h · niveau ${f.niveau}/3 · ${fmtE(f.cout)} · ${esc(findPre(f.prestataire_id))}</div>
   <div style="margin-top:7px">${f.competences.map(c=>`<span class=tag>${esc(findC(c).nom)}</span>`).join("")}</div>
  </div><div style="flex:none;text-align:right">
   ${dispo.length?`<span class="badge b-inscrite">${dispo.length} session(s) avec place</span>`:`<span class="badge b-refusee">Aucune place disponible</span>`}
   <br><button class="btn mini" style="margin-top:8px" onclick="ficheFormation('${f.id}')">Voir la fiche →</button>
  </div></div></div>`;
}
function filtreCat(){ const r=$id("cat-results"); if(!r) return; const L=listeFiltree();
 r.innerHTML = `<p class=small>${L.length} formation(s) trouvée(s).</p>` + (L.length? L.map(carteFormation).join("") : `<div class=carte><p>Aucune formation ne correspond à ces critères. Élargissez les filtres.</p></div>`); }
function ficheFormation(fid){
 const f=findF(fid), ss=sessionsDe(f.id);
 let h=`<div class=x onclick="fermerModale()">✕</div><h2>${esc(f.titre)}</h2>
 <div style="margin:6px 0"><span class=tag>${f.theme}</span><span class=tag>${f.format}</span><span class=tag>${f.duree_h} h</span><span class=tag>Niveau ${f.niveau}/3</span><span class=tag>${fmtE(f.cout)}</span></div>
 <p>${esc(f.description)}</p>
 <h3>Objectifs pédagogiques</h3><ul>${f.objectifs.map(o=>`<li>${esc(o)}</li>`).join("")}</ul>
 <h3>Compétences visées</h3><div>${f.competences.map(c=>{const c2=findC(c);return `<span class=tag title="${esc(c2.description)}">${esc(c2.nom)}${c2.critique?' ⚑':''}</span>`;}).join("")}</div>
 ${f.prerequis.length?`<h3>Prérequis</h3><ul>${f.prerequis.map(p=>`<li>${esc(p.libelle)}</li>`).join("")}</ul>`:""}
 <h3>Modalités d'évaluation</h3><p>${esc(f.evaluation)}</p>
 <p class=small><strong>Prestataire :</strong> ${esc(findPre(f.prestataire_id))} — <strong>Public cible :</strong> ${esc(f.public_cible)}</p>
 <h3>Sessions disponibles</h3>`;
 if(!ss.length) h += `<p class=small>Aucune session planifiée pour le moment.</p>`;
 for(const s of ss){ const rest=s.capacite-s.places_insnees;
  h+=`<div class=carte style="padding:10px 14px;margin-bottom:8px"><strong>${fmtD(s.date_debut)} → ${fmtD(s.date_fin)}</strong> — ${esc(s.lieu)}<br>
   <span class=small>Capacité : ${s.capacite} · Inscriptions : ${s.places_insnees} · <b style="color:${rest<=2?'var(--err)':'var(--ok)'}">${rest} place(s) restante(s)</b></span><div class=barre><i style="width:${Math.round(100*s.places_insnees/s.capacite)}%;background:${rest<=2?'var(--err)':'var(--bleu2)'}"></i></div></div>`; }
 const sal=findS(S.user.id);
 const deja = S.demandes.some(d=>d.salarie_id===sal.id && d.formation_id===fid && ["brouillon","en_attente","approuvee","inscrite"].includes(d.statut));
 if(!deja && ss.length && (S.user.role==="salarie")){
  h+=`<div class=carte style="background:#f4f8fc"><h3 style="margin-top:0">Demander l'inscription</h3>
   <label>Session souhaitée</label><select id="m-ses">${ss.map(s=>`<option value="${s.id}" ${s.places_insnees>=s.capacite?"disabled":""}>${fmtD(s.date_debut)} — ${esc(s.lieu)} (${s.capacite-s.places_insnees} places)</option>`).join("")}</select>
   <div style="margin-top:12px;display:flex;gap:8px">
    <button class="btn" onclick="creerDemande('${fid}','en_attente')">Envoyer la demande à mon manager</button>
    <button class="btn sec" onclick="creerDemande('${fid}','brouillon')">Enregistrer en brouillon</button></div>
   <p class=small style="margin-top:8px">Votre manager recevra une notification et devra motiver sa décision. Vous serez informé(e) à chaque changement de statut.</p></div>`; }
 else if(deja) h+=`<p class=small>Vous avez déjà une demande active pour cette formation.</p>`;
 ouvrirModale(h);
}
async function creerDemande(fid, statut){
 const j = await post("/api/demande/create", {formation_id:fid, session_id:$id("m-ses")?.value||null, statut});
 if(j.ok){ fermerModale(); alert(statut==="brouillon"?`Brouillon ${j.demande_id} enregistré. Vous pourrez le soumettre depuis « Mes demandes ».`:`Demande ${j.demande_id} envoyée à votre manager.`); location.hash="#/demandes"; S=await api("/api/state"); render(); }
}

/* ============================ demandes ============================ */
function vDemandes(C){
 const r=S.user.role;
 let L = r==="salarie" ? S.demandes.filter(d=>d.salarie_id===S.user.id)
       : r==="manager" ? S.demandes
       : S.demandes;
 if(r==="manager") L = L.slice();
 const ordre={en_attente:0, approuvee:1, inscrite:2, brouillon:3, terminee:4, refusee:5, annulee:6};
 L.sort((a,b)=>ordre[a.statut]-ordre[b.statut]);
 C.innerHTML=`<h2>${r==="salarie"?"Mes demandes de formation":r==="manager"?"Demandes de mon équipe":"Toutes les demandes"}</h2>
 <p class=small>Statuts : brouillon → en attente → approuvée / refusée → inscrite → terminée (ou annulée). Chaque décision est motivée et tracée dans l'historique.</p><div id="liste-dem"></div>`;
 let h="";
 if(!L.length) h=`<div class=carte><p>Aucune demande. Parcourez le <a href="#/catalogue">catalogue</a> pour en créer une.</p></div>`;
 for(const d of L){
  const f=findF(d.formation_id), sal=findS(d.salarie_id), ses=d.session_id?findSE(d.session_id):null;
  h+=`<div class=carte style="margin-bottom:10px"><div style="display:flex;justify-content:space-between;gap:10px;flex-wrap:wrap">
   <div><strong>${esc(f.titre)}</strong> ${r!=="salarie"?`<span class=small>— ${esc(sal.nom)} (${esc(sal.id)})</span>`:""}<br>
   <span class=small>${d.id} · créée le ${fmtD(d.date_creation)} · ${f.format}, ${f.duree_h} h, ${fmtE(f.cout)}${ses?` · session du ${fmtD(ses.date_debut)}`:""}</span><br>
   <span class=small>Compétences développées : ${f.competences.map(c=>esc(findC(c).nom)).join(", ")}</span></div>
   <div style="text-align:right;flex:none"><span class="badge b-${d.statut}">${STATUTS[d.statut]}</span><br>
    <button class="btn mini sec" style="margin-top:6px" onclick="histDemande('${d.id}')">Historique (${d.historique.length})</button></div></div>
   ${actionsDemande(d)}
  </div>`; }
 $id("liste-dem").innerHTML=h;
}
function actionsDemande(d){
 const r=S.user.role, sal=findS(d.salarie_id);
 let h="", zone=`<div style="margin-top:10px;padding-top:10px;border-top:1px dashed var(--bord)">`;
 if(r==="salarie" && d.salarie_id===S.user.id){
  if(d.statut==="brouillon") h+=`<button class="btn mini" onclick="transit('${d.id}','en_attente')">Soumettre à mon manager</button> `;
  if(["brouillon","en_attente","approuvee","inscrite"].includes(d.statut)) h+=`<button class="btn mini sec" onclick="if(confirm('Annuler cette demande ?'))transit('${d.id}','annulee')">Annuler</button>`; }
 if(r==="manager" && sal.manager_id===S.user.id){
  if(d.statut==="en_attente"){ h+=`<div class=ligne style="margin-top:8px"><div style="flex:2"><label>Motif de la décision (obligatoire)</label><input id="motif-${d.id}" placeholder="ex. : cohérent avec le plan de développement / budget T4…"></div>
   <button class="btn mini ok" onclick="transit('${d.id}','approuvee','motif-${d.id}')">✓ Approuver</button>
   <button class="btn mini err" onclick="transit('${d.id}','refusee','motif-${d.id}')">✗ Refuser</button></div>`; }
  const bs=S.budget_state;
  h+=`<p class=small style="margin-top:8px">Budget prévisionnel du périmètre : restant <b>${fmtE(bs.restant)}</b> (engagé ${fmtE(bs.engage)} + consommé ${fmtE(bs.consomme)} sur ${fmtE(bs.total)}).</p>`; }
 if((r==="drh"||r==="admin") && d.statut==="approuvee"){
  const ss=sessionsDe(d.formation_id).filter(s=>s.places_insnees<s.capacite);
  h+=`<div class=ligne style="margin-top:8px"><div><label>Session</label><select id="ses-${d.id}">${ss.map(s=>`<option value="${s.id}" ${d.session_id===s.id?"selected":""}>${fmtD(s.date_debut)} — ${esc(s.lieu)}</option>`).join("")||`<option value="">— aucune session avec place —</option>`}</select></div>
   <button class="btn mini" onclick="transit('${d.id}','inscrite','ses-${d.id}",true)">Inscrire en session</button> `; }
 if((r==="drh"||r==="admin") && d.statut==="inscrite"){ h+=`<div class=ligne style="margin-top:8px"><div><label>Heures réellement effectuées (prévues : ${findF(d.formation_id).duree_h} h)</label><input id="h-${d.id}" type="number" value="${findF(d.formation_id).duree_h}"></div>
   <button class="btn mini ok" onclick="transit('${d.id}','terminee','h-${d.id}')">Clôturer la formation</button></div>`; }
 h+=`</div>`;
 return zone+h+`</div>`;
}
async function transit(did, statut, inputId, avecSession){
 let body={statut};
 if(inputId){ const v=$id(inputId)?.value;
  if(statut==="inscrite") body.session_id=v; else if(statut==="terminee") body.heures_reelles=+v; else body.motif=v; }
 const j=await post(`/api/demande/${did}/transition`, body);
 if(j.ok){ S=await api("/api/state"); majNotifs(); render();
  if(j.attestation_id) alert("Formation clôturée et validée. Attestation "+j.attestation_id+" générée — téléchargeable dans « Mes attestations »."); }
}
function histDemande(did){
 const d=S.demandes.find(x=>x.id===did), f=findF(d.formation_id);
 const lib={demande_creee:"Création de la demande", approuvee:"Approbation par le manager/DRH",
  refusee:"Refus (motif obligatoire)", inscrite:"Inscription en session", terminee:"Clôture de la formation",
  annulee:"Annulation", en_attente:"Soumise à validation"};
 let h=`<div class=x onclick="fermerModale()">✕</div><h2>Historique — ${d.id}</h2><p class=small>${esc(f.titre)}</p>`;
 for(const e of d.historique){ h+=`<div class=carte style="padding:9px 13px;margin-bottom:7px"><b>${lib[e.action]||e.action}</b> <span class=small>— ${fmtD(e.date)} par ${esc(e.par)}</span>
  ${e.motif?`<div style="margin-top:4px">Motif : « ${esc(e.motif)} »</div>`:""}
  ${e.detail?`<div class=small>${esc(e.detail)}</div>`:""}</div>`; }
 ouvrirModale(h);
}

/* ============================ suivi individuel ============================ */
function vSuivi(C){
 const r=S.user.role;
 if(r==="salarie"){
  const mes=S.demandes.filter(d=>d.salarie_id===S.user.id), rals=mesRealisations().slice().sort((a,b)=>b.date_fin<a.date_fin?1:-1);
  const hR=rals.reduce((a,x)=>a+(x.heures_reelles||0),0), hP=rals.reduce((a,x)=>a+(x.heures_prevues||0),0);
  let h=`<h2>Suivi de mes formations</h2><div class="grille g4">
   <div class=kpi><div class=v>${mes.filter(d=>["en_attente","approuvee"].includes(d.statut)).length}</div><div class=t>Demandées / validées en cours</div></div>
   <div class=kpi><div class=v>${rals.length}</div><div class=t>Formations terminées</div></div>
   <div class=kpi><div class=v>${hR} h</div><div class=t>Heures réalisées</div><div class=d>Effectivement suivies (après validation), distinctes des heures prévues (${hP} h).</div></div>
   <div class=kpi><div class=v>${S.attestations.length}</div><div class=t>Attestations obtenues</div></div></div>`;
  h+=`<div class=carte><h3>Chronologie de progression</h3>`;
  if(!rals.length) h+=`<p class=small>Aucune formation terminée pour le moment.</p>`;
  for(const rl of rals){ const f=findF(rl.formation_id);
   h+=`<div style="display:flex;gap:12px;margin-bottom:10px"><div style="flex:none;width:110px;text-align:right" class=small>${fmtD(rl.date_fin)}</div>
    <div><span class="pastille" style="background:${rl.validee?'var(--ok)':'var(--err)'}"></strong></span><b>${esc(f.titre)}</b> <span class=small>— ${rl.heures_reelles} h réalisées / ${rl.heures_prevues} h prévues</span>
    ${rl.validee?`<span class="badge b-approuvee">Validée</span>`:`<span class="badge b-refusee">Non validée (assiduité &lt; 80 %)</span>`}
    ${rl.attestation_id?` · <a href="#/attestations">attestation ${rl.attestation_id}</a>`:""}
    <div>${f.competences.map(c=>`<span class=tag>${esc(findC(c).nom)}</span>`).join("")}</div></div></div>`; }
  h+=`</div><div class=carte><h3>Récapitulatif annuel ${S.date_demo.slice(0,4)}</h3>
   <p class=small>Formations terminées dans l'année : <b>${rals.filter(x=>x.date_fin.startsWith(S.date_demo.slice(0,4))).length}</b> — heures réalisées : <b>${rals.filter(x=>x.date_fin.startsWith(S.date_demo.slice(0,4))).reduce((a,x)=>a+(x.heures_reelles||0),0)} h</b>.</p></div>`;
  C.innerHTML=h; return; }
 // manager / drh : suivi équipe
 const salIds = r==="manager" ? equipesManager().map(s=>s.id) : S.salaries.map(s=>s.id);
 let h=`<h2>Formations de ${r==="manager"?"mon équipe":"l'ensemble des salariés"}</h2>`;
 h+=`<table class=tbl><tr><th>Salarié</th><th>Métier</th><th>Term. validées</th><th>Heures réalisées</th><th>Dernière formation</th></tr>`;
 for(const id of salIds){ const s=findS(id), rl=S.realisations.filter(x=>x.salarie_id===id&&x.validee).sort((a,b)=>b.date_fin<a.date_fin?1:-1);
  const dern=rl[0]?findF(rl[0].formation_id).titre:"—";
  h+=`<tr><td>${esc(s.nom)}</td><td class=small>${findM(s.metier_id)?.nom||"—"}</td><td>${rl.length}</td><td>${rl.reduce((a,x)=>a+(x.heures_reelles||0),0)} h</td><td class=small>${esc(dern)}</td></tr>`; }
 C.innerHTML=h+`</table>`;
}

/* ============================ autoévaluation ============================ */
function vAutoEval(C){
 const sal=findS(S.user.id), m=findM(sal.metier_id);
 if(!m){ C.innerHTML=`<div class=carte><p>Votre profil n'est pas associé à un référentiel de compétences.</p></div>`; return; }
 let h=`<h2>Autoévaluation des compétences</h2>
 <div class=carte style="background:#fff7e8;border-color:var(--orange)"><b>Rappel important :</b> cette autoévaluation est une <u>déclaration</u>, pas une mesure objective ou définitive de votre performance. Elle sert de support au dialogue avec votre manager, qui peut ensuite <b>valider</b> certaines compétences (une validation par évaluateur est distincte d'une simple déclaration).</div>
 <p class=small>Échelle : ${Object.entries(S.levels).map(([k,v])=>`<b>${k}</b> = ${v.split(" — ")[0]}`).join(" · ")}.</p><div id="ae-list"></div>`;
 C.innerHTML=h;
 const eff=niveauxEff(sal);
 let rows="";
 for(const [cid,cible] of Object.entries(m.competences_cibles)){
  const c=findC(cid), e=eff[cid], decl=e&&e.d?e.d:0, val=e&&e.v?e.v:null;
  const retenu=Math.max(decl||0,val||0), ecart=cible-retenu;
  const fSugg=S.formations.filter(f=>f.competences.includes(cid)&&!mesRealisations().some(r=>r.formation_id===f.id)).slice(0,3);
  rows+=`<tr><td><b>${esc(c.nom)}</b> ${c.critique?"<span class='badge b-critique'>critique</span>":""}<br><span class=small>${esc(c.description)}</span></td>
   <td style="text-align:center">${decl||"—"}</td>
   <td style="text-align:center">${val?`<b>${val}</b> ✓`:"—"}</td>
   <td style="text-align:center"><b>${retenu||0}</b></td>
   <td style="text-align:center"><b>${cible}</b></td>
   <td style="text-align:center">${ecart>0?`<span class="badge b-refusee">−${ecart}</span>`:`<span class="badge b-approuvee">OK</span>`}</td>
   <td class=small>${fSugg.map(f=>esc(f.titre)).join(" · ")||"—"}</td></tr>`; }
 $id("ae-list").innerHTML=`<table class=tbl><tr><th>Compétence du référentiel</th><th>Déclarée</th><th>Validée (évaluateur)</th><th>Niveau retenu</th><th>Cible poste</th><th>Écart</th><th>Formations susceptibles de réduire l'écart</th></tr>${rows}</table>
 <div class=carte style="margin-top:14px"><h3>Mettre à jour mes niveaux déclarés</h3>
  ${Object.entries(m.competences_cibles).map(([cid,cible])=>{const c=findC(cid);const cur=(eff[cid]&&eff[cid].d)||0;
   return `<div class=fld><label>${esc(c.nom)} (cible : ${cible})</label><select id="ae-${cid}">${[1,2,3,4,5].map(n=>`<option value="${n}" ${cur===n?"selected":""}>${n} — ${S.levels[n].split(" — ")[0]}</option>`).join("")}</select></div>`;}).join("")}
  <button class=btn onclick="sauverAE()">Enregistrer mon autoévaluation</button> <span id="ae-msg" class=small></span></div>`;
}
async function sauverAE(){
 const m=findM(findS(S.user.id).metier_id), niveaux={};
 for(const cid of Object.keys(m.competences_cibles)) niveaux[cid]=+$id("ae-"+cid).value;
 const j=await post("/api/autoevaluation", {niveaux});
 if(j.ok){ $id("ae-msg").textContent="✓ Enregistré. "+j.rappel; S=await api("/api/state"); }
}

/* ============================ recommandations ============================ */
let RECO=null;
function vReco(C){
 C.innerHTML=`<h2>Recommandations personnalisées</h2>
 <div class=carte><p class=small style="margin-top:0">Le moteur croise : vos écarts de compétences vs référentiel du poste, les compétences critiques, votre objectif d'évolution déclaré, les formations obligatoires non validées, la disponibilité des sessions, le temps disponible et le budget restant. <b>Chaque suggestion est expliquée</b> ; c'est une aide à la décision — le choix final vous appartient (et à votre manager / DRH).</p>
 <div class=ligne><div><label>Temps disponible (h)</label><input id="r-dur" type="number" value="40"></div>
 <div><label>Budget max (€) — vide = budget restant du service</label><input id="r-bud" type="number"></div>
 <button class=btn onclick="chargerReco()">Calculer mes recommandations</button></div></div><div id="reco-out"><p class=small>Lancez le calcul pour voir vos suggestions.</p></div>`;
 chargerReco();
}
async function chargerReco(){
 const dur=$id("r-dur").value, bud=$id("r-bud").value;
 RECO=await api(`/api/recommandations?duree=${dur||""}&budget=${bud||""}`);
 if(RECO.erreur){ $id("reco-out").innerHTML=`<div class=carte><p style="color:var(--err)">${esc(RECO.erreur)}</p></div>`; return; }
 const P=RECO.ponderations;
 let h=`<div class=carte><p class=small>Pondérations utilisées (visibles et modifiables par la DRH) : écart de compétence ${P.ecart_competence} pts/niveau · compétence critique +${P.competence_critique} · objectif d'évolution +${P.objectif_evolution} · formation obligatoire +${P.formation_obligatoire} · session disponible +${P.session_disponible}. Les formations déjà terminées sont exclues ; un prérequis manquant signale mais n'exclut pas (contrôle humain).</p></div>`;
 if(!RECO.recommandations.length) h+=`<div class=carte><p>Aucune recommandation : vos écarts actuels ne correspondent à aucune formation du catalogue, ou tous vos prérequis sont couverts. C'est une bonne nouvelle — parlez-en quand même avec votre manager.</p></div>`;
 RECO.recommandations.forEach((rc,i)=>{
  h+=`<div class=carte><div style="display:flex;justify-content:space-between"><h3 style="margin:0">${i+1}. ${esc(rc.titre)}</h3>
   <span class=small>score indicatif : <b>${rc.score}</b></span></div>
  <p class=small>${rc.format} · ${rc.duree_h} h · ${fmtE(rc.cout)} — prochaine session : ${esc(rc.session_prochaine)}</p>
  <b>Pourquoi cette formation ?</b><ul>${rc.pourquoi.map(p=>`<li>${esc(p)}</li>`).join("")}</ul>
  <div class=small><b>Compétences développées :</b> ${rc.competences_developpees.map(esc).join(", ")} — <b>Écarts ciblés :</b> ${rc.ecarts_reduits.length?rc.ecarts_reduits.map(e=>`${esc(e.nom)} (écart ${e.ecart})`).join(", "):"aucun écart direct (complément d'objectif)"}</div>
  ${rc.prerequis.length?`<div class=small style="margin-top:6px"><b>Prérequis :</b>${rc.prerequis.map(p=>` <span class="badge ${p.ok?'b-approuvee':'b-refusee'}">${esc(p.libelle)} — ${esc(p.detail)}</span>`).join("")}</div>`:""}
  ${rc.alertes.length?`<div style="margin-top:8px">${rc.alertes.map(a=>`<div class="alerte a-moyenne">⚠ ${esc(a)}</div>`).join("")}</div>`:""}
  ${rc.alternatives.length?`<p class=small><b>Alternatives :</b> ${rc.alternatives.map(esc).join(" · ")}</p>`:""}
  <div style="margin-top:10px"><button class="btn mini" onclick="ficheFormation('${rc.formation_id}')">Voir la fiche & demander</button>
   <button class="btn mini sec" onclick="signalerReco('${rc.formation_id}')">Signaler une recommandation inadaptée</button></div></div>`; });
 $id("reco-out").innerHTML=h;
}
function signalerReco(fid){
 ouvrirModale(`<div class=x onclick="fermerModale()">✕</div><h2>Signaler une recommandation inadaptée</h2>
 <p>Pour garantir l'équité et la fiabilité du moteur, toute recommandation peut être contestée. Votre signalement est transmis à la DRH pour revue humaine (aucune décision n'est entièrement automatisée).</p>
 <label>Votre commentaire</label><textarea id="sg-txt" rows="4" placeholder="ex. : cette formation ne correspond pas à mon poste car…"></textarea>
 <div style="margin-top:10px"><button class=btn onclick="envoyerSignalement('${fid}')">Envoyer à la DRH</button></div>`);
}
async function envoyerSignalement(fid){
 const txt=$id("sg-txt").value.trim(); if(!txt){alert("Veuillez préciser votre commentaire.");return;}
 await post("/api/notification/lire", {id:"_signalement"}); // no-op toléré
 fermerModale(); alert("Merci : votre signalement a bien été transmis à la DRH (simulation de démonstration — en production, il alimenterait le registre de revue des recommandations).");
}

/* ============================ évaluations ============================ */
function vEvals(C){
 const r=S.user.role;
 if(r==="salarie"){
  const rals=mesRealisations();
  let h=`<h2>Évaluer mes formations (questionnaire à chaud)</h2>
  <p class=small>À faire juste après une formation terminée. Rappel : la satisfaction à chaud ne mesure ni l'acquisition réelle des connaissances, ni l'impact professionnel à long terme.</p>`;
  if(!rals.length) h+=`<div class=carte><p>Aucune formation terminée à évaluer pour le moment.</p></div>`;
  for(const rl of rals){ const f=findF(rl.formation_id);
   const deja=S.evaluations.some(e=>e.salarie_id===S.user.id&&e.formation_id===f.id);
   const froide=S.evaluations_froides.some(e=>e.salarie_id===S.user.id&&e.formation_id===f.id);
   h+=`<div class=carte><b>${esc(f.titre)}</b> <span class=small>(terminée le ${fmtD(rl.date_fin)})</span>
    ${deja?`<p style="color:var(--ok)">✓ Évaluation à chaud déjà enregistrée.</p>`:
     `<div class="grille g3" style="margin-top:8px">${Object.entries({satisfaction:"Satisfaction globale",contenu:"Qualité du contenu",pertinence:"Pertinence pour le poste",animation:"Qualité de l'animation",utilite:"Utilité perçue des acquis",reutilisation:"Intention de réutiliser les connaissances"}).map(([k,t])=>`<div class=fld><label>${t} (1-5)</label><select id="ev-${rl.id}-${k}">${[1,2,3,4,5].map(n=>`<option value="${n}">${n}</option>`).join("")}</select></div>`).join("")}</div>
     <div class=fld><label>Commentaire (facultatif)</label><textarea id="ev-c-${rl.id}" rows="2"></textarea></div>
     <button class=btn onclick="envoyerEval('${f.id}','${rl.id}')">Envoyer mon évaluation</button>`}
    ${froide?`<p class=small>✓ Suivi à froid également enregistré.</p>`:
     `<details style="margin-top:8px"><summary class=small>Suivi à froid (30-90 jours après) — facultatif</summary>
      <div class=fld style="margin-top:8px"><label>Utilisation des acquis dans mon travail (1-5)</label><select id="evf-${rl.id}">${[1,2,3,4,5].map(n=>`<option value="${n}">${n}</option>`).join("")}</select></div>
      <div class=fld><label>Difficultés rencontrées</label><input id="evfd-${rl.id}"></div>
      <button class="btn mini" onclick="envoyerEvalFroide('${f.id}','${rl.id}')">Enregistrer le suivi à froid</button></details>`}
   </div>`; }
  C.innerHTML=h; return; }
 // DRH : agrégats
 let h=`<h2>Évaluations des formations (agrégats)</h2>
 <p class=small>Moyennes par formation sur l'échelle 1-5, à chaud (satisfaction immédiate) et à froid (utilisation des acquis). Ne pas confondre ces indicateurs : la satisfaction à chaud ≠ acquisition réelle ≠ impact à long terme.</p>`;
 const fmts=[...new Set(S.evaluations.map(e=>e.formation_id))];
 h+=`<table class=tbl><tr><th>Formation</th><th>Nbr réponses</th><th>Satisfaction</th><th>Contenu</th><th>Pertinence poste</th><th>Animation</th><th>Utilité</th><th>Réutilisation</th><th>Moy. à froid (acquis)</th></tr>`;
 for(const fid of fmts){ const f=findF(fid), es=S.evaluations.filter(e=>e.formation_id===fid);
  const moy=k=>es.length?(es.reduce((a,e)=>a+e.notes[k],0)/es.length).toFixed(1):"—";
  const ef=S.evaluations_froides.filter(e=>e.formation_id===fid);
  const mf=ef.length?(ef.reduce((a,e)=>a+e.utilisation_acquis,0)/ef.length).toFixed(1):"—";
  h+=`<tr><td>${esc(f.titre)}</td><td>${es.length}</td><td>${moy("satisfaction")}</td><td>${moy("contenu")}</td><td>${moy("pertinence")}</td><td>${moy("animation")}</td><td>${moy("utilite")}</td><td>${moy("reutilisation")}</td><td>${mf}</td></tr>`; }
 h+=`</table><div class=carte style="margin-top:14px"><h3>Commentaires des salariés (anonymisés)</h3>`;
 for(const e of S.evaluations){ if(e.commentaire) h+=`<div class=small style="margin-bottom:6px">« ${esc(e.commentaire)} » — ${esc(findF(e.formation_id).titre)}</div>`; }
 for(const e of S.evaluations_froides){ if(e.commentaire||e.difficultes) h+=`<div class=small style="margin-bottom:6px">[à froid] « ${esc(e.commentaire)} »${e.difficultes?" · Difficultés : "+esc(e.difficultes):""} — ${esc(findF(e.formation_id).titre)}</div>`; }
 C.innerHTML=h+`</div>`;
}
async function envoyerEval(fid, rlId){
 const notes={}; for(const k of ["satisfaction","contenu","pertinence","animation","utilite","reutilisation"]) notes[k]=+$id(`ev-${rlId}-${k}`).value;
 const j=await post("/api/evaluation", {formation_id:fid, notes, commentaire:$id("ev-c-"+rlId).value});
 if(j.ok){ alert("Évaluation enregistrée. "+j.rappel); S=await api("/api/state"); render(); }
}
async function envoyerEvalFroide(fid, rlId){
 const j=await post("/api/evaluation_froide", {formation_id:fid, utilisation_acquis:+$id("evf-"+rlId).value, difficultes:$id("evfd-"+rlId).value});
 if(j.ok){ alert("Suivi à froid enregistré. "+j.rappel); S=await api("/api/state"); render(); }
}

/* ============================ attestations ============================ */
function vAttests(C){
 let h=`<h2>Attestations de formation</h2><p class=small>Générées automatiquement quand une formation est terminée ET validée (assiduité ≥ 80 %). <b>Ce sont des attestations de démonstration, non officielles.</b></p>`;
 if(!S.attestations.length) h+=`<div class=carte><p>Aucune attestation pour le moment.</p></div>`;
 h+=`<table class=tbl><tr><th>Identifiant</th><th>Formation</th><th>Dates</th><th>Durée réalisée</th><th>Émise le</th><th></th></tr>`;
 for(const a of S.attestations){ const rl=S.realisations.find(r=>r.id===a.realisation_id); if(!rl) continue;
  const f=findF(rl.formation_id), sal=findS(rl.salarie_id);
  h+=`<tr><td class=mono>${a.id}</td><td>${esc(f.titre)}</td><td class=small>${fmtD(rl.date_debut)} → ${fmtD(rl.date_fin)}</td>
   <td>${rl.heures_reelles} h / ${rl.heures_prevues} h</td><td class=small>${fmtD(a.date_emission)}</td>
   <td><a href="/api/attestation/${a.id}" target="_blank"><button class="btn mini">⬇ Télécharger</button></a></td></tr>`; }
 C.innerHTML=h+`</table>`;
}

/* ============================ tableau de bord PDC ============================ */
function vDash(C){
 if(!S.budgets) return void (C.innerHTML=`<div class=carte><p>Accès réservé à la DRH et à l'administrateur.</p></div>`);
 C.innerHTML=`<h2>Tableau de bord — Plan de Développement des Compétences</h2>
 <div class=carte><div class=ligne>
  <div><label>Période (début)</label><input type="date" id="d-deb" value="${S.date_demo.slice(0,7)}-01"></div>
  <div><label>Période (fin)</label><input type="date" id="d-fin" value="${S.date_demo}"></div>
  <div><label>Service</label><select id="d-svc"><option value="">Tous</option>${S.services.map(s=>`<option value="${s.id}">${esc(s.nom)}</option>`).join("")}</select></div>
  <div><label>Thème</label><select id="d-th"><option value="">Tous</option>${[...new Set(S.formations.map(f=>f.theme))].sort().map(t=>`<option>${t}</option>`).join("")}</select></div>
  <div><label>Format</label><select id="d-fm"><option value="">Tous</option><option>Présentiel</option><option>E-learning</option><option>Blended</option></select></div>
  <button class=btn onclick="chargerDash()">Actualiser</button></div>
  <p class=small style="margin:8px 0 0">Les indicateurs ci-dessous sont calculés sur les données de démonstration, dans le périmètre et la période choisis. Chaque indicateur est défini — aucun chiffre n'est affiché sans signification.</p></div>
 <div id="dash-out"></div>`;
 chargerDash();
}
async function chargerDash(){
 const p=new URLSearchParams({debut:$id("d-deb").value, fin:$id("d-fin").value, service:$id("d-svc").value, theme:$id("d-th").value, format:$id("d-fm").value});
 const D=await api("/api/dashboard?"+p); if(D.erreur) return alert(D.erreur);
 const B=D.budget;
 let h=`<div class="grille g4">
  <div class=kpi><div class=v>${fmtE(B.total)}</div><div class=t>Budget total</div><div class=d>${esc(D.definitions.budget_total)}</div></div>
  <div class=kpi><div class=v>${fmtE(B.engage)}</div><div class=t>Budget engagé</div><div class=d>${esc(D.definitions.budget_engage)}</div></div>
  <div class=kpi><div class=v>${fmtE(B.consomme)}</div><div class=t>Budget consommé</div><div class=d>${esc(D.definitions.budget_consomme)}</div></div>
  <div class=kpi><div class=v>${fmtE(B.restant)}</div><div class=t>Budget restant</div><div class=d>${esc(D.definitions.budget_restant)} — taux d'utilisation : ${B.taux_utilisation_pct} %.</div></div></div>`;
 h+=`<div class="grille g4" style="margin-top:12px">
  <div class=kpi><div class=v>${D.salaries_formes}</div><div class=t>Salariés formés (période)</div><div class=d>Salariés distincts ayant suivi ≥ 1 formation validée dans la période.</div></div>
  <div class=kpi><div class=v>${D.taux_acces_pct} %</div><div class=t>Taux d'accès à la formation</div><div class=d>${esc(D.definitions.taux_acces_pct)} Effectif de référence : ${D.effectif_reference}.</div></div>
  <div class=kpi><div class=v>${D.heures_reelles} h</div><div class=t>Heures réalisées</div><div class=d>${esc(D.definitions.heures_reelles)}</div></div>
  <div class=kpi><div class=v>${D.formations_suivies}</div><div class=t>Formations suivies (réalisations validées)</div></div></div>`;
 h+=`<div class=carte style="margin-top:12px"><h3>Répartitions</h3><div class="grille g4">
  <div><b>Par thème</b>${barres(D.par_theme)}</div>
  <div><b>Par format</b>${barres(D.par_format)}</div>
  <div><b>Coûts par service (€)</b>${barresObj(D.couts_par_service)}</div>
  <div><b>Taux de validation des demandes</b><div class=v style="font-size:20px;font-weight:700;color:var(--bleu)">${D.taux_validation_pct==null?"— (aucune décision sur la période)":D.taux_validation_pct+" %"}</div><div class=d>${esc(D.definitions.taux_validation_pct)}</div></div></div></div>`;
 h+=`<div class="grille g2"><div class=carte><h3>Compétences les plus demandées</h3><p class=small>Nombre de demandes de formation (hors brouillons) visant chaque compétence, dans le périmètre.</p>
  ${D.competences_demandees.length?`<table class=tbl>${D.competences_demandees.map(([n,x])=>`<tr><td>${esc(n)}</td><td style="text-align:center">${x}</td></tr>`).join("")}</table>`:"<p class=small>Aucune demande dans le périmètre.</p>"}</div>
  <div class=carte><h3>Plus grands écarts de compétences</h3><p class=small>Écart moyen (niveau cible du référentiel − niveau déclaré/validé) sur les salariés concernés — données de démonstration.</p>
  <table class=tbl>${D.plus_grands_ecarts.map(([n,x])=>`<tr><td>${esc(n)}</td><td style="text-align:center"><b>${x}</b></td></tr>`).join("")}</table></div></div>`;
 $id("dash-out").innerHTML=h;
}
function barres(o){ const e=Object.entries(o||{}); if(!e.length) return `<p class=small>—</p>`;
 const mx=Math.max(...e.map(x=>x[1]));
 return e.map(([k,v])=>`<div style="margin-bottom:7px"><span class=small>${esc(k)} : <b>${v}</b></span><div class=barre><i style="width:${Math.round(100*v/mx)}%"></i></div></div>`).join(""); }
function barresObj(o){ const e=Object.entries(o||{}); if(!e.length) return `<p class=small>—</p>`;
 const mx=Math.max(...e.map(x=>x[1]));
 return e.sort((a,b)=>b[1]-a[1]).map(([k,v])=>`<div style="margin-bottom:7px"><span class=small>${esc(k)} : <b>${fmtE(v)}</b></span><div class=barre><i style="width:${Math.round(100*v/mx)}%"></i></div></div>`).join(""); }

/* ============================ cartographie ============================ */
async function vCarto(C){
 if(!S.budgets) return void (C.innerHTML=`<div class=carte><p>Accès réservé à la DRH.</p></div>`);
 C.innerHTML=`<h2>Cartographie des compétences stratégiques</h2>
 <p class=small>Vision consolidée : niveaux déclarés et validés vs cibles des référentiels. Données fictives — les scénarios prospectifs sont identifiés comme hypothèses (module Simulation).</p><div id="carto-out"><p class=small>Chargement…</p></div>`;
 const R=await api("/api/cartographie");
 let h=`<table class=tbl><tr><th>Compétence</th><th>Thème</th><th>Critique</th><th>Salariés concernés</th><th>Niveau moyen</th><th>Autonomes+ (≥3)</th><th>Taux autonome</th><th>Écart moyen vs cible</th><th>Signalétique</th></tr>`;
 for(const r of R){ h+=`<tr><td><b>${esc(r.nom)}</b></td><td class=small>${esc(r.theme)}</td>
  <td>${r.critique?"<span class='badge b-critique'>critique</span>":"—"}</td><td style="text-align:center">${r.effectif_concerne}</td>
  <td style="text-align:center">${r.moyenne_niveau}/5</td><td style="text-align:center">${r.personnes_autonome_plus}</td>
  <td style="text-align:center">${r.taux_autonome_pct} %</td><td style="text-align:center"><b>${r.ecart_moyen_vs_cible}</b></td>
  <td>${r.rare?"<span class='badge b-rare'>rare</span> ":""}${r.critique&&r.taux_autonome_pct<50?"<span class='badge b-refusee'>à développer en priorité</span>":""}</td></tr>`; }
 $id("carto-out").innerHTML=h+`</table><div class=carte style="margin-top:12px"><b>Lecture :</b> « rare » = ≤ 20 % des salariés concernés au niveau autonome ou plus ; « à développer en priorité » = compétence critique avec moins de 50 % de taux d'autonomie. Ces signaux orientent le plan de développement : ils ne sanctionnent aucun salarié.</div>`;
}

/* ============================ simulation ============================ */
async function vSimu(C){
 if(!S.scenarios) return void (C.innerHTML=`<div class=carte><p>Accès réservé à la DRH.</p></div>`);
 C.innerHTML=`<h2>Anticipation des besoins futurs — module de simulation</h2>
 <div class=carte><label>Scénario prospectif (hypothèse explicitement déclarée)</label>
  <select id="sim-scn">${S.scenarios.map(s=>`<option value="${s.id}">${esc(s.nom)}</option>`).join("")}</select>
  <div class=fld style="max-width:320px;margin-top:10px"><label>Contrainte budgétaire supplémentaire : réduction du budget de <b id="sim-red-lbl">0</b> %</label>
   <input type="range" min="-50" max="0" value="0" id="sim-red" oninput="$id('sim-red-lbl').textContent=this.value"></div>
  <button class=btn onclick="lancerSimu()">Lancer la simulation</button></div><div id="sim-out"><p class=small>Choisissez un scénario et lancez la simulation.</p></div>`;
 lancerSimu();
}
async function lancerSimu(){
 const j=await api(`/api/simulation?scenario=${$id("sim-scn").value}&reduction=${$id("sim-red").value}`);
 if(j.erreur) return alert(j.erreur);
 let h=`<div class=carte><h3 style="margin-top:0">${esc(j.scenario.nom)}</h3><p class=small>${esc(j.scenario.description)}</p>
  <div class="grille g4">
   <div class=kpi><div class=v>${fmtE(j.budget_annuel_actuel)}</div><div class=t>Budget annuel actuel</div></div>
   <div class=kpi><div class=v>${fmtE(j.budget_scenario_estime)}</div><div class=t>Budget scénario estimé${j.reduction_budget_pct?` (−${-j.reduction_budget_pct} %)`:""}</div></div>
   <div class=kpi><div class=v>${fmtE(j.cout_formation_estime)}</div><div class=t>Coût de formation estimé pour couvrir les écarts</div><div class=d>Hypothèse : une formation par salarié affecté (coût unitaire le plus bas).</div></div>
   <div class=kpi><div class=v>${j.lignes.reduce((a,l)=>a+l.salaries_affectes,0)}</div><div class=t>Salariés potentiellement affectés</div></div></div>
  <div class="alerte a-moyenne">⚠ ${esc(j.avertissement)}</div></div>`;
 h+=`<table class=tbl><tr><th>Compétence (hypothèse)</th><th>Cible +</th><th>Nbr concernés</th><th>Niveau moyen actuel</th><th>Cible scénario</th><th>Écart scénario</th><th>Salariés affectés</th><th>Formations à envisager</th></tr>`;
 for(const l of j.lignes){ h+=`<tr><td><b>${esc(l.nom)}</b></td><td style="text-align:center">+${l.delta_cible}</td><td style="text-align:center">${l.effectif_concerne}</td>
  <td style="text-align:center">${l.moyenne_actuelle}/5</td><td style="text-align:center">${l.cible_scenario}/5</td><td style="text-align:center"><b>${l.ecart_scenario}</b></td>
  <td style="text-align:center">${l.salaries_affectes}</td><td class=small>${l.formations_suggerees.map(esc).join(" · ")||"—"}</td></tr>`; }
 h+=`</table><div class=carte style="margin-top:12px"><b>Formations à envisager dans ce scénario :</b><br>
  ${j.formations_a_envisager.map(id=>`<span class=tag>${esc(findF(id).titre)}</span>`).join("")}</div>`;
 $id("sim-out").innerHTML=h;
}

/* ============================ équité ============================ */
async function vEquite(C){
 if(!S.budgets) return void (C.innerHTML=`<div class=carte><p>Accès réservé à la DRH.</p></div>`);
 C.innerHTML=`<h2>Équité d'accès à la formation</h2><div id="eq-out"><p class=small>Chargement…</p></div>`;
 const E=await api("/api/equite");
 let h=`<table class=tbl><tr><th>Service</th><th>Effectif (démo)</th><th>Salariés formés</th><th>Taux d'accès</th><th>Heures réalisées</th></tr>`;
 for(const l of E.lignes){ h+=`<tr><td>${esc(l.nom)}${l.prudence?" <span class='badge b-rare'>effectif faible — prudence</span>":""}</td>
  <td style="text-align:center">${l.effectif}</td><td style="text-align:center">${l.salaries_formes}</td>
  <td style="text-align:center"><b>${l.taux_acces_pct} %</b></td><td style="text-align:center">${l.heures_reelles} h</td></tr>`; }
 $id("eq-out").innerHTML=h+`</table><div class=alerte a-moyenne" style="margin-top:12px">⚖ ${esc(E.avertissement)}</div>`;
}

/* ============================ alertes ============================ */
async function vAlertes(C){
 C.innerHTML=`<h2>Alertes & automatisations</h2><p class=small>Règles configurables : demandes en attente trop longtemps, sessions presque complètes, formations obligatoires non suivies/expirées, budgets proches du plafond, compétences critiques mal couvertes.</p>
 <div id="al-out"><p class=small>Chargement…</p></div>`;
 const A=await api("/api/alertes");
 let h = A.length? "" : `<div class=carte><p style="color:var(--ok)">✓ Aucune alerte active.</p></div>`;
 for(const a of A) h+=`<div class="alerte a-${a.gravite}"><b>[${a.type}]</b> ${esc(a.message)} <a href="${a.lien}">Voir →</a></div>`;
 $id("al-out").innerHTML=h;
 if(S.parametres){ const P=S.parametres;
  h=`<div class=carte style="margin-top:14px"><h3>Paramètres des règles (DRH / administrateur)</h3><div class=ligne>
   <div><label>Délai d'attente max (jours)</label><input id="p-att" type="number" value="${P.delai_attente_jours}"></div>
   <div><label>Seuil session presque pleine (%)</label><input id="p-ses" type="number" value="${P.seuil_session_pleine_pct}"></div>
   <div><label>Seuil budget alerte (%)</label><input id="p-bud" type="number" value="${P.seuil_budget_pct}"></div>
   <button class=btn onclick="(async()=>{const j=await post('/api/parametres',{delai_attente_jours:+$id('p-att').value,seuil_session_pleine_pct:+$id('p-ses').value,seuil_budget_pct:+$id('p-bud').value});if(j.ok){S=await api('/api/state');vAlertes($id('contenu'));}})()">Enregistrer</button></div>
  <p class=small style="margin-top:8px">Ces seuils sont des règles métier documentées, applicables et modifiables — pas des décisions individuelles.</p></div>`;
  $id("al-out").insertAdjacentHTML("beforeend", h); }
}

/* ============================ admin catalogue ============================ */
function vAdminCat(C){
 if(!S.budgets) return void (C.innerHTML=`<div class=carte><p>Accès réservé à la DRH / administrateur.</p></div>`);
 C.innerHTML=`<h2>Catalogue — administration</h2>
 <div class="grille g2">
 <div class=carte><h3>Ajouter une formation</h3>
  <div class=fld><label>Titre</label><input id="af-titre"></div>
  <div class=ligne><div><label>Thème</label><select id="af-theme">${[...new Set(S.formations.map(f=>f.theme))].map(t=>`<option>${t}</option>`).join("")}</select></div>
   <div><label>Format</label><select id="af-fmt"><option>Présentiel</option><option>E-learning</option><option>Blended</option></select></div>
   <div><label>Durée (h)</label><input id="af-dur" type="number" value="14"></div>
   <div><label>Coût (€)</label><input id="af-cout" type="number" value="900"></div></div>
  <div class=ligne><div><label>Prestataire</label><select id="af-pre">${S.prestataires.map(p=>`<option value="${p.id}">${esc(p.nom)}</option>`).join("")}</select></div>
   <div><label>Niveau (1-3)</label><select id="af-niv"><option>1</option><option>2</option><option selected>2</option><option>3</option></select></div></div>
  <div class=fld><label>Description</label><textarea id="af-desc" rows="2"></textarea></div>
  <div class=fld><label>Objectifs pédagogiques (un par ligne)</label><textarea id="af-obj" rows="3"></textarea></div>
  <div class=fld><label>Compétences visées</label>
   ${S.competences.map(c=>`<label style="display:inline-block;margin:2px 8px 2px 0;font-weight:400"><input type="checkbox" class="af-cpt" value="${c.id}" style="width:auto"> ${esc(c.nom)}</label>`).join("")}</div>
  <button class=btn onclick="ajouterFormation()">Ajouter au catalogue</button></div>
 <div class=carte><h3>Ajouter une session</h3>
  <div class=fld><label>Formation</label><select id="as-fid">${S.formations.map(f=>`<option value="${f.id}">${esc(f.titre)}</option>`).join("")}</select></div>
  <div class=ligne><div><label>Début</label><input id="as-db" type="date"></div><div><label>Fin</label><input id="as-fin" type="date"></div>
   <div><label>Capacité</label><input id="as-cap" type="number" value="10"></div></div>
  <div class=fld><label>Lieu</label><input id="as-lieu" placeholder="Site Nord — Salle…"></div>
  <button class=btn onclick="ajouterSession()">Créer la session</button>
  <h3>Export des données (interopérabilité)</h3>
  <p class=small>L'export JSON structuré permet, à terme, d'échanger avec les autres outils RH de SmartFactory via interfaces ou fichiers — aucune intégration n'existe déjà.</p>
  <a class="btn sec" href="/api/export" download>⬇ Exporter l'ensemble des données (JSON)</a></div></div>`;
}
async function ajouterFormation(){
 const cpts=[...document.querySelectorAll(".af-cpt:checked")].map(x=>x.value);
 const j=await post("/api/formation/add", {titre:$id("af-titre").value, theme:$id("af-theme").value, format:$id("af-fmt").value,
  duree_h:+$id("af-dur").value, cout:+$id("af-cout").value, prestataire_id:$id("af-pre").value, niveau:+$id("af-niv").value,
  description:$id("af-desc").value, objectifs:$id("af-obj").value.split("\\n").map(s=>s.trim()).filter(Boolean), competences:cpts});
 if(j.ok){ alert("Formation "+j.formation_id+" ajoutée au catalogue."); S=await api("/api/state"); render(); }
}
async function ajouterSession(){
 const j=await post("/api/session/add", {formation_id:$id("as-fid").value, date_debut:$id("as-db").value, date_fin:$id("as-fin").value,
  capacite:+$id("as-cap").value, lieu:$id("as-lieu").value});
 if(j.ok){ alert("Session "+j.session_id+" créée."); S=await api("/api/state"); render(); }
}

/* ============================ parcours par métier ============================ */
function vParcours(C){
 let h=`<h2>Parcours de formation par métier</h2><p class=small>Chaque parcours associe le référentiel du métier (niveaux cibles), des formations recommandées et des étapes de progression. Les parcours types sont des propositions de la DRH, à adapter avec chaque salarié.</p>`;
 for(const m of S.metiers){
  h+=`<div class=carte><h3 style="margin-top:0">${esc(m.nom)} <span class=small>(${m.service_id?"rattaché : "+esc(findSvc(m.service_id)):"tous services"})</span></h3>
   <b>Référentiel (niveaux cibles) :</b><div style="margin:6px 0">${Object.entries(m.competences_cibles).map(([cid,nv])=>{const c=findC(cid);
    return `<span class=tag title="Niveau cible : ${nv}/5">${esc(c.nom)} → ${nv}${c.critique?" ⚑":""}</span>`;}).join("")}</div>
   <b>Étapes de progression :</b><ol style="margin:8px 0 0 18px;padding:0">${m.parcours.map(p=>`<li><b>${esc(p.titre)}</b> — ${esc(p.objectif)}<br>
    <span class=small>Formations : ${p.formations.map(id=>esc(findF(id).titre)).join(" · ")}</span></li>`).join("")}</ol>
   ${m.formations_obligatoires.length?`<p class=small><b>Obligatoire :</b> ${m.formations_obligatoires.map(o=>`${esc(findF(o.formation_id).titre)} (validité ${o.validite_mois} mois)`).join("; ")}</p>`:""}
  </div>`; }
 C.innerHTML=h;
}

/* ============================ équipe (manager) ============================ */
function vEquipe(C){
 if(S.user.role!=="manager") return void (C.innerHTML=`<div class=carte><p>Accès réservé aux managers.</p></div>`);
 const eq=equipesManager();
 let h=`<h2>Besoins de développement de mon équipe</h2>
 <p class=small>Écarts entre niveaux déclarés/validés et cibles du référentiel. Support au dialogue individuel — aucune note de performance n'en est déduite.</p>`;
 for(const s of eq){ const eco=ecartsLocaux(s);
  h+=`<div class=carte><b>${esc(s.nom)}</b> <span class=small>— ${findM(s.metier_id)?.nom||"—"}${s.objectif_evolution?" · objectif déclaré : "+esc(s.objectif_evolution):""}</span>
   ${eco.length?`<table class=tbl style="margin-top:8px"><tr><th>Compétence</th><th>Actuel</th><th>Cible</th><th>Écart</th></tr>${eco.map(e=>`<tr><td>${esc(e.nom)}${e.critique?" <span class='badge b-critique'>critique</span>":""}</td><td style="text-align:center">${e.actuel}</td><td style="text-align:center">${e.cible}</td><td style="text-align:center"><b>${e.ecart}</b></td></tr>`).join("")}</table>`:`<p class=small style="color:var(--ok)">✓ Aucun écart détecté sur le référentiel.</p>`}
  <div style="margin-top:8px"><button class="btn mini sec" onclick="validerCpt('${s.id}')">Valider une compétence de ce salarié</button></div></div>`; }
 C.innerHTML=h;
}
function validerCpt(salId){
 const s=findS(salId), m=findM(s.metier_id);
 let h=`<div class=x onclick="fermerModale()">✕</div><h2>Valider une compétence — ${esc(s.nom)}</h2>
 <p class=small>Une validation par évaluateur est distincte d'une autoévaluation déclarée : elle doit être justifiée (projet, observation, soutenance…). Elle ne remplace pas l'entretien professionnel.</p>
 <label>Compétence</label><select id="vc-cpt">${S.competences.map(c=>`<option value="${c.id}">${esc(c.nom)}</option>`).join("")}</select>
 <label>Niveau validé (1-5)</label><select id="vc-niv">${[1,2,3,4,5].map(n=>`<option value="${n}" ${n===3?"selected":""}>${n} — ${S.levels[n].split(" — ")[0]}</option>`).join("")}</select>
 <label>Justification (obligatoire)</label><textarea id="vc-just" rows="3"></textarea>
 <div style="margin-top:10px"><button class=btn onclick="envoyerValCpt('${salId}')">Enregistrer la validation</button></div>`;
 ouvrirModale(h);
}
async function envoyerValCpt(salId){
 const j=await post("/api/competence_validee", {salarie_id:salId, competence_id:$id("vc-cpt").value, niveau:+$id("vc-niv").value, justification:$id("vc-just").value});
 if(j.ok){ fermerModale(); alert(j.rappel); S=await api("/api/state"); render(); }
}

/* ============================ assistant chatbot ============================ */
function vAssistant(C){
 C.innerHTML=`<h2>💬 SmartSkills Assistant</h2>
 <p class=small>Mode démonstration : réponses prédéfinies + recherche dans le catalogue. <b>Aucun modèle d'IA externe n'est connecté.</b> L'assistant ne prend aucune décision RH, ne révèle pas d'informations individuelles à des tiers et oriente vers la DRH pour les questions complexes.</p>
 <div class=carte><div class="chat-box" id="chat-box"><div class="msg bot">Bonjour ! Je suis SmartSkills Assistant. Posez-moi une question : « comment demander une formation ? », « quels sont les statuts d'une demande ? », ou le titre d'une formation…<span class=conf>Assistant de démonstration — réponses prédéfinies, sans modèle d'IA externe.</span></div></div>
 <div class=ligne style="margin-top:10px"><div style="flex:3"><input id="chat-in" placeholder="Votre question…" onkeydown="if(event.key==='Enter')envoyerChat()"></div>
  <button class=btn onclick="envoyerChat()">Envoyer</button></div></div>`;
}
async function envoyerChat(){
 const inp=$id("chat-in"), q=inp.value.trim(); if(!q) return; inp.value="";
 const box=$id("chat-box");
 box.insertAdjacentHTML("beforeend", `<div class="msg user">${esc(q)}</div>`);
 const j=await api("/api/chat?q="+encodeURIComponent(q));
 box.insertAdjacentHTML("beforeend", `<div class="msg bot">${esc(j.reponse)}<span class=conf>Confiance : ${j.confiance}. ${esc(j.limite||"")}</span></div>`);
 box.scrollTop=box.scrollHeight;
}

/* ============================ documentation ============================ */
function vDocs(C){
 C.innerHTML=`<div class=doc><h2>Documentation SmartSkills</h2>
<p class=small>Extrait des livrables du projet : RGPD, IA responsable, modèle de données, moteur de recommandation, plan de tests, guides. Version ${S.version}.</p>

<h3>1. Analyse du problème & proposition de valeur</h3>
<p><b>Problèmes identifiés au service Formation :</b> (1) catalogue figé, déconnecté des besoins individuels et des évolutions technologiques ; (2) gestion administrative papier (demandes, validations, historiques, attestations non centralisés) ; (3) absence d'anticipation des écarts de compétences.</p>
<p><b>Valeur ajoutée :</b> processus numérique centralisé ; parcours personnalisés et expliqués ; pilotage par indicateurs documentés ; anticipation par scénarios ; attestations automatiques ; équité mesurée. Bénéfices : salariés (parcours clairs, traçabilité), managers (décisions motivées en un clic, vision d'équipe), DRH (pilotage budgétaire et compétences critiques).</p>

<h3>2. Modèle de données</h3>
<p>Entités : salarié · rôle utilisateur · service · métier · compétence · référentiel (métier→compétences cibles) · formation · prestataire · session · demande d'inscription · historique de validation (dans la demande) · réalisation de formation · autoévaluation · évaluation à chaud / à froid · attestation · budget · scénario · notification. Relations principales : une demande appartient à un salarié et concerne une formation (+ session optionnelle) ; une décision de manager est liée à une demande avec motif obligatoire ; une attestation ne dépend que d'une réalisation validée.</p>
<p><b>Règles de cohérence appliquées :</b> transitions de statut strictes (brouillon→en_attente→approuvée/refusée→inscrite→terminée/annulée) ; heures réalisées comptabilisées seulement après validation de la réalisation ; attestation émise uniquement si assiduité ≥ 80 % ; budget consommé ≠ budget engagé (demandes approuvées/inscrites) ; compétence déclarée ≠ compétence validée par évaluateur ; doublons de demandes actives bloqués ; sessions complètes non réservables.</p>

<h3>3. Moteur de recommandation — critères, calculs, limites</h3>
<p>Score transparent : +12 × niveaux d'écart réduits (écart = cible du référentiel − niveau actuel déclaré/validé) ; +4 si compétence critique ; +8 si contribution à l'objectif d'évolution déclaré ; +15 si formation obligatoire non validée ; +3 si session avec place disponible. Exclusions : formations déjà terminées. Signalements non-exclusifs : prérequis manquants, durée > temps indiqué, coût > budget restant du service. Alternatives proposées (formations partageant la compétence principale). <b>Limites :</b> dépendance à la qualité des autoévaluations ; pondérations arbitraires et modifiables ; ne couvre que le catalogue existant ; aucun critère sensible (âge, sexe, origine, santé) n'est utilisé ; aucune décision n'est automatisée — chaque suggestion est contestable via « Signaler une recommandation inadaptée ».</p>

<h3>4. Indicateurs du tableau de bord — définitions</h3>
<ul><li><b>Budget total</b> : somme des enveloppes annuelles allouées par service (2026).</li>
<li><b>Budget engagé</b> : coût des demandes approuvées ou inscrites, non terminées (réservation, pas dépense).</li>
<li><b>Budget consommé</b> : coût des formations terminées avec réalisation validée.</li>
<li><b>Budget restant</b> : total − engagé − consommé.</li>
<li><b>Taux d'accès à la formation</b> : salariés distincts ayant suivi ≥ 1 formation validée dans la période ÷ effectif de référence × 100.</li>
<li><b>Taux de validation des demandes</b> : approuvées (approuvée/inscrite/terminée) ÷ (approuvées + refusées) × 100.</li>
<li><b>Heures réalisées</b> : heures effectivement suivies après validation, distinctes des heures prévues.</li></ul>

<h3>5. Dossier RGPD (démonstration pédagogique)</h3>
<p><b>Données traitées :</b> identifiant fictif, rôle, service, métier, demandes, historique de formation, heures, compétences déclarées/validées, évaluations, informations budgétaires. Données indispensables : identifiant, rôle, demande/statut, heures. Facultatives : objectif d'évolution, commentaires libres. <b>Finalités :</b> gestion des inscriptions, suivi des formations, développement des compétences, attestations, pilotage budgétaire. <b>Accès :</b> le salarié consulte ses propres données ; le manager celles de son équipe (nécessaire au suivi) ; la DRH les données de pilotage ; l'administrateur technique n'accède aux données RH que si nécessaire et autorisé. <b>Conservation (durées à faire valider par DPO/juridique) :</b> demandes & décisions : 3 ans après clôture ; réalisations & attestations : 5 ans ; autoévaluations : 2 ans (période d'entretien) ; évaluations de formation : 3 ans. Suppression ou anonymisation au terme. <b>Droits :</b> accès, rectification, effacement et opposition sur demande à la « DPO » (fictive). <b>Sécurité (mesures pour une mise en production réelle) :</b> authentification forte (MFA), chiffrement TLS + at-rest, journalisation des actions sensibles, sauvegardes chiffrées, gestion d'incidents, contrôle des exports, tests de pénétration, minimisation des données. <b>Avertissement :</b> cette maquette pédagogique n'est pas un traitement réel ; sa présence ne constitue pas une preuve de conformité complète.</p>

<h3>6. Dossier IA responsable</h3>
<p><b>Usages actuels :</b> moteur de recommandation (règles pondérées, non-apprentissage), assistant conversationnel (réponses prédéfinies + recherche textuelle). Aucun modèle d'IA externe n'est connecté — c'est volontairement signalé partout. <b>Explicabilité :</b> chaque recommandation affiche ses facteurs et leur poids ; les pondérations sont visibles dans l'interface. <b>Contrôle humain :</b> aucune décision RH automatisée (accès, promotion, évolution) ; approbations/refus toujours motivés par un humain ; procédure de contestation des recommandations. <b>Biais surveillés :</b> aucun critère sensible utilisé ; biais indirects possibles (favoriser les salariés déjà formés ou les services mieux dotés) atténués par l'indicateur d'équité et la revue DRH. <b>Limites documentées :</b> erreurs factuelles possibles de l'assistant, données incomplètes, dépendance à la qualité des référentiels et des autoévaluations.</p>

<h3>7. Carnet de prompts (exemple)</h3>
<p><i>Date : ${fmtD(S.date_demo)} · Outil : assistant IA du groupe · Objectif : générer le squelette de l'application Python monofichier. · Prompt envoyé : « Conçois une application web RH en un seul fichier Python (stdlib uniquement) pour la gestion de formation et des compétences d'une usine fictive, avec catalogue filtrable, demandes validées par manager, autoévaluation 1-5, recommandations expliquées, tableau de bord budgétaire, attestations HTML et chatbot à réponses prédéfinies. » · Résultat : architecture serveur HTTP + SPA intégrée, modèle de données complet. · Erreurs/limites détectées : incohérences possibles entre budget engagé et consommé, statuts manquants dans les transitions — corrigés par le groupe (règles TRANSITIONS). · Part humaine : cadrage métier, choix des pondérations, vérification des calculs du tableau de bord, rédaction du dossier RGPD.</i> <b>Rappel :</b> aucune donnée personnelle réelle n'a été saisie dans un outil IA.</p>

<h3>8. Plan de tests (scénarios principaux)</h3>
<ol><li>Connexion des 4 rôles → chacun ne voit que son périmètre. <i>Vérifié.</i></li>
<li>Salarié : catalogue → filtre combiné (thème + format + coût) → fiche → demande → statut « en attente » + notification. <i>Vérifié.</i></li>
<li>Demande dupliquée active → refus avec message. <i>Vérifié.</i></li>
<li>Manager : approbation sans motif → bloquée ; avec motif → OK, salarié notifié. <i>Vérifié.</i></li>
<li>DRH : inscription en session complète → bloquée ; en session libre → place réservée. <i>Vérifié.</i></li>
<li>Clôture avec 70 % d'assiduité → réalisation non validée, pas d'attestation ; avec 100 % → attestation générée et téléchargeable. <i>Vérifié.</i></li>
<li>Budget : engagé (approuvées/inscrites) distinct du consommé (terminées validées). <i>Vérifié par recalcule manuel.</i></li>
<li>Autoévaluation hors échelle 1-5 → refus. Recommandation : formation déjà terminée exclue ; prérequis manquant signalé non-exclusif. <i>Vérifié.</i></li>
<li>Simulation scénario Industrie 4.0 + réduction budget −30 % → écarts et coûts estimés affichés avec mention « estimation ». <i>Vérifié.</i></li>
<li>Chatbot : question inconnue → réponse de repli avec confiance « faible » et orientation DRH. <i>Vérifié.</i></li></ol>

<h3>9. Guide utilisateur (synthèse)</h3>
<p><b>Salarié(e) :</b> Catalogue pour chercher et demander · Mes demandes pour suivre et annuler · Autoévaluation 1-5 puis dialogue avec le manager · Recommandations expliquées · Évaluer après chaque formation · Télécharger ses attestations. <b>Manager :</b> Demandes de l'équipe → approuver/refuser <i>avec motif obligatoire</i> (le budget prévisionnel est affiché) · Besoins & compétences pour préparer les entretiens · Valider des compétences avec justification. <b>DRH :</b> Tableau de bord filtrable (période, service, thème, format) · Cartographie des compétences critiques · Simulation d'anticipation · Ajout de formations/sessions · Alertes et seuils configurables · Export JSON pour interopérabilité.</p>

<h3>10. Guide technique</h3>
<p><b>Installation :</b> Python 3.9+ (aucune dépendance externe). <b>Lancement :</b> <span class=mono>python smartskills.py</span> puis ouvrir http://localhost:8090. <b>Persistance :</b> fichier JSON à côté du script ; réinitialisation via l'administrateur (sf-9001 → alertes/règles, ou POST /api/reset). <b>Architecture :</b> monofichier : modèle + règles métier + API JSON + SPA intégrée. <b>Limites honnêtes :</b> authentification simplifiée (mot de passe « demo ») — non conforme production ; pas de multi-sites ; les projections sont des estimations ; l'assistant n'est pas un vrai LLM.</p>

<h3>11. Critères de réussite & perspectives</h3>
<p>Toutes les fonctionnalités minimales sont présentes et testables (plan de tests §8) ; données cohérentes entre écrans (une seule source : l'API) ; recommandations expliquées ; indicateurs documentés ; RGPD et biais documentés. <b>Perspectives :</b> connecteurs vers les 6 autres outils RH SmartFactory via exports structurés, planification des créneaux avec contraintes de production, évaluation d'impact à 12 mois, MFA et audit trail complet pour la production.</p>
</div>`;
}

/* ============================ démarrage ============================ */
init();
</script></body></html>"""

if __name__ == "__main__":
    main()
