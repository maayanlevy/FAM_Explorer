import streamlit as st
import pandas as pd
import json
from firebase_admin import db
import os

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
        if company_ids and company_id not in company_ids:
            continue
        
        company_info = df_company[df_company["ID"] == company_id]
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
