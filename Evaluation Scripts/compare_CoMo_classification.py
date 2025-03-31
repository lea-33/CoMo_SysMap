from pymongo import MongoClient
from collections import defaultdict

# MongoDB Connection Setup
tls_certificate_path = r"zert.pem"

CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]
collection = db["ACM_paper_filter3"]

# Allowed values for reference
valid_categories = ["computational modelling", "none", "invalid result", "missing"]

# Dictionary to store pairwise counts
pair_counts = defaultdict(int)

# Query all entries and count pairs
entries = collection.find({}, {"LLM_ComputationalModel": 1, "CoMo-10_03": 1})

for entry in entries:
    llm_value = entry.get("CoMo-10_03", "missing")
    abstract_value = entry.get("CoMo-12_03", "missing")

    # Ensure values are within the expected categories
    if llm_value in valid_categories and abstract_value in valid_categories:
        pair_counts[(llm_value, abstract_value)] += 1

# Print results
print("Occurrences of (LLM_ComputationalModel, Abstract_ComputationalModel) pairs:\n")
for pair, count in sorted(pair_counts.items()):
    print(f"{pair}: {count}")
