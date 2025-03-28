import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pymongo import MongoClient

# MongoDB connection setup
tls_certificate_path = r"C:\Users\leagi\Documents\1_Master_Bioinformatik\WS_2024_25\Human-Computer Interaction\sys_map\zert.pem"

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
print(f'Number of matching entries: {len(data)}')

# Convert data to DataFrame
df = pd.DataFrame(data)

# Ensure 'year' column exists and convert to integer
df["year"] = pd.to_datetime(df["date_publication"], format="%d-%m-%Y", errors="coerce").dt.year

# Drop NaN values in 'year' column
df = df.dropna(subset=["year"]).copy()
df["year"] = df["year"].astype(int)  # Convert to integer

# Count occurrences of papers per year
year_counts = df["year"].value_counts().sort_index()

# Plot the bar chart
plt.figure(figsize=(12, 6))
sns.barplot(x=year_counts.index, y=year_counts.values, color="royalblue")

# Formatting
plt.xlabel("Publication Year")
plt.ylabel("Number of Papers")
plt.title("Distribution of Papers Across Publication Years")
plt.xticks(rotation=45)
plt.grid(axis='y', linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()


# Compute cumulative sum and percentage to get the table for contribution over the timeline
year_counts_cumsum = year_counts.cumsum()
total_papers = year_counts.sum()
year_counts_percentage = (year_counts_cumsum / total_papers) * 100

# Create a DataFrame for the table
cumulative_table = pd.DataFrame({
    "Year": year_counts.index,
    "Papers in Year": year_counts.values,
    "Cumulative Papers": year_counts_cumsum.values,
    "Cumulative Percentage": year_counts_percentage.values
})

# Display the table
import ace_tools_open as tools
tools.display_dataframe_to_user(name="Cumulative Paper Distribution", dataframe=cumulative_table)

# Plot the cumulative percentage curve
plt.figure(figsize=(12, 6))
sns.lineplot(x=year_counts.index, y=year_counts_percentage, marker="o", color="royalblue")

# Formatting
plt.xlabel("Publication Year")
plt.ylabel("Cumulative Percentage of Papers")
plt.title("Cumulative Percentage of Papers Over Time")
plt.xticks(rotation=45)
plt.grid(axis='both', linestyle="--", alpha=0.7)
plt.tight_layout()
plt.show()

# Save as a LaTeX table (.tex)
latex_table = cumulative_table.to_latex(index=False, column_format="|c|c|c|c|", caption="Cumulative Percentage of Papers Over Time", label="tab:cumulative_papers")
with open("cumulative_papers.tex", "w") as f:
    f.write(latex_table)