import pandas as pd
from sqlalchemy import create_engine

def get_data():
    # Créer une connexion SQLAlchemy
    engine = create_engine('postgresql://malick.diouf:nA@8q9WMdNCpPH@leuk.laiterieduberger.sn:5432/leuk_webapp_production')

    # Données Can
    can = pd.read_sql("""
        SELECT * FROM can('2025-02-01', '2025-02-28')
        WHERE code_produits LIKE '%DSP%'
    """, engine)

    # Données zonage
    zonage = pd.read_sql("SELECT * FROM zonage()", engine)

    # Données pilier
    pilier = pd.read_sql("SELECT * FROM pilier_Leuk()", engine)

    return can, pilier, zonage
can, pilier, zonage= get_data()

# Enregistrer les premières lignes des DataFrames dans des fichiers CSV
can.head().to_csv('can_head.csv', index=False)
pilier.head().to_csv('pilier_head.csv', index=False)
zonage.head().to_csv('zonage_head.csv', index=False)