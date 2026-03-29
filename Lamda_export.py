import json
import boto3
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key
import csv
from io import StringIO

# Initialisation des clients AWS
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MeteoTraitee')

# Nom de votre bucket
BUCKET_NAME = "projet-meteo-1"

def lambda_handler(event, context):
    print("🚀 Démarrage de Lambda-Export - Génération rapport hebdomadaire")
    
    try:
        # 1. Définir la période (7 derniers jours)
        date_fin = datetime.now()
        date_debut = date_fin - timedelta(days=7)
        
        print(f"📅 Période: {date_debut.strftime('%Y-%m-%d')} au {date_fin.strftime('%Y-%m-%d')}")
        
        # 2. Liste des villes
        villes = ['Dakar', 'Thies', 'Saint-Louis', 'Bamako', 'Abidjan', 'Ouagadougou']
        
        # 3. Préparer le fichier CSV en mémoire
        csv_buffer = StringIO()
        csv_writer = csv.writer(csv_buffer)
        
        # En-tête du CSV
        csv_writer.writerow([
            'Ville', 'Date', 'Heure', 
            'Temperature', 'Humidite', 'Pression', 'Vent',
            'Temp_Min', 'Temp_Max', 'Temp_Moyenne',
            'Description'
        ])
        
        total_lignes = 0
        
        # 4. Pour chaque ville, récupérer les données
        for ville in villes:
            print(f"🔍 Recherche des données pour {ville}...")
            
            # Pour chaque jour de la période
            for i in range(7):
                date_jour = date_debut + timedelta(days=i)
                date_str = date_jour.strftime("%Y-%m-%d")
                
                # Requête dans DynamoDB
                response = table.query(
                    KeyConditionExpression=Key('ville_date').eq(f"{ville}#{date_str}")
                )
                
                items = response.get('Items', [])
                
                for item in items:
                    csv_writer.writerow([
                        ville,
                        date_str,
                        item.get('heure', ''),
                        item.get('temperature', ''),
                        item.get('humidite', ''),
                        item.get('pression', ''),
                        item.get('vent', ''),
                        item.get('temp_min', ''),
                        item.get('temp_max', ''),
                        item.get('temp_moyenne', ''),
                        item.get('description', '')
                    ])
                    total_lignes += 1
        
        # 5. Générer le nom du fichier
        nom_fichier = f"reports/rapport-hebdo-{date_fin.strftime('%Y-%m-%d')}.csv"
        
        # 6. Sauvegarder dans S3
        s3_client.put_object(
            Bucket=BUCKET_NAME,
            Key=nom_fichier,
            Body=csv_buffer.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        
        print(f"✅ Rapport généré avec {total_lignes} lignes")
        print(f"📁 Fichier sauvegardé: s3://{BUCKET_NAME}/{nom_fichier}")
        
        return {
            'statusCode': 200,
            'body': json.dumps({
                'message': 'Rapport généré avec succès',
                'fichier': nom_fichier,
                'lignes': total_lignes
            })
        }
        
    except Exception as e:
        print(f"❌ Erreur: {type(e).__name__} - {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps(f'Erreur: {str(e)}')
        }