import streamlit as st
from navigate_agents import navigate_agents
from st_aggrid import AgGrid, GridUpdateMode
from st_aggrid.grid_options_builder import GridOptionsBuilder
import pandas as pd
import json
import os
from dotenv import load_dotenv
import streamlit.components.v1 as components
import requests

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

def sanitize_id(company_id):
    # Replace periods with commas or any other character that Firebase allows
    return company_id.replace('.', ',')

def fetch_agents_from_firebase(company_id):
    try:
        sanitized_id = sanitize_id(company_id)
        ref = db.reference(f'Agents/{sanitized_id}')
        agents_data = ref.get()
        if agents_data:
            return agents_data
        else:
            return None
    except Exception as e:
        st.error(f"Error fetching agents from Firebase: {e}")
        return None

def store_agents_in_firebase(company_id, agents_data):
    try:
        sanitized_id = sanitize_id(company_id)
        ref = db.reference(f'Agents/{sanitized_id}')
        ref.set(agents_data)
    except Exception as e:
        st.error(f"Error storing agents in Firebase: {e}")

def display_api_data(company_id, df_zapier):
    api_data = df_zapier[df_zapier['ID'] == company_id]
    
    if not api_data.empty:
        st.subheader(f"{company_id} - Service Details:")
        
        # Display the service description from the first row
        service_description = api_data.iloc[0]['Descroption']  # Note the typo in the original column name
        st.markdown(f"**Service Description:** {service_description}")
        st.markdown("---")
        
        col1, col2 = st.columns(2)
        for i, row in api_data.iterrows():
            api_type = row['API Type']
            api_name = row['API Name']
            
            # Define Google's yellow and green colors
            google_yellow = "#FBBC05"
            google_green = "#34A853"
            
            # Choose color based on API type
            color = google_yellow if api_type == 'Trigger' else google_green
            
            # Create a card with custom CSS using Google's yellow and green
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
                <div style="
                    position: absolute;
                    top: 0;
                    left: 0;
                    width: 5px;
                    height: 100%;
                    background-color: {color};
                "></div>
                <h5 style="margin-left: 10px; color: #202124; font-family: 'Google Sans',Roboto,Arial,sans-serif;">{api_name}</h5>
                <span style="
                    margin-left: 10px;
                    padding: 2px 8px;
                    background-color: {color};
                    color: #fff;
                    border-radius: 12px;
                    font-family: Roboto,Arial,sans-serif;
                    font-size: 0.8em;
                    font-weight: bold;
                ">{api_type}</span>
            </div>
            """
            
            # Alternate between columns
            if i % 2 == 0:
                col1.markdown(card_html, unsafe_allow_html=True)
            else:
                col2.markdown(card_html, unsafe_allow_html=True)
    else:
        st.info("No API data available for this company.")

def get_ai_agent_description(company_data, df_zapier):
    api_url = "https://api.anthropic.com/v1/messages"
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": os.getenv("ANTHROPIC_API_KEY") or st.secrets["anthropic"]["api_key"],
        "anthropic-version": "2023-06-01" 
    }
    
    prompt = f"""
    Company: {company_data['company.name']}
    Description: {company_data['company.description']}
    Category: {company_data['company.category.industry']}
    APIs: {', '.join(df_zapier[df_zapier['ID'] == company_data['ID']]['API Name'].tolist())}
    
    Based on the information above, describe AI agents that can replicate what this company offers through its APIs. Focus on the key functionalities and how an AI agent could automate or enhance these processes.
    Output in JSON of agents, with each agent represented as json with the following keys: "Title": "", "AgentDescription": "", "UsedBy": [], "RelatedAPIs": []
    For example an agent can contain: 
      "Title": "ChatGPT",
      "AgentDescription": "ChatGPT is a conversational AI model developed by OpenAI, based on the GPT-4 architecture. It can understand and generate human-like text based on the input it receives.",
      "UsedBy": ["Businesses for customer support", "Individuals for personal assistance", "Developers for integrating conversational AI into applications"],
      "RelatedAPIs": ["OpenAI GPT-4 API", "Twilio API", "Slack API"]
    Constrain response to the json, no other text
    """
    
    data = {
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 1000
    }
      
    response = requests.post(api_url, headers=headers, json=data)
    
    if response.status_code == 200:
        response_json = response.json()
        agent_text = response_json['content'][0]['text']
        return agent_text
    else:
        return f"Error: {response.status_code} - {response.text}"

def display_ai_agents(agent_data):
    try:
        agents_json = json.loads(agent_data)
        agents = agents_json.get("agents", [])
    except json.JSONDecodeError:
        st.error("Error decoding agent data")
        return

    st.subheader("AI Agent Descriptions")
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
    # Locations filter
    locations = st.sidebar.multiselect("Select Locations", options=df_company["company.geo.country"].unique().tolist(), default=[])

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

    # Initialize the filter condition as True
    filter_condition = pd.Series([True] * len(df_company))
    
    if locations:
        filter_condition &= df_company["company.geo.country"].isin(locations)

    # Apply the filter condition
    df_filtered = df_filtered[filter_condition]

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
