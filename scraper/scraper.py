"""
Web scraper for dining hall food data
Scrapes from UT Austin FoodPro longmenu.aspx pages using requests + BeautifulSoup
"""
import requests
from bs4 import BeautifulSoup
from datetime import date, datetime
import time
import sys
import re
from pathlib import Path

# Dining hall configuration
DINING_HALLS = {
    "J2": {
        "locationNum": "12",
        "locationName": "J2+Dining"
    },
    "JCL": {
        "locationNum": "12(a)",
        "locationName": "JCL+Dining"
    },
    "Kins": {
        "locationNum": "03",
        "locationName": "Kins+Dining"
    }
}

MEAL_TYPES = ["Breakfast", "Lunch", "Dinner"]

BASE_URL = "https://hf-foodpro.austin.utexas.edu/foodpro/longmenu.aspx"


class DiningHallScraper:
    """Scraper for dining hall food data using requests and BeautifulSoup"""

    def __init__(self, db_path=None, auto_save=False):
        """
        Initialize the scraper

        Args:
            db_path: Path to database file (optional)
            auto_save: Whether to automatically save to database (default: False)
        """
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.db_path = db_path
        self.auto_save = auto_save

    def build_url(self, dining_hall, meal_type, target_date=None):
        """
        Build URL for a specific dining hall and meal

        Args:
            dining_hall: Name of dining hall (J2, JCL, or Kins)
            meal_type: Breakfast, Lunch, or Dinner
            target_date: Date object (defaults to today)

        Returns:
            Full URL string
        """
        if target_date is None:
            target_date = date.today()

        hall_config = DINING_HALLS[dining_hall]

        # Format date as MM/DD/YYYY
        date_str = target_date.strftime("%m%%2f%d%%2f%Y")

        url = (
            f"{BASE_URL}?"
            f"sName=University+Housing+and+Dining"
            f"&locationNum={hall_config['locationNum']}"
            f"&locationName={hall_config['locationName']}"
            f"&naFlag=1"
            f"&WeeksMenus=This+Week%27s+Menus"
            f"&dtdate={date_str}"
            f"&mealName={meal_type}"
        )

        return url

    def scrape_meal(self, dining_hall, meal_type, target_date=None):
        """
        Scrape a single meal from a dining hall

        Args:
            dining_hall: Name of dining hall (J2, JCL, or Kins)
            meal_type: Breakfast, Lunch, or Dinner
            target_date: Date object (defaults to today)

        Returns:
            List of food dictionaries
        """
        url = self.build_url(dining_hall, meal_type, target_date)

        print(f"\nScraping {dining_hall} - {meal_type}")
        print(f"URL: {url}")

        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            foods = self._parse_food_table(soup, dining_hall, meal_type)

            print(f"Found {len(foods)} food items")
            return foods

        except requests.exceptions.RequestException as e:
            print(f"  Error fetching {dining_hall} - {meal_type}: {e}")
            return []
        except Exception as e:
            print(f"  Error parsing {dining_hall} - {meal_type}: {e}")
            return []

    def _parse_food_table(self, soup, dining_hall, meal_type):
        """
        Parse the food table from the HTML

        Args:
            soup: BeautifulSoup object
            dining_hall: Name of dining hall
            meal_type: Breakfast, Lunch, or Dinner

        Returns:
            List of food dictionaries
        """
        foods = []

        # Find all food items by looking for divs with class 'longmenucoldispname'
        food_divs = soup.find_all('div', class_='longmenucoldispname')

        if not food_divs:
            print("  No food items found on page")
            return foods

        for food_div in food_divs:
            # Find the label.aspx link
            label_link = food_div.find('a', href=lambda x: x and 'label.aspx' in x)

            if label_link:
                food_data = self._extract_food_from_div(food_div, label_link, dining_hall, meal_type)
                if food_data:
                    foods.append(food_data)

        return foods

    def _extract_food_from_div(self, food_div, label_link, dining_hall, meal_type):
        """
        Extract food data from a food div element

        Args:
            food_div: BeautifulSoup div element with class 'longmenucoldispname'
            label_link: Link to label.aspx page
            dining_hall: Name of dining hall
            meal_type: Meal type

        Returns:
            Food dictionary or None
        """
        try:
            # Get food name from the link text
            food_name = label_link.get_text(strip=True)

            if not food_name:
                return None

            # Get the label URL
            label_url = label_link['href']
            if not label_url.startswith('http'):
                label_url = 'https://hf-foodpro.austin.utexas.edu/foodpro/' + label_url

            # Fetch nutrition details from the label page
            nutrition_data = self._fetch_nutrition_details(label_url)

            food_data = {
                "name": food_name,
                "dining_hall": dining_hall,
                "meal_type": meal_type,
                "protein": nutrition_data.get('protein'),
                "carbs": nutrition_data.get('carbs'),
                "fats": nutrition_data.get('fats'),
                "calories": nutrition_data.get('calories'),
                "scraped_date": str(date.today())
            }

            print(f"  {food_name}: {food_data.get('protein', 0)}g protein, "
                  f"{food_data.get('carbs', 0)}g carbs, {food_data.get('fats', 0)}g fat, "
                  f"{food_data.get('calories', 0)} cal")

            return food_data

        except Exception as e:
            print(f"  Error extracting food from div: {e}")
            return None

    def _fetch_nutrition_details(self, nutrition_url):
        """
        Fetch detailed nutrition information from nutrition page

        Args:
            nutrition_url: URL to the nutrition details page

        Returns:
            Dictionary with protein, carbs, fats, calories
        """
        try:
            response = self.session.get(nutrition_url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            nutrition = {
                'protein': None,
                'carbs': None,
                'fats': None,
                'calories': None
            }

            # Get all text from the page
            page_text = soup.get_text()

            # Pattern 1: Look for the cleaner tabular format (e.g., "Calories 239kcal")
            cal_match = re.search(r'Calories\s+(\d+\.?\d*)kcal', page_text, re.IGNORECASE)
            if cal_match:
                nutrition['calories'] = float(cal_match.group(1))

            # Pattern 2: Look for "Fat" followed by number and g (e.g., "Fat 15.7g")
            # This should match "Total Fat" or just "Fat"
            fat_match = re.search(r'(?:Total\s+)?Fat\s+(\d+\.?\d*)g', page_text, re.IGNORECASE)
            if fat_match:
                nutrition['fats'] = float(fat_match.group(1))

            # Pattern 3: Look for "Carbohydrates" (e.g., "Carbohydrates 0g")
            # This should match "Total Carbohydrate", "Carbohydrates", or "Carbs"
            carb_match = re.search(r'(?:Total\s+)?Carbohydrate[s]?\s+(\d+\.?\d*)g', page_text, re.IGNORECASE)
            if carb_match:
                nutrition['carbs'] = float(carb_match.group(1))

            # Pattern 4: Look for "Protein" (e.g., "Protein 24.8g")
            prot_match = re.search(r'Protein\s+(\d+\.?\d*)g', page_text, re.IGNORECASE)
            if prot_match:
                nutrition['protein'] = float(prot_match.group(1))

            # Fallback: If we didn't find values in the cleaner format, try the old patterns
            if nutrition['calories'] is None:
                cal_match = re.search(r'calories[^\d]*(\d+)', page_text, re.IGNORECASE)
                if cal_match:
                    nutrition['calories'] = float(cal_match.group(1))

            if nutrition['protein'] is None:
                prot_match = re.search(r'protein[^\d]*(\d+\.?\d*)\s*g', page_text, re.IGNORECASE)
                if prot_match:
                    nutrition['protein'] = float(prot_match.group(1))

            if nutrition['carbs'] is None:
                carb_match = re.search(r'carbohydrate[^\d]*(\d+\.?\d*)\s*g', page_text, re.IGNORECASE)
                if carb_match:
                    nutrition['carbs'] = float(carb_match.group(1))

            if nutrition['fats'] is None:
                fat_match = re.search(r'total\s+fat[^\d]*(\d+\.?\d*)\s*g', page_text, re.IGNORECASE)
                if fat_match:
                    nutrition['fats'] = float(fat_match.group(1))

            return nutrition

        except Exception as e:
            print(f"  Error fetching nutrition details: {e}")
            return {
                'protein': None,
                'carbs': None,
                'fats': None,
                'calories': None
            }

    def scrape_all_meals(self, dining_hall, target_date=None):
        """
        Scrape all meals (Breakfast, Lunch, Dinner) for a dining hall

        Args:
            dining_hall: Name of dining hall (J2, JCL, or Kins)
            target_date: Date object (defaults to today)

        Returns:
            List of all food data
        """
        all_foods = []

        for meal_type in MEAL_TYPES:
            meal_foods = self.scrape_meal(dining_hall, meal_type, target_date)
            all_foods.extend(meal_foods)
            time.sleep(0.5)  # Be nice to the server

        return all_foods

    def scrape_all_dining_halls(self, target_date=None):
        """
        Scrape all dining halls and all meals

        Args:
            target_date: Date object (defaults to today)

        Returns:
            List of all food data
        """
        all_foods = []

        for dining_hall in DINING_HALLS.keys():
            hall_foods = self.scrape_all_meals(dining_hall, target_date)
            all_foods.extend(hall_foods)
            time.sleep(1)  # Be nice to the server

        return all_foods


def scrape_todays_meals(dining_hall=None):
    """
    Main function to scrape today's meals

    Args:
        dining_hall: Optional - specific dining hall to scrape (J2, JCL, or Kins)
                    If None, scrapes all dining halls

    Returns:
        List of food dictionaries
    """
    scraper = DiningHallScraper()

    print("=" * 60)
    print("DINING HALL SCRAPER")
    print("=" * 60)

    if dining_hall:
        if dining_hall not in DINING_HALLS:
            print(f"Error: Invalid dining hall '{dining_hall}'")
            print(f"Valid options: {', '.join(DINING_HALLS.keys())}")
            return []

        all_foods = scraper.scrape_all_meals(dining_hall)
    else:
        all_foods = scraper.scrape_all_dining_halls()

    print("\n" + "=" * 60)
    print(f"TOTAL FOODS SCRAPED: {len(all_foods)}")
    print("=" * 60)

    return all_foods


if __name__ == "__main__":
    import argparse
    import json

    parser = argparse.ArgumentParser(description="Scrape dining hall food data")
    parser.add_argument(
        "--hall",
        type=str,
        choices=list(DINING_HALLS.keys()),
        help="Specific dining hall to scrape (J2, JCL, or Kins)"
    )

    args = parser.parse_args()

    foods = scrape_todays_meals(dining_hall=args.hall)

    # Save to JSON
    output_path = Path(__file__).parent / "scraped_foods.json"
    with open(output_path, 'w') as f:
        json.dump(foods, f, indent=2)

    print(f"\nFoods saved to {output_path}")
