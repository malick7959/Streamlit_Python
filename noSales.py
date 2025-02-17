import pandas as pd
import streamlit as st
import psycopg2
import folium
from streamlit_folium import folium_static
from io import BytesIO
import datetime

# Connexion à la base de données
@st.cache_data
def get_data():
    connexion = psycopg2.connect(
        dbname="leuk_webapp_production",
        user="malick.diouf",
        password="nA@8q9WMdNCpPH",
        host="leuk.laiterieduberger.sn",
        port="5432"
    )

    query = """
    SELECT name, qr_code, address, phone, secteur, zone, region, golden_shop, lat, lng, cluster, 
           zo.libelle, d.day, p.status, max(date) AS max
    FROM point_of_sales p 
    INNER JOIN sectors s ON p.sector_id = s.id
    INNER JOIN zonage() z ON z.secteur = s.label 
    INNER JOIN clusters c ON c.id = p.cluster_id 
    INNER JOIN zones zo ON zo.id = p.zone_id
    INNER JOIN deliverydays d ON d.id = zo.deliveryday_id
    INNER JOIN sales sa on sa.point_of_sale_id = p.id
    WHERE p.status = 'Activate' 
      AND zone LIKE ('%Ourassogui%')
    GROUP BY name, qr_code, address, phone, secteur, zone, region, golden_shop, lat, lng, cluster, 
             zo.libelle, d.day, p.status
    """
    
    pdv = pd.read_sql(query, connexion)
    connexion.close()
    
    return pdv

# Chargement des données
@st.cache_data
def load_data():
    return get_data()

# Nettoyage des données
@st.cache_data
def clean_data(pdv):
    pdv['max'] = pd.to_datetime(pdv['max'], errors='coerce')
    pdv['max'].fillna(pd.to_datetime(datetime.date.today()), inplace=True)
    pdv['lat'] = pd.to_numeric(pdv['lat'], errors='coerce')
    pdv['lng'] = pd.to_numeric(pdv['lng'], errors='coerce')
    pdv['Remarque'] = ""  # Ajout de la colonne Remarque
    return pdv.dropna(subset=['lat', 'lng'])

# Interface Streamlit
st.title("📊 Gestion du Referentiel des PDV")

# Actualisation des données
refresh_button = st.button("🔄 Actualiser les données")
if refresh_button:
    pdv = load_data()
    pdv = clean_data(pdv)
    st.success("Données actualisées avec succès!")
else:
    pdv = load_data()
    pdv = clean_data(pdv)

# Filtrage des données
st.sidebar.header("🔽 Filtres")
select_region = st.sidebar.selectbox("🌍 Région", options=pdv["region"].unique())
select_zone = st.sidebar.multiselect("📍 Zone", options=pdv["zone"].unique(), default=pdv["zone"].unique())
select_secteur = st.sidebar.multiselect("🏬 Secteur", options=pdv["secteur"].unique(), default=pdv["secteur"].unique())
date_slider = st.sidebar.slider("📅 Plage de dates", min_value=pdv["max"].min().date(), max_value=pdv["max"].max().date(), value=(pdv["max"].min().date(), pdv["max"].max().date()))
select_day = st.sidebar.multiselect("🗓️ Sélectionner le(s) jour(s)", options=pdv["day"].unique(), default=pdv["day"].unique())

# Filtrage par jours sélectionnés
pdv = pdv[pdv["day"].isin(select_day)]

# Filtrage par les dates
pdv = pdv[(pdv["max"].dt.date >= date_slider[0]) & (pdv["max"].dt.date <= date_slider[1])]

# Filtrage par la région, zone et secteur
if select_region:
    pdv = pdv[pdv["region"] == select_region]
if select_zone:
    pdv = pdv[pdv["zone"].isin(select_zone)]
if select_secteur:
    pdv = pdv[pdv["secteur"].isin(select_secteur)]

# Affichage des KPIs (métriques)
st.metric("📌 Nombre total de PDV", len(pdv))

# Affichage du tableau interactif avec Remarque éditable
st.write("### 📋 Liste des Points de Vente")
edited_pdv = st.data_editor(
    pdv[['name', 'qr_code', 'address', 'phone', 'secteur', 'zone', 'region', 'libelle', 'day', 'max', 'lat', 'lng', 'Remarque']],
    column_config={
        "Remarque": st.column_config.TextColumn()
    },
    disabled=["name", "qr_code", "address", "phone", "secteur", "zone", "region", "libelle", "day", "max", "lat", "lng"],
    num_rows="dynamic"
)

# Fonction pour convertir le DataFrame en fichier Excel
def to_excel(df):
    """Convertit un DataFrame Pandas en fichier Excel pour le téléchargement."""
    towrite = BytesIO()
    with pd.ExcelWriter(towrite, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Points_de_Vente')
    return towrite.getvalue()

# Ajout du bouton de téléchargement
st.download_button(
    label="📥 Télécharger les données en Excel",
    data=to_excel(edited_pdv),
    file_name="points_de_vente.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Affichage de la carte
st.write("### 🗺️ Carte des Points de Vente")
if not edited_pdv.empty:
    m = folium.Map(location=[edited_pdv["lat"].mean(), edited_pdv["lng"].mean()], zoom_start=10, tiles="CartoDB dark_matter")
    jour_colors = {
        "Lundi": "red", "Mardi": "blue", "Mercredi": "green", "Jeudi": "yellow",
        "Vendredi": "purple", "Samedi": "orange", "Dimanche": "gray"
    }
    current_year = datetime.datetime.now().year
    for _, row in edited_pdv.iterrows():
        # Vérification si le point de vente a été visité cette année
        if row['max'].year != current_year:
            icon_color = "white"
            icon = "times-circle"  # Crois rouge pour les non-visités
        else:
            icon_color = jour_colors.get(row['day'], "gray")
            icon = "info-sign"  # Icône info pour les visités cette année
        
        # Création du popup HTML avec style
        popup_html = f"""
        <div style="background-color: {icon_color}; padding: 10px; border-radius: 5px; color: black; text-align: center;">
            <b>{row['name']}</b><br>
            🗓️ Jour : {row["day"]}<br>
            📅 Dernière Vente : {row['max']}<br>
            📍 Zone : {row["zone"]}<br>
            🏬 Secteur : {row["secteur"]}<br>
            📞 Téléphone : {row["phone"]}<br>
            qr_code: {row["qr_code"]}<br>
        </div>
        """

        # Création du style de l'icône
        icon_style = {
            "iconColor": "red" if icon == "times-circle" else icon_color,  # Crois rouge pour non-visités
            "color": icon_color,   # Couleur de fond de l'icône
            "icon": icon,          # Icône Font Awesome
            "prefix": "fa"         # Utiliser Font Awesome pour l'icône
        }

        # Ajouter le marqueur avec l'icône personnalisée
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['name'],
            icon=folium.Icon(**icon_style)  # Appliquer les styles à l'icône
        ).add_to(m)

    # Affichage de la carte
    folium_static(m)
else:
    st.warning("Aucun point de vente disponible avec les filtres sélectionnés.")
