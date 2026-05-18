import os
import json
import bcrypt
import jwt
import tempfile
import shutil
from datetime import datetime, timedelta
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from PyPDF2 import PdfReader
from docx import Document
import spacy

# Chargement des variables d'environnement
from dotenv import load_dotenv
load_dotenv()

# Configuration MySQL
MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = os.getenv("MYSQL_PORT", "3308")
MYSQL_USER = os.getenv("MYSQL_USER", "jobs_user")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "jobspassword")
MYSQL_DB = os.getenv("MYSQL_DATABASE", "jobs_db")

engine = create_engine(f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PASSWORD}@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}")

# JWT
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "votre_secret_tres_long_a_changer")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 1

# Modèles Pydantic
class UserRegister(BaseModel):
    email: str
    password: str

class UserLogin(BaseModel):
    email: str
    password: str

class UserPreferences(BaseModel):
    competences: List[str]
    ville: Optional[str] = None
    teletravail: bool = False
    type_contrat: Optional[str] = None
    niveau_experience: Optional[str] = None
    notifications_enabled: bool = False

class JobRecommendation(BaseModel):
    offre_id: int
    titre: str
    entreprise: str
    ville: str
    type_contrat: str
    teletravail: str
    competences_match: List[str]
    score: float
    url: str

# Application FastAPI
app = FastAPI(title="Job Recommendation API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5000", "http://localhost:8501", "http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# NLP
nlp = spacy.load("fr_core_news_md")
SKILLS_KEYWORDS = [
    "python", "sql", "java", "scala", "spark", "hadoop", "kafka", "airflow",
    "aws", "azure", "gcp", "docker", "kubernetes", "pandas", "numpy", "tensorflow",
    "pytorch", "scikit-learn", "tableau", "power bi", "git", "ci/cd", "etl", "big data"
]

def extract_text_from_pdf(file_path: str) -> str:
    reader = PdfReader(file_path)
    return "".join(page.extract_text() or "" for page in reader.pages)

def extract_text_from_docx(file_path: str) -> str:
    doc = Document(file_path)
    return "\n".join(para.text for para in doc.paragraphs)

def extract_skills_from_text(text: str) -> List[str]:
    doc = nlp(text.lower())
    found = {token.text for token in doc if token.text in SKILLS_KEYWORDS}
    return list(found)

def get_current_user(token: str = Header(...)):
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        if not user_id:
            raise HTTPException(status_code=401, detail="Token invalide")
        with engine.connect() as conn:
            user = conn.execute(
                text("SELECT id, email, preferences, notifications_enabled FROM users WHERE id = :id"),
                {"id": user_id}
            ).fetchone()
            if not user:
                raise HTTPException(status_code=401, detail="Utilisateur introuvable")
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expiré")
    except Exception:
        raise HTTPException(status_code=401, detail="Token invalide")

# Endpoints d'authentification
@app.post("/register")
def register(user: UserRegister):
    with engine.connect() as conn:
        existing = conn.execute(text("SELECT id FROM users WHERE email = :email"), {"email": user.email}).fetchone()
        if existing:
            raise HTTPException(status_code=400, detail="Email déjà utilisé")
        hashed = bcrypt.hashpw(user.password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        conn.execute(
            text("INSERT INTO users (email, password_hash) VALUES (:email, :pwd)"),
            {"email": user.email, "pwd": hashed}
        )
        conn.commit()
    return {"message": "Utilisateur créé avec succès"}

@app.post("/login")
def login(user: UserLogin):
    with engine.connect() as conn:
        result = conn.execute(
            text("SELECT id, password_hash FROM users WHERE email = :email"),
            {"email": user.email}
        ).fetchone()
        if not result:
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
        if not bcrypt.checkpw(user.password.encode('utf-8'), result.password_hash.encode('utf-8')):
            raise HTTPException(status_code=401, detail="Email ou mot de passe incorrect")
        token = jwt.encode(
            {"user_id": result.id, "exp": datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)},
            SECRET_KEY,
            algorithm=ALGORITHM
        )
        return {"access_token": token, "token_type": "bearer"}

@app.get("/user/preferences")
def get_preferences(current_user=Depends(get_current_user)):
    prefs = current_user.preferences if current_user.preferences else {}
    notif = bool(current_user.notifications_enabled)
    return {"preferences": prefs, "notifications_enabled": notif}

@app.put("/user/preferences")
def update_preferences(prefs: UserPreferences, current_user=Depends(get_current_user)):
    with engine.connect() as conn:
        conn.execute(
            text("UPDATE users SET preferences = :prefs, notifications_enabled = :notif WHERE id = :id"),
            {"prefs": json.dumps(prefs.dict()), "notif": prefs.notifications_enabled, "id": current_user.id}
        )
        conn.commit()
    return {"message": "Préférences mises à jour"}

# Endpoint de recommandation (avec log dans l'historique)
@app.post("/recommend", response_model=List[JobRecommendation])
def recommend(profile: UserPreferences, limit: int = 10, token: Optional[str] = Header(None)):
    current_user = None
    if token:
        try:
            current_user = get_current_user(token)
        except:
            pass
    with engine.connect() as conn:
        sql_offres = """
            SELECT f.offre_id, d.titre, d.entreprise, d.url, l.ville, l.teletravail,
                   c.type_contrat, c.niveau_experience
            FROM fact_offres f
            JOIN dim_offre_detail d ON f.offre_id = d.offre_id
            JOIN dim_localisation l ON f.localisation_id = l.localisation_id
            JOIN dim_contrat c ON f.contrat_id = c.contrat_id
            WHERE f.est_active = TRUE
        """
        offres = conn.execute(text(sql_offres)).fetchall()
        sql_comp = """
            SELECT offre_id, nom
            FROM fact_offre_competence fc
            JOIN dim_competence c ON fc.competence_id = c.competence_id
        """
        comp_par_offre = {}
        for row in conn.execute(text(sql_comp)):
            comp_par_offre.setdefault(row.offre_id, []).append(row.nom)
        results = []
        for offre in offres:
            score = 0
            comps_offre = comp_par_offre.get(offre.offre_id, [])
            communs = set(profile.competences) & set(comps_offre)
            score += len(communs) * 10
            if profile.ville and offre.ville and offre.ville.lower() == profile.ville.lower():
                score += 20
            if profile.teletravail and offre.teletravail and offre.teletravail.lower() == "oui":
                score += 15
            if profile.type_contrat and offre.type_contrat == profile.type_contrat:
                score += 10
            if profile.niveau_experience and offre.niveau_experience == profile.niveau_experience:
                score += 5
            if score > 0:
                results.append({
                    "offre_id": offre.offre_id,
                    "titre": offre.titre,
                    "entreprise": offre.entreprise,
                    "ville": offre.ville or "Non précisée",
                    "type_contrat": offre.type_contrat or "Non précisé",
                    "teletravail": offre.teletravail or "Non",
                    "competences_match": list(communs),
                    "score": score,
                    "url": offre.url
                })
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]
        # Log dans l'historique si utilisateur connecté
        if current_user:
            conn.execute(
                text("""
                    INSERT INTO user_history (user_id, search_criteria, results_count)
                    VALUES (:uid, :criteria, :count)
                """),
                {
                    "uid": current_user.id,
                    "criteria": json.dumps(profile.dict()),
                    "count": len(results)
                }
            )
            conn.commit()
        return results

@app.post("/recommend_from_cv", response_model=List[JobRecommendation])
async def recommend_from_cv(
    file: UploadFile = File(...),
    ville: Optional[str] = Form(None),
    teletravail: bool = Form(False),
    type_contrat: Optional[str] = Form(None),
    niveau_experience: Optional[str] = Form(None),
    limit: int = Form(10),
    token: Optional[str] = Header(None)
):
    suffix = os.path.splitext(file.filename)[1]
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name
    try:
        if file.filename.endswith(".pdf"):
            text = extract_text_from_pdf(tmp_path)
        elif file.filename.endswith(".docx"):
            text = extract_text_from_docx(tmp_path)
        else:
            raise HTTPException(status_code=400, detail="Format non supporté")
    finally:
        os.unlink(tmp_path)
    competences = extract_skills_from_text(text)
    if not competences:
        raise HTTPException(status_code=400, detail="Aucune compétence technique reconnue")
    profile = UserPreferences(
        competences=competences,
        ville=ville,
        teletravail=teletravail,
        type_contrat=type_contrat,
        niveau_experience=niveau_experience,
        notifications_enabled=False
    )
    return recommend(profile, limit, token)

# Nouveaux endpoints
@app.get("/user/history")
def get_user_history(current_user=Depends(get_current_user), limit: int = 20):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT searched_at, search_criteria, results_count
                FROM user_history
                WHERE user_id = :uid
                ORDER BY searched_at DESC
                LIMIT :limit
            """),
            {"uid": current_user.id, "limit": limit}
        ).fetchall()
    return [
        {
            "searched_at": row.searched_at.isoformat(),
            "search_criteria": json.loads(row.search_criteria),
            "results_count": row.results_count
        }
        for row in rows
    ]

@app.get("/stats/offers_per_day")
def offers_per_day(days: int = 30):
    with engine.connect() as conn:
        rows = conn.execute(
            text("""
                SELECT d.date_complete, COUNT(*) AS nb
                FROM fact_offres f
                JOIN dim_date d ON f.date_scraped_id = d.date_id
                WHERE d.date_complete >= DATE_SUB(CURDATE(), INTERVAL :days DAY)
                GROUP BY d.date_complete
                ORDER BY d.date_complete
            """),
            {"days": days}
        ).fetchall()
    return [{"date": str(row.date_complete), "count": row.nb} for row in rows]

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)