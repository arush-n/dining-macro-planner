"""
Debug script to fetch and examine the HTML structure
"""
import requests
from bs4 import BeautifulSoup

url = "https://hf-foodpro.austin.utexas.edu/foodpro/longmenu.aspx?sName=University+Housing+and+Dining&locationNum=03&locationName=Kins+Dining&naFlag=1&WeeksMenus=This+Week%27s+Menus&dtdate=11%2f12%2f2025&mealName=Breakfast"

response = requests.get(url)
soup = BeautifulSoup(response.content, 'html.parser')

# Save the entire HTML to a file for inspection
with open('debug_page.html', 'w', encoding='utf-8') as f:
    f.write(soup.prettify())

print("HTML saved to debug_page.html")

# Find all tables
tables = soup.find_all('table')
print(f"\nFound {len(tables)} tables")

# Print first few links with 'nutrition' in them
links = soup.find_all('a', href=lambda x: x and 'nutrition' in x.lower())
print(f"\nFound {len(links)} nutrition links")

if links:
    print("\nFirst few nutrition links:")
    for i, link in enumerate(links[:5]):
        print(f"  {i+1}. {link.get_text(strip=True)[:50]} - {link.get('href')}")

# Try to find food items by looking at the structure
print("\n\nLooking for food item patterns...")
divs = soup.find_all('div', class_=True)
print(f"Found {len(divs)} divs with classes")

# Print some class names
unique_classes = set()
for div in divs:
    for cls in div.get('class', []):
        unique_classes.add(cls)

print(f"\nUnique div classes: {sorted(unique_classes)[:20]}")
