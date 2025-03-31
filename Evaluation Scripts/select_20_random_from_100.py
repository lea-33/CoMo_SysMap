import json
from pymongo import MongoClient
from bson import ObjectId
import random

# Path to the certificate
tls_certificate_path = r"zert.pem"

# MongoDB connection string
CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]  # Replace with your database name
collection = db["ACM_paper_filter3"]  # Replace with your collection name

# MongoDB query with $and condition
query = {"CoMo-10_03": "computational modelling"}

entries = list(collection.find(query))
print(f"Number of matching entries: {len(entries)}")


# Randomly select 20 entries from the filtered dataset
random_entries = random.sample(entries, 10)

# Print the DOI numbers of the selected entries
print("DOI numbers of 10 randomly selected entries:")
for i, entry in enumerate(random_entries, start=1):
    url = entry.get('url', 'No URL')
    print(f"{url}")
