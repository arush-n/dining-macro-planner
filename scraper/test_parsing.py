"""
Test script to verify nutrition parsing logic
"""
import re

# Sample HTML text as it appears on the page
sample_nutrition_text = """
Blackened Tilapia

Nutrition
Facts
1 servings per container
Serving size
1 each
Calories
per serving	239
 	Amount/serving
% Daily Value*
 	Amount/serving
% Daily Value*


*

The % Daily Value
(DV) tells you how
much a nutrient
in a serving of
food contributes to
a daily diet. 2,000
calories a day is
used for general
nutrition advice.
 	Total Fat 15.7g
20%
 	Total Carbohydrate. 0g
0%

 	    Saturated Fat 1.5g
8%
 	    Dietary Fiber 0g
0%

 	    Trans Fat 0g

 	    Total Sugars 0g


 	Cholesterol 61.9mg
21%
 	      Includes 0g Added Sugars
0%

 	Sodium 692.7mg
30%
 	Protein 24.8g



Calories 239kcal  10%
Fat 15.7g  20%
Saturated Fat 1.5g  8%
Trans Fatty Acid 0g
Cholesterol 61.9mg  21%
Sodium 692.7mg  30%
Carbohydrates 0g  0%
Dietary Fiber 0g  0%
Total Sugars 0g
Added Sugar 0g  0%
Protein 24.8g  50%
Vitamin D - mcg 3.9mcg  1%
Calcium 0.2mg  0%
Iron 0mg  0%
Potassium 383.3mg  8%
INGREDIENTS:  Unbreaded Tilapia Fish (Tilapia), Canola & Extra Virgin Olive Oil Blend (Canola oil, virgin olive oil, beta-carotene (color) ), Cajun Seasoning (Dehydrated Garlic, Spices, Salt, Paprika (Color), Dehydrated Onion, Red Pepper.), Sliced Green Onion (Green Onions)
ALLERGENS: Fish
Contains Fish Halal Friendly
The University of Texas at Austin does not guarantee the accuracy of nutrition information; ingredient and nutrition content of foods may vary due to changes in product formulation, recipe substitutions, portion size and other factors. The nutrition analyses provided here are approximations only. Guests with food allergies or other food intolerances should consult a Chef or Dining Manager for specific ingredient questions. Guests may also consult our Registered Dietitians for additional assistance at dietitian@austin.utexas.edu.
"""

def parse_nutrition(page_text):
    """
    Parse nutrition information using the same logic as the scraper
    """
    nutrition = {
        'protein': None,
        'carbs': None,
        'fats': None,
        'calories': None
    }

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


if __name__ == "__main__":
    print("=" * 60)
    print("NUTRITION PARSING TEST")
    print("=" * 60)
    print("\nTesting with Blackened Tilapia sample data...\n")

    # Expected values
    expected = {
        'calories': 239.0,
        'fats': 15.7,
        'carbs': 0.0,
        'protein': 24.8
    }

    # Parse the sample text
    result = parse_nutrition(sample_nutrition_text)

    # Display results
    print("EXTRACTED VALUES:")
    print(f"  Calories: {result['calories']}")
    print(f"  Fat:      {result['fats']}g")
    print(f"  Carbs:    {result['carbs']}g")
    print(f"  Protein:  {result['protein']}g")

    print("\nEXPECTED VALUES:")
    print(f"  Calories: {expected['calories']}")
    print(f"  Fat:      {expected['fats']}g")
    print(f"  Carbs:    {expected['carbs']}g")
    print(f"  Protein:  {expected['protein']}g")

    # Verify results
    print("\n" + "=" * 60)
    print("VERIFICATION:")
    print("=" * 60)

    all_correct = True
    for key in expected:
        if result[key] == expected[key]:
            print(f"  [OK] {key.capitalize()}: MATCH")
        else:
            print(f"  [FAIL] {key.capitalize()}: MISMATCH (got {result[key]}, expected {expected[key]})")
            all_correct = False

    print("\n" + "=" * 60)
    if all_correct:
        print("SUCCESS! All values extracted correctly.")
    else:
        print("FAILURE! Some values did not match.")
    print("=" * 60)
