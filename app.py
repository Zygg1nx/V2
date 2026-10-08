#!/usr/bin/env python3
"""
SmartSkills - Application RH pour SmartFactory
Mini-LMS + Gestion Prévisionnelle des Compétences
Fichier unique - Flask + SQLite + Jinja2
"""

import os
import json
import sqlite3
import hashlib
import secrets
import datetime
from functools import wraps
from io import BytesIO

from flask import (
    Flask, render_template_string, request, redirect, url_for,
    session, flash, jsonify, g, make_response, send_file
)

# ==============================================================================
# CONFIGURATION
# ==============================================================================

app = Flask(__name__)
app.secret_key = secrets.token_hex(32)
app.config['DATABASE'] = 'smartskills.db'
app.config['PERMANENT_SESSION_LIFETIME'] = datetime.timedelta(hours=8)

# ==============================================================================
# BASE DE DONNÉES
# ==============================================================================

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(exception):
    db = g.pop('db', None)
    if db is not None:
        db.close()

def init_db():
    db = get_db()
    db.executescript('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        employee_id TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        first_name TEXT NOT NULL,
        last_name TEXT NOT NULL,
        email TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('salarie','manager','rh','admin')),
        service_id INTEGER,
        job_id INTEGER,
        manager_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (manager_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE NOT NULL,
        site TEXT NOT NULL DEFAULT 'Lyon',
        budget_formation REAL DEFAULT 50000
    );

    CREATE TABLE IF NOT EXISTS jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        service_id INTEGER,
        FOREIGN KEY (service_id) REFERENCES services(id)
    );

    CREATE TABLE IF NOT EXISTS competences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT NOT NULL,
        description TEXT
    );

    CREATE TABLE IF NOT EXISTS job_competences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        target_level INTEGER NOT NULL CHECK(target_level BETWEEN 1 AND 5),
        is_critical INTEGER DEFAULT 0,
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (competence_id) REFERENCES competences(id),
        UNIQUE(job_id, competence_id)
    );

    CREATE TABLE IF NOT EXISTS providers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        contact_email TEXT,
        speciality TEXT,
        rating REAL DEFAULT 4.0
    );

    CREATE TABLE IF NOT EXISTS formations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT NOT NULL,
        description TEXT,
        objectives TEXT,
        format TEXT CHECK(format IN ('presentiel','e-learning','blended')),
        duration_hours INTEGER NOT NULL,
        cost REAL NOT NULL,
        provider_id INTEGER,
        difficulty TEXT CHECK(difficulty IN ('debutant','intermediaire','avance','expert')),
        prerequisites TEXT,
        evaluation_mode TEXT,
        target_audience TEXT,
        theme TEXT NOT NULL,
        is_active INTEGER DEFAULT 1,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (provider_id) REFERENCES providers(id)
    );

    CREATE TABLE IF NOT EXISTS formation_competences (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formation_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        level_gain INTEGER DEFAULT 1,
        FOREIGN KEY (formation_id) REFERENCES formations(id),
        FOREIGN KEY (competence_id) REFERENCES competences(id),
        UNIQUE(formation_id, competence_id)
    );

    CREATE TABLE IF NOT EXISTS sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        formation_id INTEGER NOT NULL,
        start_date DATE NOT NULL,
        end_date DATE NOT NULL,
        location TEXT,
        max_participants INTEGER DEFAULT 15,
        current_participants INTEGER DEFAULT 0,
        status TEXT DEFAULT 'ouverte' CHECK(status IN ('ouverte','complete','annulee','terminee')),
        FOREIGN KEY (formation_id) REFERENCES formations(id)
    );

    CREATE TABLE IF NOT EXISTS enrollment_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        formation_id INTEGER NOT NULL,
        session_id INTEGER,
        status TEXT DEFAULT 'en_attente' CHECK(status IN
            ('brouillon','en_attente','approuvee','refusee','inscrite','terminee','annulee')),
        motivation TEXT,
        manager_comment TEXT,
        manager_decision_date TIMESTAMP,
        decided_by INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (formation_id) REFERENCES formations(id),
        FOREIGN KEY (session_id) REFERENCES sessions(id),
        FOREIGN KEY (decided_by) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS completed_formations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        formation_id INTEGER NOT NULL,
        session_id INTEGER,
        enrollment_id INTEGER,
        hours_completed REAL NOT NULL,
        completion_date DATE NOT NULL,
        certificate_id TEXT UNIQUE,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (formation_id) REFERENCES formations(id),
        FOREIGN KEY (enrollment_id) REFERENCES enrollment_requests(id)
    );

    CREATE TABLE IF NOT EXISTS self_assessments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        competence_id INTEGER NOT NULL,
        declared_level INTEGER NOT NULL CHECK(declared_level BETWEEN 1 AND 5),
        assessment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        comment TEXT,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (competence_id) REFERENCES competences(id)
    );

    CREATE TABLE IF NOT EXISTS formation_evaluations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        formation_id INTEGER NOT NULL,
        completed_formation_id INTEGER,
        satisfaction INTEGER CHECK(satisfaction BETWEEN 1 AND 5),
        content_quality INTEGER CHECK(content_quality BETWEEN 1 AND 5),
        relevance INTEGER CHECK(relevance BETWEEN 1 AND 5),
        animation_quality INTEGER CHECK(animation_quality BETWEEN 1 AND 5),
        usefulness INTEGER CHECK(usefulness BETWEEN 1 AND 5),
        would_recommend INTEGER CHECK(would_recommend BETWEEN 1 AND 5),
        comment TEXT,
        eval_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        eval_type TEXT DEFAULT 'chaud' CHECK(eval_type IN ('chaud','froid')),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (formation_id) REFERENCES formations(id)
    );

    CREATE TABLE IF NOT EXISTS notifications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        message TEXT NOT NULL,
        is_read INTEGER DEFAULT 0,
        link TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );

    CREATE TABLE IF NOT EXISTS budget_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        service_id INTEGER,
        year INTEGER NOT NULL,
        total_budget REAL NOT NULL,
        committed_budget REAL DEFAULT 0,
        consumed_budget REAL DEFAULT 0,
        FOREIGN KEY (service_id) REFERENCES services(id)
    );

    CREATE TABLE IF NOT EXISTS audit_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        action TEXT NOT NULL,
        entity_type TEXT,
        entity_id INTEGER,
        details TEXT,
        ip_address TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    ''')
    db.commit()

def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

def seed_data():
    db = get_db()
    if db.execute("SELECT COUNT(*) FROM users").fetchone()[0] > 0:
        return

    # Services
    services = [
        ('Production', 'Lyon', 120000),
        ('Maintenance', 'Lyon', 80000),
        ('Qualité', 'Grenoble', 60000),
        ('R&D', 'Paris', 100000),
        ('Logistique', 'Lyon', 50000),
        ('IT & Digital', 'Paris', 90000),
        ('RH', 'Lyon', 40000),
    ]
    for s in services:
        db.execute("INSERT INTO services (name, site, budget_formation) VALUES (?,?,?)", s)

    # Métiers
    jobs = [
        ('Opérateur de production', 'Conduit les opérations de fabrication', 1),
        ('Technicien de maintenance', 'Assure la maintenance préventive et curative', 2),
        ('Responsable qualité', 'Pilote le système qualité', 3),
        ('Ingénieur méthodes', 'Optimise les processus de production', 1),
        ('Responsable d\'équipe', 'Manage une équipe de production', 1),
        ('Analyste de données industrielles', 'Analyse les données de production', 4),
        ('Technicien qualité', 'Réalise les contrôles qualité', 3),
        ('Développeur industriel', 'Développe les solutions digitales usine', 6),
        ('Responsable formation', 'Pilote le plan de développement des compétences', 7),
        ('Chef de projet logistique', 'Coordonne les flux logistiques', 5),
    ]
    for j in jobs:
        db.execute("INSERT INTO jobs (title, description, service_id) VALUES (?,?,?)", j)

    # Compétences
    competences = [
        ('Lean Manufacturing', 'Technique', 'Méthodologie d\'amélioration continue'),
        ('Maintenance prédictive', 'Technique', 'Anticiper les pannes par analyse de données'),
        ('Analyse de données', 'Digital', 'Collecter, traiter et interpréter des données'),
        ('Python / Programmation', 'Digital', 'Développer des scripts et applications'),
        ('Gestion de projet', 'Transverse', 'Planifier et piloter un projet'),
        ('Management d\'équipe', 'Management', 'Encadrer et motiver une équipe'),
        ('Cybersécurité industrielle', 'Digital', 'Protéger les systèmes industriels'),
        ('Normes ISO 9001', 'Qualité', 'Maîtriser le référentiel qualité'),
        ('Sécurité au travail', 'Réglementaire', 'Prévenir les risques professionnels'),
        ('Communication interpersonnelle', 'Transverse', 'Communiquer efficacement'),
        ('Automatisme / PLC', 'Technique', 'Programmer des automates industriels'),
        ('IoT industriel', 'Digital', 'Capteurs connectés et supervision'),
        ('Excel avancé', 'Digital', 'Tableaux croisés, macros, Power Query'),
        ('Anglais professionnel', 'Langue', 'Communiquer en anglais dans un contexte pro'),
        ('Conduite du changement', 'Management', 'Accompagner les transformations'),
        ('Intelligence artificielle appliquée', 'Digital', 'Utiliser l\'IA dans l\'industrie'),
        ('Supply Chain Management', 'Logistique', 'Optimiser la chaîne d\'approvisionnement'),
        ('Lecture de plans techniques', 'Technique', 'Interpréter plans et schémas'),
        ('Résolution de problèmes', 'Transverse', 'Appliquer des méthodes structurées (8D, DMAIC)'),
        ('RGPD et protection des données', 'Réglementaire', 'Respecter la réglementation données personnelles'),
    ]
    for c in competences:
        db.execute("INSERT INTO competences (name, category, description) VALUES (?,?,?)", c)

    # Référentiel compétences par métier
    job_comps = [
        (1, 1, 3, 1), (1, 9, 4, 1), (1, 18, 3, 0), (1, 10, 3, 0),
        (2, 2, 4, 1), (2, 11, 4, 1), (2, 12, 3, 0), (2, 9, 4, 1), (2, 18, 4, 0),
        (3, 8, 5, 1), (3, 19, 4, 1), (3, 9, 4, 0), (3, 5, 3, 0),
        (4, 1, 4, 1), (4, 3, 4, 1), (4, 5, 4, 0), (4, 13, 3, 0), (4, 19, 4, 1),
        (5, 6, 5, 1), (5, 10, 4, 1), (5, 15, 4, 1), (5, 5, 4, 0), (5, 1, 3, 0),
        (6, 3, 5, 1), (6, 4, 4, 1), (6, 16, 4, 1), (6, 13, 4, 0), (6, 12, 3, 0),
        (7, 8, 4, 1), (7, 19, 3, 0), (7, 9, 3, 0), (7, 18, 3, 0),
        (8, 4, 5, 1), (8, 7, 4, 1), (8, 12, 4, 0), (8, 3, 4, 0),
        (9, 5, 4, 1), (9, 15, 4, 1), (9, 6, 3, 0), (9, 20, 4, 1),
        (10, 17, 5, 1), (10, 5, 4, 1), (10, 13, 3, 0), (10, 14, 3, 0),
    ]
    for jc in job_comps:
        db.execute("INSERT INTO job_competences (job_id, competence_id, target_level, is_critical) VALUES (?,?,?,?)", jc)

    # Prestataires
    providers = [
        ('FormaTech Industries', 'contact@formatech.demo', 'Techniques industrielles', 4.5),
        ('DigiSkills Academy', 'info@digiskills.demo', 'Digital et data', 4.2),
        ('LeaderPro Formation', 'hello@leaderpro.demo', 'Management et soft skills', 4.0),
        ('SafeWork Institute', 'formation@safework.demo', 'Sécurité et réglementation', 4.3),
        ('QualityCert', 'contact@qualitycert.demo', 'Qualité et normes', 4.1),
        ('LinguaPro', 'info@linguapro.demo', 'Langues professionnelles', 3.9),
        ('DataFactory School', 'learn@datafactory.demo', 'Data science et IA', 4.6),
    ]
    for p in providers:
        db.execute("INSERT INTO providers (name, contact_email, speciality, rating) VALUES (?,?,?,?)", p)

    # Formations
    formations = [
        ('Lean Manufacturing - Fondamentaux', 'Découverte des principes du Lean', 'Comprendre et appliquer les bases du Lean', 'presentiel', 14, 1200, 1, 'debutant', None, 'Quiz + mise en situation', 'Opérateurs, techniciens', 'Excellence opérationnelle'),
        ('Lean Manufacturing - Perfectionnement', 'Approfondissement Lean Six Sigma', 'Maîtriser les outils avancés du Lean', 'blended', 21, 2200, 1, 'avance', 'Lean Fondamentaux', 'Projet pratique', 'Ingénieurs, responsables', 'Excellence opérationnelle'),
        ('Maintenance prédictive avec IoT', 'Capteurs et analyse prédictive', 'Mettre en place une maintenance prédictive', 'blended', 21, 2800, 1, 'intermediaire', None, 'Projet + soutenance', 'Techniciens maintenance', 'Maintenance'),
        ('Python pour l\'industrie', 'Initiation à Python pour automatiser', 'Écrire des scripts Python pour l\'industrie', 'e-learning', 28, 1500, 2, 'debutant', None, 'Exercices en ligne', 'Tous profils techniques', 'Digital'),
        ('Analyse de données industrielles', 'Exploiter les données de production', 'Analyser et visualiser des données', 'blended', 21, 2000, 7, 'intermediaire', 'Excel avancé', 'Étude de cas', 'Analystes, ingénieurs', 'Digital'),
        ('Management d\'équipe en industrie', 'Fondamentaux du management opérationnel', 'Développer son leadership d\'équipe', 'presentiel', 14, 1800, 3, 'intermediaire', None, 'Jeux de rôle + évaluation 360', 'Responsables d\'équipe', 'Management'),
        ('Conduite du changement', 'Accompagner les transformations', 'Piloter un projet de changement', 'presentiel', 7, 1100, 3, 'intermediaire', None, 'Plan d\'action individuel', 'Managers, chefs de projet', 'Management'),
        ('Cybersécurité industrielle', 'Protéger les systèmes SCADA et OT', 'Identifier et prévenir les cybermenaces', 'blended', 14, 2500, 2, 'avance', None, 'Simulation d\'attaque', 'IT, maintenance', 'Cybersécurité'),
        ('Normes ISO 9001:2015', 'Comprendre et appliquer ISO 9001', 'Maîtriser le référentiel qualité', 'presentiel', 14, 1600, 5, 'intermediaire', None, 'QCM + audit blanc', 'Responsables qualité', 'Qualité'),
        ('Sécurité au travail - Niveau 1', 'Prévention des risques professionnels', 'Adopter les comportements sécuritaires', 'presentiel', 7, 600, 4, 'debutant', None, 'QCM', 'Tous salariés', 'Sécurité'),
        ('Sécurité au travail - Niveau 2', 'Analyse des risques et DUERP', 'Évaluer et documenter les risques', 'presentiel', 14, 1200, 4, 'intermediaire', 'Sécurité Niveau 1', 'Étude de cas', 'Encadrants, préventeurs', 'Sécurité'),
        ('Excel avancé pour l\'industrie', 'TCD, Power Query, macros VBA', 'Automatiser le traitement de données', 'e-learning', 14, 800, 2, 'intermediaire', None, 'Exercices pratiques', 'Tous profils', 'Digital'),
        ('Anglais professionnel B2', 'Anglais des affaires et technique', 'Communiquer en anglais professionnel', 'blended', 40, 2200, 6, 'intermediaire', None, 'TOEIC blanc', 'Tous profils', 'Langues'),
        ('Intelligence artificielle pour l\'industrie', 'Machine learning appliqué à la production', 'Comprendre et piloter des projets IA', 'blended', 21, 3200, 7, 'avance', 'Analyse de données', 'Projet + soutenance', 'Ingénieurs, data analysts', 'Digital'),
        ('Gestion de projet - Fondamentaux', 'Méthodes et outils de gestion de projet', 'Planifier et suivre un projet', 'presentiel', 14, 1400, 3, 'debutant', None, 'Mise en situation', 'Tous profils', 'Transverse'),
        ('Communication interpersonnelle', 'Techniques de communication efficace', 'Améliorer ses relations professionnelles', 'presentiel', 7, 900, 3, 'debutant', None, 'Jeux de rôle', 'Tous profils', 'Transverse'),
        ('Résolution de problèmes - Méthode 8D', 'Résolution structurée de problèmes', 'Appliquer la méthode 8D', 'presentiel', 7, 1000, 5, 'intermediaire', None, 'Étude de cas réel', 'Techniciens, ingénieurs', 'Qualité'),
        ('Automatismes et programmation PLC', 'Programmation d\'automates Siemens/Schneider', 'Programmer et maintenir un automate', 'presentiel', 28, 3500, 1, 'avance', None, 'TP sur simulateur', 'Techniciens maintenance', 'Technique'),
        ('Supply Chain et logistique 4.0', 'Transformation digitale de la supply chain', 'Optimiser les flux avec le digital', 'blended', 14, 1800, 2, 'intermediaire', None, 'Étude de cas', 'Logisticiens, chefs de projet', 'Logistique'),
        ('RGPD et protection des données', 'Conformité RGPD en entreprise', 'Mettre en œuvre la conformité RGPD', 'e-learning', 7, 500, 4, 'debutant', None, 'QCM', 'Tous profils', 'Réglementaire'),
        ('Lecture de plans et schémas techniques', 'Interpréter plans mécaniques et électriques', 'Lire et exploiter un plan technique', 'presentiel', 14, 1100, 1, 'debutant', None, 'Exercices pratiques', 'Opérateurs, techniciens', 'Technique'),
        ('IoT industriel - Capteurs connectés', 'Déployer des capteurs IoT en usine', 'Concevoir une architecture IoT simple', 'blended', 14, 2000, 2, 'intermediaire', None, 'Projet pratique', 'Techniciens, ingénieurs', 'Digital'),
    ]
    for f in formations:
        db.execute("""INSERT INTO formations
            (title, description, objectives, format, duration_hours, cost, provider_id,
             difficulty, prerequisites, evaluation_mode, target_audience, theme)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""", f)

    # Compétences par formation
    fc = [
        (1,1,1),(2,1,2),(3,2,2),(3,12,1),(4,4,2),(5,3,2),(5,13,1),
        (6,6,2),(6,10,1),(7,15,2),(8,7,2),(9,8,2),(10,9,1),
        (11,9,2),(12,13,2),(13,14,2),(14,16,2),(14,3,1),
        (15,5,2),(16,10,2),(17,19,2),(18,11,2),(19,17,2),
        (20,20,1),(21,18,2),(22,12,2),
    ]
    for x in fc:
        db.execute("INSERT INTO formation_competences (formation_id, competence_id, level_gain) VALUES (?,?,?)", x)

    # Sessions
    base = datetime.date(2025, 1, 1)
    sessions_data = []
    for fid in range(1, 23):
        for offset in [30, 90, 150]:
            sd = base + datetime.timedelta(days=offset)
            dur = db.execute("SELECT duration_hours FROM formations WHERE id=?", (fid,)).fetchone()
            if dur:
                days = max(1, dur[0] // 7)
                ed = sd + datetime.timedelta(days=days)
                loc = 'Lyon' if fid % 3 != 0 else 'Paris'
                sessions_data.append((fid, sd.isoformat(), ed.isoformat(), f'Site {loc}', 15, 0, 'ouverte'))
    for s in sessions_data:
        db.execute("INSERT INTO sessions (formation_id, start_date, end_date, location, max_participants, current_participants, status) VALUES (?,?,?,?,?,?,?)", s)

    # Utilisateurs
    pwd = hash_password('demo2025')
    users = [
        ('SF001', pwd, 'Marie', 'Dupont', 'marie.dupont@smartfactory.demo', 'salarie', 1, 1, None),
        ('SF002', pwd, 'Jean', 'Martin', 'jean.martin@smartfactory.demo', 'salarie', 2, 2, None),
        ('SF003', pwd, 'Sophie', 'Bernard', 'sophie.bernard@smartfactory.demo', 'salarie', 3, 7, None),
        ('SF004', pwd, 'Pierre', 'Durand', 'pierre.durand@smartfactory.demo', 'salarie', 1, 4, None),
        ('SF005', pwd, 'Claire', 'Lefebvre', 'claire.lefebvre@smartfactory.demo', 'salarie', 4, 6, None),
        ('SF006', pwd, 'Thomas', 'Moreau', 'thomas.moreau@smartfactory.demo', 'salarie', 5, 10, None),
        ('SF007', pwd, 'Julie', 'Petit', 'julie.petit@smartfactory.demo', 'salarie', 6, 8, None),
        ('SF010', pwd, 'Laurent', 'Garcia', 'laurent.garcia@smartfactory.demo', 'manager', 1, 5, None),
        ('SF011', pwd, 'Nathalie', 'Roux', 'nathalie.roux@smartfactory.demo', 'manager', 2, 5, None),
        ('SF012', pwd, 'François', 'Morel', 'francois.morel@smartfactory.demo', 'manager', 3, 5, None),
        ('SF013', pwd, 'Isabelle', 'Simon', 'isabelle.simon@smartfactory.demo', 'manager', 4, 5, None),
        ('SF020', pwd, 'Catherine', 'Leroy', 'catherine.leroy@smartfactory.demo', 'rh', 7, 9, None),
        ('SF099', pwd, 'Admin', 'Système', 'admin@smartfactory.demo', 'admin', 7, 9, None),
    ]
    for u in users:
        db.execute("""INSERT INTO users
            (employee_id, password_hash, first_name, last_name, email, role, service_id, job_id, manager_id)
            VALUES (?,?,?,?,?,?,?,?,?)""", u)

    # Affecter les managers
    manager_map = {1: 8, 2: 9, 3: 10, 4: 11, 5: 8, 6: 11, 7: 11}
    for uid, mid in manager_map.items():
        db.execute("UPDATE users SET manager_id=? WHERE id=?", (mid, uid))

    # Autoévaluations initiales
    assessments = [
        (1,1,2),(1,9,3),(1,18,2),(1,10,2),
        (2,2,3),(2,11,3),(2,12,1),(2,9,3),(2,18,3),
        (3,8,3),(3,19,2),(3,9,2),(3,5,2),
        (4,1,3),(4,3,2),(4,5,2),(4,13,2),(4,19,2),
        (5,3,4),(5,4,3),(5,16,2),(5,13,3),(5,12,2),
        (6,17,3),(6,5,2),(6,13,2),(6,14,2),
        (7,4,4),(7,7,3),(7,12,3),(7,3,3),
    ]
    for a in assessments:
        db.execute("INSERT INTO self_assessments (user_id, competence_id, declared_level) VALUES (?,?,?)", a)

    # Demandes de formation
    requests_data = [
        (1, 1, 1, 'en_attente', 'Souhaite améliorer mes compétences Lean'),
        (1, 10, 4, 'approuvee', 'Formation sécurité obligatoire', 'Validé - formation prioritaire'),
        (2, 3, 7, 'en_attente', 'Maintenance prédictive pour anticiper les pannes'),
        (2, 22, 10, 'approuvee', 'Compléter mes compétences IoT'),
        (3, 9, 13, 'en_attente', 'Renouvellement certification ISO'),
        (4, 5, 16, 'approuvee', 'Analyse de données pour optimisation process'),
        (4, 2, 19, 'terminee', 'Lean avancé pour amélioration continue', 'Excellent profil'),
        (5, 14, 22, 'en_attente', 'IA pour la production'),
        (6, 19, 25, 'approuvee', 'Supply Chain 4.0'),
        (7, 8, 28, 'en_attente', 'Cybersécurité pour les systèmes industriels'),
    ]
    for r in requests_data:
        if len(r) == 5:
            db.execute("""INSERT INTO enrollment_requests
                (user_id, formation_id, session_id, status, motivation) VALUES (?,?,?,?,?)""", r)
        else:
            db.execute("""INSERT INTO enrollment_requests
                (user_id, formation_id, session_id, status, motivation, manager_comment) VALUES (?,?,?,?,?,?)""", r)

    # Formations terminées
    completed = [
        (4, 2, 19, 7, 21.0, '2025-02-15', 'CERT-2025-001'),
        (1, 10, 4, 2, 7.0, '2025-01-20', 'CERT-2025-002'),
    ]
    for c in completed:
        db.execute("""INSERT INTO completed_formations
            (user_id, formation_id, session_id, enrollment_id, hours_completed, completion_date, certificate_id)
            VALUES (?,?,?,?,?,?,?)""", c)

    # Évaluations
    evals = [
        (4, 2, 1, 5, 5, 4, 4, 5, 5, 'Excellente formation, très applicable', 'chaud'),
        (1, 10, 2, 4, 4, 5, 4, 4, 4, 'Bonne formation sécurité', 'chaud'),
    ]
    for e in evals:
        db.execute("""INSERT INTO formation_evaluations
            (user_id, formation_id, completed_formation_id, satisfaction, content_quality, relevance,
             animation_quality, usefulness, would_recommend, comment, eval_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""", e)

    # Budget
    year = 2025
    for sid in range(1, 8):
        svc = db.execute("SELECT budget_formation FROM services WHERE id=?", (sid,)).fetchone()
        total = svc[0] if svc else 50000
        db.execute("INSERT INTO budget_entries (service_id, year, total_budget, committed_budget, consumed_budget) VALUES (?,?,?,?,?)",
                   (sid, year, total, total * 0.3, total * 0.1))

    # Notifications
    notifs = [
        (1, 'Demande en attente', 'Votre demande pour "Lean Manufacturing - Fondamentaux" est en attente de validation.', '/my-requests'),
        (8, 'Demande à valider', 'Marie Dupont a demandé la formation "Lean Manufacturing - Fondamentaux".', '/manager/requests'),
        (2, 'Demande en attente', 'Votre demande pour "Maintenance prédictive avec IoT" est en attente.', '/my-requests'),
    ]
    for n in notifs:
        db.execute("INSERT INTO notifications (user_id, title, message, link) VALUES (?,?,?,?)", n)

    db.commit()

# ==============================================================================
# AUTHENTIFICATION ET AUTORISATION
# ==============================================================================

def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Veuillez vous connecter.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def role_required(*roles):
    def decorator(f):
        @wraps(f)
        def decorated(*args, **kwargs):
            if 'user_id' not in session:
                return redirect(url_for('login'))
            if session.get('role') not in roles:
                flash('Accès non autorisé.', 'danger')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated
    return decorator

def get_current_user():
    if 'user_id' not in session:
        return None
    db = get_db()
    return db.execute("""
        SELECT u.*, s.name as service_name, j.title as job_title
        FROM users u
        LEFT JOIN services s ON u.service_id = s.id
        LEFT JOIN jobs j ON u.job_id = j.id
        WHERE u.id = ?
    """, (session['user_id'],)).fetchone()

def log_action(action, entity_type=None, entity_id=None, details=None):
    db = get_db()
    db.execute("INSERT INTO audit_log (user_id, action, entity_type, entity_id, details, ip_address) VALUES (?,?,?,?,?,?)",
               (session.get('user_id'), action, entity_type, entity_id, details, request.remote_addr))
    db.commit()

def notify_user(user_id, title, message, link=None):
    db = get_db()
    db.execute("INSERT INTO notifications (user_id, title, message, link) VALUES (?,?,?,?)",
               (user_id, title, message, link))
    db.commit()

@app.context_processor
def inject_globals():
    user = get_current_user()
    unread = 0
    if user:
        db = get_db()
        unread = db.execute("SELECT COUNT(*) FROM notifications WHERE user_id=? AND is_read=0",
                            (user['id'],)).fetchone()[0]
    return dict(current_user=user, unread_notifications=unread)

# ==============================================================================
# TEMPLATES HTML
# ==============================================================================

BASE_CSS = """
:root {
    --primary: #1a56db;
    --primary-dark: #1e40af;
    --primary-light: #dbeafe;
    --secondary: #059669;
    --secondary-light: #d1fae5;
    --accent: #f59e0b;
    --accent-light: #fef3c7;
    --danger: #dc2626;
    --danger-light: #fee2e2;
    --dark: #111827;
    --gray-900: #1f2937;
    --gray-700: #374151;
    --gray-500: #6b7280;
    --gray-300: #d1d5db;
    --gray-100: #f3f4f6;
    --white: #ffffff;
    --sidebar-w: 260px;
    --radius: 10px;
    --shadow: 0 1px 3px rgba(0,0,0,0.1), 0 1px 2px rgba(0,0,0,0.06);
    --shadow-md: 0 4px 6px rgba(0,0,0,0.07), 0 2px 4px rgba(0,0,0,0.06);
}
* { margin:0; padding:0; box-sizing:border-box; }
body { font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; background: var(--gray-100); color: var(--dark); line-height:1.6; }
a { color: var(--primary); text-decoration:none; }
a:hover { text-decoration:underline; }

.login-page { min-height:100vh; display:flex; align-items:center; justify-content:center; background:linear-gradient(135deg, #1e3a5f 0%, #1a56db 100%); }
.login-box { background:var(--white); border-radius:var(--radius); padding:40px; width:400px; max-width:95vw; box-shadow:var(--shadow-md); }
.login-box h1 { font-size:1.5rem; color:var(--primary-dark); margin-bottom:8px; }
.login-box .subtitle { color:var(--gray-500); font-size:0.9rem; margin-bottom:24px; }
.login-box .brand { display:flex; align-items:center; gap:12px; margin-bottom:24px; }
.login-box .brand .logo { width:48px; height:48px; background:var(--primary); border-radius:10px; display:flex; align-items:center; justify-content:center; color:white; font-weight:700; font-size:1.2rem; }

.layout { display:flex; min-height:100vh; }
.sidebar { width:var(--sidebar-w); background:var(--gray-900); color:var(--white); position:fixed; top:0; left:0; bottom:0; overflow-y:auto; z-index:100; display:flex; flex-direction:column; }
.sidebar-brand { padding:20px; border-bottom:1px solid rgba(255,255,255,0.1); display:flex; align-items:center; gap:12px; }
.sidebar-brand .logo { width:40px; height:40px; background:var(--primary); border-radius:8px; display:flex; align-items:center; justify-content:center; font-weight:700; font-size:1rem; }
.sidebar-brand span { font-weight:600; font-size:1.1rem; }
.sidebar-nav { flex:1; padding:16px 0; }
.sidebar-nav a { display:flex; align-items:center; gap:12px; padding:10px 20px; color:rgba(255,255,255,0.7); font-size:0.9rem; transition:all 0.2s; border-left:3px solid transparent; }
.sidebar-nav a:hover, .sidebar-nav a.active { background:rgba(255,255,255,0.08); color:var(--white); text-decoration:none; border-left-color:var(--primary); }
.sidebar-nav .nav-section { padding:16px 20px 8px; font-size:0.7rem; text-transform:uppercase; letter-spacing:1px; color:rgba(255,255,255,0.4); }
.sidebar-user { padding:16px 20px; border-top:1px solid rgba(255,255,255,0.1); }
.sidebar-user .name { font-weight:600; font-size:0.9rem; }
.sidebar-user .role-badge { display:inline-block; padding:2px 8px; border-radius:20px; font-size:0.7rem; margin-top:4px; }
.role-salarie { background:var(--primary-light); color:var(--primary-dark); }
.role-manager { background:var(--accent-light); color:#92400e; }
.role-rh { background:var(--secondary-light); color:#065f46; }
.role-admin { background:var(--danger-light); color:#991b1b; }

.main { margin-left:var(--sidebar-w); flex:1; }
.topbar { background:var(--white); border-bottom:1px solid var(--gray-300); padding:14px 32px; display:flex; justify-content:space-between; align-items:center; position:sticky; top:0; z-index:50; }
.topbar h2 { font-size:1.2rem; color:var(--dark); }
.topbar-actions { display:flex; align-items:center; gap:16px; }
.notif-badge { position:relative; }
.notif-badge .count { position:absolute; top:-6px; right:-6px; background:var(--danger); color:white; font-size:0.65rem; padding:1px 5px; border-radius:10px; }
.content { padding:24px 32px; max-width:1400px; }

.card { background:var(--white); border-radius:var(--radius); box-shadow:var(--shadow); padding:24px; margin-bottom:20px; }
.card-header { display:flex; justify-content:space-between; align-items:center; margin-bottom:16px; padding-bottom:12px; border-bottom:1px solid var(--gray-100); }
.card-header h3 { font-size:1.05rem; color:var(--dark); }
.card-grid { display:grid; grid-template-columns:repeat(auto-fill, minmax(280px,1fr)); gap:20px; }
.stat-card { background:var(--white); border-radius:var(--radius); box-shadow:var(--shadow); padding:20px; border-left:4px solid var(--primary); }
.stat-card.green { border-left-color:var(--secondary); }
.stat-card.amber { border-left-color:var(--accent); }
.stat-card.red { border-left-color:var(--danger); }
.stat-card .label { font-size:0.8rem; color:var(--gray-500); text-transform:uppercase; letter-spacing:0.5px; }
.stat-card .value { font-size:1.8rem; font-weight:700; margin:4px 0; color:var(--dark); }
.stat-card .detail { font-size:0.8rem; color:var(--gray-500); }

table { width:100%; border-collapse:collapse; }
table th { text-align:left; padding:10px 12px; background:var(--gray-100); font-size:0.8rem; color:var(--gray-500); text-transform:uppercase; letter-spacing:0.5px; border-bottom:2px solid var(--gray-300); }
table td { padding:10px 12px; border-bottom:1px solid var(--gray-100); font-size:0.9rem; }
table tr:hover td { background:var(--gray-100); }

.badge { display:inline-block; padding:3px 10px; border-radius:20px; font-size:0.75rem; font-weight:600; }
.badge-pending { background:#fef3c7; color:#92400e; }
.badge-approved { background:#d1fae5; color:#065f46; }
.badge-rejected { background:#fee2e2; color:#991b1b; }
.badge-completed { background:#dbeafe; color:#1e40af; }
.badge-enrolled { background:#e0e7ff; color:#3730a3; }
.badge-cancelled { background:#f3f4f6; color:#6b7280; }
.badge-draft { background:#f3f4f6; color:#6b7280; }

.btn { display:inline-flex; align-items:center; gap:6px; padding:8px 16px; border-radius:6px; font-size:0.85rem; font-weight:500; border:none; cursor:pointer; transition:all 0.2s; text-decoration:none !important; }
.btn-primary { background:var(--primary); color:white; }
.btn-primary:hover { background:var(--primary-dark); }
.btn-success { background:var(--secondary); color:white; }
.btn-success:hover { background:#047857; }
.btn-danger { background:var(--danger); color:white; }
.btn-danger:hover { background:#b91c1c; }
.btn-outline { background:transparent; border:1px solid var(--gray-300); color:var(--gray-700); }
.btn-outline:hover { border-color:var(--primary); color:var(--primary); }
.btn-sm { padding:5px 10px; font-size:0.78rem; }

.form-group { margin-bottom:16px; }
.form-group label { display:block; font-size:0.85rem; font-weight:500; margin-bottom:4px; color:var(--gray-700); }
.form-group input, .form-group select, .form-group textarea {
    width:100%; padding:9px 12px; border:1px solid var(--gray-300); border-radius:6px; font-size:0.9rem; font-family:inherit;
}
.form-group input:focus, .form-group select:focus, .form-group textarea:focus { outline:none; border-color:var(--primary); box-shadow:0 0 0 3px rgba(26,86,219,0.15); }
.form-row { display:flex; gap:16px; }
.form-row .form-group { flex:1; }

.filters { display:flex; gap:12px; flex-wrap:wrap; margin-bottom:20px; align-items:end; }
.filters .form-group { margin-bottom:0; min-width:160px; }
.filters .form-group label { font-size:0.78rem; }
.filters .form-group select, .filters .form-group input { padding:7px 10px; font-size:0.83rem; }

.alert { padding:12px 16px; border-radius:6px; margin-bottom:16px; font-size:0.9rem; }
.alert-success { background:var(--secondary-light); color:#065f46; border-left:4px solid var(--secondary); }
.alert-danger { background:var(--danger-light); color:#991b1b; border-left:4px solid var(--danger); }
.alert-warning { background:var(--accent-light); color:#92400e; border-left:4px solid var(--accent); }
.alert-info { background:var(--primary-light); color:var(--primary-dark); border-left:4px solid var(--primary); }

.progress-bar { background:var(--gray-100); border-radius:10px; height:10px; overflow:hidden; }
.progress-bar .fill { height:100%; border-radius:10px; transition:width 0.5s; }
.fill-blue { background:var(--primary); }
.fill-green { background:var(--secondary); }
.fill-amber { background:var(--accent); }
.fill-red { background:var(--danger); }

.skill-gap { display:flex; align-items:center; gap:12px; margin-bottom:12px; padding:10px; background:var(--gray-100); border-radius:6px; }
.skill-gap .name { flex:1; font-weight:500; font-size:0.9rem; }
.skill-gap .levels { display:flex; gap:4px; align-items:center; font-size:0.8rem; }
.skill-gap .gap-indicator { padding:2px 8px; border-radius:10px; font-size:0.75rem; font-weight:600; }
.gap-ok { background:#d1fae5; color:#065f46; }
.gap-small { background:#fef3c7; color:#92400e; }
.gap-large { background:#fee2e2; color:#991b1b; }

.stars { color:var(--accent); }
.formation-card { border:1px solid var(--gray-300); border-radius:var(--radius); padding:20px; transition:all 0.2s; }
.formation-card:hover { border-color:var(--primary); box-shadow:var(--shadow-md); }
.formation-card .title { font-size:1rem; font-weight:600; margin-bottom:6px; }
.formation-card .meta { display:flex; flex-wrap:wrap; gap:8px; margin:8px 0; }
.formation-card .meta span { font-size:0.78rem; padding:2px 8px; background:var(--gray-100); border-radius:4px; color:var(--gray-700); }
.formation-card .desc { font-size:0.85rem; color:var(--gray-500); margin-bottom:12px; }

.tabs { display:flex; border-bottom:2px solid var(--gray-300); margin-bottom:20px; }
.tabs a { padding:10px 20px; font-size:0.9rem; color:var(--gray-500); border-bottom:2px solid transparent; margin-bottom:-2px; }
.tabs a:hover { color:var(--primary); text-decoration:none; }
.tabs a.active { color:var(--primary); border-bottom-color:var(--primary); font-weight:600; }

.empty-state { text-align:center; padding:40px; color:var(--gray-500); }
.empty-state .icon { font-size:3rem; margin-bottom:12px; }
.empty-state h3 { color:var(--gray-700); margin-bottom:8px; }

.chart-container { background:var(--white); border-radius:var(--radius); padding:20px; }
.bar-chart { display:flex; align-items:flex-end; gap:8px; height:200px; padding-top:20px; }
.bar-chart .bar-wrapper { flex:1; display:flex; flex-direction:column; align-items:center; height:100%; justify-content:flex-end; }
.bar-chart .bar { width:100%; min-width:20px; max-width:60px; background:var(--primary); border-radius:4px 4px 0 0; transition:height 0.5s; }
.bar-chart .bar-label { font-size:0.7rem; color:var(--gray-500); margin-top:6px; text-align:center; word-break:break-word; }
.bar-chart .bar-value { font-size:0.7rem; font-weight:600; margin-bottom:4px; }

.donut-chart { width:160px; height:160px; border-radius:50%; position:relative; display:flex; align-items:center; justify-content:center; margin:0 auto; }
.donut-chart .center { position:absolute; width:100px; height:100px; background:white; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-direction:column; }
.donut-chart .center .pct { font-size:1.5rem; font-weight:700; }
.donut-chart .center .lbl { font-size:0.7rem; color:var(--gray-500); }

.chat-container { position:fixed; bottom:20px; right:20px; z-index:200; }
.chat-toggle { width:56px; height:56px; border-radius:50%; background:var(--primary); color:white; border:none; cursor:pointer; font-size:1.5rem; box-shadow:var(--shadow-md); display:flex; align-items:center; justify-content:center; }
.chat-window { position:absolute; bottom:70px; right:0; width:380px; max-height:500px; background:white; border-radius:var(--radius); box-shadow:0 10px 40px rgba(0,0,0,0.15); display:none; flex-direction:column; overflow:hidden; }
.chat-window.open { display:flex; }
.chat-header { padding:16px; background:var(--primary); color:white; font-weight:600; display:flex; justify-content:space-between; align-items:center; }
.chat-messages { flex:1; padding:16px; overflow-y:auto; max-height:350px; }
.chat-msg { margin-bottom:12px; }
.chat-msg .bubble { padding:10px 14px; border-radius:12px; font-size:0.85rem; max-width:85%; display:inline-block; }
.chat-msg.bot .bubble { background:var(--gray-100); }
.chat-msg.user { text-align:right; }
.chat-msg.user .bubble { background:var(--primary); color:white; }
.chat-input { display:flex; border-top:1px solid var(--gray-300); }
.chat-input input { flex:1; border:none; padding:12px; font-size:0.85rem; }
.chat-input button { border:none; background:var(--primary); color:white; padding:12px 16px; cursor:pointer; }

.modal-overlay { position:fixed; top:0; left:0; right:0; bottom:0; background:rgba(0,0,0,0.5); z-index:300; display:none; align-items:center; justify-content:center; }
.modal-overlay.open { display:flex; }
.modal { background:white; border-radius:var(--radius); padding:32px; max-width:600px; width:95vw; max-height:90vh; overflow-y:auto; }
.modal h3 { margin-bottom:16px; }

@media (max-width:768px) {
    .sidebar { transform:translateX(-100%); }
    .main { margin-left:0; }
    .content { padding:16px; }
    .card-grid { grid-template-columns:1fr; }
    .form-row { flex-direction:column; }
    .filters { flex-direction:column; }
    .topbar { padding:12px 16px; }
}
"""

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartSkills - Connexion</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
<div class="login-page">
    <div class="login-box">
        <div class="brand">
            <div class="logo">SF</div>
            <div>
                <h1>SmartSkills</h1>
                <div class="subtitle">SmartFactory — Plateforme de développement des compétences</div>
            </div>
        </div>
        {% with messages = get_flashed_messages(with_categories=true) %}
        {% for cat, msg in messages %}
        <div class="alert alert-{{ cat }}">{{ msg }}</div>
        {% endfor %}
        {% endwith %}
        <form method="POST">
            <div class="form-group">
                <label for="employee_id">Identifiant salarié</label>
                <input type="text" id="employee_id" name="employee_id" placeholder="Ex: SF001" required>
            </div>
            <div class="form-group">
                <label for="password">Mot de passe</label>
                <input type="password" id="password" name="password" placeholder="demo2025" required>
            </div>
            <button type="submit" class="btn btn-primary" style="width:100%; justify-content:center; padding:11px;">Se connecter</button>
        </form>
        <div style="margin-top:24px; padding:16px; background:var(--gray-100); border-radius:6px; font-size:0.8rem;">
            <strong>Comptes de démonstration</strong> (mot de passe : demo2025)<br><br>
            <table style="width:100%; font-size:0.78rem;">
                <tr><td><strong>SF001</strong></td><td>Marie Dupont</td><td><span class="badge role-salarie">Salarié</span></td></tr>
                <tr><td><strong>SF002</strong></td><td>Jean Martin</td><td><span class="badge role-salarie">Salarié</span></td></tr>
                <tr><td><strong>SF005</strong></td><td>Claire Lefebvre</td><td><span class="badge role-salarie">Salarié</span></td></tr>
                <tr><td><strong>SF010</strong></td><td>Laurent Garcia</td><td><span class="badge role-manager">Manager</span></td></tr>
                <tr><td><strong>SF011</strong></td><td>Nathalie Roux</td><td><span class="badge role-manager">Manager</span></td></tr>
                <tr><td><strong>SF020</strong></td><td>Catherine Leroy</td><td><span class="badge role-rh">RH</span></td></tr>
                <tr><td><strong>SF099</strong></td><td>Admin Système</td><td><span class="badge role-admin">Admin</span></td></tr>
            </table>
            <br><em>Application de démonstration pédagogique — Données fictives</em>
        </div>
    </div>
</div>
</body>
</html>
"""

LAYOUT_TEMPLATE = """
<!DOCTYPE html>
<html lang="fr">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>SmartSkills — {{ page_title|default('Tableau de bord') }}</title>
    <style>""" + BASE_CSS + """</style>
</head>
<body>
<div class="layout">
    <aside class="sidebar">
        <div class="sidebar-brand">
            <div class="logo">SF</div>
            <span>SmartSkills</span>
        </div>
        <nav class="sidebar-nav">
            <div class="nav-section">Navigation</div>
            <a href="{{ url_for('dashboard') }}" class="{{ 'active' if active_page=='dashboard' }}">📊 Tableau de bord</a>
            <a href="{{ url_for('catalogue') }}" class="{{ 'active' if active_page=='catalogue' }}">📚 Catalogue</a>
            <a href="{{ url_for('my_requests') }}" class="{{ 'active' if active_page=='my_requests' }}">📝 Mes demandes</a>
            <a href="{{ url_for('my_formations') }}" class="{{ 'active' if active_page=='my_formations' }}">🎓 Mes formations</a>
            <a href="{{ url_for('self_assessment') }}" class="{{ 'active' if active_page=='self_assessment' }}">📈 Autoévaluation</a>
            <a href="{{ url_for('recommendations') }}" class="{{ 'active' if active_page=='recommendations' }}">🎯 Recommandations</a>
            {% if current_user and current_user.role in ('manager','rh','admin') %}
            <div class="nav-section">Management</div>
            <a href="{{ url_for('manager_requests') }}" class="{{ 'active' if active_page=='manager_requests' }}">✅ Demandes équipe</a>
            <a href="{{ url_for('team_skills') }}" class="{{ 'active' if active_page=='team_skills' }}">👥 Compétences équipe</a>
            {% endif %}
            {% if current_user and current_user.role in ('rh','admin') %}
            <div class="nav-section">Pilotage RH</div>
            <a href="{{ url_for('rh_dashboard') }}" class="{{ 'active' if active_page=='rh_dashboard' }}">📊 Tableau de bord RH</a>
            <a href="{{ url_for('skills_map') }}" class="{{ 'active' if active_page=='skills_map' }}">🗺️ Cartographie</a>
            <a href="{{ url_for('manage_catalogue') }}" class="{{ 'active' if active_page=='manage_catalogue' }}">⚙️ Gérer le catalogue</a>
            <a href="{{ url_for('budget_view') }}" class="{{ 'active' if active_page=='budget' }}">💰 Budget</a>
            {% endif %}
            {% if current_user and current_user.role == 'admin' %}
            <div class="nav-section">Administration</div>
            <a href="{{ url_for('admin_users') }}" class="{{ 'active' if active_page=='admin_users' }}">👤 Utilisateurs</a>
            <a href="{{ url_for('audit_logs') }}" class="{{ 'active' if active_page=='audit' }}">📋 Journal d'audit</a>
            {% endif %}
            <div class="nav-section">Compte</div>
            <a href="{{ url_for('notifications_page') }}" class="{{ 'active' if active_page=='notifications' }}">🔔 Notifications{% if unread_notifications %} ({{ unread_notifications }}){% endif %}</a>
            <a href="{{ url_for('rgpd_info') }}">🔒 RGPD</a>
            <a href="{{ url_for('logout') }}">🚪 Déconnexion</a>
        </nav>
        {% if current_user %}
        <div class="sidebar-user">
            <div class="name">{{ current_user.first_name }} {{ current_user.last_name }}</div>
            <span class="badge role-{{ current_user.role }}">{{ current_user.role|upper }}</span>
            <div style="font-size:0.75rem; color:rgba(255,255,255,0.5); margin-top:4px;">{{ current_user.employee_id }} — {{ current_user.service_name }}</div>
        </div>
        {% endif %}
    </aside>
    <div class="main">
        <div class="topbar">
            <h2>{{ page_title|default('Tableau de bord') }}</h2>
            <div class="topbar-actions">
                <a href="{{ url_for('notifications_page') }}" class="notif-badge" title="Notifications">
                    🔔{% if unread_notifications %}<span class="count">{{ unread_notifications }}</span>{% endif %}
                </a>
                <span style="font-size:0.85rem; color:var(--gray-500);">{{ current_user.first_name if current_user else '' }}</span>
            </div>
        </div>
        <div class="content">
            {% with messages = get_flashed_messages(with_categories=true) %}
            {% for cat, msg in messages %}
            <div class="alert alert-{{ cat }}">{{ msg }}</div>
            {% endfor %}
            {% endwith %}
            {% block content %}{% endblock %}
        </div>
    </div>
</div>

<!-- Chatbot -->
<div class="chat-container">
    <div class="chat-window" id="chatWindow">
        <div class="chat-header">
            <span>💬 SmartSkills Assistant</span>
            <button onclick="toggleChat()" style="background:none;border:none;color:white;cursor:pointer;font-size:1.2rem;">✕</button>
        </div>
        <div class="chat-messages" id="chatMessages">
            <div class="chat-msg bot"><div class="bubble">Bonjour ! Je suis l'assistant SmartSkills. Comment puis-je vous aider ?<br><br>Exemples :<br>• "Quelles formations en digital ?"<br>• "Comment faire une demande ?"<br>• "Qu'est-ce que l'autoévaluation ?"</div></div>
        </div>
        <div class="chat-input">
            <input type="text" id="chatInput" placeholder="Votre question..." onkeypress="if(event.key==='Enter')sendChat()">
            <button onclick="sendChat()">➤</button>
        </div>
    </div>
    <button class="chat-toggle" onclick="toggleChat()" title="Assistant SmartSkills">💬</button>
</div>

<script>
function toggleChat() {
    document.getElementById('chatWindow').classList.toggle('open');
}
function sendChat() {
    const input = document.getElementById('chatInput');
    const msg = input.value.trim();
    if (!msg) return;
    const msgs = document.getElementById('chatMessages');
    msgs.innerHTML += '<div class="chat-msg user"><div class="bubble">' + escapeHtml(msg) + '</div></div>';
    input.value = '';
    fetch('/api/chat', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({message:msg})})
    .then(r=>r.json()).then(data=>{
        msgs.innerHTML += '<div class="chat-msg bot"><div class="bubble">' + data.response + '</div></div>';
        msgs.scrollTop = msgs.scrollHeight;
    });
}
function escapeHtml(t){const d=document.createElement('div');d.textContent=t;return d.innerHTML;}
</script>
</body>
</html>
"""

# ==============================================================================
# ROUTES
# ==============================================================================

@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        eid = request.form.get('employee_id', '').strip().upper()
        pwd = request.form.get('password', '')
        db = get_db()
        user = db.execute("SELECT * FROM users WHERE employee_id=?", (eid,)).fetchone()
        if user and user['password_hash'] == hash_password(pwd):
            session.permanent = True
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['employee_id'] = user['employee_id']
            log_action('login')
            flash('Connexion réussie.', 'success')
            return redirect(url_for('dashboard'))
        flash('Identifiant ou mot de passe incorrect.', 'danger')
    return render_template_string(LOGIN_TEMPLATE)

@app.route('/logout')
def logout():
    log_action('logout')
    session.clear()
    flash('Vous êtes déconnecté.', 'info')
    return redirect(url_for('login'))

# --- DASHBOARD ---
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    user = get_current_user()
    uid = user['id']

    # Stats personnelles
    pending = db.execute("SELECT COUNT(*) FROM enrollment_requests WHERE user_id=? AND status='en_attente'", (uid,)).fetchone()[0]
    approved = db.execute("SELECT COUNT(*) FROM enrollment_requests WHERE user_id=? AND status IN ('approuvee','inscrite')", (uid,)).fetchone()[0]
    completed_count = db.execute("SELECT COUNT(*) FROM completed_formations WHERE user_id=?", (uid,)).fetchone()[0]
    hours = db.execute("SELECT COALESCE(SUM(hours_completed),0) FROM completed_formations WHERE user_id=?", (uid,)).fetchone()[0]

    # Écarts de compétences
    gaps = db.execute("""
        SELECT c.name, jc.target_level,
               COALESCE(sa.declared_level, 1) as current_level,
               jc.target_level - COALESCE(sa.declared_level, 1) as gap
        FROM job_competences jc
        JOIN competences c ON jc.competence_id = c.id
        LEFT JOIN self_assessments sa ON sa.competence_id = jc.competence_id AND sa.user_id = ?
        WHERE jc.job_id = ?
        ORDER BY gap DESC
        LIMIT 5
    """, (uid, user['job_id'])).fetchall()

    # Dernières demandes
    recent_requests = db.execute("""
        SELECT er.*, f.title as formation_title
        FROM enrollment_requests er
        JOIN formations f ON er.formation_id = f.id
        WHERE er.user_id = ?
        ORDER BY er.created_at DESC LIMIT 5
    """, (uid,)).fetchall()

    # Notifications récentes
    notifs = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (uid,)).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card-grid">
        <div class="stat-card">
            <div class="label">Demandes en attente</div>
            <div class="value">{{ pending }}</div>
        </div>
        <div class="stat-card green">
            <div class="label">Formations approuvées</div>
            <div class="value">{{ approved }}</div>
        </div>
        <div class="stat-card amber">
            <div class="label">Formations terminées</div>
            <div class="value">{{ completed_count }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Heures réalisées</div>
            <div class="value">{{ hours|int }}h</div>
        </div>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
        <div class="card">
            <div class="card-header"><h3>📈 Écarts de compétences prioritaires</h3></div>
            {% if gaps %}
            {% for g in gaps %}
            <div class="skill-gap">
                <div class="name">{{ g.name }}</div>
                <div class="levels">
                    <span>{{ g.current_level }}/5</span>
                    <span>→</span>
                    <span>{{ g.target_level }}/5</span>
                </div>
                <span class="gap-indicator {% if g.gap <= 0 %}gap-ok{% elif g.gap == 1 %}gap-small{% else %}gap-large{% endif %}">
                    {% if g.gap <= 0 %}✓ OK{% elif g.gap == 1 %}Δ {{ g.gap }}{% else %}Δ {{ g.gap }}{% endif %}
                </span>
            </div>
            {% endfor %}
            <div style="margin-top:12px;"><a href="{{ url_for('self_assessment') }}" class="btn btn-outline btn-sm">Voir mon autoévaluation →</a></div>
            {% else %}
            <div class="empty-state"><p>Complétez votre autoévaluation pour voir vos écarts.</p></div>
            {% endif %}
        </div>

        <div class="card">
            <div class="card-header"><h3>📝 Dernières demandes</h3></div>
            {% if recent_requests %}
            <table>
                <tr><th>Formation</th><th>Statut</th><th>Date</th></tr>
                {% for r in recent_requests %}
                <tr>
                    <td>{{ r.formation_title }}</td>
                    <td><span class="badge badge-{{ 'pending' if r.status=='en_attente' else 'approved' if r.status in ('approuvee','inscrite') else 'completed' if r.status=='terminee' else 'rejected' if r.status=='refusee' else 'draft' }}">{{ r.status|replace('_',' ')|title }}</span></td>
                    <td style="font-size:0.8rem;">{{ r.created_at[:10] }}</td>
                </tr>
                {% endfor %}
            </table>
            {% else %}
            <div class="empty-state"><p>Aucune demande pour le moment.</p><a href="{{ url_for('catalogue') }}" class="btn btn-primary btn-sm">Découvrir le catalogue</a></div>
            {% endif %}
        </div>
    </div>

    {% if notifs %}
    <div class="card">
        <div class="card-header"><h3>🔔 Notifications récentes</h3></div>
        {% for n in notifs %}
        <div style="padding:8px 0; border-bottom:1px solid var(--gray-100); {% if not n.is_read %}font-weight:600;{% endif %}">
            <div style="font-size:0.85rem;">{{ n.title }}</div>
            <div style="font-size:0.8rem; color:var(--gray-500);">{{ n.message }}</div>
        </div>
        {% endfor %}
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Tableau de bord", active_page="dashboard",
                                  pending=pending, approved=approved, completed_count=completed_count,
                                  hours=hours, gaps=gaps, recent_requests=recent_requests, notifs=notifs)


# --- CATALOGUE ---
@app.route('/catalogue')
@login_required
def catalogue():
    db = get_db()
    theme = request.args.get('theme', '')
    fmt = request.args.get('format', '')
    difficulty = request.args.get('difficulty', '')
    search = request.args.get('search', '')

    query = """SELECT f.*, p.name as provider_name FROM formations f
               LEFT JOIN providers p ON f.provider_id = p.id WHERE f.is_active=1"""
    params = []
    if theme:
        query += " AND f.theme=?"
        params.append(theme)
    if fmt:
        query += " AND f.format=?"
        params.append(fmt)
    if difficulty:
        query += " AND f.difficulty=?"
        params.append(difficulty)
    if search:
        query += " AND (f.title LIKE ? OR f.description LIKE ? OR f.theme LIKE ?)"
        params.extend([f'%{search}%'] * 3)
    query += " ORDER BY f.title"
    formations = db.execute(query, params).fetchall()

    themes = db.execute("SELECT DISTINCT theme FROM formations WHERE is_active=1 ORDER BY theme").fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <form method="GET" class="filters">
            <div class="form-group">
                <label>Recherche</label>
                <input type="text" name="search" value="{{ search }}" placeholder="Mot-clé...">
            </div>
            <div class="form-group">
                <label>Thème</label>
                <select name="theme"><option value="">Tous</option>
                {% for t in themes %}<option value="{{ t.theme }}" {{ 'selected' if t.theme==theme_filter }}>{{ t.theme }}</option>{% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Format</label>
                <select name="format"><option value="">Tous</option>
                <option value="presentiel" {{ 'selected' if fmt=='presentiel' }}>Présentiel</option>
                <option value="e-learning" {{ 'selected' if fmt=='e-learning' }}>E-learning</option>
                <option value="blended" {{ 'selected' if fmt=='blended' }}>Blended</option>
                </select>
            </div>
            <div class="form-group">
                <label>Niveau</label>
                <select name="difficulty"><option value="">Tous</option>
                <option value="debutant" {{ 'selected' if difficulty=='debutant' }}>Débutant</option>
                <option value="intermediaire" {{ 'selected' if difficulty=='intermediaire' }}>Intermédiaire</option>
                <option value="avance" {{ 'selected' if difficulty=='avance' }}>Avancé</option>
                <option value="expert" {{ 'selected' if difficulty=='expert' }}>Expert</option>
                </select>
            </div>
            <div class="form-group"><label>&nbsp;</label><button type="submit" class="btn btn-primary">Filtrer</button></div>
            <div class="form-group"><label>&nbsp;</label><a href="{{ url_for('catalogue') }}" class="btn btn-outline">Réinitialiser</a></div>
        </form>
    </div>

    <div style="margin-bottom:12px; color:var(--gray-500); font-size:0.85rem;">{{ formations|length }} formation(s) trouvée(s)</div>

    <div class="card-grid">
    {% for f in formations %}
        <div class="formation-card">
            <div class="title">{{ f.title }}</div>
            <div class="meta">
                <span>{{ f.format|title }}</span>
                <span>{{ f.duration_hours }}h</span>
                <span>{{ f.cost|int }}€</span>
                <span>{{ f.difficulty|title }}</span>
                <span>{{ f.theme }}</span>
            </div>
            <div class="desc">{{ f.description }}</div>
            <div style="display:flex; gap:8px;">
                <a href="{{ url_for('formation_detail', fid=f.id) }}" class="btn btn-outline btn-sm">Voir détail</a>
                <a href="{{ url_for('request_enrollment', fid=f.id) }}" class="btn btn-primary btn-sm">Demander</a>
            </div>
        </div>
    {% endfor %}
    </div>

    {% if not formations %}
    <div class="empty-state"><div class="icon">📚</div><h3>Aucune formation trouvée</h3><p>Essayez d'autres critères de recherche.</p></div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Catalogue de formations", active_page="catalogue",
                                  formations=formations, themes=themes, theme_filter=theme, fmt=fmt,
                                  difficulty=difficulty, search=search)


# --- DÉTAIL FORMATION ---
@app.route('/formation/<int:fid>')
@login_required
def formation_detail(fid):
    db = get_db()
    f = db.execute("""SELECT f.*, p.name as provider_name, p.rating as provider_rating
                      FROM formations f LEFT JOIN providers p ON f.provider_id=p.id WHERE f.id=?""", (fid,)).fetchone()
    if not f:
        flash('Formation introuvable.', 'danger')
        return redirect(url_for('catalogue'))

    competences = db.execute("""SELECT c.name, c.category, fc.level_gain
                               FROM formation_competences fc JOIN competences c ON fc.competence_id=c.id
                               WHERE fc.formation_id=?""", (fid,)).fetchall()

    sessions = db.execute("SELECT * FROM sessions WHERE formation_id=? AND status='ouverte' ORDER BY start_date", (fid,)).fetchall()

    evals = db.execute("""SELECT AVG(satisfaction) as avg_sat, AVG(content_quality) as avg_cq,
                          AVG(relevance) as avg_rel, AVG(usefulness) as avg_use, COUNT(*) as cnt
                          FROM formation_evaluations WHERE formation_id=?""", (fid,)).fetchone()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <a href="{{ url_for('catalogue') }}" class="btn btn-outline btn-sm" style="margin-bottom:16px;">← Retour au catalogue</a>

    <div class="card">
        <h2 style="margin-bottom:8px;">{{ f.title }}</h2>
        <div style="display:flex; flex-wrap:wrap; gap:8px; margin-bottom:16px;">
            <span class="badge badge-completed">{{ f.format|title }}</span>
            <span class="badge badge-pending">{{ f.difficulty|title }}</span>
            <span class="badge" style="background:var(--gray-100);">{{ f.theme }}</span>
        </div>

        <div style="display:grid; grid-template-columns:2fr 1fr; gap:24px;">
            <div>
                <h4>Description</h4>
                <p style="margin-bottom:16px; color:var(--gray-700);">{{ f.description }}</p>

                <h4>Objectifs pédagogiques</h4>
                <p style="margin-bottom:16px; color:var(--gray-700);">{{ f.objectives }}</p>

                {% if f.prerequisites %}
                <h4>Prérequis</h4>
                <p style="margin-bottom:16px; color:var(--gray-700);">{{ f.prerequisites }}</p>
                {% endif %}

                <h4>Compétences développées</h4>
                {% for c in competences %}
                <div style="display:inline-block; margin:4px; padding:4px 12px; background:var(--primary-light); border-radius:20px; font-size:0.8rem;">
                    {{ c.name }} <span style="color:var(--secondary);">(+{{ c.level_gain }})</span>
                </div>
                {% endfor %}
            </div>
            <div>
                <div style="background:var(--gray-100); padding:20px; border-radius:var(--radius);">
                    <div style="margin-bottom:12px;"><strong>Durée :</strong> {{ f.duration_hours }}h</div>
                    <div style="margin-bottom:12px;"><strong>Coût :</strong> {{ f.cost|int }} €</div>
                    <div style="margin-bottom:12px;"><strong>Prestataire :</strong> {{ f.provider_name }}</div>
                    <div style="margin-bottom:12px;"><strong>Évaluation :</strong> {{ f.evaluation_mode }}</div>
                    <div style="margin-bottom:12px;"><strong>Public :</strong> {{ f.target_audience }}</div>
                    {% if evals and evals.cnt > 0 %}
                    <div style="margin-bottom:12px;"><strong>Note moyenne :</strong> {{ "%.1f"|format(evals.avg_sat) }}/5 ({{ evals.cnt }} avis)</div>
                    {% endif %}
                    <a href="{{ url_for('request_enrollment', fid=f.id) }}" class="btn btn-primary" style="width:100%; justify-content:center; margin-top:8px;">Demander cette formation</a>
                </div>
            </div>
        </div>
    </div>

    {% if sessions %}
    <div class="card">
        <div class="card-header"><h3>📅 Sessions disponibles</h3></div>
        <table>
            <tr><th>Date début</th><th>Date fin</th><th>Lieu</th><th>Places</th><th>Action</th></tr>
            {% for s in sessions %}
            <tr>
                <td>{{ s.start_date }}</td>
                <td>{{ s.end_date }}</td>
                <td>{{ s.location }}</td>
                <td>{{ s.current_participants }}/{{ s.max_participants }}</td>
                <td><a href="{{ url_for('request_enrollment', fid=f.id, sid=s.id) }}" class="btn btn-primary btn-sm">Choisir</a></td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title=f['title'], active_page="catalogue",
                                  f=f, competences=competences, sessions=sessions, evals=evals)


# --- DEMANDE D'INSCRIPTION ---
@app.route('/request/<int:fid>', methods=['GET','POST'])
@login_required
def request_enrollment(fid):
    db = get_db()
    user = get_current_user()
    f = db.execute("SELECT * FROM formations WHERE id=?", (fid,)).fetchone()
    if not f:
        flash('Formation introuvable.', 'danger')
        return redirect(url_for('catalogue'))

    sid = request.args.get('sid', type=int)
    sessions = db.execute("SELECT * FROM sessions WHERE formation_id=? AND status='ouverte' ORDER BY start_date", (fid,)).fetchall()

    if request.method == 'POST':
        session_id = request.form.get('session_id', type=int)
        motivation = request.form.get('motivation', '').strip()

        # Vérifier si demande existante
        existing = db.execute("SELECT id FROM enrollment_requests WHERE user_id=? AND formation_id=? AND status NOT IN ('refusee','annulee')",
                              (user['id'], fid)).fetchone()
        if existing:
            flash('Vous avez déjà une demande pour cette formation.', 'warning')
            return redirect(url_for('my_requests'))

        db.execute("""INSERT INTO enrollment_requests (user_id, formation_id, session_id, status, motivation)
                      VALUES (?,?,?,?,?)""", (user['id'], fid, session_id, 'en_attente', motivation))
        db.commit()

        # Notifier le manager
        if user['manager_id']:
            notify_user(user['manager_id'],
                        'Nouvelle demande de formation',
                        f"{user['first_name']} {user['last_name']} demande la formation \"{f['title']}\".",
                        '/manager/requests')

        log_action('enrollment_request', 'enrollment_requests', fid, f"Formation: {f['title']}")
        flash('Demande envoyée avec succès.', 'success')
        return redirect(url_for('my_requests'))

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <a href="{{ url_for('formation_detail', fid=f.id) }}" class="btn btn-outline btn-sm" style="margin-bottom:16px;">← Retour</a>

    <div class="card">
        <h3>Demande d'inscription</h3>
        <p style="color:var(--gray-500); margin-bottom:20px;">{{ f.title }} — {{ f.duration_hours }}h — {{ f.cost|int }} €</p>

        <form method="POST">
            <div class="form-group">
                <label>Session souhaitée</label>
                <select name="session_id" required>
                    <option value="">Sélectionnez une session</option>
                    {% for s in sessions %}
                    <option value="{{ s.id }}" {{ 'selected' if s.id == sid }}>
                        {{ s.start_date }} au {{ s.end_date }} — {{ s.location }} ({{ s.max_participants - s.current_participants }} places)
                    </option>
                    {% endfor %}
                </select>
            </div>
            <div class="form-group">
                <label>Motivation (facultatif)</label>
                <textarea name="motivation" rows="4" placeholder="Expliquez pourquoi cette formation vous serait utile..."></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Envoyer la demande</button>
        </form>
    </div>
    """)

    return render_template_string(template, page_title="Demande d'inscription", active_page="catalogue",
                                  f=f, sessions=sessions, sid=sid)


# --- MES DEMANDES ---
@app.route('/my-requests')
@login_required
def my_requests():
    db = get_db()
    uid = session['user_id']
    requests_list = db.execute("""
        SELECT er.*, f.title as formation_title, f.format, f.duration_hours, f.cost,
               s.start_date, s.end_date, s.location
        FROM enrollment_requests er
        JOIN formations f ON er.formation_id = f.id
        LEFT JOIN sessions s ON er.session_id = s.id
        WHERE er.user_id = ?
        ORDER BY er.created_at DESC
    """, (uid,)).fetchall()

    status_map = {
        'brouillon': ('badge-draft', 'Brouillon'),
        'en_attente': ('badge-pending', 'En attente'),
        'approuvee': ('badge-approved', 'Approuvée'),
        'refusee': ('badge-rejected', 'Refusée'),
        'inscrite': ('badge-enrolled', 'Inscrite'),
        'terminee': ('badge-completed', 'Terminée'),
        'annulee': ('badge-cancelled', 'Annulée'),
    }

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    {% if requests_list %}
    <div class="card">
        <div class="card-header">
            <h3>Mes demandes de formation ({{ requests_list|length }})</h3>
        </div>
        <table>
            <tr><th>Formation</th><th>Format</th><th>Session</th><th>Coût</th><th>Statut</th><th>Commentaire manager</th><th>Action</th></tr>
            {% for r in requests_list %}
            <tr>
                <td><a href="{{ url_for('formation_detail', fid=r.formation_id) }}">{{ r.formation_title }}</a></td>
                <td>{{ r.format|title }}</td>
                <td>{% if r.start_date %}{{ r.start_date }}{% else %}—{% endif %}</td>
                <td>{{ r.cost|int }} €</td>
                <td><span class="badge {{ status_map[r.status][0] }}">{{ status_map[r.status][1] }}</span></td>
                <td style="font-size:0.8rem; max-width:200px;">{{ r.manager_comment or '—' }}</td>
                <td>
                    {% if r.status == 'terminee' %}
                    <a href="{{ url_for('evaluate_formation', eid=r.id) }}" class="btn btn-outline btn-sm">Évaluer</a>
                    <a href="{{ url_for('certificate', eid=r.id) }}" class="btn btn-outline btn-sm">Attestation</a>
                    {% elif r.status == 'en_attente' %}
                    <a href="{{ url_for('cancel_request', eid=r.id) }}" class="btn btn-outline btn-sm" onclick="return confirm('Annuler cette demande ?')">Annuler</a>
                    {% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% else %}
    <div class="card empty-state">
        <div class="icon">📝</div>
        <h3>Aucune demande</h3>
        <p>Consultez le catalogue pour trouver une formation.</p>
        <a href="{{ url_for('catalogue') }}" class="btn btn-primary" style="margin-top:12px;">Voir le catalogue</a>
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Mes demandes", active_page="my_requests",
                                  requests_list=requests_list, status_map=status_map)

@app.route('/cancel-request/<int:eid>')
@login_required
def cancel_request(eid):
    db = get_db()
    er = db.execute("SELECT * FROM enrollment_requests WHERE id=? AND user_id=?", (eid, session['user_id'])).fetchone()
    if er and er['status'] == 'en_attente':
        db.execute("UPDATE enrollment_requests SET status='annulee', updated_at=CURRENT_TIMESTAMP WHERE id=?", (eid,))
        db.commit()
        flash('Demande annulée.', 'info')
    return redirect(url_for('my_requests'))


# --- MES FORMATIONS ---
@app.route('/my-formations')
@login_required
def my_formations():
    db = get_db()
    uid = session['user_id']

    completed = db.execute("""
        SELECT cf.*, f.title, f.format, f.duration_hours, f.theme
        FROM completed_formations cf
        JOIN formations f ON cf.formation_id = f.id
        WHERE cf.user_id = ?
        ORDER BY cf.completion_date DESC
    """, (uid,)).fetchall()

    total_hours = sum(c['hours_completed'] for c in completed)

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card-grid" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card green">
            <div class="label">Formations terminées</div>
            <div class="value">{{ completed|length }}</div>
        </div>
        <div class="stat-card">
            <div class="label">Heures réalisées</div>
            <div class="value">{{ total_hours|int }}h</div>
        </div>
        <div class="stat-card amber">
            <div class="label">Attestations</div>
            <div class="value">{{ completed|selectattr('certificate_id')|list|length }}</div>
        </div>
    </div>

    <div class="card">
        <div class="card-header"><h3>🎓 Historique de formation</h3></div>
        {% if completed %}
        <table>
            <tr><th>Formation</th><th>Format</th><th>Thème</th><th>Heures</th><th>Date</th><th>Attestation</th></tr>
            {% for c in completed %}
            <tr>
                <td>{{ c.title }}</td>
                <td>{{ c.format|title }}</td>
                <td>{{ c.theme }}</td>
                <td>{{ c.hours_completed|int }}h</td>
                <td>{{ c.completion_date }}</td>
                <td>{% if c.certificate_id %}<a href="{{ url_for('certificate', eid=c.enrollment_id) }}" class="btn btn-outline btn-sm">📄 {{ c.certificate_id }}</a>{% else %}—{% endif %}</td>
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <div class="empty-state"><div class="icon">🎓</div><h3>Pas encore de formation terminée</h3></div>
        {% endif %}
    </div>
    """)

    return render_template_string(template, page_title="Mes formations", active_page="my_formations",
                                  completed=completed, total_hours=total_hours)


# --- AUTOÉVALUATION ---
@app.route('/self-assessment', methods=['GET', 'POST'])
@login_required
def self_assessment():
    db = get_db()
    user = get_current_user()
    uid = user['id']

    if request.method == 'POST':
        for key, value in request.form.items():
            if key.startswith('comp_'):
                cid = int(key.replace('comp_', ''))
                level = int(value)
                existing = db.execute("SELECT id FROM self_assessments WHERE user_id=? AND competence_id=?", (uid, cid)).fetchone()
                if existing:
                    db.execute("UPDATE self_assessments SET declared_level=?, assessment_date=CURRENT_TIMESTAMP WHERE id=?",
                               (level, existing['id']))
                else:
                    db.execute("INSERT INTO self_assessments (user_id, competence_id, declared_level) VALUES (?,?,?)",
                               (uid, cid, level))
        db.commit()
        log_action('self_assessment', 'self_assessments', uid)
        flash('Autoévaluation enregistrée.', 'success')
        return redirect(url_for('self_assessment'))

    # Compétences du poste
    job_comps = db.execute("""
        SELECT c.id, c.name, c.category, jc.target_level, jc.is_critical,
               COALESCE(sa.declared_level, 0) as current_level
        FROM job_competences jc
        JOIN competences c ON jc.competence_id = c.id
        LEFT JOIN self_assessments sa ON sa.competence_id = c.id AND sa.user_id = ?
        WHERE jc.job_id = ?
        ORDER BY c.category, c.name
    """, (uid, user['job_id'])).fetchall()

    level_labels = {0: 'Non évalué', 1: 'Débutant', 2: 'Notions de base', 3: 'Autonome', 4: 'Avancé', 5: 'Expert'}

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="alert alert-info">
        <strong>ℹ️ Information :</strong> L'autoévaluation est un outil de dialogue entre vous et votre manager.
        Elle ne constitue pas une évaluation de performance. Les niveaux sont déclaratifs et indicatifs.
    </div>

    <div class="card">
        <div class="card-header">
            <h3>📈 Mes compétences — {{ user.job_title }}</h3>
            <span style="font-size:0.8rem; color:var(--gray-500);">Échelle : 1 (Débutant) → 5 (Expert)</span>
        </div>

        <form method="POST">
        {% for c in job_comps %}
        <div class="skill-gap">
            <div class="name">
                {{ c.name }}
                {% if c.is_critical %}<span style="color:var(--danger); font-size:0.7rem;">● Critique</span>{% endif %}
                <div style="font-size:0.75rem; color:var(--gray-500);">{{ c.category }}</div>
            </div>
            <div style="display:flex; align-items:center; gap:16px;">
                <div style="text-align:center;">
                    <div style="font-size:0.7rem; color:var(--gray-500);">Mon niveau</div>
                    <select name="comp_{{ c.id }}" style="padding:4px 8px; border-radius:4px; border:1px solid var(--gray-300);">
                        {% for i in range(1,6) %}
                        <option value="{{ i }}" {{ 'selected' if c.current_level==i }}>{{ i }} - {{ level_labels[i] }}</option>
                        {% endfor %}
                    </select>
                </div>
                <div style="text-align:center;">
                    <div style="font-size:0.7rem; color:var(--gray-500);">Cible</div>
                    <div style="font-size:1.1rem; font-weight:700; color:var(--primary);">{{ c.target_level }}</div>
                </div>
                <div>
                    {% set gap = c.target_level - (c.current_level if c.current_level > 0 else 1) %}
                    <span class="gap-indicator {% if gap <= 0 %}gap-ok{% elif gap == 1 %}gap-small{% else %}gap-large{% endif %}">
                        {% if gap <= 0 %}✓ Atteint{% elif gap == 1 %}Δ {{ gap }}{% else %}Δ {{ gap }}{% endif %}
                    </span>
                </div>
            </div>
        </div>
        {% endfor %}
        <div style="margin-top:16px;">
            <button type="submit" class="btn btn-primary">Enregistrer mon autoévaluation</button>
        </div>
        </form>
    </div>
    """)

    return render_template_string(template, page_title="Autoévaluation", active_page="self_assessment",
                                  user=user, job_comps=job_comps, level_labels=level_labels)


# --- RECOMMANDATIONS ---
@app.route('/recommendations')
@login_required
def recommendations():
    db = get_db()
    user = get_current_user()
    uid = user['id']

    # Calculer les écarts
    gaps = db.execute("""
        SELECT c.id as comp_id, c.name, jc.target_level,
               COALESCE(sa.declared_level, 1) as current_level,
               jc.target_level - COALESCE(sa.declared_level, 1) as gap,
               jc.is_critical
        FROM job_competences jc
        JOIN competences c ON jc.competence_id = c.id
        LEFT JOIN self_assessments sa ON sa.competence_id = c.id AND sa.user_id = ?
        WHERE jc.job_id = ? AND jc.target_level > COALESCE(sa.declared_level, 1)
        ORDER BY jc.is_critical DESC, (jc.target_level - COALESCE(sa.declared_level, 1)) DESC
    """, (uid, user['job_id'])).fetchall()

    # Formations déjà demandées
    already = [r['formation_id'] for r in db.execute(
        "SELECT formation_id FROM enrollment_requests WHERE user_id=? AND status NOT IN ('refusee','annulee')", (uid,)).fetchall()]

    # Recommander des formations pour chaque gap
    recs = []
    seen_formations = set()
    for g in gaps:
        formations = db.execute("""
            SELECT f.*, fc.level_gain, p.name as provider_name
            FROM formation_competences fc
            JOIN formations f ON fc.formation_id = f.id
            LEFT JOIN providers p ON f.provider_id = p.id
            WHERE fc.competence_id = ? AND f.is_active = 1
            ORDER BY fc.level_gain DESC, f.cost ASC
        """, (g['comp_id'],)).fetchall()

        for f in formations:
            if f['id'] not in seen_formations:
                seen_formations.add(f['id'])
                recs.append({
                    'formation': f,
                    'competence': g['name'],
                    'gap': g['gap'],
                    'is_critical': g['is_critical'],
                    'already_requested': f['id'] in already,
                    'reason': f"Réduit l'écart de {g['gap']} niveau(x) en « {g['name']} »"
                        + (" — compétence critique" if g['is_critical'] else ""),
                    'level_gain': f['level_gain'],
                })

    # Trier : critiques d'abord, puis par gap descendant
    recs.sort(key=lambda x: (-x['is_critical'], -x['gap']))

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="alert alert-info">
        <strong>ℹ️ Recommandations personnalisées</strong> — Ces suggestions sont basées sur les écarts entre votre autoévaluation
        et les compétences cibles de votre poste. Elles constituent une aide à la décision, pas une obligation.
        Discutez-en avec votre manager.
    </div>

    {% if recs %}
    <div style="margin-bottom:12px; font-size:0.85rem; color:var(--gray-500);">{{ recs|length }} formation(s) recommandée(s) pour réduire vos écarts de compétences</div>

    {% for r in recs %}
    <div class="card" style="border-left:4px solid {% if r.is_critical %}var(--danger){% else %}var(--primary){% endif %};">
        <div style="display:flex; justify-content:space-between; align-items:start;">
            <div>
                <h4 style="margin-bottom:4px;">{{ r.formation.title }}</h4>
                <div style="font-size:0.8rem; color:var(--gray-500); margin-bottom:8px;">{{ r.formation.provider_name }} — {{ r.formation.format|title }} — {{ r.formation.duration_hours }}h — {{ r.formation.cost|int }} €</div>
                <div style="font-size:0.85rem; margin-bottom:8px;">
                    <strong>Pourquoi ?</strong> {{ r.reason }}
                </div>
                <div style="display:flex; gap:8px; flex-wrap:wrap;">
                    <span class="badge badge-completed">Compétence : {{ r.competence }}</span>
                    <span class="badge {% if r.gap >= 2 %}badge-rejected{% else %}badge-pending{% endif %}">Écart : Δ{{ r.gap }}</span>
                    <span class="badge badge-approved">Gain : +{{ r.level_gain }}</span>
                    {% if r.is_critical %}<span class="badge badge-rejected">⚠ Critique</span>{% endif %}
                </div>
            </div>
            <div style="text-align:right;">
                {% if r.already_requested %}
                <span class="badge badge-pending">Déjà demandée</span>
                {% else %}
                <a href="{{ url_for('request_enrollment', fid=r.formation.id) }}" class="btn btn-primary btn-sm">Demander</a>
                {% endif %}
                <br><a href="{{ url_for('formation_detail', fid=r.formation.id) }}" class="btn btn-outline btn-sm" style="margin-top:6px;">Détail</a>
            </div>
        </div>
    </div>
    {% endfor %}
    {% else %}
    <div class="card empty-state">
        <div class="icon">🎯</div>
        <h3>Aucune recommandation</h3>
        <p>Complétez d'abord votre autoévaluation ou vos compétences sont au niveau cible.</p>
        <a href="{{ url_for('self_assessment') }}" class="btn btn-primary" style="margin-top:12px;">Faire mon autoévaluation</a>
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Recommandations", active_page="recommendations", recs=recs)


# --- MANAGER : DEMANDES ÉQUIPE ---
@app.route('/manager/requests', methods=['GET', 'POST'])
@role_required('manager', 'rh', 'admin')
def manager_requests():
    db = get_db()
    user = get_current_user()
    uid = user['id']

    if request.method == 'POST':
        eid = request.form.get('enrollment_id', type=int)
        action = request.form.get('action')
        comment = request.form.get('comment', '').strip()

        er = db.execute("SELECT er.*, u.first_name, u.last_name, f.title FROM enrollment_requests er JOIN users u ON er.user_id=u.id JOIN formations f ON er.formation_id=f.id WHERE er.id=?", (eid,)).fetchone()
        if er:
            new_status = 'approuvee' if action == 'approve' else 'refusee'
            db.execute("""UPDATE enrollment_requests SET status=?, manager_comment=?,
                         manager_decision_date=CURRENT_TIMESTAMP, decided_by=?, updated_at=CURRENT_TIMESTAMP
                         WHERE id=?""", (new_status, comment, uid, eid))

            # Si approuvée, mettre à jour le budget
            if new_status == 'approuvee':
                f = db.execute("SELECT cost FROM formations WHERE id=?", (er['formation_id'],)).fetchone()
                u_svc = db.execute("SELECT service_id FROM users WHERE id=?", (er['user_id'],)).fetchone()
                if f and u_svc:
                    db.execute("UPDATE budget_entries SET committed_budget = committed_budget + ? WHERE service_id=? AND year=2025",
                               (f['cost'], u_svc['service_id']))

            db.commit()
            status_label = 'approuvée' if new_status == 'approuvee' else 'refusée'
            notify_user(er['user_id'],
                        f'Demande {status_label}',
                        f'Votre demande pour "{er["title"]}" a été {status_label}.' + (f' Commentaire: {comment}' if comment else ''),
                        '/my-requests')
            log_action(f'enrollment_{action}', 'enrollment_requests', eid, f"Status: {new_status}")
            flash(f'Demande {status_label}.', 'success')
        return redirect(url_for('manager_requests'))

    # Récupérer les demandes de l'équipe
    if user['role'] in ('rh', 'admin'):
        pending = db.execute("""
            SELECT er.*, u.first_name, u.last_name, u.employee_id,
                   f.title as formation_title, f.cost, f.duration_hours, f.format,
                   s.name as service_name
            FROM enrollment_requests er
            JOIN users u ON er.user_id = u.id
            JOIN formations f ON er.formation_id = f.id
            LEFT JOIN services s ON u.service_id = s.id
            WHERE er.status = 'en_attente'
            ORDER BY er.created_at ASC
        """).fetchall()
    else:
        pending = db.execute("""
            SELECT er.*, u.first_name, u.last_name, u.employee_id,
                   f.title as formation_title, f.cost, f.duration_hours, f.format,
                   s.name as service_name
            FROM enrollment_requests er
            JOIN users u ON er.user_id = u.id
            JOIN formations f ON er.formation_id = f.id
            LEFT JOIN services s ON u.service_id = s.id
            WHERE u.manager_id = ? AND er.status = 'en_attente'
            ORDER BY er.created_at ASC
        """, (uid,)).fetchall()

    # Historique
    if user['role'] in ('rh', 'admin'):
        history = db.execute("""
            SELECT er.*, u.first_name, u.last_name, f.title as formation_title, f.cost
            FROM enrollment_requests er JOIN users u ON er.user_id=u.id
            JOIN formations f ON er.formation_id=f.id
            WHERE er.status IN ('approuvee','refusee','terminee')
            ORDER BY er.updated_at DESC LIMIT 20
        """).fetchall()
    else:
        history = db.execute("""
            SELECT er.*, u.first_name, u.last_name, f.title as formation_title, f.cost
            FROM enrollment_requests er JOIN users u ON er.user_id=u.id
            JOIN formations f ON er.formation_id=f.id
            WHERE u.manager_id=? AND er.status IN ('approuvee','refusee','terminee')
            ORDER BY er.updated_at DESC LIMIT 20
        """, (uid,)).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card-grid" style="grid-template-columns:repeat(3,1fr);">
        <div class="stat-card amber">
            <div class="label">En attente</div>
            <div class="value">{{ pending|length }}</div>
        </div>
        <div class="stat-card green">
            <div class="label">Approuvées récemment</div>
            <div class="value">{{ history|selectattr('status','equalto','approuvee')|list|length }}</div>
        </div>
        <div class="stat-card red">
            <div class="label">Refusées récemment</div>
            <div class="value">{{ history|selectattr('status','equalto','refusee')|list|length }}</div>
        </div>
    </div>

    <div class="card">
        <div class="card-header"><h3>⏳ Demandes en attente</h3></div>
        {% if pending %}
        {% for r in pending %}
        <div style="border:1px solid var(--gray-300); border-radius:var(--radius); padding:16px; margin-bottom:12px;">
            <div style="display:flex; justify-content:space-between; align-items:start;">
                <div>
                    <strong>{{ r.first_name }} {{ r.last_name }}</strong> ({{ r.employee_id }}) — {{ r.service_name }}
                    <h4 style="margin:6px 0;">{{ r.formation_title }}</h4>
                    <div style="font-size:0.8rem; color:var(--gray-500);">
                        {{ r.format|title }} — {{ r.duration_hours }}h — {{ r.cost|int }} €
                    </div>
                    {% if r.motivation %}
                    <div style="margin-top:8px; font-size:0.85rem; font-style:italic; color:var(--gray-700);">
                        "{{ r.motivation }}"
                    </div>
                    {% endif %}
                </div>
                <div style="font-size:0.8rem; color:var(--gray-500);">{{ r.created_at[:10] }}</div>
            </div>
            <form method="POST" style="margin-top:12px; display:flex; gap:8px; align-items:end; flex-wrap:wrap;">
                <input type="hidden" name="enrollment_id" value="{{ r.id }}">
                <div class="form-group" style="flex:1; margin-bottom:0;">
                    <label>Commentaire</label>
                    <input type="text" name="comment" placeholder="Motif de la décision (facultatif)">
                </div>
                <button type="submit" name="action" value="approve" class="btn btn-success btn-sm">✓ Approuver</button>
                <button type="submit" name="action" value="reject" class="btn btn-danger btn-sm">✕ Refuser</button>
            </form>
        </div>
        {% endfor %}
        {% else %}
        <div class="empty-state"><p>Aucune demande en attente.</p></div>
        {% endif %}
    </div>

    {% if history %}
    <div class="card">
        <div class="card-header"><h3>📋 Historique des décisions</h3></div>
        <table>
            <tr><th>Salarié</th><th>Formation</th><th>Coût</th><th>Statut</th><th>Commentaire</th></tr>
            {% for r in history %}
            <tr>
                <td>{{ r.first_name }} {{ r.last_name }}</td>
                <td>{{ r.formation_title }}</td>
                <td>{{ r.cost|int }} €</td>
                <td><span class="badge badge-{{ 'approved' if r.status=='approuvee' else 'rejected' if r.status=='refusee' else 'completed' }}">{{ r.status|replace('_',' ')|title }}</span></td>
                <td style="font-size:0.8rem;">{{ r.manager_comment or '—' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Demandes de l'équipe", active_page="manager_requests",
                                  pending=pending, history=history)


# --- COMPÉTENCES ÉQUIPE ---
@app.route('/team-skills')
@role_required('manager', 'rh', 'admin')
def team_skills():
    db = get_db()
    user = get_current_user()

    if user['role'] in ('rh', 'admin'):
        members = db.execute("""
            SELECT u.id, u.first_name, u.last_name, u.employee_id, j.title as job_title, s.name as service_name
            FROM users u LEFT JOIN jobs j ON u.job_id=j.id LEFT JOIN services s ON u.service_id=s.id
            WHERE u.role='salarie' ORDER BY s.name, u.last_name
        """).fetchall()
    else:
        members = db.execute("""
            SELECT u.id, u.first_name, u.last_name, u.employee_id, j.title as job_title, s.name as service_name
            FROM users u LEFT JOIN jobs j ON u.job_id=j.id LEFT JOIN services s ON u.service_id=s.id
            WHERE u.manager_id=? ORDER BY u.last_name
        """, (user['id'],)).fetchall()

    team_data = []
    for m in members:
        gaps = db.execute("""
            SELECT c.name, jc.target_level, COALESCE(sa.declared_level,1) as current_level,
                   jc.target_level - COALESCE(sa.declared_level,1) as gap, jc.is_critical
            FROM job_competences jc
            JOIN competences c ON jc.competence_id=c.id
            LEFT JOIN self_assessments sa ON sa.competence_id=c.id AND sa.user_id=?
            WHERE jc.job_id = (SELECT job_id FROM users WHERE id=?)
            ORDER BY jc.is_critical DESC, gap DESC
        """, (m['id'], m['id'])).fetchall()
        team_data.append({'member': m, 'gaps': gaps})

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header"><h3>👥 Compétences de l'équipe ({{ team_data|length }} membres)</h3></div>

        {% for td in team_data %}
        <details style="margin-bottom:12px; border:1px solid var(--gray-300); border-radius:6px;">
            <summary style="padding:12px; cursor:pointer; font-weight:600;">
                {{ td.member.first_name }} {{ td.member.last_name }} ({{ td.member.employee_id }})
                <span style="font-weight:400; color:var(--gray-500);">— {{ td.member.job_title }} — {{ td.member.service_name }}</span>
                {% set critical_gaps = td.gaps|selectattr('gap','gt',0)|selectattr('is_critical')|list %}
                {% if critical_gaps %}<span class="badge badge-rejected">{{ critical_gaps|length }} écart(s) critique(s)</span>{% endif %}
            </summary>
            <div style="padding:0 12px 12px;">
                {% if td.gaps %}
                {% for g in td.gaps %}
                <div class="skill-gap" style="margin-bottom:4px;">
                    <div class="name" style="font-size:0.85rem;">{{ g.name }}{% if g.is_critical %} <span style="color:var(--danger);">●</span>{% endif %}</div>
                    <div class="levels">{{ g.current_level }}/5 → {{ g.target_level }}/5</div>
                    <span class="gap-indicator {% if g.gap <= 0 %}gap-ok{% elif g.gap == 1 %}gap-small{% else %}gap-large{% endif %}">
                        {% if g.gap <= 0 %}✓{% else %}Δ{{ g.gap }}{% endif %}
                    </span>
                </div>
                {% endfor %}
                {% else %}
                <p style="color:var(--gray-500); font-size:0.85rem;">Autoévaluation non renseignée.</p>
                {% endif %}
            </div>
        </details>
        {% endfor %}
    </div>
    """)

    return render_template_string(template, page_title="Compétences de l'équipe", active_page="team_skills",
                                  team_data=team_data)


# --- ÉVALUATION À CHAUD ---
@app.route('/evaluate/<int:eid>', methods=['GET', 'POST'])
@login_required
def evaluate_formation(eid):
    db = get_db()
    uid = session['user_id']
    er = db.execute("""
        SELECT er.*, f.title FROM enrollment_requests er
        JOIN formations f ON er.formation_id=f.id
        WHERE er.id=? AND er.user_id=? AND er.status='terminee'
    """, (eid, uid)).fetchone()

    if not er:
        flash('Formation non trouvée ou non terminée.', 'danger')
        return redirect(url_for('my_requests'))

    # Check already evaluated
    existing = db.execute("SELECT id FROM formation_evaluations WHERE user_id=? AND formation_id=?",
                          (uid, er['formation_id'])).fetchone()
    if existing:
        flash('Vous avez déjà évalué cette formation.', 'info')
        return redirect(url_for('my_requests'))

    if request.method == 'POST':
        db.execute("""INSERT INTO formation_evaluations
            (user_id, formation_id, completed_formation_id, satisfaction, content_quality,
             relevance, animation_quality, usefulness, would_recommend, comment, eval_type)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (uid, er['formation_id'], eid,
             request.form.get('satisfaction', type=int),
             request.form.get('content_quality', type=int),
             request.form.get('relevance', type=int),
             request.form.get('animation_quality', type=int),
             request.form.get('usefulness', type=int),
             request.form.get('would_recommend', type=int),
             request.form.get('comment', ''),
             'chaud'))
        db.commit()
        flash('Merci pour votre évaluation !', 'success')
        return redirect(url_for('my_requests'))

    questions = [
        ('satisfaction', 'Satisfaction globale'),
        ('content_quality', 'Qualité du contenu'),
        ('relevance', 'Pertinence pour votre poste'),
        ('animation_quality', 'Qualité de l\'animation'),
        ('usefulness', 'Utilité perçue des acquis'),
        ('would_recommend', 'Recommanderiez-vous cette formation ?'),
    ]

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <h3>Évaluation : {{ er.title }}</h3>
        <p style="color:var(--gray-500); margin-bottom:20px;">Évaluation à chaud — votre retour est précieux pour améliorer nos formations.</p>

        <form method="POST">
            {% for key, label in questions %}
            <div class="form-group">
                <label>{{ label }}</label>
                <div style="display:flex; gap:12px;">
                    {% for i in range(1,6) %}
                    <label style="display:flex; align-items:center; gap:4px; cursor:pointer;">
                        <input type="radio" name="{{ key }}" value="{{ i }}" required> {{ i }}
                    </label>
                    {% endfor %}
                    <span style="font-size:0.75rem; color:var(--gray-500);">(1=Faible, 5=Excellent)</span>
                </div>
            </div>
            {% endfor %}
            <div class="form-group">
                <label>Commentaire (facultatif)</label>
                <textarea name="comment" rows="3" placeholder="Vos remarques..."></textarea>
            </div>
            <button type="submit" class="btn btn-primary">Envoyer mon évaluation</button>
        </form>
    </div>
    """)

    return render_template_string(template, page_title="Évaluation", active_page="my_requests",
                                  er=er, questions=questions)


# --- ATTESTATION ---
@app.route('/certificate/<int:eid>')
@login_required
def certificate(eid):
    db = get_db()
    uid = session['user_id']

    cf = db.execute("""
        SELECT cf.*, f.title, f.objectives, f.duration_hours, f.evaluation_mode,
               u.first_name, u.last_name, u.employee_id,
               p.name as provider_name
        FROM completed_formations cf
        JOIN formations f ON cf.formation_id = f.id
        JOIN users u ON cf.user_id = u.id
        LEFT JOIN providers p ON f.provider_id = p.id
        WHERE cf.enrollment_id = ? AND cf.user_id = ?
    """, (eid, uid)).fetchone()

    if not cf:
        flash('Attestation introuvable.', 'danger')
        return redirect(url_for('my_formations'))

    # Compétences de la formation
    comps = db.execute("""
        SELECT c.name FROM formation_competences fc
        JOIN competences c ON fc.competence_id = c.id
        WHERE fc.formation_id = ?
    """, (cf['formation_id'],)).fetchall()

    cert_html = f"""
    <!DOCTYPE html>
    <html><head><meta charset="UTF-8"><title>Attestation {cf['certificate_id']}</title>
    <style>
        body {{ font-family: 'Georgia', serif; margin:0; padding:40px; background:white; }}
        .cert {{ max-width:800px; margin:0 auto; border:3px solid #1a56db; padding:60px; position:relative; }}
        .cert::before {{ content:''; position:absolute; top:10px; left:10px; right:10px; bottom:10px; border:1px solid #dbeafe; }}
        .header {{ text-align:center; margin-bottom:40px; }}
        .logo {{ display:inline-block; width:60px; height:60px; background:#1a56db; border-radius:10px; color:white;
                 font-weight:700; font-size:1.5rem; line-height:60px; text-align:center; margin-bottom:12px; }}
        h1 {{ color:#1a56db; font-size:1.8rem; margin:8px 0; }}
        h2 {{ color:#374151; font-size:1.1rem; font-weight:400; }}
        .body {{ text-align:center; margin:30px 0; }}
        .name {{ font-size:1.5rem; font-weight:700; color:#111827; margin:8px 0; }}
        .formation {{ font-size:1.2rem; color:#1a56db; font-weight:600; margin:16px 0; }}
        .details {{ text-align:left; margin:30px 0; padding:20px; background:#f9fafb; border-radius:8px; }}
        .details p {{ margin:6px 0; font-size:0.9rem; color:#374151; }}
        .footer {{ text-align:center; margin-top:30px; font-size:0.8rem; color:#6b7280; }}
        .demo {{ background:#fee2e2; color:#991b1b; padding:8px; text-align:center; font-size:0.75rem; margin-top:20px; border-radius:4px; }}
        @media print {{ .demo {{ display:none; }} body {{ padding:20px; }} }}
        .btn {{ display:inline-block; padding:10px 20px; background:#1a56db; color:white; border-radius:6px; text-decoration:none; margin:10px; }}
    </style></head><body>
    <div style="text-align:center; margin-bottom:20px;">
        <button onclick="window.print()" class="btn" style="border:none; cursor:pointer; font-size:0.9rem;">🖨️ Imprimer / PDF</button>
        <a href="{url_for('my_formations')}" class="btn" style="background:#6b7280;">← Retour</a>
    </div>
    <div class="cert">
        <div class="header">
            <div class="logo">SF</div>
            <h1>ATTESTATION DE FORMATION</h1>
            <h2>SmartFactory — Développement des compétences</h2>
        </div>
        <div class="body">
            <p>Nous certifions que</p>
            <div class="name">{cf['first_name']} {cf['last_name']}</div>
            <p>Identifiant : {cf['employee_id']}</p>
            <p style="margin-top:20px;">a suivi avec succès la formation</p>
            <div class="formation">{cf['title']}</div>
        </div>
        <div class="details">
            <p><strong>Objectifs :</strong> {cf['objectives']}</p>
            <p><strong>Durée réalisée :</strong> {int(cf['hours_completed'])} heures</p>
            <p><strong>Date de réalisation :</strong> {cf['completion_date']}</p>
            <p><strong>Prestataire :</strong> {cf['provider_name'] or 'SmartFactory interne'}</p>
            <p><strong>Évaluation :</strong> {cf['evaluation_mode'] or 'N/A'}</p>
            <p><strong>Compétences visées :</strong> {', '.join(c['name'] for c in comps)}</p>
        </div>
        <div class="footer">
            <p>Attestation n° <strong>{cf['certificate_id']}</strong></p>
            <p>Date d'émission : {datetime.date.today().isoformat()}</p>
            <p>SmartFactory — Service Formation et Développement des Compétences</p>
        </div>
        <div class="demo">⚠️ DOCUMENT DE DÉMONSTRATION — Application pédagogique SmartSkills — Ne constitue pas un certificat officiel</div>
    </div>
    </body></html>
    """

    return cert_html


# --- TABLEAU DE BORD RH ---
@app.route('/rh/dashboard')
@role_required('rh', 'admin')
def rh_dashboard():
    db = get_db()

    total_employees = db.execute("SELECT COUNT(*) FROM users WHERE role='salarie'").fetchone()[0]
    formed = db.execute("SELECT COUNT(DISTINCT user_id) FROM completed_formations").fetchone()[0]
    total_hours = db.execute("SELECT COALESCE(SUM(hours_completed),0) FROM completed_formations").fetchone()[0]
    total_requests = db.execute("SELECT COUNT(*) FROM enrollment_requests").fetchone()[0]
    pending_requests = db.execute("SELECT COUNT(*) FROM enrollment_requests WHERE status='en_attente'").fetchone()[0]
    approved_requests = db.execute("SELECT COUNT(*) FROM enrollment_requests WHERE status IN ('approuvee','inscrite','terminee')").fetchone()[0]

    access_rate = round((formed / total_employees * 100), 1) if total_employees > 0 else 0
    approval_rate = round((approved_requests / total_requests * 100), 1) if total_requests > 0 else 0

    # Budget global
    budget = db.execute("SELECT COALESCE(SUM(total_budget),0) as total, COALESCE(SUM(committed_budget),0) as committed, COALESCE(SUM(consumed_budget),0) as consumed FROM budget_entries WHERE year=2025").fetchone()

    # Par thème
    by_theme = db.execute("""
        SELECT f.theme, COUNT(*) as cnt FROM enrollment_requests er
        JOIN formations f ON er.formation_id=f.id
        WHERE er.status NOT IN ('annulee','refusee')
        GROUP BY f.theme ORDER BY cnt DESC
    """).fetchall()

    # Par format
    by_format = db.execute("""
        SELECT f.format, COUNT(*) as cnt FROM enrollment_requests er
        JOIN formations f ON er.formation_id=f.id
        WHERE er.status NOT IN ('annulee','refusee')
        GROUP BY f.format ORDER BY cnt DESC
    """).fetchall()

    # Évaluations moyennes
    avg_evals = db.execute("""
        SELECT AVG(satisfaction) as sat, AVG(content_quality) as cq,
               AVG(relevance) as rel, AVG(usefulness) as use_val, COUNT(*) as cnt
        FROM formation_evaluations
    """).fetchone()

    # Écarts critiques
    critical_gaps = db.execute("""
        SELECT c.name, COUNT(DISTINCT sa.user_id) as employees_below, jc.target_level,
               AVG(sa.declared_level) as avg_level
        FROM job_competences jc
        JOIN competences c ON jc.competence_id=c.id
        JOIN self_assessments sa ON sa.competence_id=c.id
        WHERE jc.is_critical=1 AND sa.declared_level < jc.target_level
        GROUP BY c.id
        ORDER BY (jc.target_level - AVG(sa.declared_level)) DESC
        LIMIT 10
    """).fetchall()

    # Par service
    by_service = db.execute("""
        SELECT s.name, COUNT(DISTINCT cf.user_id) as formed,
               COUNT(DISTINCT u.id) as total,
               COALESCE(SUM(cf.hours_completed),0) as hours
        FROM services s
        LEFT JOIN users u ON u.service_id=s.id AND u.role='salarie'
        LEFT JOIN completed_formations cf ON cf.user_id=u.id
        GROUP BY s.id
        ORDER BY s.name
    """).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="alert alert-info">
        <strong>ℹ️ Tableau de bord de pilotage</strong> — Données de démonstration. Les indicateurs sont calculés
        sur les données fictives du système. En production, connecter au SIRH pour données réelles.
    </div>

    <div class="card-grid" style="grid-template-columns:repeat(4,1fr);">
        <div class="stat-card"><div class="label">Salariés formés</div><div class="value">{{ formed }}/{{ total_employees }}</div><div class="detail">Taux d'accès : {{ access_rate }}%</div></div>
        <div class="stat-card green"><div class="label">Heures réalisées</div><div class="value">{{ total_hours|int }}h</div></div>
        <div class="stat-card amber"><div class="label">Demandes en attente</div><div class="value">{{ pending_requests }}</div></div>
        <div class="stat-card"><div class="label">Taux de validation</div><div class="value">{{ approval_rate }}%</div><div class="detail">{{ approved_requests }}/{{ total_requests }} demandes</div></div>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
        <div class="card">
            <div class="card-header"><h3>💰 Budget formation 2025</h3></div>
            <div style="margin-bottom:12px;">
                <div style="display:flex; justify-content:space-between; margin-bottom:4px;">
                    <span>Consommé : {{ budget.consumed|int }} €</span>
                    <span>Total : {{ budget.total|int }} €</span>
                </div>
                <div class="progress-bar" style="height:14px;">
                    <div class="fill fill-green" style="width:{{ (budget.consumed/budget.total*100) if budget.total > 0 else 0 }}%;"></div>
                </div>
            </div>
            <div style="display:flex; justify-content:space-between; font-size:0.85rem; color:var(--gray-500);">
                <span>Engagé : {{ budget.committed|int }} €</span>
                <span>Restant : {{ (budget.total - budget.committed)|int }} €</span>
            </div>
            <p style="font-size:0.75rem; color:var(--gray-500); margin-top:8px;">
                Budget total = somme des budgets formation par service. Consommé = formations terminées. Engagé = formations approuvées.
            </p>
        </div>

        <div class="card">
            <div class="card-header"><h3>📊 Répartition par thème</h3></div>
            <div class="bar-chart">
                {% for t in by_theme %}
                <div class="bar-wrapper">
                    <div class="bar-value">{{ t.cnt }}</div>
                    <div class="bar" style="height:{{ (t.cnt / (by_theme[0].cnt if by_theme else 1)) * 150 }}px; background:hsl({{ loop.index0 * 40 }}, 60%, 55%);"></div>
                    <div class="bar-label">{{ t.theme[:12] }}</div>
                </div>
                {% endfor %}
            </div>
        </div>
    </div>

    <div style="display:grid; grid-template-columns:1fr 1fr; gap:20px;">
        <div class="card">
            <div class="card-header"><h3>⚠️ Compétences critiques — Écarts majeurs</h3></div>
            {% if critical_gaps %}
            {% for g in critical_gaps %}
            <div class="skill-gap">
                <div class="name">{{ g.name }}<div style="font-size:0.7rem; color:var(--gray-500);">{{ g.employees_below }} salarié(s) en dessous</div></div>
                <div class="levels">Moy: {{ "%.1f"|format(g.avg_level) }}/5 → Cible: {{ g.target_level }}/5</div>
                <span class="gap-indicator gap-large">Δ {{ "%.1f"|format(g.target_level - g.avg_level) }}</span>
            </div>
            {% endfor %}
            {% else %}
            <p style="color:var(--gray-500);">Pas d'écart critique identifié.</p>
            {% endif %}
        </div>

        <div class="card">
            <div class="card-header"><h3>🏢 Accès à la formation par service</h3></div>
            <table>
                <tr><th>Service</th><th>Formés</th><th>Effectif</th><th>Taux</th><th>Heures</th></tr>
                {% for s in by_service %}
                <tr>
                    <td>{{ s.name }}</td>
                    <td>{{ s.formed }}</td>
                    <td>{{ s.total }}</td>
                    <td>{{ "%.0f"|format(s.formed/s.total*100) if s.total > 0 else 0 }}%</td>
                    <td>{{ s.hours|int }}h</td>
                </tr>
                {% endfor %}
            </table>
            <p style="font-size:0.75rem; color:var(--gray-500); margin-top:8px;">
                Indicateur d'équité — à surveiller pour identifier d'éventuels déséquilibres d'accès.
            </p>
        </div>
    </div>

    {% if avg_evals and avg_evals.cnt > 0 %}
    <div class="card">
        <div class="card-header"><h3>⭐ Satisfaction moyenne des formations ({{ avg_evals.cnt }} évaluations)</h3></div>
        <div style="display:flex; gap:32px; flex-wrap:wrap;">
            <div style="text-align:center;"><div style="font-size:2rem; font-weight:700; color:var(--primary);">{{ "%.1f"|format(avg_evals.sat) }}</div><div style="font-size:0.8rem; color:var(--gray-500);">Satisfaction</div></div>
            <div style="text-align:center;"><div style="font-size:2rem; font-weight:700; color:var(--primary);">{{ "%.1f"|format(avg_evals.cq) }}</div><div style="font-size:0.8rem; color:var(--gray-500);">Contenu</div></div>
            <div style="text-align:center;"><div style="font-size:2rem; font-weight:700; color:var(--primary);">{{ "%.1f"|format(avg_evals.rel) }}</div><div style="font-size:0.8rem; color:var(--gray-500);">Pertinence</div></div>
            <div style="text-align:center;"><div style="font-size:2rem; font-weight:700; color:var(--primary);">{{ "%.1f"|format(avg_evals.use_val) }}</div><div style="font-size:0.8rem; color:var(--gray-500);">Utilité</div></div>
        </div>
        <p style="font-size:0.75rem; color:var(--gray-500); margin-top:8px;">
            Évaluation à chaud uniquement. Ne mesure pas l'acquisition réelle ni l'impact à long terme.
        </p>
    </div>
    {% endif %}
    """)

    return render_template_string(template, page_title="Tableau de bord RH", active_page="rh_dashboard",
                                  total_employees=total_employees, formed=formed, total_hours=total_hours,
                                  total_requests=total_requests, pending_requests=pending_requests,
                                  approved_requests=approved_requests, access_rate=access_rate,
                                  approval_rate=approval_rate, budget=budget, by_theme=by_theme,
                                  by_format=by_format, avg_evals=avg_evals, critical_gaps=critical_gaps,
                                  by_service=by_service)


# --- CARTOGRAPHIE DES COMPÉTENCES ---
@app.route('/skills-map')
@role_required('rh', 'admin')
def skills_map():
    db = get_db()

    skills = db.execute("""
        SELECT c.id, c.name, c.category,
               COUNT(DISTINCT sa.user_id) as assessed_count,
               AVG(sa.declared_level) as avg_level,
               COUNT(DISTINCT jc.job_id) as jobs_requiring,
               MAX(jc.is_critical) as is_critical,
               MAX(jc.target_level) as max_target
        FROM competences c
        LEFT JOIN self_assessments sa ON sa.competence_id=c.id
        LEFT JOIN job_competences jc ON jc.competence_id=c.id
        GROUP BY c.id
        ORDER BY c.category, c.name
    """).fetchall()

    categories = sorted(set(s['category'] for s in skills))

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="alert alert-info">
        <strong>🗺️ Cartographie des compétences</strong> — Vue consolidée basée sur les autoévaluations et les référentiels métiers.
        Données indicatives à croiser avec les observations managériales.
    </div>

    {% for cat in categories %}
    <div class="card">
        <div class="card-header"><h3>{{ cat }}</h3></div>
        <table>
            <tr><th>Compétence</th><th>Salariés évalués</th><th>Niveau moyen</th><th>Cible max</th><th>Critique</th><th>Écart</th></tr>
            {% for s in skills if s.category == cat %}
            <tr>
                <td><strong>{{ s.name }}</strong></td>
                <td>{{ s.assessed_count }}</td>
                <td>
                    {% if s.avg_level %}
                    <div class="progress-bar" style="width:100px; display:inline-block;">
                        <div class="fill fill-blue" style="width:{{ s.avg_level/5*100 }}%;"></div>
                    </div>
                    {{ "%.1f"|format(s.avg_level) }}/5
                    {% else %}—{% endif %}
                </td>
                <td>{{ s.max_target or '—' }}</td>
                <td>{% if s.is_critical %}<span class="badge badge-rejected">Critique</span>{% else %}—{% endif %}</td>
                <td>
                    {% if s.avg_level and s.max_target %}
                        {% set gap = s.max_target - s.avg_level %}
                        <span class="gap-indicator {% if gap <= 0 %}gap-ok{% elif gap <= 1 %}gap-small{% else %}gap-large{% endif %}">
                            {% if gap <= 0 %}✓{% else %}Δ {{ "%.1f"|format(gap) }}{% endif %}
                        </span>
                    {% else %}—{% endif %}
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    {% endfor %}
    """)

    return render_template_string(template, page_title="Cartographie des compétences", active_page="skills_map",
                                  skills=skills, categories=categories)


# --- GESTION DU CATALOGUE (RH) ---
@app.route('/manage/catalogue')
@role_required('rh', 'admin')
def manage_catalogue():
    db = get_db()
    formations = db.execute("""
        SELECT f.*, p.name as provider_name,
               (SELECT COUNT(*) FROM enrollment_requests er WHERE er.formation_id=f.id AND er.status NOT IN ('annulee','refusee')) as request_count
        FROM formations f LEFT JOIN providers p ON f.provider_id=p.id
        ORDER BY f.theme, f.title
    """).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header">
            <h3>⚙️ Gestion du catalogue ({{ formations|length }} formations)</h3>
            <a href="{{ url_for('add_formation') }}" class="btn btn-primary btn-sm">+ Ajouter une formation</a>
        </div>
        <table>
            <tr><th>Titre</th><th>Thème</th><th>Format</th><th>Durée</th><th>Coût</th><th>Prestataire</th><th>Demandes</th><th>Actif</th><th>Actions</th></tr>
            {% for f in formations %}
            <tr>
                <td>{{ f.title }}</td>
                <td>{{ f.theme }}</td>
                <td>{{ f.format|title }}</td>
                <td>{{ f.duration_hours }}h</td>
                <td>{{ f.cost|int }} €</td>
                <td>{{ f.provider_name }}</td>
                <td>{{ f.request_count }}</td>
                <td>{% if f.is_active %}<span class="badge badge-approved">Oui</span>{% else %}<span class="badge badge-cancelled">Non</span>{% endif %}</td>
                <td>
                    <a href="{{ url_for('toggle_formation', fid=f.id) }}" class="btn btn-outline btn-sm">
                        {{ 'Désactiver' if f.is_active else 'Activer' }}
                    </a>
                </td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """)

    return render_template_string(template, page_title="Gérer le catalogue", active_page="manage_catalogue",
                                  formations=formations)


@app.route('/manage/formation/add', methods=['GET', 'POST'])
@role_required('rh', 'admin')
def add_formation():
    db = get_db()
    if request.method == 'POST':
        db.execute("""INSERT INTO formations
            (title, description, objectives, format, duration_hours, cost, provider_id,
             difficulty, prerequisites, evaluation_mode, target_audience, theme)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (request.form['title'], request.form['description'], request.form['objectives'],
             request.form['format'], request.form.get('duration_hours', type=int),
             request.form.get('cost', type=float), request.form.get('provider_id', type=int),
             request.form['difficulty'], request.form.get('prerequisites', ''),
             request.form.get('evaluation_mode', ''), request.form.get('target_audience', ''),
             request.form['theme']))
        db.commit()
        flash('Formation ajoutée.', 'success')
        return redirect(url_for('manage_catalogue'))

    providers = db.execute("SELECT * FROM providers ORDER BY name").fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <h3>Ajouter une formation</h3>
        <form method="POST">
            <div class="form-row">
                <div class="form-group"><label>Titre*</label><input type="text" name="title" required></div>
                <div class="form-group"><label>Thème*</label><input type="text" name="theme" required placeholder="Ex: Digital, Management..."></div>
            </div>
            <div class="form-group"><label>Description</label><textarea name="description" rows="3"></textarea></div>
            <div class="form-group"><label>Objectifs pédagogiques</label><textarea name="objectives" rows="2"></textarea></div>
            <div class="form-row">
                <div class="form-group"><label>Format*</label>
                    <select name="format" required><option value="presentiel">Présentiel</option><option value="e-learning">E-learning</option><option value="blended">Blended</option></select>
                </div>
                <div class="form-group"><label>Durée (heures)*</label><input type="number" name="duration_hours" required min="1"></div>
                <div class="form-group"><label>Coût (€)*</label><input type="number" name="cost" required min="0" step="0.01"></div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Difficulté*</label>
                    <select name="difficulty" required><option value="debutant">Débutant</option><option value="intermediaire">Intermédiaire</option><option value="avance">Avancé</option><option value="expert">Expert</option></select>
                </div>
                <div class="form-group"><label>Prestataire</label>
                    <select name="provider_id"><option value="">—</option>{% for p in providers %}<option value="{{ p.id }}">{{ p.name }}</option>{% endfor %}</select>
                </div>
            </div>
            <div class="form-row">
                <div class="form-group"><label>Prérequis</label><input type="text" name="prerequisites"></div>
                <div class="form-group"><label>Évaluation</label><input type="text" name="evaluation_mode"></div>
                <div class="form-group"><label>Public cible</label><input type="text" name="target_audience"></div>
            </div>
            <button type="submit" class="btn btn-primary">Ajouter</button>
            <a href="{{ url_for('manage_catalogue') }}" class="btn btn-outline">Annuler</a>
        </form>
    </div>
    """)
    return render_template_string(template, page_title="Ajouter une formation", active_page="manage_catalogue",
                                  providers=providers)


@app.route('/manage/formation/toggle/<int:fid>')
@role_required('rh', 'admin')
def toggle_formation(fid):
    db = get_db()
    f = db.execute("SELECT is_active FROM formations WHERE id=?", (fid,)).fetchone()
    if f:
        db.execute("UPDATE formations SET is_active=? WHERE id=?", (0 if f['is_active'] else 1, fid))
        db.commit()
        flash('Statut mis à jour.', 'success')
    return redirect(url_for('manage_catalogue'))


# --- COMPLÉTER UNE FORMATION (RH) ---
@app.route('/manage/complete/<int:eid>', methods=['POST'])
@role_required('rh', 'admin')
def complete_formation(eid):
    db = get_db()
    er = db.execute("SELECT * FROM enrollment_requests WHERE id=? AND status='approuvee'", (eid,)).fetchone()
    if not er:
        flash('Demande non trouvable ou non approuvée.', 'danger')
        return redirect(url_for('manager_requests'))

    f = db.execute("SELECT * FROM formations WHERE id=?", (er['formation_id'],)).fetchone()
    cert_id = f"CERT-{datetime.date.today().year}-{secrets.token_hex(3).upper()}"

    db.execute("""INSERT INTO completed_formations
        (user_id, formation_id, session_id, enrollment_id, hours_completed, completion_date, certificate_id)
        VALUES (?,?,?,?,?,?,?)""",
        (er['user_id'], er['formation_id'], er['session_id'], eid, f['duration_hours'],
         datetime.date.today().isoformat(), cert_id))

    db.execute("UPDATE enrollment_requests SET status='terminee', updated_at=CURRENT_TIMESTAMP WHERE id=?", (eid,))

    # Budget consumed
    u_svc = db.execute("SELECT service_id FROM users WHERE id=?", (er['user_id'],)).fetchone()
    if u_svc:
        db.execute("UPDATE budget_entries SET consumed_budget = consumed_budget + ? WHERE service_id=? AND year=2025",
                   (f['cost'], u_svc['service_id']))

    db.commit()
    notify_user(er['user_id'], 'Formation terminée',
                f'Votre formation "{f["title"]}" est déclarée terminée. Attestation disponible.', '/my-formations')
    flash('Formation déclarée terminée.', 'success')
    return redirect(url_for('manager_requests'))


# --- BUDGET ---
@app.route('/budget')
@role_required('rh', 'admin')
def budget_view():
    db = get_db()
    budgets = db.execute("""
        SELECT be.*, s.name as service_name
        FROM budget_entries be
        JOIN services s ON be.service_id=s.id
        WHERE be.year=2025
        ORDER BY s.name
    """).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header"><h3>💰 Budget formation 2025 par service</h3></div>
        <table>
            <tr><th>Service</th><th>Budget total</th><th>Engagé</th><th>Consommé</th><th>Restant</th><th>Utilisation</th></tr>
            {% for b in budgets %}
            <tr>
                <td>{{ b.service_name }}</td>
                <td>{{ b.total_budget|int }} €</td>
                <td>{{ b.committed_budget|int }} €</td>
                <td>{{ b.consumed_budget|int }} €</td>
                <td>{{ (b.total_budget - b.committed_budget)|int }} €</td>
                <td>
                    <div class="progress-bar" style="width:120px;">
                        <div class="fill {% if b.committed_budget/b.total_budget > 0.9 %}fill-red{% elif b.committed_budget/b.total_budget > 0.7 %}fill-amber{% else %}fill-green{% endif %}"
                             style="width:{{ (b.committed_budget/b.total_budget*100) if b.total_budget > 0 else 0 }}%;"></div>
                    </div>
                    <span style="font-size:0.8rem;">{{ "%.0f"|format(b.committed_budget/b.total_budget*100) if b.total_budget > 0 else 0 }}%</span>
                </td>
            </tr>
            {% endfor %}
        </table>
        <p style="font-size:0.75rem; color:var(--gray-500); margin-top:12px;">
            Budget engagé = coût des formations approuvées. Budget consommé = formations terminées.
            Budget restant = total - engagé. Ces montants sont des données de démonstration.
        </p>
    </div>
    """)

    return render_template_string(template, page_title="Budget formation", active_page="budget", budgets=budgets)


# --- NOTIFICATIONS ---
@app.route('/notifications')
@login_required
def notifications_page():
    db = get_db()
    uid = session['user_id']
    notifs = db.execute("SELECT * FROM notifications WHERE user_id=? ORDER BY created_at DESC LIMIT 50", (uid,)).fetchall()

    # Marquer comme lues
    db.execute("UPDATE notifications SET is_read=1 WHERE user_id=? AND is_read=0", (uid,))
    db.commit()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header"><h3>🔔 Notifications</h3></div>
        {% if notifs %}
        {% for n in notifs %}
        <div style="padding:12px; border-bottom:1px solid var(--gray-100); {% if not n.is_read %}background:var(--primary-light);{% endif %}">
            <div style="display:flex; justify-content:space-between;">
                <strong style="font-size:0.9rem;">{{ n.title }}</strong>
                <span style="font-size:0.75rem; color:var(--gray-500);">{{ n.created_at[:16] }}</span>
            </div>
            <p style="font-size:0.85rem; color:var(--gray-700); margin-top:4px;">{{ n.message }}</p>
            {% if n.link %}<a href="{{ n.link }}" class="btn btn-outline btn-sm" style="margin-top:4px;">Voir →</a>{% endif %}
        </div>
        {% endfor %}
        {% else %}
        <div class="empty-state"><div class="icon">🔔</div><h3>Aucune notification</h3></div>
        {% endif %}
    </div>
    """)

    return render_template_string(template, page_title="Notifications", active_page="notifications", notifs=notifs)


# --- ADMIN : UTILISATEURS ---
@app.route('/admin/users')
@role_required('admin')
def admin_users():
    db = get_db()
    users = db.execute("""
        SELECT u.*, s.name as service_name, j.title as job_title
        FROM users u
        LEFT JOIN services s ON u.service_id=s.id
        LEFT JOIN jobs j ON u.job_id=j.id
        ORDER BY u.role, u.last_name
    """).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header"><h3>👤 Utilisateurs ({{ users|length }})</h3></div>
        <table>
            <tr><th>ID</th><th>Nom</th><th>Email</th><th>Rôle</th><th>Service</th><th>Métier</th></tr>
            {% for u in users %}
            <tr>
                <td>{{ u.employee_id }}</td>
                <td>{{ u.first_name }} {{ u.last_name }}</td>
                <td style="font-size:0.8rem;">{{ u.email }}</td>
                <td><span class="badge role-{{ u.role }}">{{ u.role|upper }}</span></td>
                <td>{{ u.service_name or '—' }}</td>
                <td>{{ u.job_title or '—' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """)

    return render_template_string(template, page_title="Gestion des utilisateurs", active_page="admin_users",
                                  users=users)


# --- ADMIN : JOURNAL D'AUDIT ---
@app.route('/admin/audit')
@role_required('admin')
def audit_logs():
    db = get_db()
    logs = db.execute("""
        SELECT al.*, u.employee_id, u.first_name, u.last_name
        FROM audit_log al
        LEFT JOIN users u ON al.user_id=u.id
        ORDER BY al.created_at DESC LIMIT 100
    """).fetchall()

    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <div class="card-header"><h3>📋 Journal d'audit (100 dernières actions)</h3></div>
        <table>
            <tr><th>Date</th><th>Utilisateur</th><th>Action</th><th>Entité</th><th>Détails</th><th>IP</th></tr>
            {% for l in logs %}
            <tr>
                <td style="font-size:0.8rem;">{{ l.created_at[:19] }}</td>
                <td>{{ l.first_name or '—' }} {{ l.last_name or '' }}</td>
                <td><span class="badge badge-completed">{{ l.action }}</span></td>
                <td>{{ l.entity_type or '—' }}</td>
                <td style="font-size:0.8rem; max-width:200px;">{{ l.details or '—' }}</td>
                <td style="font-size:0.8rem;">{{ l.ip_address or '—' }}</td>
            </tr>
            {% endfor %}
        </table>
    </div>
    """)

    return render_template_string(template, page_title="Journal d'audit", active_page="audit", logs=logs)


# --- RGPD ---
@app.route('/rgpd')
@login_required
def rgpd_info():
    template = LAYOUT_TEMPLATE.replace('{% block content %}{% endblock %}', """
    <div class="card">
        <h3>🔒 Protection des données personnelles — SmartSkills</h3>
        <p style="color:var(--gray-500); margin-bottom:20px;">
            Information relative au traitement de vos données dans le cadre de l'application SmartSkills.
            <strong>Application de démonstration pédagogique — toutes les données sont fictives.</strong>
        </p>

        <h4 style="margin-top:20px;">1. Responsable de traitement</h4>
        <p>SmartFactory SA (fictif) — Service Formation et Développement des Compétences</p>

        <h4 style="margin-top:20px;">2. Données traitées</h4>
        <ul>
            <li><strong>Identification :</strong> identifiant salarié (fictif), nom, prénom, email professionnel, service, métier</li>
            <li><strong>Formation :</strong> demandes d'inscription, historique, heures réalisées, attestations</li>
            <li><strong>Compétences :</strong> autoévaluations (déclaratives), niveaux cibles par poste</li>
            <li><strong>Évaluations :</strong> satisfaction à chaud des formations</li>
            <li><strong>Connexion :</strong> journaux d'accès (date, action, IP)</li>
        </ul>
        <p>Aucune donnée sensible (santé, opinions, origine) n'est collectée.</p>

        <h4 style="margin-top:20px;">3. Finalités</h4>
        <ul>
            <li>Gestion administrative des inscriptions et du suivi de formation</li>
            <li>Pilotage du plan de développement des compétences</li>
            <li>Identification des écarts de compétences pour accompagner les collaborateurs</li>
            <li>Production d'attestations de formation</li>
            <li>Pilotage budgétaire</li>
        </ul>

        <h4 style="margin-top:20px;">4. Base légale</h4>
        <p>Exécution du contrat de travail et obligations légales de l'employeur en matière de formation (articles L6312-1 et suivants du Code du travail).</p>

        <h4 style="margin-top:20px;">5. Destinataires</h4>
        <ul>
            <li><strong>Salarié :</strong> accès à ses propres données uniquement</li>
            <li><strong>Manager :</strong> accès aux demandes et compétences de son équipe directe</li>
            <li><strong>Service RH :</strong> accès aux données nécessaires au pilotage de la formation</li>
            <li><strong>Admin :</strong> accès technique pour maintenance, sans finalité RH</li>
        </ul>

        <h4 style="margin-top:20px;">6. Conservation (durées indicatives à valider avec le DPO)</h4>
        <ul>
            <li>Données de formation : durée de la relation contractuelle + 5 ans</li>
            <li>Autoévaluations : 3 ans glissants</li>
            <li>Évaluations à chaud : 2 ans</li>
            <li>Journaux d'accès : 12 mois</li>
            <li>Attestations : 10 ans (obligation légale de traçabilité)</li>
        </ul>

        <h4 style="margin-top:20px;">7. Vos droits</h4>
        <p>Conformément au RGPD, vous disposez d'un droit d'accès, de rectification, d'effacement (sous réserve des obligations légales),
        de limitation et de portabilité de vos données. Pour exercer ces droits : <strong>dpo@smartfactory.demo</strong></p>

        <h4 style="margin-top:20px;">8. Sécurité</h4>
        <ul>
            <li>Authentification par identifiant/mot de passe (en production : SSO + MFA)</li>
            <li>Gestion des rôles et permissions par profil</li>
            <li>Journalisation des accès et actions sensibles</li>
            <li>En production : chiffrement TLS, sauvegardes chiffrées, tests de pénétration</li>
        </ul>

        <h4 style="margin-top:20px;">9. IA et algorithmes</h4>
        <p>Le moteur de recommandation de SmartSkills utilise des règles explicites basées sur les écarts de compétences.
        Il ne prend aucune décision automatisée. Les recommandations sont des suggestions soumises à validation humaine.</p>
        <p>Aucun critère discriminant (âge, sexe, origine) n'est utilisé. Un contrôle humain et une possibilité de
        contestation sont prévus.</p>

        <div class="alert alert-warning" style="margin-top:20px;">
            <strong>⚠️ Avertissement :</strong> Cette page décrit les principes de protection des données appliqués dans le cadre
            de cette maquette pédagogique. La conformité effective d'un déploiement en production nécessiterait une analyse d'impact (AIPD),
            la validation du DPO, des contrats avec les sous-traitants et une architecture technique adaptée.
        </div>
    </div>
    """)

    return render_template_string(template, page_title="RGPD & Protection des données", active_page="rgpd")


# --- CHATBOT API ---
@app.route('/api/chat', methods=['POST'])
@login_required
def chat_api():
    data = request.get_json()
    message = data.get('message', '').lower().strip()
    db = get_db()

    # Réponses basées sur des règles
    if any(w in message for w in ['bonjour', 'salut', 'hello', 'hey']):
        resp = "Bonjour ! Je suis l'assistant SmartSkills. Comment puis-je vous aider ? 😊"

    elif any(w in message for w in ['demande', 'inscrire', 'inscription']):
        resp = """Pour demander une formation :<br>
        1. Consultez le <a href="/catalogue">catalogue</a><br>
        2. Cliquez sur une formation puis "Demander"<br>
        3. Choisissez une session et ajoutez votre motivation<br>
        4. Votre manager sera notifié pour validation.<br><br>
        Statuts possibles : en attente → approuvée → inscrite → terminée"""

    elif any(w in message for w in ['autoévaluation', 'auto-évaluation', 'évaluer', 'compétence']):
        resp = """L'<a href="/self-assessment">autoévaluation</a> vous permet d'estimer votre niveau sur les compétences de votre poste.<br><br>
        Échelle : 1 (Débutant) → 5 (Expert)<br><br>
        ⚠️ C'est un outil de dialogue avec votre manager, pas une mesure de performance.<br>
        Les écarts identifiés alimentent vos recommandations de formation."""

    elif any(w in message for w in ['recommandation', 'suggestion', 'parcours']):
        resp = """Les <a href="/recommendations">recommandations</a> sont calculées selon :<br>
        • Vos écarts de compétences (autoévaluation vs cible du poste)<br>
        • Les compétences critiques de votre métier<br>
        • Les formations disponibles dans le catalogue<br><br>
        Ce sont des suggestions, pas des obligations. Discutez-en avec votre manager."""

    elif any(w in message for w in ['statut', 'état', 'avancement']):
        resp = """Les statuts de demande sont :<br>
        • <strong>En attente</strong> : soumise, en attente de validation manager<br>
        • <strong>Approuvée</strong> : validée par le manager<br>
        • <strong>Refusée</strong> : non retenue (motif indiqué)<br>
        • <strong>Terminée</strong> : formation réalisée, attestation disponible<br>
        • <strong>Annulée</strong> : annulée par le salarié"""

    elif any(w in message for w in ['attestation', 'certificat', 'diplôme']):
        resp = """Les attestations sont générées automatiquement quand une formation est déclarée terminée.<br>
        Rendez-vous dans <a href="/my-formations">Mes formations</a> pour les télécharger.<br><br>
        ⚠️ Les attestations de démonstration ne sont pas des certificats officiels."""

    elif any(w in message for w in ['budget']):
        resp = "Le budget formation est géré par service. Votre manager et la DRH peuvent consulter le budget restant avant de valider une demande."

    elif any(w in message for w in ['rgpd', 'données', 'vie privée', 'confidentialité']):
        resp = """Vos données sont protégées. Consultez notre <a href="/rgpd">page RGPD</a> pour connaître :<br>
        • Les données collectées<br>• Les finalités<br>• Vos droits (accès, rectification, effacement)<br>
        Contact DPO : dpo@smartfactory.demo"""

    elif 'formation' in message and any(w in message for w in ['digital', 'numérique', 'data', 'python', 'ia']):
        formations = db.execute("SELECT title, duration_hours, cost FROM formations WHERE theme IN ('Digital','Cybersécurité') AND is_active=1").fetchall()
        if formations:
            items = ''.join(f"<br>• {f['title']} ({f['duration_hours']}h — {int(f['cost'])}€)" for f in formations)
            resp = f"Formations Digital/Cybersécurité disponibles :{items}<br><br><a href='/catalogue?theme=Digital'>Voir dans le catalogue →</a>"
        else:
            resp = "Aucune formation digitale trouvée actuellement."

    elif 'formation' in message and any(w in message for w in ['management', 'manager', 'leader']):
        formations = db.execute("SELECT title, duration_hours, cost FROM formations WHERE theme='Management' AND is_active=1").fetchall()
        if formations:
            items = ''.join(f"<br>• {f['title']} ({f['duration_hours']}h — {int(f['cost'])}€)" for f in formations)
            resp = f"Formations Management disponibles :{items}<br><br><a href='/catalogue?theme=Management'>Voir dans le catalogue →</a>"
        else:
            resp = "Aucune formation management trouvée."

    elif 'formation' in message or 'catalogue' in message:
        count = db.execute("SELECT COUNT(*) FROM formations WHERE is_active=1").fetchone()[0]
        resp = f"Le catalogue contient <strong>{count} formations</strong> actives.<br>Consultez le <a href='/catalogue'>catalogue complet</a> ou précisez un thème (ex: 'formations digital')."

    elif any(w in message for w in ['aide', 'help', 'comment']):
        resp = """Je peux vous aider sur :<br>
        • 📚 Le catalogue de formations<br>
        • 📝 Les demandes d'inscription<br>
        • 📈 L'autoévaluation des compétences<br>
        • 🎯 Les recommandations de parcours<br>
        • 📄 Les attestations<br>
        • 🔒 La protection des données<br><br>
        Posez-moi votre question !"""

    elif any(w in message for w in ['merci', 'thanks']):
        resp = "Avec plaisir ! N'hésitez pas si vous avez d'autres questions. 😊"

    else:
        resp = """Je ne suis pas sûr de comprendre votre question. 🤔<br><br>
        Essayez par exemple :<br>
        • "Comment faire une demande de formation ?"<br>
        • "Quelles formations en digital ?"<br>
        • "Qu'est-ce que l'autoévaluation ?"<br>
        • "Où trouver mes attestations ?"<br><br>
        Pour une question complexe, contactez la DRH : <strong>formation@smartfactory.demo</strong><br><br>
        <em>Note : je suis un assistant basé sur des réponses prédéfinies, pas un modèle d'IA générative.</em>"""

    return jsonify({'response': resp})


# --- API : Compléter une formation depuis le tableau manager (RH) ---
@app.route('/api/mark-complete', methods=['POST'])
@role_required('rh', 'admin')
def api_mark_complete():
    eid = request.form.get('enrollment_id', type=int)
    if eid:
        return complete_formation(eid)
    return redirect(url_for('manager_requests'))


# ==============================================================================
# INITIALISATION
# ==============================================================================

with app.app_context():
    init_db()
    seed_data()


# ==============================================================================
# DÉMARRAGE
# ==============================================================================

if __name__ == '__main__':
    print("""
    ╔══════════════════════════════════════════════════════════════╗
    ║                                                              ║
    ║   🏭 SmartSkills — SmartFactory                              ║
    ║   Plateforme de développement des compétences                ║
    ║                                                              ║
    ║   Application de démonstration pédagogique                   ║
    ║   Toutes les données sont fictives                           ║
    ║                                                              ║
    ║   🌐 Ouvrez http://127.0.0.1:5000 dans votre navigateur     ║
    ║                                                              ║
    ║   Comptes de démo (mot de passe: demo2025) :                 ║
    ║   • SF001 — Marie Dupont (Salarié)                           ║
    ║   • SF010 — Laurent Garcia (Manager)                         ║
    ║   • SF020 — Catherine Leroy (RH)                             ║
    ║   • SF099 — Admin Système (Admin)                            ║
    ║                                                              ║
    ╚══════════════════════════════════════════════════════════════╝
    """)
    app.run(debug=True, host='0.0.0.0', port=5000)