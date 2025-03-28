import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient

# Plotting style
plt.rcParams.update({
    'font.size': 13,
    'axes.titlesize': 19,
    'axes.labelsize': 14,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14,
})

# MongoDB connection setup
tls_certificate_path = r"C:\Users\leagi\Documents\1_Master_Bioinformatik\WS_2024_25\Human-Computer Interaction\sys_map\zert.pem"

CONNECTION_STRING = (
    "mongodb+srv://hci.9iakh.mongodb.net/"
    "?authSource=%24external&authMechanism=MONGODB-X509"
    f"&tls=true&tlsCertificateKeyFile={tls_certificate_path}"
)

mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]
collection = db["ACM_paper_filter3"]

# Query: Select entries where "CoMo-12_03" is "yes" and key exists
query = {
    "CoMo-12_03": "yes",
    "como-tax-openess2-2": {"$exists": True}
}
entries = list(collection.find(query))

# Define the relevant keys to analyze
base_keys = [
    "como-tax-topic2", "como-tax-type_of_evaluation2", "como-tax-target_user_group2",
    "como-tax-research_problem2", "como-tax-openess2", "como-tax-modelling_approach2",
    "como-tax-improvement_proposal2", "como-tax-ethics2", "como-tax-data_used2", "como-tax-contribution2"
]

# Include versions (-2, -3, ...) for each key
keys_to_compare = []
for key in base_keys:
    for i in range(1, 5):  # 4 versions and the base keys
        keys_to_compare.append(f"{key}-{i}")

# Include base keys to keys_to_compare
keys_to_compare.extend(base_keys)

# Process data into a DataFrame
papers = []
for entry in entries:
    paper_data = {"Paper": str(entry.get("_id"))}  # Use MongoDB _id as Paper ID

    for key in keys_to_compare:
        if key in entry:  # Only include existing keys
            paper_data[key] = entry[key]

    papers.append(paper_data)

df = pd.DataFrame(papers)

# Extract unique category prefixes (e.g., "como-tax-topic2")
category_prefixes = set(col.rsplit("-", 1)[0] for col in df.columns if col != "Paper")

# **Compute Consistency Scores**
consistency_scores = {}

for cat in category_prefixes:
    category_cols = [col for col in df.columns if col.startswith(cat)]  # Get all category versions

    if len(category_cols) > 1:  # Ensure multiple versions exist for comparison
        consistency_per_paper = []

        for index, row in df.iterrows():
            labels = row[category_cols].dropna().tolist()  # Get assigned labels for this paper

            if labels:  # Ensure there are assigned labels
                most_frequent_label_count = max(pd.Series(labels).value_counts())  # Count most frequent label
                total_labels = len(labels)  # Total assigned labels
                consistency_score = most_frequent_label_count / total_labels  # Compute consistency
            else:
                consistency_score = np.nan  # No labels assigned

            consistency_per_paper.append(consistency_score)

        consistency_scores[cat] = consistency_per_paper

# Convert to DataFrame
consistency_df = pd.DataFrame(consistency_scores, index=df["Paper"])

# remove the invalid category
invalid_category = ["como-tax"]  # Define the invalid category

# Remove invalid categories from plotting
valid_categories = [cat for cat in consistency_df.columns if cat not in invalid_category]
consistency_df_filtered = consistency_df[valid_categories]  # Filter out invalid category

# Rename columns
renamed_columns = {
    col: col.replace("como-tax-", "").replace("2", "") for col in consistency_df_filtered.columns
}
consistency_df_filtered.rename(columns=renamed_columns, inplace=True)


# **Print Assigned Labels for Each Paper**
for index, row in df.iterrows():
    print(f"\n📄 Paper ID: {row['Paper']}")

    for category in category_prefixes:
        assigned_labels = row[[col for col in df.columns if col.startswith(category)]].dropna().tolist()
        print(f"{category}: {assigned_labels}" if assigned_labels else f"{category}: No labels assigned")

# **Bar Plot: Average Consistency Per Category**
plt.figure(figsize=(12, 6))
consistency_df_filtered.mean().sort_values().plot(kind="bar", color="skyblue", edgecolor="black")
plt.title("Average Consistency Across Categories")
plt.ylabel("Average Consistency Score")
plt.xticks(rotation=30, ha="right")
plt.ylim(0, 1.0)
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()

# **Heatmap: Consistency Per Paper-Category**
plt.figure(figsize=(12, 6))
sns.heatmap(consistency_df_filtered, annot=True, cmap="coolwarm", fmt=".2f", linewidths=0.5)
plt.title("Consistency Score Per Paper-Category")
plt.ylabel("Paper ID")
plt.xlabel("Category")
plt.xticks(rotation=45, ha="right")
plt.tight_layout()
plt.show()

# **Boxplot: Consistency Score Distribution**
plt.figure(figsize=(12, 6))
sns.boxplot(data=consistency_df_filtered, palette="coolwarm")
plt.title("Consistency Score Distribution Across Categories")
plt.ylabel("Consistency Score")
plt.xticks(rotation=45, ha="right")
plt.ylim(0, 1.0)
plt.grid(axis="y", linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()
