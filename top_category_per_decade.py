import pandas as pd
from pymongo import MongoClient
import matplotlib.pyplot as plt
import os

# Plotting Style
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

svg_output_folder = r"SVG_Plots"
os.makedirs(svg_output_folder, exist_ok=True)

# Initialize MongoDB connection
mongo_client = MongoClient(CONNECTION_STRING)
db = mongo_client["HCI"]
collection = db["ACM_paper_filter3"]

# Fetch data from MongoDB
query = {"CoMo-12_03" : "yes"}
data = list(collection.find(query))

# Convert data to DataFrame
df = pd.DataFrame(data)

# Ensure 'year' and 'decade' columns exist
df["year"] = pd.to_datetime(df["date_publication"], format="%d-%m-%Y", errors="coerce").dt.year
df["decade"] = (df["year"] // 10) * 10  # Grouping into 5-year intervals

# Drop rows where 'year' is NaN
df = df.dropna(subset=["year"])

# Define keys to process
keys_list = [
    "como-tax-topic2", "como-tax-ethics2", "como-tax-modelling_approach2",
    "como-tax-contribution2", "como-tax-improvement_proposal2",
    "como-tax-research_problem2", "como-tax-type_of_evaluation2",
    "como-tax-openess2", "como-tax-target_user_group2", "como-tax-data_used2"
]

# Create output directory for CSVs
output_folder = "CHI_percentages_per_decade"
os.makedirs(output_folder, exist_ok=True)

# Define a fixed color for 'invalid result'
custom_colors = {
    "invalid result": "black",
}

# Process each key
for key in keys_list:
    if key not in df.columns:
        print(f"Skipping '{key}' as it is not found in the DataFrame.")
        continue

    # Drop rows where key is NaN
    df_filtered = df.dropna(subset=[key])

    # Count occurrences of each key per decade
    value_counts = df_filtered.groupby(["decade", key]).size().reset_index(name="count")

    # Get the most common values per decade
    top_values = value_counts.sort_values(["decade", "count"], ascending=[True, False])
    top_value = top_values.groupby("decade").head(1)
    print(f"Most frequent value for {key}: {top_value}")

    # Pivot for stacked bar chart
    pivot_df = top_values.pivot(index="decade", columns=key, values="count").fillna(0)
    pivot_df.index = pivot_df.index.astype(int)

    # Get total counts per decade for percentage calculation
    total_counts = value_counts.groupby("decade")["count"].sum().reset_index(name="total")

    # Merge total counts and compute percentage
    value_counts = value_counts.merge(total_counts, on="decade")
    value_counts["percentage"] = (value_counts["count"] / value_counts["total"]) * 100

    # Pivot data for CSV
    percentage_pivot = value_counts.pivot(index="decade", columns=key, values="percentage").fillna(0)

    # Round values to 1 decimal
    percentage_pivot = percentage_pivot.round(1)

    # Save percentage data to CSV
    csv_filename = os.path.join(output_folder, f"CHI_percentage_{key}.csv")
    percentage_pivot.to_csv(csv_filename)
    print(f"Saved '{key}' percentage data to: {csv_filename}")

    key_name = key.split("-")[-1]
    key_name = key_name.replace("2", "")

    # Determine colors for each category in the current key
    column_categories = pivot_df.columns.tolist()
    colors = [custom_colors.get(col, None) for col in column_categories]

    # Use a default colormap for non-specified categories
    from itertools import cycle

    default_colors = cycle(plt.cm.tab20.colors)

    # Fill in unspecified colors
    final_colors = [color if color else next(default_colors) for color in colors]


    # Plot stacked bar chart
    pivot_df.plot(kind="bar", stacked=True, figsize=(14, 7), color=final_colors)
    plt.xlabel("Decade")
    plt.ylabel("Count")
    plt.title(f"'{key_name}' Values Per Decade")

    # Next line only for the Topic Plot:
    if key_name == "topic":
        plt.legend(title=key_name, bbox_to_anchor=(1.05, 1), loc='upper left')  # Moves legend outside the plot

    else:
        plt.legend(title=key_name, loc="upper left", bbox_to_anchor=(0.02, 0.98))
    plt.xticks(rotation=45)
    plt.tight_layout()

    svg_filename = os.path.join(svg_output_folder, f"{key_name}.pdf")
    plt.savefig(svg_filename, format="pdf")
    plt.show()
