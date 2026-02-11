import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Pagina configuratie
st.set_page_config(page_title="Monitor Doorstroom Twente-Saxion", layout="wide")

st.title("📊 Monitor Doorstroom: ROC van Twente naar Saxion")
st.markdown("""
Deze applicatie analyseert de instroom in het Hoger Onderwijs vanuit het mbo. 
Upload de jaarlijkse DUO-bestanden om de trends te actualiseren.
""")

# Sidebar voor data upload
st.sidebar.header("Data Management")
uploaded_files = st.sidebar.file_uploader(
    "Upload DUO CSV bestanden (bijv. 2022, 2023, 2024)", 
    type="csv", 
    accept_multiple_files=True
)

@st.cache_data
def load_and_combine_data(files):
    all_data = []
    for file in files:
        try:
            # We proberen verschillende scheidingstekens omdat DUO bestanden soms variëren
            df = pd.read_csv(file)
            all_data.append(df)
        except Exception as e:
            st.error(f"Fout bij laden van {file.name}: {e}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        # Zorg dat 'Aantal' numeriek is
        combined['Aantal'] = pd.to_numeric(combined['Aantal'], errors='coerce').fillna(0)
        return combined
    return None

data = load_and_combine_data(uploaded_files)

if data is not None:
    # --- FILTERS ---
    st.sidebar.divider()
    st.sidebar.subheader("Filters")
    
    # Filter op Herkomst (Standaard ROC van Twente)
    alle_herkomst = sorted(data['Herkomst naam instelling'].dropna().unique())
    default_herkomst = "ROC van Twente" if "ROC van Twente" in alle_herkomst else alle_herkomst[0]
    selected_herkomst = st.sidebar.selectbox("Selecteer Herkomstinstelling", alle_herkomst, index=alle_herkomst.index(default_herkomst))

    # Filter op Bestemming (Standaard Saxion)
    alle_ho = sorted(data['HO naam instelling'].dropna().unique())
    default_ho = "Saxion" if "Saxion" in alle_ho else alle_ho[0]
    selected_ho = st.sidebar.multiselect("Selecteer HO Bestemming(en)", alle_ho, default=[default_ho])

    # Subset data op basis van filters
    filtered_df = data[data['Herkomst naam instelling'] == selected_herkomst]
    ho_subset = filtered_df[filtered_df['HO naam instelling'].isin(selected_ho)]

    # --- KPI's ---
    kpi1, kpi2, kpi3 = st.columns(3)
    totaal_instroom_2024 = ho_subset[ho_subset['Jaar'] == 2024]['Aantal'].sum()
    totaal_instroom_2023 = ho_subset[ho_subset['Jaar'] == 2023]['Aantal'].sum()
    
    delta = None
    if totaal_instroom_2023 > 0:
        diff = totaal_instroom_2024 - totaal_instroom_2023
        delta = f"{diff} t.o.v. vorig jaar"

    kpi1.metric("Instroom 2024 (geselecteerd)", f"{int(totaal_instroom_2024)} studenten", delta)
    kpi2.metric("Aantal HO Instellingen", len(ho_subset['HO naam instelling'].unique()))
    kpi3.metric("Unieke Opleidingen", len(ho_subset['HO naam opleiding'].unique()))

    # --- GRAFIEKEN ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Meerjarige Trend Instroom")
        trend_data = ho_subset.groupby(['Jaar', 'HO naam instelling'])['Aantal'].sum().reset_index()
        fig_trend = px.line(trend_data, x='Jaar', y='Aantal', color='HO naam instelling', 
                             markers=True, line_shape='linear',
                             title=f"Instroom vanuit {selected_herkomst}")
        fig_trend.update_xaxes(dtick=1)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col2:
        st.subheader("Marktaandeel per Bestemming (2024)")
        markt_2024 = filtered_df[filtered_df['Jaar'] == 2024].groupby('HO naam instelling')['Aantal'].sum().reset_index()
        # Pak de top 5 en groep de rest
        top_5 = markt_2024.nlargest(5, 'Aantal')
        fig_pie = px.pie(markt_2024, values='Aantal', names='HO naam instelling', 
                         title=f"Waar gaan {selected_herkomst} studenten heen?")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader("Populaire Opleidingssectoren (Top 10)")
        sector_data = ho_subset[ho_subset['Jaar'] == 2024].groupby('HO naam opleiding')['Aantal'].sum().reset_index()
        sector_data = sector_data.nlargest(10, 'Aantal')
        fig_bar = px.bar(sector_data, x='Aantal', y='HO naam opleiding', orientation='h',
                         title="Grootste opleidingen in 2024", color='Aantal')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col4:
        st.subheader("Herkomst Onderwijssoort")
        # Direct vs Indirect inzichtelijk maken
        herkomst_type = ho_subset.groupby(['Jaar', 'Herkomst onderwijssoort'])['Aantal'].sum().reset_index()
        fig_area = px.area(herkomst_type, x='Jaar', y='Aantal', color='Herkomst onderwijssoort',
                           title="Directe vs. Indirecte Instroom over tijd")
        fig_area.update_xaxes(dtick=1)
        st.plotly_chart(fig_area, use_container_width=True)

    # --- DATATABEL ---
    with st.expander("Bekijk Ruwe Data"):
        st.dataframe(ho_subset, use_container_width=True)

else:
    st.info("Upload CSV-bestanden in de zijbalk om de analyse te starten.")
    st.image("https://via.placeholder.com/800x400.png?text=Wachtend+op+data+upload", use_container_width=True)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Ontwikkeld voor Data-analyse in het MBO")
