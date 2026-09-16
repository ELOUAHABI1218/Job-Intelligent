#  Job Intelligent — Dashboard Power BI

> *"Chaque jour, des milliers d'offres Data sont publiées... mais les candidats passent encore des heures à les chercher."*

**Job Intelligent** est une plateforme data engineering de bout en bout qui collecte, centralise et analyse des offres d'emploi (Data / IT) issues de plusieurs sources, puis propose un système de recommandation personnalisé basé sur le CV du candidat, le tout visualisé via un dashboard Power BI.



##  Architecture technique

<img width="717" height="402" alt="image" src="https://github.com/user-attachments/assets/9d21d3f2-a36d-451c-a948-e19847462f61" />


##  Collecte des données

Trois sources d'offres d'emploi sont exploitées :

| Source | Méthode | Description |
|---|---|---|
| **France Travail** | API officielle | Offres d'emploi françaises structurées au format JSON |
| **Adzuna** | API | Offres internationales orientées Data Engineering / IT |
| **Rekrute.ma** | Scraping (Selenium) | Pas d'API publique disponible → scraping automatisé |

**Fonctionnement technique du scraping/collecte :**
Connexion à la source → Extraction des données → Conversion en JSON → Stockage dans le Data Lake.

##  Data Lake

Le Data Lake repose sur **MinIO**, choisi car :
- il conserve les données historiques,
- il s'intègre facilement avec les outils Big Data (Python, Airflow, Spark...),
- il fonctionne comme un vrai cloud storage professionnel.

**Architecture en trois couches (médaillon) :**

| Couche | Contenu | Rôle |
|---|---|---|
| 🥉 **Bronze** | Données brutes | Données originales telles qu'elles arrivent des APIs et scrapers |
| 🥈 **Silver** | Données nettoyées | Données préparées et standardisées |
| 🥇 **Gold** | Données analytiques | Prêtes pour Power BI, reporting, KPIs, visualisation, recommandation |

## 🏭 Data Warehouse & ETL

### Data Warehouse (MySQL)

Caractéristiques :
- Orienté sujet
- Intégré
- Non volatile
- Évolutif dans le temps

### Modélisation : schéma en étoile

- **Table de faits** : `fact_offres` (offre_id, source_id, date_scraped_id, date_publie_id, localisation_id, contrat_id, nb_competences, est_active...)
- **Dimensions** : `dim_date`, `dim_localisation`, `dim_source`, `dim_contrat`, `dim_competence`, `dim_offre_details`

**Avantages :** simplicité des requêtes, performances rapides pour les agrégations, grande flexibilité pour ajouter de nouvelles dimensions.

### Pipeline ETL

1. **Extraction**
2. **Transformation**
3. **Chargement**

## 🔄 Orchestration (Apache Airflow)

**DAG principal :** `job_intelligent_pipeline_simplified`
<img width="1206" height="305" alt="image" src="https://github.com/user-attachments/assets/d4afdc13-9d93-4e58-8383-d67c6c0bcc79" />

| Aspect | Détail |
|---|---|
| Planification | Quotidienne à 6h00 UTC |
| Gestion des erreurs | 2 retries, timeouts |
| Ordonnancement | Les 3 tâches de scraping s'exécutent en parallèle |

## 🎯 Système de recommandation
<img width="857" height="474" alt="image" src="https://github.com/user-attachments/assets/629439a2-1e11-48ec-8795-e8304750b343" />

Le candidat peut soumettre son profil via un formulaire, un CV (upload) ou son compte utilisateur → **FastAPI** → **MySQL** → calcul du score → affichage des offres recommandées sur l'interface **Flask** (+ notifications par e-mail).

### Traitement d'un CV avec NLP
1. Extraction du texte (PyPDF2 / python-docx)
2. Nettoyage (minuscules, ponctuation, espaces inutiles)
3. Analyse NLP avec **spaCy**
4. Détection des compétences
5. Construction du profil
6. Recommandation

### Formule de scoring

```
Score = (Compétences_match × 10)
      + (Ville_identique ? 20 : 0)
      + (Télétravail_accepté ? 15 : 0)
      + (Contrat_identique ? 10 : 0)
      + (Expérience_identique ? 5 : 0)
```

**Exemple :** Profil `[python, sql]` — Casablanca — Télétravail Oui — CDI — Confirmé
→ 2 compétences (20) + ville (20) + télétravail (15) + contrat (10) + expérience (5) = **70 points**

## 📊 Visualisation

Dashboard interactif sous **Power BI Desktop** exploitant les données de la couche Gold (KPIs, tendances par source, compétences les plus demandées, répartition géographique, etc.).

## 🛠️ Stack technique

- **Langage :** Python
- **Scraping :** Selenium
- **Stockage / Data Lake :** MinIO
- **Base de données / Data Warehouse :** MySQL
- **Orchestration :** Apache Airflow
- **API :** FastAPI
- **NLP :** spaCy
- **Interface web :** Flask
- **Conteneurisation :** Docker
- **Visualisation :** Power BI
- **Notifications :** Gmail (SMTP)

⚙️ Installation

Clone the repository:

git clone https://github.com/YOUR_USERNAME/job-intelligent.git
cd job-intelligent

Create a virtual environment:

python -m venv venv

Activate it on Windows:

venv\Scripts\activate

Install dependencies:

pip install -r requirements.txt
🔐 Environment Variables

Create a .env file based on .env.example.

Example:

DATABASE_HOST=
DATABASE_PORT=
DATABASE_NAME=
DATABASE_USER=
DATABASE_PASSWORD=

KAFKA_BOOTSTRAP_SERVERS=

API_KEY=

## ✅ Conclusion

Ce projet a permis de mettre en pratique des compétences en Data Engineering, NLP, visualisation de données et architecture distribuée, à travers une solution concrète répondant à un besoin réel du marché de l'emploi.

---

*Projet réalisé dans le cadre académique — ENSAH*
