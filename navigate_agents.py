import streamlit as st
import pandas as pd
import json
from firebase_admin import db

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

def display_agents(agents_by_company):
    st.subheader("AI Agents")
    col1, col2 = st.columns(2)
    for company_id, agents in agents_by_company.items():
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
                <p style="margin-left: 10px; font-family: Roboto,Arial,sans-serif;"><b>Company ID:</b> {company_id}</p>
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

    # Sanitize the keys in agents_data
    agents_data = {sanitize_id(key): value for key, value in agents_data.items()}

    # Sidebar for filtering options
    st.sidebar.header("Filter Companies")
    
    company_ids = st.sidebar.multiselect("Select Company IDs", options=df_company["ID"].unique().tolist(), default=[])
    industries = st.sidebar.multiselect("Select Industries", options=df_company["company.category.industry"].unique().tolist(), default=[])
    technologies = st.sidebar.multiselect("Select Technologies", options=df_company["company.tech"].str.split(', ').explode().unique().tolist(), default=[])

    # Initialize the filter condition as True
    filter_condition = pd.Series([True] * len(df_company))

    if company_ids:
        filter_condition &= df_company["ID"].isin(company_ids)
    if industries:
        filter_condition &= df_company["company.category.industry"].isin(industries)
    if technologies:
        tech_filter = df_company["company.tech"].str.split(', ').apply(lambda x: any(tech in technologies for tech in x) if isinstance(x, list) else False)
        filter_condition &= tech_filter

    # Apply the filter condition
    filtered_companies = df_company[filter_condition]
    filtered_company_ids = filtered_companies["ID"].unique()

    # Collect agents for filtered companies
    filtered_agents_by_company = {}

    for company_id in filtered_company_ids:
        sanitized_id = sanitize_id(company_id)
        if sanitized_id in agents_data:
            company_agents = agents_data[sanitized_id]
            if isinstance(company_agents, str):
                # Parse the JSON string
                company_agents = json.loads(company_agents)
            if "agents" in company_agents:
                filtered_agents_by_company[company_id] = company_agents["agents"]

    if filtered_agents_by_company:
        display_agents(filtered_agents_by_company)
    else:
        st.info("No agents match the selected criteria.")

# Ensure the function is called when running the script directly
if __name__ == "__main__":
    navigate_agents()
