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
      AND zone LIKE '%Kaolack%'
    GROUP BY name, qr_code, address, phone, secteur, zone, region, golden_shop, lat, lng, cluster, 
             zo.libelle, d.day, p.status
    """
    
    pdv = pd.read_sql(query, connexion)
    connexion.close()
    
    return pdv

# Chargement des données
pdv = get_data()

# Transformation des données
@st.cache_data
def clean_data(pdv):
    # Vérification de la validité des dates dans 'max'
    def safe_to_datetime(date_str):
        try:
            return pd.to_datetime(date_str, errors='raise')
        except Exception as e:
            return pd.NaT

    # Appliquer la conversion en datetime sur la colonne 'max' avec gestion des erreurs
    pdv['max'] = pdv['max'].apply(safe_to_datetime)

    # Vérification des lignes invalides après conversion
    nat_rows = pdv[pdv['max'].isna()]
    if not nat_rows.empty:
        st.warning(f"Certaines dates dans la colonne 'max' n'ont pas pu être converties en datetime.")
        st.write(nat_rows[['name', 'max']])

    # Remplacer les NaT par la date du jour
    today = datetime.date.today()
    pdv['max'].fillna(pd.to_datetime(today), inplace=True)

    pdv['lat'] = pd.to_numeric(pdv['lat'], errors='coerce')
    pdv['lng'] = pd.to_numeric(pdv['lng'], errors='coerce')

    # Supprimer les lignes avec des latitudes ou longitudes manquantes
    pdv = pdv.dropna(subset=['lat', 'lng'])
    
    return pdv

pdv = clean_data(pdv)

# Interface Streamlit
st.title("📊 Gestion du Referentiel des PDV")

# Bouton de rafraîchissement
if st.button("🔄 Actualiser"):
    st.rerun()

# Barre de recherche QR Code
recherche = st.text_input("🔍 Rechercher un QR Code :", "")

# Filtres latéraux
st.sidebar.header("🔽 Filtres")

select_status = st.sidebar.radio("📌 Status Pdv", options=pdv['status'].unique())
select_region = st.sidebar.selectbox("🌍 Région", options=pdv["region"].unique())
select_zone = st.sidebar.multiselect("📍 Zone", options=pdv["zone"].unique(), default=pdv["zone"].unique())
select_secteur = st.sidebar.multiselect("🏬 Secteur", options=pdv["secteur"].unique(), default=pdv["secteur"].unique())
select_cluster = st.sidebar.multiselect("🔗 Cluster", options=pdv["cluster"].unique(), default=pdv["cluster"].unique())
select_jour = st.sidebar.multiselect("📅 Jour", options=pdv["day"].unique(), default=pdv["day"].unique())

# Sélecteur de plage de dates
date_slider = st.sidebar.slider(
    "📅 Sélectionner une plage de dates", 
    min_value=pdv["max"].min().date(), 
    max_value=pdv["max"].max().date(), 
    value=(pdv["max"].min().date(), pdv["max"].max().date())
)

# Filtrage par la plage de dates sélectionnée
pdv = pdv[(pdv["max"].dt.date >= date_slider[0]) & (pdv["max"].dt.date <= date_slider[1])]

# Application des autres filtres
pdv_select = pdv.query(
    "status == @select_status & region == @select_region & zone == @select_zone & secteur == @select_secteur & cluster == @select_cluster & day == @select_jour"
)

# Recherche QR Code
if recherche:
    pdv_select = pdv_select[pdv_select["qr_code"].str.contains(recherche, case=False, na=False)]

# Affichage des KPIs
st.metric("📌 Nombre total de PDV", len(pdv_select))

# Affichage du tableau filtré
st.write(f"### 📋 Points de Vente avec des ventes effectuées entre {date_slider[0]} et {date_slider[1]}")
st.dataframe(pdv_select[['name', 'qr_code', 'address', 'phone', 'secteur', 'zone', 'region', 'libelle', 'day', 'max']])

# Fonction pour télécharger en Excel
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, sheet_name="PDV", index=False)
    return output.getvalue()

# Bouton de téléchargement
st.download_button(
    label="📥 Télécharger les données",
    data=to_excel(pdv_select),
    file_name="PDV_Kaolack.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# Carte interactive avec marqueurs pour dates "max" non correspondantes à l'année en cours
st.write("### 🗺️ Visualisation des Points de Vente")

if pdv_select.empty:
    st.error("Aucun point de vente à afficher pour les filtres sélectionnés.")
else:
    # Créer la carte centrée autour de la moyenne des latitudes et longitudes des points de vente
    m = folium.Map(location=[pdv_select["lat"].mean(), pdv_select["lng"].mean()], zoom_start=10, tiles="CartoDB dark_matter")

    # Définir les couleurs en fonction des jours de la semaine
    jour_colors = {
        "Lundi": "red", "Mardi": "blue", "Mercredi": "green", "Jeudi": "yellow",
        "Vendredi": "purple", "Samedi": "orange", "Dimanche": "gray"
    }

    # Obtenir l'année actuelle
    current_year = datetime.datetime.now().year

    # Ajouter des markers avec des icônes personnalisées
    for _, row in pdv_select.iterrows():
        # Vérifier si l'année de la date "max" ne correspond pas à l'année en cours
        if row['max'].year != current_year:
            icon_color = "white"  # Marqueur pour dates max non correspondantes
            icon = "times-circle"  # Icône de croix rouge
        else:
            icon_color = jour_colors.get(row['day'], "gray")
            icon = "info-sign"

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

        # Créer une icône avec une bordure et une couleur dynamique
        icon_style = {
            "iconColor": "red",  # Couleur de l'icône
            "color": icon_color,   # Couleur de fond de l'icône
            "icon": icon,          # Icône Font Awesome
            "prefix": "fa"         # Utiliser Font Awesome pour l'icône
        }

        # Ajouter le marqueur avec une icône personnalisée
        folium.Marker(
            location=[row["lat"], row["lng"]],
            popup=folium.Popup(popup_html, max_width=300),
            tooltip=row['name'],
            icon=folium.Icon(**icon_style)  # Appliquer les styles à l'icône
        ).add_to(m)

    # Afficher la première carte dans Streamlit
    folium_static(m)