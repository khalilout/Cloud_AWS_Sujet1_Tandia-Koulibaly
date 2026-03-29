import json
import boto3
from decimal import Decimal
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

# Initialisation des clients AWS
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MeteoTraitee')

# Dictionnaire de conversion des noms de dossiers en noms de villes
CONVERSION_VILLES = {
    'dakar': 'Dakar',
    'thies': 'Thies',
    'saint-louis': 'Saint-Louis',
    'bamako': 'Bamako',
    'abidjan': 'Abidjan',
    'ouagadougou': 'Ouagadougou'
}

def lambda_handler(event, context):
    print("🚀 Démarrage de Lambda-Traitement amélioré")
    
    for record in event['Records']:
        bucket = record['s3']['bucket']['name']
        key = record['s3']['object']['key']
        
        print(f"📂 Nouveau fichier détecté : {bucket}/{key}")
        
        try:
            # 1. Lire le nouveau fichier JSON depuis S3
            response = s3_client.get_object(Bucket=bucket, Key=key)
            data = json.loads(response['Body'].read().decode('utf-8'))
            
            # 2. Extraire les informations
            parts = key.split('/')
            dossier_ville = parts[1].lower()
            
            # Convertir en nom de ville propre
            if dossier_ville in CONVERSION_VILLES:
                ville = CONVERSION_VILLES[dossier_ville]
            else:
                ville = dossier_ville.capitalize()
            
            # Extraire les données météo
            temp_actuelle = Decimal(str(data['main']['temp']))
            humidite_actuelle = Decimal(str(data['main']['humidity']))
            pression_actuelle = Decimal(str(data['main']['pressure']))
            vent_actuel = Decimal(str(data['wind']['speed']))
            
            # 3. Récupérer la date pour les calculs
            maintenant = datetime.now()
            date_actuelle = maintenant.strftime("%Y-%m-%d")
            heure_actuelle = maintenant.hour
            
            # 4. Récupérer les données précédentes pour cette ville aujourd'hui
            print(f"🔍 Recherche des données précédentes pour {ville} le {date_actuelle}")
            
            response_ddb = table.query(
                KeyConditionExpression=Key('ville_date').eq(f"{ville}#{date_actuelle}")
            )
            
            items = response_ddb.get('Items', [])
            
            # Initialiser avec les valeurs actuelles
            temp_min = temp_actuelle
            temp_max = temp_actuelle
            temp_sum = temp_actuelle
            humidite_sum = humidite_actuelle
            vent_sum = vent_actuel
            count = 1
            
            # Si on a des données précédentes, les inclure dans les calculs
            if items:
                print(f"📊 {len(items)} mesures précédentes trouvées pour aujourd'hui")
                
                for item in items:
                    temp_min = min(temp_min, Decimal(str(item['temperature'])))
                    temp_max = max(temp_max, Decimal(str(item['temperature'])))
                    temp_sum += Decimal(str(item['temperature']))
                    humidite_sum += Decimal(str(item['humidite']))
                    vent_sum += Decimal(str(item['vent']))
                    count += 1
            
            # Calculer les moyennes
            temp_moyenne = temp_sum / Decimal(str(count))
            humidite_moyenne = humidite_sum / Decimal(str(count))
            vent_moyen = vent_sum / Decimal(str(count))
            
            print(f"📈 Statistiques pour {ville}:")
            print(f"   Temp: min={temp_min}°C, max={temp_max}°C, moy={temp_moyenne:.1f}°C")
            print(f"   Humidité moy: {humidite_moyenne:.0f}%")
            print(f"   Vent moy: {vent_moyen:.1f} m/s")
            
            # 5. Sauvegarder la nouvelle mesure dans DynamoDB
            item = {
                'ville_date': f"{ville}#{date_actuelle}",
                'heure': heure_actuelle,
                'temperature': temp_actuelle,
                'humidite': humidite_actuelle,
                'pression': pression_actuelle,
                'vent': vent_actuel,
                'temp_min': temp_min,
                'temp_max': temp_max,
                'temp_moyenne': temp_moyenne,
                'humidite_moyenne': humidite_moyenne,
                'vent_moyen': vent_moyen,
                'nb_mesures': count,
                'description': data['weather'][0]['description']
            }
            
            table.put_item(Item=item)
            print(f"✅ Données sauvegardées dans DynamoDB pour {ville} à {heure_actuelle}h")
            
            # 6. Déplacer le fichier vers processed/
            new_key = key.replace('raw/', 'processed/', 1)
            s3_client.copy_object(
                Bucket=bucket,
                CopySource={'Bucket': bucket, 'Key': key},
                Key=new_key
            )
            s3_client.delete_object(Bucket=bucket, Key=key)
            print(f"📦 Fichier déplacé vers {new_key}")
            
        except Exception as e:
            print(f"❌ Erreur: {type(e).__name__} - {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Traitement amélioré terminé !')
    }