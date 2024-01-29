import requests
from bs4 import BeautifulSoup
import pandas as pd
import concurrent.futures


# Constants
BASE_URL = "https://www.justwatch.com"

# Improved error handling and request sessions
def fetch_url(url):
    try:
        response = requests.get(url, verify=False)
        response.raise_for_status()
        return response.text
    except requests.RequestException as e:
        print(f"Error fetching URL: {url}, Error: {e}")
        return None

def get_movies_from_url(url):
    html_content = fetch_url(url)
    if not html_content:
        return []

    soup = BeautifulSoup(html_content, 'html.parser')
    div = soup.find('div', class_='title-list-grid')

    return [BASE_URL + link.get('href') for link in div.find_all('a', class_='title-list-grid__item--link')] if div else []

def get_movie_info(url):
    html_content = fetch_url(url)
    if not html_content:
        return None

    soup = BeautifulSoup(html_content, 'html.parser')
    title = soup.find('div', class_='title-block')
    movie_name = title.get_text().strip() if title else 'Unknown'

    data_dict = {'movie_url': url, 'movie_name': movie_name, 'movie_details': None}
    article = soup.find('article', class_='buybox')

    if article:
        sibling = article.next_sibling.next_sibling
        if sibling and sibling.p:
            data_dict['movie_details'] = sibling.p.get_text().strip()

    for tag in soup.find_all('div', class_='detail-infos'):
        data = tag.find('h3', class_='detail-infos__subheading')
        value = tag.find('div', class_='detail-infos__value')
        if data and value:
            data_dict[data.get_text(strip=True)[:19].strip()] = value.get_text(strip=True)

    return data_dict

def get_cleaned_df_from_movies_data(final_data):
    df = pd.DataFrame(final_data)
    df['age_rating'] = df['Age rating'].str.strip()
    df['ratings'] = df['Rating'].str.extract(r'(\d+\.\d+)').astype(float)
    df[['movie_name', 'release_year']] = df['movie_name'].str.extract(r'(.*) \((\d{4})\)')
    df['genres'] = df['Genres']
    df['runtime'] = df['Runtime']
    df['production_country'] = df['Production country']
    df['director_name'] = df['Director']
    df['release_year'] = df['release_year'].astype(int)
    df['movie_details'] = df['movie_details'].str.strip()
    return df[["movie_name","movie_details","ratings","age_rating","release_year","genres","runtime","production_country","director_name"]]

def main_scraper(url):
    movies_list = get_movies_from_url(url)

    # Use ThreadPoolExecutor for parallel requests
    with concurrent.futures.ThreadPoolExecutor(max_workers=100) as executor:
        # Map the function to the movies list and execute in parallel
        future_to_url = {executor.submit(get_movie_info, movie_url): movie_url for movie_url in movies_list}
        final_data = []
        for future in concurrent.futures.as_completed(future_to_url):
            try:
                data = future.result()
                if data:
                    final_data.append(data)
            except Exception as exc:
                print(f'Generated an exception: {exc}')

    cleaned_df = get_cleaned_df_from_movies_data(final_data)
    return cleaned_df



# Example usage
url = 'https://www.justwatch.com/in/movies?release_year_from=2000'


df = main_scraper(url)
top_movies = df.sort_values(by=['release_year','ratings'], ascending=False).reset_index(drop=True)

# Convert DataFrame to HTML
html_table = top_movies.to_html(classes="table table-striped", index=False, escape=False)

# Add CSS for styling
html_output = f"""
<html>
<head>
    <title>Top Movies</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            background-color: #f4f4f4;
            color: #333;
        }}
        h1 {{
            color: #0066cc;
            text-align: center;
        }}
        .table {{
            border-collapse: collapse;
            margin: 25px 0;
            font-size: 0.9em;
            min-width: 400px;
            border-radius: 5px 5px 0 0;
            overflow: hidden;
            box-shadow: 0 0 20px rgba(0, 0, 0, 0.15);
        }}
        .table-striped tbody tr:nth-of-type(odd) {{
            background-color: #f3f3f3;
        }}
        .table thead tr {{
            background-color: #009879;
            color: #ffffff;
            text-align: left;
        }}
        .table th, 
        .table td {{
            padding: 12px 15px;
        }}
        .table td {{
            border-bottom: 1px solid #dddddd;
        }}
    </style>
</head>
<body>
    <h1>Top Movies</h1>
    {html_table}
</body>
</html>
"""

import os

# Your file path
file_path = 'docs/index.html'

# Check if the directory exists
dir_name = os.path.dirname(file_path)
if not os.path.exists(dir_name):
    # If the directory does not exist, create it
    os.makedirs(dir_name)

# Write the HTML output to a file
with open(file_path, 'w', encoding='utf-8') as file:
    file.write(html_output)

