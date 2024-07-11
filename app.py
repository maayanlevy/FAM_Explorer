import streamlit as st
from navigate_agents import navigate_agents
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import pandas as pd
import json
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components

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
import firebase_admin
from firebase_admin import credentials, db

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
def fetch_zapier_data():
    ref = db.reference('Zapier_Data')
    data = ref.get()
    parsed_data = [json.loads(value) for value in data.values()]
    return pd.DataFrame(parsed_data)

def main():
    # Set page config at the very top
    st.set_page_config(page_title="GEB First Addressable Market Explorer", layout="wide")

    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "Navigate Agents"])

    if page == "Home":
        home()
    elif page == "Navigate Agents":
        navigate_agents()

def home():
    # Your existing code for the home page goes here
    
    # Add this line to display the app logo
    st.image("geb-logo.png", width=200, use_column_width=False)
    
    st.title("GEB First Addressable Market Explorer")

    df_company = fetch_company_data()
    df_zapier = fetch_zapier_data()

    name_column = 'company.name'
    domain_column = 'Domain'

    # Load tech status JSON
    with open('tech_status.json') as f:
        tech_status = json.load(f)
    # Filtering
    st.sidebar.header("Search")
    search_term = st.sidebar.text_input("Search by name or domain")
    # Sidebar for table customization
    st.sidebar.header("List Preferences")
    
    # Column selection
    all_columns = df_company.columns.tolist()
    default_columns = ['ID', name_column, domain_column, 'company.category.industry', 'company.metrics.employees', 'company.foundedYear', 'company.geo.country']
    selected_columns = st.sidebar.multiselect(
        "Select columns to display",
        options=all_columns,
        default=default_columns
    )

    # Sorting
    sort_column = st.sidebar.selectbox("Sort by", options=selected_columns, index=selected_columns.index('company.metrics.employees'))
    sort_ascending = st.sidebar.checkbox("Sort Ascending", value=False)

    # Apply filtering
    if search_term:
        df_filtered = df_company[
            df_company[name_column].str.contains(search_term, case=False, na=False) |
            df_company[domain_column].str.contains(search_term, case=False, na=False)
        ]
    else:
        df_filtered = df_company

    # Apply sorting
    df_sorted = df_filtered.sort_values(by=sort_column, ascending=sort_ascending)

    # Table display with AgGrid
    st.subheader("Companies and Services")
    gb = GridOptionsBuilder.from_dataframe(df_sorted[selected_columns])
    gb.configure_selection('single', use_checkbox=False)
    gb.configure_grid_options(domLayout='normal')
    gridOptions = gb.build()

    grid_response = AgGrid(
        df_sorted[selected_columns],
        gridOptions=gridOptions,
        update_mode=GridUpdateMode.SELECTION_CHANGED,
        fit_columns_on_grid_load=True,
        height=400,
        allow_unsafe_jscode=True
    )

    selected_rows = grid_response['selected_rows']

    # Company details section
    st.header("Target Company Details")
    
    company_data = None
    if isinstance(selected_rows, pd.DataFrame) and not selected_rows.empty:
        selected_id = selected_rows.iloc[0]['ID']
        company_data = df_sorted[df_sorted['ID'] == selected_id].iloc[0]
        st.session_state.ai_agents_loaded = False  # Reset AI agents loaded state
        st.session_state.agent_data = None  # Reset agent data
    elif isinstance(selected_rows, list) and len(selected_rows) > 0:
        selected_id = selected_rows[0]['ID']
        company_data = df_sorted[df_sorted['ID'] == selected_id].iloc[0]
        st.session_state.ai_agents_loaded = False  # Reset AI agents loaded state
        st.session_state.agent_data = None  # Reset agent data
    
    if company_data is None:
        # Fallback to dropdown selection if no row is selected
        selected_company = st.selectbox("Switch company", df_sorted[name_column])
        company_data = df_sorted[df_sorted[name_column] == selected_company].iloc[0]
        st.session_state.ai_agents_loaded = False  # Reset AI agents loaded state
        st.session_state.agent_data = None  # Reset agent data
    
    if company_data is not None:
        col1, col2 = st.columns(2)
        with col1:
            if not pd.isna(company_data['company.logo']):
                st.image(company_data['company.logo'], width=100)
            st.markdown(f"### {company_data[name_column]}")
            st.markdown(f"**Website:** {company_data[domain_column]}")
            st.markdown(f"**Industry:** {company_data['company.category.industry']}")
            try:
                st.markdown(f"**Founded:** {int(company_data['company.foundedYear'])}")
            except (ValueError, TypeError):
                st.markdown("**Founded:** Not available")
            st.markdown(f"**Location:** {company_data['company.location']}")
            try:
                st.markdown(f"**Employees:** {int(company_data['company.metrics.employees'])}")
            except (ValueError, TypeError):
                st.markdown("**Employees:** Not available")
            st.markdown(f"**Country:** {company_data['company.geo.country']}")
        
        with col2:
            st.markdown("**Description:**")
            st.markdown(company_data['company.description'])
            
            st.markdown("**Technologies:**")
            technologies = company_data['company.tech'].split(', ') if not pd.isna(company_data['company.tech']) else []

            # Create a flexbox container for the tags
            tech_html = "<div style='display: flex; flex-wrap: wrap; gap: 5px; overflow:auto; max-height:180px;'>"
            for tech in technologies:
                background_color = '#d4edda' if tech_status.get(tech) == 1 else '#f0f0f0'
                tech_html += f"""
                    <div style="
                        display: inline-block;
                        background-color: {background_color};
                        color: #333;
                        padding: 5px 8px;
                        border-radius: 12px;
                        font-size: 0.8em;
                        white-space: nowrap;
                        font-family: sans-serif;
                    ">{tech}</div>
                """
            tech_html += "</div>"

            components.html(tech_html, height=200)  

        # Automatically load APIs
        company_id = company_data['ID']
        display_api_data(company_id, df_zapier)

        if "ai_agents_loaded" not in st.session_state:
            st.session_state.ai_agents_loaded = False

        if st.button("Ideate AI Agents"):
            agents_data = fetch_agents_from_firebase(company_id)
            if agents_data:
                st.session_state.agent_data = agents_data
            else:
                agent_data = get_ai_agent_description(company_data, df_zapier)
                st.session_state.agent_data = agent_data
                store_agents_in_firebase(company_id, agent_data)
            st.session_state.ai_agents_loaded = True

        if st.session_state.ai_agents_loaded:
            display_ai_agents(st.session_state.agent_data)

if __name__ == "__main__":
    main()
