import streamlit as st
import pandas as pd
import firebase_admin
from firebase_admin import credentials, db
import json
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Function to get Firebase credentials
def get_firebase_credentials():
    if os.getenv("FIREBASE_TYPE"):
        return {
            "type": os.getenv("FIREBASE_TYPE"),
            "project_id": os.getenv("FIREBASE_PROJECT_ID"),
            "private_key_id": os.getenv("FIREBASE_PRIVATE_KEY_ID"),
            "private_key": os.getenv("FIREBASE_PRIVATE_KEY").replace('\\n', '\n'),
            "client_email": os.getenv("FIREBASE_CLIENT_EMAIL"),
            "client_id": os.getenv("FIREBASE_CLIENT_ID"),
            "auth_uri": os.getenv("FIREBASE_AUTH_URI"),
            "token_uri": os.getenv("FIREBASE_TOKEN_URI"),
            "auth_provider_x509_cert_url": os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL"),
            "client_x509_cert_url": os.getenv("FIREBASE_CLIENT_X509_CERT_URL")
        }
    else:
        return {
            "type": st.secrets["firebase"]["type"],
            "project_id": st.secrets["firebase"]["project_id"],
            "private_key_id": st.secrets["firebase"]["private_key_id"],
            "private_key": st.secrets["firebase"]["private_key"],
            "client_email": st.secrets["firebase"]["client_email"],
            "client_id": st.secrets["firebase"]["client_id"],
            "auth_uri": st.secrets["firebase"]["auth_uri"],
            "token_uri": st.secrets["firebase"]["token_uri"],
            "auth_provider_x509_cert_url": st.secrets["firebase"]["auth_provider_x509_cert_url"],
            "client_x509_cert_url": st.secrets["firebase"]["client_x509_cert_url"]
        }

# Function to get Firebase database URL
def get_firebase_database_url():
    return os.getenv("FIREBASE_DATABASE_URL") or st.secrets["firebase"]["database"]["url"]

# Initialize Firebase if not already initialized
if not firebase_admin._apps:
    cred = credentials.Certificate(get_firebase_credentials())
    firebase_admin.initialize_app(cred, {
        'databaseURL': get_firebase_database_url()
    })

@st.cache_data
def fetch_company_data():
    ref = db.reference('FinalMergedData')
    data = ref.get()
    parsed_data = [json.loads(value) for value in data.values()]
    return pd.DataFrame(parsed_data)

@st.cache_data
def fetch_agents_data():
    ref = db.reference('Agents')
    data = ref.get()
    return data

def sanitize_id(company_id):
    # Replace periods with commas or any other character that Firebase allows
    return company_id.replace('.', ',')


def display_agents(agents):
    st.subheader("AI Agents")
    col1, col2 = st.columns(2)
    for i, agent in enumerate(agents):
        title = agent.get("Title", "Unknown Agent")
        description = agent.get("AgentDescription", "No description available.")
        used_by = agent.get("UsedBy", [])
        related_apis = agent.get("RelatedAPIs", [])
        
        # Create a card with custom CSS
        card_html = f"""
        <div style="
            border: 1px solid #ddd;
            border-radius: 8px;
            padding: 16px;
            margin: 10px 0;
            background-color: white;
            box-shadow: 0 1px 2px 0 rgba(60,64,67,0.3), 0 1px 3px 1px rgba(60,64,67,0.15);
            position: relative;
            overflow: hidden;
        ">
            <h5 style="margin-left: 10px; color: #202124; font-family: 'Google Sans',Roboto,Arial,sans-serif;">{title}</h5>
            <p style="margin-left: 10px; font-family: Roboto,Arial,sans-serif;">{description}</p>
            <p style="margin-left: 10px; font-family: Roboto,Arial,sans-serif;"><b>Used By:</b> {', '.join(used_by)}</p>
            <p style="margin-left: 10px; font-family: Roboto,Arial,sans-serif;"><b>Related APIs:</b> {', '.join(related_apis)}</p>
        </div>
        """
        # Alternate between columns
        if i % 2 == 0:
            col1.markdown(card_html, unsafe_allow_html=True)
        else:
            col2.markdown(card_html, unsafe_allow_html=True)

def navigate_agents():
    st.title("Navigate AI Agents")
    
    df_company = fetch_company_data()
    agents_data = fetch_agents_data()

    if not agents_data:
        st.info("No agents data available.")
        return

    # Filtering options
    company_ids = st.multiselect("Select Company IDs", options=df_company["ID"].unique().tolist())
    industries = st.multiselect("Select Industries", options=df_company["company.category.industry"].unique().tolist())
    technologies = st.multiselect("Select Technologies", options=df_company["company.tech"].str.split(', ').explode().unique().tolist())

    filtered_agents = []

    for company_id, agents in agents_data.items():
        sanitized_id = sanitize_id(company_id)
        
        if company_ids and sanitized_id not in company_ids:
            continue
        
        company_info = df_company[df_company["ID"] == sanitized_id]
        if not company_info.empty:
            industry = company_info["company.category.industry"].values[0]
            company_technologies = company_info["company.tech"].values[0].split(', ') if not pd.isna(company_info["company.tech"].values[0]) else []

            if industries and industry not in industries:
                continue

            if technologies and not any(tech in technologies for tech in company_technologies):
                continue
            
            filtered_agents.extend(agents.values())
    
    if filtered_agents:
        display_agents(filtered_agents)
    else:
        st.info("No agents match the selected criteria.")