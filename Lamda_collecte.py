import json
import urllib.request
import urllib.parse
import boto3
from datetime import datetime

# Initialisation du client S3
s3_client = boto3.client('s3')

# VOS INFORMATIONS PERSONNELLES (À MODIFIER !)
API_KEY = "32fcbaf20baa52a5caebecc46ddbfc0a"  # REMPLACEZ par votre vraie clé
BUCKET_NAME = "projet-meteo-1"       # REMPLACEZ par le nom de votre compartiment

# Liste des 6 villes d'Afrique de l'Ouest (sans accents pour éviter les problèmes)
VILLES = [
    {"nom": "Dakar", "pays": "SN"},
    {"nom": "Thies", "pays": "SN"},  # "Thiès" sans accent
    {"nom": "Saint-Louis", "pays": "SN"},
    {"nom": "Bamako", "pays": "ML"},
    {"nom": "Abidjan", "pays": "CI"},
    {"nom": "Ouagadougou", "pays": "BF"}
]

def lambda_handler(event, context):
    print("🚀 Démarrage de Lambda-Collecte")
    print(f"🔑 Clé API utilisée: {API_KEY[:5]}... (cachée pour sécurité)")
    
    for ville_info in VILLES:
        ville = ville_info["nom"]
        pays = ville_info["pays"]
        
        try:
            # 1. Préparer la requête avec encodage correct
            query = f"{ville},{pays}"
            query_encoded = urllib.parse.quote(query)
            url = f"https://api.openweathermap.org/data/2.5/weather?q={query_encoded}&appid={API_KEY}&units=metric&lang=fr"
            
            print(f"🌍 Appel API pour {ville}...")
            
            # 2. Appeler l'API avec un timeout
            request = urllib.request.Request(url)
            with urllib.request.urlopen(request, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))
            
            # 3. Vérifier que la réponse est valide
            if data.get('cod') != 200:
                print(f"⚠️ Réponse inattendue pour {ville}: {data}")
                continue
            
            # 4. Préparer le nom du fichier dans S3
            maintenant = datetime.now()
            date_annee = maintenant.strftime("%Y")
            date_mois = maintenant.strftime("%m")
            date_jour = maintenant.strftime("%d")
            heure_minute = maintenant.strftime("%H-%M-%S")
            
            # Format: raw/Dakar/2024/03/21/14-30-45.json
            chemin_fichier = f"raw/{ville}/{date_annee}/{date_mois}/{date_jour}/{heure_minute}.json"
            
            # 5. Sauvegarder dans S3
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=chemin_fichier,
                Body=json.dumps(data, indent=2, ensure_ascii=False).encode('utf-8'),
                ContentType='application/json'
            )
            
            print(f"✅ Données sauvegardées: {ville} → {chemin_fichier}")
            print(f"   Température: {data['main']['temp']}°C, Humidité: {data['main']['humidity']}%")
            
        except urllib.error.HTTPError as e:
            print(f"❌ Erreur HTTP pour {ville}: {e.code} - {e.reason}")
            if e.code == 401:
                print("   ⚠️  Vérifiez votre clé API ! Elle est peut-être incorrecte ou pas encore activée.")
        except Exception as e:
            print(f"❌ Erreur pour {ville}: {type(e).__name__} - {str(e)}")
    
    return {
        'statusCode': 200,
        'body': json.dumps('Collecte terminée !')
    }