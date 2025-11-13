"""
Comprehensive Scraping Service
Main entry point for all scraping operations with database integration
"""
import sys
from pathlib import Path
import sqlite3
import json
from datetime import date, datetime

sys.path.append(str(Path(__file__).parent.parent))

# Import scraper module - handle both direct and package imports
try:
    from scraper.scraper import DiningHallScraper, DINING_HALLS, MEAL_TYPES
except ModuleNotFoundError:
    from scraper import DiningHallScraper, DINING_HALLS, MEAL_TYPES

from config import DATABASE_PATH, DEFAULT_CONFIDENCE


class ScrapingService:
    """
    Main scraping service with database integration and API support
    """

    def __init__(self, db_path=None):
        """Initialize scraping service"""
        self.db_path = db_path or DATABASE_PATH
        self.scraper = None

    def _get_scraper(self, auto_save=True):
        """Get or create scraper instance"""
        if self.scraper is None or self.scraper.auto_save != auto_save:
            # Import here to avoid circular dependency
            from scraper.scraper import DiningHallScraper
            self.scraper = DiningHallScraper(db_path=self.db_path, auto_save=auto_save)
        return self.scraper

    def scrape_dining_hall(
        self,
        dining_hall: str,
        target_date: date = None,
        save_to_db: bool = True
    ) -> dict:
        """
        Scrape a single dining hall for all meals

        Args:
            dining_hall: Dining hall name (J2, JCL, or Kins)
            target_date: Target date (defaults to today)
            save_to_db: Whether to save to database

        Returns:
            Dictionary with scrape results
        """
        if dining_hall not in DINING_HALLS:
            return {
                "status": "error",
                "message": f"Invalid dining hall: {dining_hall}",
                "valid_halls": list(DINING_HALLS.keys())
            }

        scraper = self._get_scraper(auto_save=save_to_db)

        try:
            foods = scraper.scrape_all_meals(dining_hall, target_date)

            return {
                "status": "success",
                "dining_hall": dining_hall,
                "date": str(target_date or date.today()),
                "foods_scraped": len(foods),
                "saved_to_database": save_to_db,
                "foods": foods
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "dining_hall": dining_hall
            }

    def scrape_all_dining_halls(
        self,
        target_date: date = None,
        save_to_db: bool = True
    ) -> dict:
        """
        Scrape all dining halls

        Args:
            target_date: Target date (defaults to today)
            save_to_db: Whether to save to database

        Returns:
            Dictionary with scrape results
        """
        scraper = self._get_scraper(auto_save=save_to_db)

        try:
            foods = scraper.scrape_all_dining_halls(target_date)

            # Get breakdown by dining hall
            by_hall = {}
            for food in foods:
                hall = food['dining_hall']
                by_hall[hall] = by_hall.get(hall, 0) + 1

            return {
                "status": "success",
                "date": str(target_date or date.today()),
                "total_foods_scraped": len(foods),
                "by_dining_hall": by_hall,
                "saved_to_database": save_to_db,
                "foods": foods
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }

    def scrape_specific_meal(
        self,
        dining_hall: str,
        meal_type: str,
        target_date: date = None,
        save_to_db: bool = True
    ) -> dict:
        """
        Scrape a specific meal

        Args:
            dining_hall: Dining hall name
            meal_type: Meal type (Breakfast, Lunch, Dinner)
            target_date: Target date
            save_to_db: Whether to save to database

        Returns:
            Dictionary with scrape results
        """
        if dining_hall not in DINING_HALLS:
            return {
                "status": "error",
                "message": f"Invalid dining hall: {dining_hall}",
                "valid_halls": list(DINING_HALLS.keys())
            }

        if meal_type not in MEAL_TYPES:
            return {
                "status": "error",
                "message": f"Invalid meal type: {meal_type}",
                "valid_types": MEAL_TYPES
            }

        scraper = self._get_scraper(auto_save=save_to_db)

        try:
            foods = scraper.scrape_meal(dining_hall, meal_type, target_date)

            # Save manually if needed
            if save_to_db and foods and not scraper.auto_save:
                scraper.save_to_database(foods)

            return {
                "status": "success",
                "dining_hall": dining_hall,
                "meal_type": meal_type,
                "date": str(target_date or date.today()),
                "foods_scraped": len(foods),
                "saved_to_database": save_to_db,
                "foods": foods
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e),
                "dining_hall": dining_hall,
                "meal_type": meal_type
            }

    def get_scrape_status(self) -> dict:
        """
        Get current scraping status from database

        Returns:
            Dictionary with scrape statistics
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        try:
            # Total foods
            cursor.execute("SELECT COUNT(*) FROM foods")
            total_foods = cursor.fetchone()[0]

            # Foods by dining hall and meal type
            cursor.execute("""
                SELECT dining_hall, meal_type, COUNT(*) as count
                FROM foods
                GROUP BY dining_hall, meal_type
            """)
            breakdown = {}
            for hall, meal, count in cursor.fetchall():
                if hall not in breakdown:
                    breakdown[hall] = {}
                breakdown[hall][meal] = count

            # Latest scrape date
            cursor.execute("SELECT MAX(scraped_date) FROM foods")
            latest_scrape = cursor.fetchone()[0]

            # Foods scraped today
            cursor.execute("""
                SELECT COUNT(*) FROM foods
                WHERE DATE(scraped_date) = DATE('now')
            """)
            today_count = cursor.fetchone()[0]

            # Foods by hall
            cursor.execute("""
                SELECT dining_hall, COUNT(*) as count
                FROM foods
                GROUP BY dining_hall
            """)
            by_hall = dict(cursor.fetchall())

            return {
                "status": "success",
                "total_foods": total_foods,
                "by_dining_hall": by_hall,
                "breakdown": breakdown,
                "latest_scrape_date": latest_scrape,
                "scraped_today": today_count
            }

        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
        finally:
            conn.close()

    def refresh_all_data(self) -> dict:
        """
        Refresh all dining hall data (scrape everything)

        Returns:
            Dictionary with refresh results
        """
        print("\n" + "=" * 70)
        print("REFRESHING ALL DINING HALL DATA")
        print("=" * 70)

        result = self.scrape_all_dining_halls(save_to_db=True)

        if result['status'] == 'success':
            status = self.get_scrape_status()
            result['database_status'] = status

            print(f"\n[COMPLETE] Refresh successful!")
            print(f"  Total foods scraped: {result['total_foods_scraped']}")
            print(f"  Total in database: {status.get('total_foods', 0)}")
            print("=" * 70)

        return result


# Singleton service instance
_scraping_service = None

def get_scraping_service() -> ScrapingService:
    """Get or create singleton scraping service instance"""
    global _scraping_service
    if _scraping_service is None:
        _scraping_service = ScrapingService()
    return _scraping_service


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Scraping Service - Manage dining hall data")
    parser.add_argument(
        "command",
        choices=["scrape", "status", "refresh"],
        help="Command to execute"
    )
    parser.add_argument(
        "--hall",
        choices=list(DINING_HALLS.keys()),
        help="Dining hall to scrape"
    )
    parser.add_argument(
        "--meal",
        choices=MEAL_TYPES,
        help="Meal type to scrape"
    )
    parser.add_argument(
        "--date",
        help="Target date (YYYY-MM-DD)"
    )

    args = parser.parse_args()

    service = get_scraping_service()

    # Parse date if provided
    target_date = None
    if args.date:
        try:
            target_date = datetime.strptime(args.date, "%Y-%m-%d").date()
        except ValueError:
            print("ERROR: Invalid date format. Use YYYY-MM-DD")
            sys.exit(1)

    # Execute command
    if args.command == "status":
        result = service.get_scrape_status()
        print(json.dumps(result, indent=2))

    elif args.command == "refresh":
        result = service.refresh_all_data()
        print(json.dumps(result, indent=2))

    elif args.command == "scrape":
        if args.hall and args.meal:
            result = service.scrape_specific_meal(args.hall, args.meal, target_date)
        elif args.hall:
            result = service.scrape_dining_hall(args.hall, target_date)
        else:
            result = service.scrape_all_dining_halls(target_date)

        print(json.dumps(result, indent=2))
