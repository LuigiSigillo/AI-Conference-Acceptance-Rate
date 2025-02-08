import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import re
import numpy as np
def remove_emoji(text):
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F1E0-\U0001F1FF"  # flags (iOS)
        "\U00002702-\U000027B0"  # other symbols
        "\U000024C2-\U0001F251"
        "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
        "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
        "\U0001F700-\U0001F77F"  # Alchemical Symbols
        "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
        "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
        "]+", flags=re.UNICODE)
    return emoji_pattern.sub(r'', text).strip()

# Function to extract table data and macrocategory
def extract_table_data(lines):
    tables = {}
    capture = False
    current_table = []
    conference_name = None
    macrocategory = None

    for line in lines:
        if "to add a " in line:
            break
        if line.startswith('##'):
            macrocategory = line.strip().replace('##', '').strip()
            macrocategory = remove_emoji(macrocategory)
        elif '<summary>' in line:
            capture = True
            conference_name = re.search(r'<summary><b><font size="4">(.*?)</font></b></summary>', line).group(1)
            conference_name = conference_name.split("-")[0].strip()
            current_table = []
        elif '</details>' in line:
            capture = False
            if conference_name and current_table:
                tables[(macrocategory, conference_name)] = current_table
        elif capture:
            current_table.append(line)
    
    return tables

def extract_values(cell):
    match = re.match(r' (\d+\.\d+)% \((\d+)/(\d+)\) ', cell)
    if match:
        return float(match.group(1)), int(match.group(2)), int(match.group(3))
    print(f"Failed to match: {cell}")
    return None, None, None
# Function to create a DataFrame from table data
def create_dataframe(table_data):
    df = pd.read_csv(io.StringIO(''.join(table_data)), sep='|', engine='python')
    df.columns = [col.strip() for col in df.columns]
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    df = df.iloc[1:2]  # Select only the first row (row index 1)
    # Create new DataFrame
    new_data = {'Year': [], 'Type': [], 'Value': []}

    for col in df.columns[2:]:
        percentage, first_num, second_num = extract_values(df[col][1])
        new_data['Year'].extend([col, col, col])
        new_data['Type'].extend(['Acceptance Rate', 'Accepted', 'Total'])
        new_data['Value'].extend([percentage, first_num, second_num])
    return pd.DataFrame(new_data)

# Function to plot data
def plot_ok(conf_name, years, submission_numbers, accepted_numbers, acceptance_rates):
    data = pd.DataFrame({
        'Year': years,
        'Submissions': submission_numbers,
        'Accepted': accepted_numbers,
        'Acceptance Rate': acceptance_rates
    })

    # Set the style
    sns.set_theme()

    # Create figure and axis
    fig, ax1 = plt.subplots(figsize=(12, 6))

    # Plot submission and accepted numbers as bar chart
    bar_width = 0.35
    index = np.arange(len(years))

    sns.barplot(x='Year', y='Submissions', data=data, color='tab:blue', alpha=0.6, label='Submissions', ax=ax1)
    sns.barplot(x='Year', y='Accepted', data=data, color='tab:green', alpha=0.6, label='Accepted Papers', ax=ax1)

    ax1.set_xlabel('Year')
    ax1.set_ylabel('Number of Papers', color='tab:blue')
    ax1.tick_params(axis='y', labelcolor='tab:blue')

    # Create a second y-axis for the acceptance rates
    ax2 = ax1.twinx()
    sns.lineplot(x='Year', y='Acceptance Rate', data=data, color='tab:red', marker='o', label='Acceptance Rate', ax=ax2)
    ax2.set_ylabel('Acceptance Rate (%)', color='tab:red')
    ax2.tick_params(axis='y', labelcolor='tab:red')

    # Disable grid lines for the secondary y-axis
    ax2.grid(False)

    # Remove NaN or infinite values from acceptance_rates
    cleaned_acceptance_rates = [rate for rate in acceptance_rates if not (np.isnan(rate) or np.isinf(rate))]

    # Set y-axis limits for acceptance rates
    if cleaned_acceptance_rates:
        ax2.set_ylim(min(cleaned_acceptance_rates) - 5, max(cleaned_acceptance_rates) + 5)

    # Annotate each point with the acceptance rate percentage
    for i, rate in enumerate(acceptance_rates):
        ax2.text(i, rate + 0.5, f'{rate}%', color='tab:red', ha='center')

    # Add title and legend
    plt.title(conf_name+' Submission Numbers, Accepted Papers, and Acceptance Rates Over the Years')
    fig.tight_layout()

    # Add legends
    ax1.legend(loc='upper left')
    ax2.legend(loc='upper right')


    # Save the plot
    plt.savefig("graphs/singles/"+conf_name.lower().rstrip()+".png", dpi=300)
    plt.close()

# Plot the combined data
def plot_combined_data(combined_df):
    sns.set_theme()

    # Create figure and axes
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 9))

    # Plot acceptance rates as line chart
    sns.lineplot(x='Year', y='Value', hue='Color', data=combined_df[combined_df['Type'] == 'Acceptance Rate'],
                  marker='o', ax=ax1, palette='tab10', legend=True)
    ax1.set_ylabel('Acceptance Rate (%)', color='tab:red')
    ax1.tick_params(axis='y', labelcolor='tab:red')
    ax1.set_title('Acceptance Rates Over the Years')
    ax1.grid(True)

    # Set y-axis limits for acceptance rates
    acceptance_rates = combined_df[combined_df['Type'] == 'Acceptance Rate']['Value']
    cleaned_acceptance_rates = [rate for rate in acceptance_rates if not (np.isnan(rate) or np.isinf(rate))]
    if cleaned_acceptance_rates:
        ax1.set_ylim(min(cleaned_acceptance_rates) - 5, max(cleaned_acceptance_rates) + 5)

    # Plot submissions as line chart
    sns.lineplot(x='Year', y='Value', hue='Color', data=combined_df[combined_df['Type'] == 'Total'],
                  marker='o', ax=ax2, palette='tab10', legend=True)
    ax2.set_ylabel('Number of Submissions', color='tab:blue')
    ax2.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_title('Submissions Over the Years')
    ax2.grid(True)

    # Adjust layout
    fig.tight_layout()
    plt.subplots_adjust(top=0.9, bottom=0.1, left=0.05, right=0.95)

    # Save the plot
    plt.savefig("graphs/combined_plot.png", dpi=300)
    plt.close()

# Function to plot data for a macrocategory
def plot_macrocategory_data(combined_df, macrocategory):
    sns.set_theme()

    # Filter data for the macrocategory
    macro_df = combined_df[combined_df['Macrocategory'] == macrocategory].copy()

    # Identify the top 10 conferences by the number of submissions
    total_submissions = macro_df[macro_df['Type'] == 'Total']
    top_conferences = total_submissions.groupby('Conference')['Value'].sum().nlargest(10).index

    # Assign colors to conferences
    macro_df.loc[:, 'Color'] = macro_df['Conference'].apply(lambda x: x if x in top_conferences else 'Other')

    # Create figure and axes
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(18, 6))

    # Plot acceptance rates as line chart
    sns.lineplot(x='Year', y='Value', hue='Color', data=macro_df[macro_df['Type'] == 'Acceptance Rate'], marker='o', ax=ax1, palette='tab10', legend=True)
    ax1.set_ylabel('Acceptance Rate (%)', color='tab:red')
    ax1.tick_params(axis='y', labelcolor='tab:red')
    ax1.set_title(f'Acceptance Rates Over the Years')
    ax1.grid(True)

    # Set y-axis limits for acceptance rates
    acceptance_rates = macro_df[macro_df['Type'] == 'Acceptance Rate']['Value']
    cleaned_acceptance_rates = [rate for rate in acceptance_rates if not (np.isnan(rate) or np.isinf(rate))]
    if cleaned_acceptance_rates:
        ax1.set_ylim(min(cleaned_acceptance_rates) - 5, max(cleaned_acceptance_rates) + 5)

    # Plot submissions as line chart
    sns.lineplot(x='Year', y='Value', hue='Color', data=macro_df[macro_df['Type'] == 'Total'], marker='o', ax=ax2, palette='tab10', legend=True)
    ax2.set_ylabel('Number of Submissions', color='tab:blue')
    ax2.tick_params(axis='y', labelcolor='tab:blue')
    ax2.set_title(f'Submissions Over the Years')
    ax2.grid(True)

    # Adjust layout
    fig.tight_layout()
    plt.subplots_adjust(top=0.9, bottom=0.1, left=0.05, right=0.95)

   
    # Set the title of the plot to the macrocategory
    fig.suptitle(macrocategory, fontsize=16)

    # Save the plot
    plt.savefig(f"graphs/multi/{macrocategory}_combined_plot.png", dpi=300)
    plt.close()



def generate_single_plots(lines):
    # Extract all tables
    tables = extract_table_data(lines)

    # Create DataFrames and plot data for each conference
    for (conference_name,short_conf_name), table_data in tables.items():
        df = create_dataframe(table_data)
        years = df['Year'].unique().tolist()
        acceptance_rates = df[df['Type'] == 'Acceptance Rate']['Value'].tolist()
        accepted_numbers = df[df['Type'] == 'Accepted']['Value'].tolist()
        submission_numbers = df[df['Type'] == 'Total']['Value'].tolist()
        plot_ok(short_conf_name, years, submission_numbers, accepted_numbers, acceptance_rates)

def generate_all_plots(lines,num_categories=10):
    # Extract all tables
    tables = extract_table_data(lines)

    # Combine data for all conferences
    combined_data = []
    # Define the number of unique categories
    for (conference_name,short_conf_name), table_data in tables.items():
        df = create_dataframe(table_data)
        df['Conference'] = short_conf_name
        combined_data.append(df)

    combined_df = pd.concat(combined_data).reset_index(drop=True)

    # Convert 'Year' column to numeric and sort by 'Year'
    combined_df['Year'] = pd.to_numeric(combined_df['Year'], errors='coerce')
    combined_df = combined_df.sort_values(by='Year')

    # Convert 'Value' column to numeric, forcing errors to NaN
    combined_df['Value'] = pd.to_numeric(combined_df['Value'], errors='coerce')

    # Identify the top 10 conferences by the number of submissions
    total_submissions = combined_df[combined_df['Type'] == 'Total']
    top_conferences = total_submissions.groupby('Conference')['Value'].sum().nlargest(num_categories).index

    # Assign colors to conferences
    combined_df['Color'] = combined_df['Conference'].apply(lambda x: x if x in top_conferences else 'Other')
    plot_combined_data(combined_df)

def generate_all_plots_macrocat(lines):
    # Extract all tables
    tables = extract_table_data(lines)

    # Combine data for all conferences
    combined_data = []

    for (macrocategory, conference_name), table_data in tables.items():
        df = create_dataframe(table_data)
        df['Conference'] = conference_name
        df['Macrocategory'] = macrocategory
        combined_data.append(df)

    combined_df = pd.concat(combined_data).reset_index(drop=True)

    # Convert 'Year' column to numeric and sort by 'Year'
    combined_df['Year'] = pd.to_numeric(combined_df['Year'], errors='coerce')
    combined_df = combined_df.sort_values(by='Year')

    # Convert 'Value' column to numeric, forcing errors to NaN
    combined_df['Value'] = pd.to_numeric(combined_df['Value'], errors='coerce')

    # Generate plots for each macrocategory
    macrocategories = combined_df['Macrocategory'].unique()
    for macrocategory in macrocategories:
        plot_macrocategory_data(combined_df, macrocategory)

if __name__ == '__main__':
    # Read the markdown file
    with open('README.md', 'r') as f:
        lines = f.readlines()

        generate_single_plots(lines)
        generate_all_plots(lines)
        generate_all_plots_macrocat(lines)