# ------ TRAITEMENT DE DONNEES SOUS PYTHONS DATA PROCESSING ------#

# importation des librairies

import pandas as pd
import psycopg2 as pg2
import numpy as np

def extract_data():
    
# ------ Extraction des donnees depuis Postgres, excel, csv, etc ------#

    print("Extraction des donnees en cours...")

    # Paramètres de connexion

    connexions = pg2.connect(
        dbname="leuk_webapp_production",
        user="malick.diouf",
        password="nA@8q9WMdNCpPH",  
        host="leuk.laiterieduberger.sn",
        port="5432"
    )

    # Récupération des données

    zonage = pd.read_sql("select * from zonage();", connexions)
    
    pilier = pd.read_sql("select * from pilier_Leuk();", connexions)
    
    can = pd.read_sql("select * from can('2025-01-01','2025-01-31');", connexions)
    
    # Fermeture de la connexion

    connexions.close()
    
    catalogue = pd.read_excel("Catalogue.xlsx")
    
    print("Extraction des donnees terminee.")
    
    return can, zonage, pilier, catalogue

# ------- Transformation des donnees -------#
def transform_data(can,zonage,pilier,catalogue):
        
        print("Transformation des donnees en cours...")
        
        # Renomer les colonnes 
        zonage = zonage.rename(columns={'Secteur':'secteur'})
        pilier =pilier.rename(columns={'sku_commcare':'code_produits'})
        
        # Jointure des donnees
        df = pd.merge(left=can, right=zonage, how= "inner", on= "secteur")
        df = pd.merge(left=df, right=pilier, how= "inner", on= "code_produits")
        
        # Conversion de la colonne date en datetime
        df['date'] = pd.to_datetime(df['date'])
        
        # Ajout de la colonne mois
        df['mois'] = df['date'].dt.month
        
        # Ajout de la colonne CAHT
        df['CAHT'] =np.where(df['pilier'] == 'LF', df["can"], df['can']/1.18)
        


