import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt

# Connect to MongoDB
tls_certificate_path = r"zert.pem"

CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]
collection = db["ACM_paper_filter3"]

query = {"CoMo-12_03" : "yes"}

data = list(collection.find(query))

# Convert data to DataFrame
df = pd.DataFrame(data)

# Convert 'publication_date' to year and then to decade
df["year"] = pd.to_datetime(df["date_publication"], format="%d-%m-%Y", errors="coerce").dt.year
df["decade"] = (df["year"] // 10) * 10

# Drop entries without a valid year or modelling approach
df = df.dropna(subset=["year", "como-tax-topic2"])

# Count occurrences of modelling approaches per decade
modelling_approach_counts = df.groupby(["decade", "como-tax-topic2"]).size().reset_index(name="count")

# Pivot data for stacked bar chart
pivot_df = modelling_approach_counts.pivot(index="decade", columns="como-tax-topic2", values="count").fillna(0)
pivot_df.index = pivot_df.index.astype(int)

# Plot stacked bar chart
pivot_df.plot(kind="bar", stacked=True, figsize=(15, 6))
plt.xlabel("Decade")
plt.ylabel("Count")
plt.title("Distribution of Topics Per Decade")
plt.legend(title="Topics", loc="upper left", bbox_to_anchor=(0.02, 0.98))
plt.xticks(rotation=45)
plt.tight_layout()
plt.show()

