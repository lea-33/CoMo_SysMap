import pandas as pd
import matplotlib.pyplot as plt
from pymongo import MongoClient

# Plotting Style
plt.rcParams.update({
    'font.size': 13,
    'axes.titlesize': 19,
    'axes.labelsize': 14,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
})

# MongoDB connection setup
tls_certificate_path = r"zert.pem"

CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

# Initialize MongoDB connection
mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]
collection = db["ACM_paper_filter3"]

# Fetch data from MongoDB
query = {"CoMo-12_03": "yes"}
data = list(collection.find(query))

# Convert data to DataFrame
df = pd.DataFrame(data)

# Ensure 'year' column exists
df["year"] = pd.to_datetime(df["date_publication"], format="%d-%m-%Y", errors="coerce").dt.year

# Drop rows where 'year' or 'como-tax-topic' is NaN
df = df.dropna(subset=["year", "como-tax-topic2"])

# Find the first and last appearance of each unique topic
topic_years = df.groupby("como-tax-topic2")["year"].agg(First_Appearance="min", Last_Appearance="max").reset_index()

# Sort topics by first appearance for better visualization
topic_years = topic_years.sort_values("First_Appearance")

# Plot: Gantt-style timeline
fig, ax = plt.subplots(figsize=(14, 9))

# Generate bars for each topic
for i, row in topic_years.iterrows():
    ax.barh(row["como-tax-topic2"], row["Last_Appearance"] - row["First_Appearance"],
            left=row["First_Appearance"], color="skyblue", edgecolor="black")

# Formatting
ax.set_xlabel("Year")
ax.set_ylabel("Topics")
ax.set_title("First and Last Appearance of Topics Over Time")
ax.grid(axis="x", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()
