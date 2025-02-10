from flask import Flask, render_template, request
import requests
import os
import csv
import io
import time
import difflib

app = Flask(__name__, template_folder="templates")  # Ensures Flask finds the templates folder

# Add your Google Places API Key here
GOOGLE_PLACES_API_KEY = "AIzaSyBKV3J2dZprkaubf99rMp-qQGE10uTMOcw"  # Replace with your actual API key

# List of common words to exclude from phrase match
COMMON_WORDS = {"vision", "optical", "care", "eye", "clinic", "center", "hospital", "sight", "health"}

# Function to format competitor names into phrase match format
def format_phrase_match(name):
    words = name.split()
    filtered_words = [word for word in words if word.lower() not in COMMON_WORDS]
    return f'"{" ".join(filtered_words)}"' if filtered_words else f'"{name}"'

# Function to check if two names are similar
def is_similar(name1, name2, threshold=0.6):  # Adjusted threshold to be less strict
    return difflib.SequenceMatcher(None, name1.lower(), name2.lower()).ratio() > threshold
# Function to fetch optometry practices in a city with pagination handling
def get_optometry_practices(city, client_practice_name):
    url = f"https://maps.googleapis.com/maps/api/place/textsearch/json?query=optometrists+in+{city}&key={GOOGLE_PLACES_API_KEY}"
    competitors = []
    next_page_token = None
    
    for _ in range(5):  # Fetch up to 100 results (5 pages of 20 each)
        if next_page_token:
            print(f"🔄 Waiting for Google to allow next_page_token...")
            time.sleep(3)  # Google requires a delay before using next_page_token
            response = requests.get(f"{url}&pagetoken={next_page_token}").json()
        else:
            response = requests.get(url).json()
        
        print("📡 API Response:", response)  # Debugging API Response
        
        if "results" in response:
            page_competitors = [place["name"] for place in response["results"]]
            print(f"✅ Fetched {len(response['results'])} competitors")
            competitors.extend(page_competitors)
        else:
            print("❌ No results found in API response!")
        
        next_page_token = response.get("next_page_token")
        if not next_page_token:
            break
        
    print("📌 Competitor List Before Filtering:", competitors)  # Debugging line

    # Remove the client’s practice name and similar variations from the results
    filtered_competitors = [comp for comp in competitors if not is_similar(comp, client_practice_name)]
    
    print("📌 Competitor List After Filtering:", filtered_competitors)  # Debugging line

    return list(set(filtered_competitors))  # Ensure no duplicate names

# Function to save form data to a CSV file
def save_to_csv(city, email, client_practice_name):
    with open("submissions.csv", mode="a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([city, email, client_practice_name])

@app.route('/', methods=['GET', 'POST'])
def index():
    try:
        competitors = []
        if request.method == 'POST':
            city = request.form.get('city', '').strip()
            email = request.form.get('email', '').strip()
            client_practice_name = request.form.get('client_practice_name', '').strip()

            # Save form data to CSV
            save_to_csv(city, email, client_practice_name)
            print(f"✅ Form Saved - City: {city}, Email: {email}, Client Practice: {client_practice_name}")

            if city and email and client_practice_name:
                competitors = get_optometry_practices(city, client_practice_name)

        return render_template('index.html', competitors=competitors)  # Ensures Flask looks in the templates folder
    
    except Exception as e:
        print(f"❌ Error: {str(e)}")  # Debugging error message
        return f"Error: {str(e)}"  # Show error on page for debugging

@app.route('/download', methods=['POST'])
def download():
    competitors = request.form.getlist('competitors')
    output = io.StringIO()
    writer = csv.writer(output)
    
    for competitor in competitors:
        formatted_name = format_phrase_match(competitor)
        writer.writerow([formatted_name])  # Formatting for Google Ads phrase match
    
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()),
                     mimetype="text/csv",
                     as_attachment=True,
                     download_name="negative_keywords.csv")

if __name__ == '__main__':
    app.run(debug=True)
