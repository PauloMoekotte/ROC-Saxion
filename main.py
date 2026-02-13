import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

# Pagina configuratie
st.set_page_config(page_title="Monitor Doorstroom Twente-Saxion", layout="wide")

st.title("📊 Monitor Doorstroom: ROC van Twente naar Saxion")
st.markdown("""
Deze applicatie analyseert de instroom in het Hoger Onderwijs vanuit het mbo. Upload de jaarlijkse 
DUO-bestanden 'Herkomst ho-studenten' om de trends te actualiseren. 
Die bestanden vind je [hier](https://duo.nl/open_onderwijsdata/onderwijs-algemeen/leerlingen-en-studentenstromen/leerlingen-en-studentenstromen.jsp) en moet je eerst downloaden om ze te kunnen gebruiken.
Zie het [Stromenbestand herkomst ho-studenten](https://duo.nl/open_onderwijsdata/images/herkomst-ho.pdf) voor een toelichting op de data. 
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
            # DUO bestanden gebruiken vaak een puntkomma (;) of komma (,) afhankelijk van de export
            # We proberen eerst met sep=None om het automatisch te detecteren
            df = pd.read_csv(file, sep=None, engine='python')
            all_data.append(df)
        except Exception as e:
            st.error(f"Fout bij laden van {file.name}: {e}")
    
    if all_data:
        combined = pd.concat(all_data, ignore_index=True)
        # Zorg dat 'Aantal' numeriek is en Jaar een integer
        combined['Aantal'] = pd.to_numeric(combined['Aantal'], errors='coerce').fillna(0)
        combined['Jaar'] = pd.to_numeric(combined['Jaar'], errors='coerce').fillna(0).astype(int)
        return combined
    return None

data = load_and_combine_data(uploaded_files)

if data is not None:
    # --- FILTERS ---
    st.sidebar.divider()
    st.sidebar.subheader("Filters")
    
    # Filter op Herkomst (Standaard ROC van Twente)
    herkomst_col = 'Herkomst naam instelling'
    bestemming_col = 'HO naam instelling'
    
    alle_herkomst = sorted(data[herkomst_col].dropna().unique())
    # Zoek naar ROC van Twente in de lijst
    default_herkomst_idx = 0
    for i, name in enumerate(alle_herkomst):
        if "ROC van Twente" in name:
            default_herkomst_idx = i
            break
            
    selected_herkomst = st.sidebar.selectbox("Selecteer Herkomstinstelling", alle_herkomst, index=default_herkomst_idx)

    # Filter op Bestemming (Standaard Saxion)
    alle_ho = sorted(data[bestemming_col].dropna().unique())
    default_ho_list = [h for h in alle_ho if "Saxion" in h]
    selected_ho = st.sidebar.multiselect("Selecteer HO Bestemming(en)", alle_ho, default=default_ho_list if default_ho_list else None)

    # Subset data op basis van filters
    filtered_df = data[data[herkomst_col] == selected_herkomst]
    ho_subset = filtered_df[filtered_df[bestemming_col].isin(selected_ho)]

    # --- KPI's ---
    kpi1, kpi2, kpi3 = st.columns(3)
    
    jaren = sorted(ho_subset['Jaar'].unique(), reverse=True)
    huidig_jaar = jaren[0] if jaren else 2024
    vorig_jaar = huidig_jaar - 1
    
    totaal_huidig = ho_subset[ho_subset['Jaar'] == huidig_jaar]['Aantal'].sum()
    totaal_vorig = ho_subset[ho_subset['Jaar'] == vorig_jaar]['Aantal'].sum()
    
    delta = None
    if totaal_vorig > 0:
        diff = totaal_huidig - totaal_vorig
        delta = f"{int(diff)} t.o.v. {vorig_jaar}"

    kpi1.metric(f"Instroom {huidig_jaar}", f"{int(totaal_huidig)} studenten", delta)
    kpi2.metric("Aantal HO Instellingen", len(ho_subset[bestemming_col].unique()))
    kpi3.metric("Unieke Opleidingen", len(ho_subset['HO naam opleiding'].unique()))

    # --- GRAFIEKEN ---
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Meerjarige Trend Instroom")
        trend_data = ho_subset.groupby(['Jaar', bestemming_col])['Aantal'].sum().reset_index()
        fig_trend = px.line(trend_data, x='Jaar', y='Aantal', color=bestemming_col, 
                             markers=True, line_shape='linear',
                             title=f"Instroom vanuit {selected_herkomst}")
        fig_trend.update_xaxes(dtick=1)
        st.plotly_chart(fig_trend, use_container_width=True)

    with col2:
        st.subheader(f"Marktaandeel Bestemming ({huidig_jaar})")
        markt_data = filtered_df[filtered_df['Jaar'] == huidig_jaar].groupby(bestemming_col)['Aantal'].sum().reset_index()
        fig_pie = px.pie(markt_data, values='Aantal', names=bestemming_col, 
                         title=f"Bestemmingen van {selected_herkomst} studenten")
        st.plotly_chart(fig_pie, use_container_width=True)

    st.divider()

    col3, col4 = st.columns(2)

    with col3:
        st.subheader(f"Top 10 Opleidingen ({huidig_jaar})")
        sector_data = ho_subset[ho_subset['Jaar'] == huidig_jaar].groupby('HO naam opleiding')['Aantal'].sum().reset_index()
        sector_data = sector_data.nlargest(10, 'Aantal')
        fig_bar = px.bar(sector_data, x='Aantal', y='HO naam opleiding', orientation='h',
                         title=f"Grootste opleidingen bij geselecteerde HO's", color='Aantal',
                         color_continuous_scale='Viridis')
        fig_bar.update_layout(yaxis={'categoryorder':'total ascending'})
        st.plotly_chart(fig_bar, use_container_width=True)

    with col4:
        st.subheader("Herkomst Onderwijssoort")
        herkomst_type = ho_subset.groupby(['Jaar', 'Herkomst onderwijssoort'])['Aantal'].sum().reset_index()
        fig_area = px.area(herkomst_type, x='Jaar', y='Aantal', color='Herkomst onderwijssoort',
                           title="Directe vs. Indirecte Instroom trend")
        fig_area.update_xaxes(dtick=1)
        st.plotly_chart(fig_area, use_container_width=True)

    # --- DATATABEL ---
    with st.expander("Bekijk Ruwe Data Selectie"):
        st.dataframe(ho_subset, use_container_width=True)

else:
    st.info("Upload CSV-bestanden in de zijbalk om de analyse te starten.")
    st.markdown("""
    **Instructies:**
    1. Download de herkomstbestanden van DUO (bijv. 2022 t/m 2024).
    2. Sleep ze vanuit de downloadmap in de uploader in de zijbalk.
    3. De monitor herkent automatisch de jaren en instellingen.
    4. Selecteer de instellingen (mbo en/of hbo) via de filteropties.
    """)

# Footer
st.sidebar.markdown("---")
st.sidebar.caption("Ontwikkeld voor Data-analyse in het MBO")
