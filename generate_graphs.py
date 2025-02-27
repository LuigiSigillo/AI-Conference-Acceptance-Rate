import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import io
import re
import folium
from folium.plugins import MarkerCluster
from geopy.exc import GeocoderTimedOut, GeocoderServiceError
import time
from geopy.geocoders import Nominatim
from tqdm import tqdm
import random
import numpy as np
from selenium import webdriver

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
        elif '<summary>' in line and not "Geographic" in line:
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

def extract_values_location(cell):
    match = re.match(r'([A-Za-z\s]+),\s*([A-Za-z\s]+)', cell)
    if match:
        return match.group(1).strip(), match.group(2).strip()
    print(f"Failed to match: {cell}")
    return None, None

# Function to create a DataFrame from table data
def create_dataframe(table_data):
    df = pd.read_csv(io.StringIO(''.join(table_data)), sep='|', engine='python')
    df.columns = [col.strip() for col in df.columns]
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    df_y = df.iloc[1:2]  # Select only the first row (row index 1)
    # Create new DataFrame
    new_data = {'Year': [], 'Type': [], 'Value': []}

    for col in df_y.columns[2:]:
        percentage, first_num, second_num = extract_values(df_y[col][1])
        new_data['Year'].extend([col, col, col])
        new_data['Type'].extend(['Acceptance Rate', 'Accepted', 'Total'])
        new_data['Value'].extend([percentage, first_num, second_num])

    return pd.DataFrame(new_data)

# Function to create a DataFrame from table data
def create_dataframe_location(table_data):
    df = pd.read_csv(io.StringIO(''.join(table_data)), sep='|', engine='python')
    df.columns = [col.strip() for col in df.columns]
    df = df.dropna(axis=1, how='all').dropna(axis=0, how='all')
    df_l = df.iloc[2:3] 
    # Create new DataFrame
    new_data = {'Year': [], 'Type': [], 'Location': []}

    for col in df_l.columns[2:]:
        city, country = extract_values_location(df_l[col][2])
        new_data['Year'].extend([col, col])
        new_data['Type'].extend(['City', 'Country'])
        new_data['Location'].extend([city, country])

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

import matplotlib.colors as mcolors

# # Caching geocoded locations to avoid redundant API calls
geocode_cache = {}

def get_coordinates(location):
    """Convert location (City, Country) to latitude and longitude."""
    if location in geocode_cache:
        return geocode_cache[location]  # Return cached value

    geolocator = Nominatim(user_agent="geo_mapper")
    try:
        time.sleep(1)  # Avoid hitting API limits
        loc = geolocator.geocode(location)
        if loc:
            geocode_cache[location] = (loc.latitude, loc.longitude)
            return loc.latitude, loc.longitude
    except GeocoderTimedOut:
        print(f"Geocoding timed out for: {location}")
    return None, None  # Return None if not found
    
def get_conference_colors(conferences):
    """Assign a unique color to each conference."""
    color_list = list(mcolors.TABLEAU_COLORS.keys())  # Use predefined colors
    random.shuffle(color_list)  # Shuffle to distribute colors randomly
    return {conf: color_list[i % len(color_list)] for i, conf in enumerate(conferences)}
# def save_map_as_png(html_file, output_file):
#     """Convert Folium HTML map to PNG using Selenium."""
#     options = webdriver.ChromeOptions()
#     options.add_argument("--headless")
#     options.add_argument("--window-size=1200x800")  # Set window size for full capture

#     driver = webdriver.Chrome(options=options)
#     driver.get(f"file://{html_file}")

#     # Wait to ensure map is fully loaded
#     time.sleep(3)

#     # Save screenshot
#     driver.save_screenshot(output_file)
#     driver.quit()
#     print(f"Map saved as {output_file}")

# def add_legend(map_, conference_colors):
#     """Add a legend to the Folium map."""
#     legend_html = '''
#     <div style="position: fixed; 
#                 bottom: 50px; left: 50px; width: 200px; height: auto; 
#                 background-color: white; z-index:9999; font-size:14px;
#                 border:2px solid grey; padding: 10px;">
#     <h4>Conference Colors</h4>
#     '''
#     for conf, color in conference_colors.items():
#         legend_html += f'<i style="background:{color};width:20px;height:20px;display:inline-block;"></i> {conf}<br>'
#     legend_html += '</div>'
#     map_.get_root().html.add_child(folium.Element(legend_html))

# def visualize_locations(lines, save_as_png=True, output_file="conference_map.png"):
#         # Extract all tables
#     tables = extract_table_data(lines)
#     # Combine data for all conferences
#     combined_data = []
#     for (conference_name, short_conf_name), table_data in tables.items():
#         df = create_dataframe_location(table_data)
#         df['Conference'] = short_conf_name
#         df['Year'] = df['Year'].astype(str)  # Ensure year is string for labeling
#         # df['Lat'], df['Lon'] = zip(*df['Location'].apply(get_coordinates))  # Geocode locations
#         combined_data.append(df)

#     combined_df = pd.concat(combined_data).reset_index(drop=True)
#     # Filter out rows where the city is "Virtual" and the country is "Event"
#     combined_df = combined_df[~((combined_df['Type'] == 'City') & (combined_df['Location'] == 'Virtual'))]
#     combined_df = combined_df[~((combined_df['Type'] == 'Country') & (combined_df['Location'] == 'Event'))]
#     # Apply geocoding only to locations with Type == 'City'
#     city_df = combined_df[combined_df['Type'] == 'City'].copy()
#     city_df['Lat'], city_df['Lon'] = zip(*city_df['Location'].apply(get_coordinates))
#     combined_df = combined_df.merge(city_df[['Location', 'Lat', 'Lon']], on='Location', how='left')

#     # Count the occurrences of each city and country
#     city_counts = combined_df[combined_df['Type'] == 'City']['Location'].value_counts().head(10)
#     country_counts = combined_df[combined_df['Type'] == 'Country']['Location'].value_counts().head(10)

#     # Print the counts
#     print("City counts:")
#     for city, count in city_counts.items():
#         print(f"{city}: {count}")

#     print("\nCountry counts:")
#     for country, count in country_counts.items():
#         print(f"{country}: {count}")
    
    
#     # Print the top 5 locations for each conference
#     conferences = combined_df['Conference'].unique()
#     for conference in conferences:
#         print(f"\nTop 5 locations for {conference}:")
#         conference_df = combined_df[combined_df['Conference'] == conference]
#         city_counts = conference_df[conference_df['Type'] == 'City']['Location'].value_counts().head(5)
#         country_counts = conference_df[conference_df['Type'] == 'Country']['Location'].value_counts().head(5)
        
#         print("Cities:")
#         for city, count in city_counts.items():
#             print(f"{city}: {count}")
        
#         print("Countries:")
#         for country, count in country_counts.items():
#             print(f"{country}: {count}")


#     # Assign colors to conferences
#     combined_df = combined_df.dropna(subset=['Lat', 'Lon'])
#     conference_colors = get_conference_colors(combined_df['Conference'].unique())

#     # Create a folium map centered around a reasonable default
#     map_center = [combined_df["Lat"].mean(), combined_df["Lon"].mean()]
#     map_ = folium.Map(location=map_center, zoom_start=2)

#     # Add markers
#     for _, row in combined_df.iterrows():
#         conf_name = row['Conference']
#         year = row['Year']
#         location = row['Location']
#         lat, lon = row['Lat'], row['Lon']
#         color = conference_colors[conf_name]
#         if location is not None:
#             # Create a marker with the conference name and year
#             folium.Marker(
#                 location=[lat, lon],
#                 popup=f"{conf_name} {year} ({location})",
#                 icon=folium.Icon(color=color)
#             ).add_to(map_)
#     # Add legend to the map
#     add_legend(map_, conference_colors)
#     # Save as HTML
#     html_file = "conference_map.html"
#     map_.save(html_file)

#     if save_as_png:
#         # Convert HTML to PNG using Selenium
#         save_map_as_png(html_file, output_file)

#     return map_

import geopandas as gpd
from shapely.geometry import Point

def visualize_locations_geopandas(lines, output_file="graphs/maps/conference_map_geopandas.png"):
    # Extract location tables for geocoding
    tables = extract_table_data(lines)
    location_data = []
    submission_data = []
    for (conference_name, short_conf_name), table_data in tables.items():
        # For location data (used for geocoding)
        df_loc = create_dataframe_location(table_data)
        df_loc['Conference'] = short_conf_name
        df_loc['Year'] = df_loc['Year'].astype(str)
        location_data.append(df_loc)

        # Also extract submission data from the acceptance table
        df_sub = create_dataframe(table_data)
        df_sub['Conference'] = short_conf_name
        submission_data.append(df_sub)
    
    # Build DataFrames
    loc_df = pd.concat(location_data).reset_index(drop=True)
    sub_df = pd.concat(submission_data).reset_index(drop=True)
    

    
    # Count the occurrences of each city and country
    city_counts = loc_df[loc_df['Type'] == 'City']['Location'].value_counts().head(11)
    country_counts = loc_df[loc_df['Type'] == 'Country']['Location'].value_counts().head(11)

    # Print the counts in Markdown table format

    print("### City Counts")
    print("| City | Count |")
    print("| --- | --- |")
    for city, count in city_counts.items():
        print(f"| {city} | {count} |")

    print("\n### Country Counts")
    print("| Country | Count |")
    print("| --- | --- |")
    for country, count in country_counts.items():
        print(f"| {country} | {count} |")


    # Print Markdown tables for the top 5 locations for each conference
    # conferences = sub_df['Conference'].unique()
    # for conference in conferences:
    #     print(f"\n#### Top 5 Locations for {conference}")
    #     # Cities table
    #     print("\n**Cities:**")
    #     print("| City | Count |")
    #     print("| --- | --- |")
    #     conference_df = loc_df[loc_df['Conference'] == conference]
    #     city_counts_top = conference_df[conference_df['Type'] == 'City']['Location'].value_counts().head(5)
    #     for city, count in city_counts_top.items():
    #         print(f"| {city} | {count} |")
        
    #     # Countries table
    #     print("\n**Countries:**")
    #     print("| Country | Count |")
    #     print("| --- | --- |")
    #     country_counts_top = conference_df[conference_df['Type'] == 'Country']['Location'].value_counts().head(5)
    #     for country, count in country_counts_top.items():
    #         print(f"| {country} | {count} |")
   
    # Compute top 10 conferences by submissions
    sub_df['Value'] = pd.to_numeric(sub_df['Value'], errors='coerce')
    total_submissions = sub_df[sub_df['Type'] == 'Total']
    top_conferences = total_submissions.groupby('Conference')['Value'].sum().nlargest(10).index.tolist()
    # Filter location data to only those top conferences
    loc_df = loc_df[loc_df['Conference'].isin(top_conferences)]
    
    # Filter out unwanted rows
    loc_df = loc_df[~((loc_df['Type'] == 'City') & (loc_df['Location'] == 'Virtual'))]
    loc_df = loc_df[~((loc_df['Type'] == 'Country') & (loc_df['Location'] == 'Event'))]
    
    # Geocode only locations with Type == 'City'
    city_df = loc_df[loc_df['Type'] == 'City'].copy()
    coords = city_df['Location'].apply(lambda loc: get_coordinates(loc) or (None, None))
    city_df['Lat'], city_df['Lon'] = zip(*coords)
    loc_df = loc_df.merge(city_df[['Location', 'Lat', 'Lon']], on='Location', how='left')
    loc_df = loc_df.dropna(subset=['Lat', 'Lon'])
    
    # Assign colors to conferences (only for those in the top 10)
    conference_colors = get_conference_colors(loc_df['Conference'].unique())
    
    # Create a GeoDataFrame using the conference locations
    geometry = [Point(lon, lat) for lon, lat in zip(loc_df['Lon'], loc_df['Lat'])]
    gdf = gpd.GeoDataFrame(loc_df, geometry=geometry, crs="EPSG:4326")
    
    # Load a world map from an external GeoJSON resource
    world = gpd.read_file("https://raw.githubusercontent.com/datasets/geo-countries/master/data/countries.geojson")    
    
    # Plot the world map and each conference's locations with its unique color
    fig, ax = plt.subplots(1, 1, figsize=(15, 10))
    world.plot(ax=ax, color='lightgrey', edgecolor='white')
    
    for conf in gdf['Conference'].unique():
        conf_gdf = gdf[gdf['Conference'] == conf]
        conf_gdf.plot(
            ax=ax,
            markersize=100,
            marker='o',
            color=conference_colors[conf],
            label=conf,
            alpha=0.7
        )
    
    ax.set_title("Top 10 Conference Locations by Submissions")
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(title="Conference")
    
    plt.savefig(output_file, dpi=300, bbox_inches='tight', pad_inches=0)
    # plt.show()
    # Define bounding boxes for continents
    # Define bounding boxes for continents, including Africa and Australia
    continents = {
        "Americas": {"lon_min": -170, "lon_max": -30, "lat_min": -60, "lat_max": 75},
        "Europe": {"lon_min": -25, "lon_max": 40, "lat_min": 34, "lat_max": 72},
        "Asia": {"lon_min": 25, "lon_max": 180, "lat_min": 5, "lat_max": 80},
        "Africa": {"lon_min": -20, "lon_max": 55, "lat_min": -35, "lat_max": 38},
        "Australia": {"lon_min": 110, "lon_max": 155, "lat_min": -45, "lat_max": -10},
    }
    
    # Create separate maps for each continent
    for cont, bounds in continents.items():
        fig, ax = plt.subplots(1, 1, figsize=(15, 10))
        # Plot world countries and limit the view to the bounding box
        world.plot(ax=ax, color='lightgrey', edgecolor='white')
        ax.set_xlim(bounds["lon_min"], bounds["lon_max"])
        ax.set_ylim(bounds["lat_min"], bounds["lat_max"])
        
        # Filter conference points within the bounding box
        cont_points = gdf[
            (gdf['Lon'] >= bounds["lon_min"]) &
            (gdf['Lon'] <= bounds["lon_max"]) &
            (gdf['Lat'] >= bounds["lat_min"]) &
            (gdf['Lat'] <= bounds["lat_max"])
        ]
        
        for conf in cont_points['Conference'].unique():
            conf_gdf = cont_points[cont_points['Conference'] == conf]
            conf_gdf.plot(
                ax=ax,
                markersize=100,
                marker='o',
                color=conference_colors[conf],
                label=conf,
                alpha=0.7
            )
        
        ax.set_title(f"Top 10 Conference Locations in {cont}")
        ax.set_xlabel("Longitude")
        ax.set_ylabel("Latitude")
        ax.legend(title="Conference")
        
        plt.savefig(f"graphs/maps/conference_map_geopandas_{cont.lower()}.png", dpi=300, bbox_inches='tight', pad_inches=0)
        plt.close()


if __name__ == '__main__':
    # Read the markdown file
    with open('README.md', 'r', encoding='utf-8') as f:
        lines = f.readlines()

        generate_single_plots(lines)
        generate_all_plots(lines)
        generate_all_plots_macrocat(lines)
        visualize_locations_geopandas(lines)