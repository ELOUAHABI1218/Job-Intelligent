import streamlit as st
import requests

# Configuration
API_BASE = "http://localhost:8001"

# Initialisation de la session
if "token" not in st.session_state:
    st.session_state.token = None
if "user_email" not in st.session_state:
    st.session_state.user_email = None

# Fonctions d'authentification
def login(email, password):
    resp = requests.post(f"{API_BASE}/login", json={"email": email, "password": password})
    if resp.status_code == 200:
        data = resp.json()
        st.session_state.token = data["access_token"]
        st.session_state.user_email = email
        return True
    return False

def register(email, password):
    resp = requests.post(f"{API_BASE}/register", json={"email": email, "password": password})
    return resp.status_code == 200

def get_preferences():
    if not st.session_state.token:
        return None
    headers = {"token": st.session_state.token}
    try:
        resp = requests.get(f"{API_BASE}/user/preferences", headers=headers)
        if resp.status_code == 200:
            return resp.json()
    except:
        pass
    return None

def update_preferences(prefs):
    headers = {"token": st.session_state.token, "Content-Type": "application/json"}
    resp = requests.put(f"{API_BASE}/user/preferences", json=prefs, headers=headers)
    return resp.status_code == 200

# Configuration de la page
st.set_page_config(page_title="JobMatcher", page_icon="🎯", layout="wide", initial_sidebar_state="collapsed")

# CSS personnalisé
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    * { font-family: 'Inter', sans-serif; }
    .auth-bg {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        z-index: -1;
    }
    .auth-card {
        background: rgba(255,255,255,0.95);
        border-radius: 24px;
        padding: 2rem;
        box-shadow: 0 20px 35px -10px rgba(0,0,0,0.3);
        backdrop-filter: blur(2px);
        max-width: 450px;
        margin: 2rem auto;
    }
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 20px;
        color: white;
        text-align: center;
        margin-bottom: 2rem;
        box-shadow: 0 10px 15px -3px rgba(0,0,0,0.1);
    }
    .card {
        background: white;
        border-radius: 16px;
        padding: 1.2rem;
        margin-bottom: 1rem;
        box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1);
        transition: transform 0.2s;
        border-left: 5px solid #667eea;
    }
    .card:hover { transform: translateY(-3px); box-shadow: 0 10px 25px -5px rgba(0,0,0,0.15); }
    .job-title { font-size: 1.2rem; font-weight: 700; color: #1f2937; margin-bottom: 0.5rem; }
    .company { color: #4b5563; font-weight: 600; margin-bottom: 0.5rem; }
    .badge {
        background: #e0e7ff; color: #4338ca; padding: 0.25rem 0.75rem; border-radius: 20px;
        font-size: 0.7rem; font-weight: 600; display: inline-block; margin-right: 0.5rem;
    }
    .skill-tag {
        background: #f3f4f6; color: #1f2937; padding: 0.2rem 0.6rem; border-radius: 30px;
        font-size: 0.7rem; font-weight: 500; display: inline-block; margin: 0.2rem 0.2rem;
    }
    .score { background: #10b981; color: white; border-radius: 20px; padding: 0.2rem 0.8rem; font-weight: 600; font-size: 0.7rem; display: inline-block; }
    .stButton > button { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; border: none; padding: 0.5rem; font-weight: 600; border-radius: 30px; width: 100%; }
    .stButton > button:hover { transform: scale(1.02); color: white; }
</style>
""", unsafe_allow_html=True)

# Gestion de l'authentification
if not st.session_state.token:
    st.markdown('<div class="auth-bg"></div>', unsafe_allow_html=True)
    st.markdown('<div class="auth-card">', unsafe_allow_html=True)
    st.title("🔐 JobMatcher")
    st.markdown("### Trouvez votre prochain défi Data")
    tab1, tab2 = st.tabs(["Connexion", "Inscription"])
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email")
            password = st.text_input("Mot de passe", type="password")
            if st.form_submit_button("Se connecter"):
                if login(email, password):
                    st.success("Connecté !")
                    st.rerun()
                else:
                    st.error("Identifiants incorrects")
    with tab2:
        with st.form("register_form"):
            email = st.text_input("Email")
            pwd = st.text_input("Mot de passe", type="password")
            confirm = st.text_input("Confirmer", type="password")
            if st.form_submit_button("S'inscrire"):
                if pwd != confirm:
                    st.error("Mots de passe différents")
                elif len(pwd) < 6:
                    st.error("Mot de passe trop court")
                elif register(email, pwd):
                    st.success("Compte créé ! Connectez-vous.")
                else:
                    st.error("Email déjà utilisé")
    st.markdown('</div>', unsafe_allow_html=True)
else:
    # Interface principale
    st.markdown('<div class="main-header"><h1>🎯 JobMatcher</h1><p>Recommandations personnalisées d\'offres Data</p></div>', unsafe_allow_html=True)
    col1, col2 = st.columns([3,1])
    with col1:
        st.markdown(f"**👋 Connecté en tant que {st.session_state.user_email}**")
    with col2:
        if st.button("Se déconnecter"):
            st.session_state.token = None
            st.session_state.user_email = None
            st.rerun()

    # Récupération des préférences
    prefs_data = get_preferences()
    if prefs_data:
        current_prefs = prefs_data.get("preferences") or {}
        notif_enabled = prefs_data.get("notifications_enabled", False)
    else:
        current_prefs = {}
        notif_enabled = False

    tab_search, tab_settings = st.tabs(["🔍 Recherche", "⚙️ Préférences"])
    
    with tab_search:
        with st.form("search_form"):
            col1, col2 = st.columns(2)
            with col1:
                competences_val = ", ".join(current_prefs.get("competences", [])) if current_prefs.get("competences") else "python, sql, spark"
                competences = st.text_input("Compétences (ex: python, sql, spark)", value=competences_val)
                ville = st.text_input("Ville", value=current_prefs.get("ville", ""))
            with col2:
                teletravail = st.checkbox("🏠 Télétravail", value=current_prefs.get("teletravail", False))
                type_contrat = st.selectbox("Contrat", ["", "CDI", "CDD", "Freelance", "Stage", "Alternance"],
                                            index=["", "CDI", "CDD", "Freelance", "Stage", "Alternance"].index(current_prefs.get("type_contrat", "")) if current_prefs.get("type_contrat") else 0)
                niveau_exp = st.selectbox("Expérience", ["", "Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5+ ans)"],
                                          index=["", "Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5+ ans)"].index(current_prefs.get("niveau_experience", "")) if current_prefs.get("niveau_experience") else 0)
            submitted = st.form_submit_button("🔍 Rechercher")
            if submitted:
                if competences.strip():
                    payload = {
                        "competences": [c.strip() for c in competences.split(",") if c.strip()],
                        "ville": ville or None,
                        "teletravail": teletravail,
                        "type_contrat": type_contrat or None,
                        "niveau_experience": niveau_exp or None,
                        "notifications_enabled": False
                    }
                    with st.spinner("Recherche..."):
                        try:
                            resp = requests.post(f"{API_BASE}/recommend", json=payload, timeout=10)
                            if resp.status_code == 200:
                                data = resp.json()
                                if data:
                                    st.success(f"🎉 {len(data)} offres trouvées")
                                    for job in data:
                                        st.markdown(f"""
                                        <div class="card">
                                            <div class="job-title">{job['titre']}</div>
                                            <div class="company">🏢 {job['entreprise']}</div>
                                            <div>
                                                <span class="badge">📍 {job['ville']}</span>
                                                <span class="badge">📄 {job['type_contrat']}</span>
                                                <span class="badge">🏠 {job['teletravail']}</span>
                                                <span class="score">⭐ Score: {job['score']}</span>
                                            </div>
                                            <div><strong>🔧 Compétences matchées :</strong><br>
                                            {''.join(f'<span class="skill-tag">{s}</span>' for s in job['competences_match'])}</div>
                                            <div style="margin-top:12px;"><a href="{job['url']}" target="_blank" style="color:#667eea; font-weight:600;">👉 Voir l'offre →</a></div>
                                        </div>
                                        """, unsafe_allow_html=True)
                                else:
                                    st.info("Aucune offre correspondante")
                            else:
                                st.error("Erreur API")
                        except Exception as e:
                            st.error(f"Erreur de connexion : {e}")
                else:
                    st.warning("Saisissez au moins une compétence")

    with tab_settings:
        with st.form("prefs_form"):
            competences_str = st.text_input("Mes compétences", value=", ".join(current_prefs.get("competences", [])))
            ville = st.text_input("Ville préférée", value=current_prefs.get("ville", ""))
            teletravail = st.checkbox("Accepter télétravail", value=current_prefs.get("teletravail", False))
            type_contrat = st.selectbox("Type de contrat", ["", "CDI", "CDD", "Freelance", "Stage", "Alternance"],
                                        index=["", "CDI", "CDD", "Freelance", "Stage", "Alternance"].index(current_prefs.get("type_contrat", "")) if current_prefs.get("type_contrat") else 0)
            niveau_exp = st.selectbox("Niveau d'expérience", ["", "Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5+ ans)"],
                                      index=["", "Junior (0-2 ans)", "Confirmé (3-5 ans)", "Senior (5+ ans)"].index(current_prefs.get("niveau_experience", "")) if current_prefs.get("niveau_experience") else 0)
            notifications = st.checkbox("📧 Recevoir des offres par email", value=notif_enabled)
            if st.form_submit_button("💾 Enregistrer"):
                prefs = {
                    "competences": [c.strip() for c in competences_str.split(",") if c.strip()],
                    "ville": ville or None,
                    "teletravail": teletravail,
                    "type_contrat": type_contrat or None,
                    "niveau_experience": niveau_exp or None,
                    "notifications_enabled": notifications
                }
                if update_preferences(prefs):
                    st.success("Préférences mises à jour !")
                else:
                    st.error("Erreur")