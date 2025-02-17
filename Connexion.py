import pandas as pd
import streamlit as st
import psycopg2  # Utiliser psycopg2 pour se connecter à PostgreSQL

# Paramètres de connexion
dbname = "leuk_webapp_production"
user = "malick.diouf"
password = "nA@8q9WMdNCpPH"  #Ton mot de passe
host = "leuk.laiterieduberger.sn"
port = "5432"

# Connexion à la base de donnees 
connexion = psycopg2.connect(
    dbname=dbname,
    user=user,
    password=password,
    host=host,
    port=port
)

# Récupération des donnees 
query = """
       SELECT secteur,date,code_produits,qte,can,pertes
       FROM can('2025-01-01','2025-01-31')
      """  

query1 = "SELECT * FROM zonage()"

data = pd.read_sql(query, connexion)
data = data.rename(columns={'Secteur':'secteur'})
data1 = pd.read_sql(query1, connexion)

# Jointure avec Pandas 

df = pd.merge(left=data, right=data1, how= "inner", on= "secteur")

# Regroupement de donnees
# groupby(): Permet de regrouper des colonnes en appliquant une seule fonction d'aggregation
CAN_Secteur = df.groupby('secteur')['can'].sum()
CAN_Secteur_Produits = df.groupby(['secteur','code_produits'])['can'].sum()
TCD = df.pivot_table(values='can', index='region',aggfunc= 'sum')

# Fermeture de connexion apres avoir recuperer les donnees 

connexion.close()
print(df.head())