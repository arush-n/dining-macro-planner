"""
Generate embeddings for foods in the database
Uses text similarity for semantic search

Note: This is a simplified implementation using TF-IDF
For production, consider using Claude embeddings or sentence-transformers
"""
import sqlite3
import numpy as np
import pickle
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent.parent))
from config import DATABASE_PATH

class FoodEmbeddingGenerator:
    """Generate and store embeddings for food items"""

    def __init__(self, db_path=None):
        self.db_path = db_path or DATABASE_PATH
        self.vectorizer = TfidfVectorizer(
            ngram_range=(1, 2),  # Use unigrams and bigrams
            max_features=500
        )

    def generate_all_embeddings(self):
        """
        Generate embeddings for all foods in database
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Get all foods
        cursor.execute("SELECT id, name FROM foods")
        foods = cursor.fetchall()

        if not foods:
            print("No foods found in database. Load foods first.")
            conn.close()
            return

        food_ids = [f[0] for f in foods]
        food_names = [f[1] for f in foods]

        print(f"Generating embeddings for {len(foods)} foods...")

        # Generate embeddings using TF-IDF
        embeddings = self.vectorizer.fit_transform(food_names).toarray()

        # Store embeddings in database
        for food_id, embedding in zip(food_ids, embeddings):
            # Serialize embedding as blob
            embedding_blob = pickle.dumps(embedding)

            # Check if embedding exists
            cursor.execute(
                "SELECT id FROM food_embeddings WHERE food_id = ?",
                (food_id,)
            )
            existing = cursor.fetchone()

            if existing:
                cursor.execute("""
                    UPDATE food_embeddings
                    SET embedding = ?, created_at = CURRENT_TIMESTAMP
                    WHERE food_id = ?
                """, (embedding_blob, food_id))
            else:
                cursor.execute("""
                    INSERT INTO food_embeddings (food_id, embedding)
                    VALUES (?, ?)
                """, (food_id, embedding_blob))

        conn.commit()
        print(f"✓ Generated and stored {len(embeddings)} embeddings")

        # Save vectorizer for later use
        vectorizer_path = Path(self.db_path).parent / "tfidf_vectorizer.pkl"
        with open(vectorizer_path, 'wb') as f:
            pickle.dump(self.vectorizer, f)
        print(f"✓ Saved vectorizer to {vectorizer_path}")

        conn.close()

    def find_similar_foods(self, food_name: str, top_k: int = 5):
        """
        Find foods similar to the given food name

        Args:
            food_name: Name of food
            top_k: Number of similar foods to return

        Returns:
            List of (food_id, food_name, similarity_score) tuples
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Load vectorizer
        vectorizer_path = Path(self.db_path).parent / "tfidf_vectorizer.pkl"
        if not vectorizer_path.exists():
            print("Vectorizer not found. Generate embeddings first.")
            conn.close()
            return []

        with open(vectorizer_path, 'rb') as f:
            self.vectorizer = pickle.load(f)

        # Generate embedding for query
        query_embedding = self.vectorizer.transform([food_name]).toarray()[0]

        # Get all food embeddings
        cursor.execute("""
            SELECT fe.food_id, f.name, fe.embedding
            FROM food_embeddings fe
            JOIN foods f ON fe.food_id = f.id
        """)
        rows = cursor.fetchall()

        similarities = []
        for food_id, name, embedding_blob in rows:
            embedding = pickle.loads(embedding_blob)
            similarity = cosine_similarity([query_embedding], [embedding])[0][0]
            similarities.append((food_id, name, similarity))

        # Sort by similarity
        similarities.sort(key=lambda x: x[2], reverse=True)

        conn.close()
        return similarities[:top_k]


def generate_embeddings():
    """Main function to generate embeddings"""
    generator = FoodEmbeddingGenerator()
    generator.generate_all_embeddings()


def test_similarity():
    """Test similarity search"""
    generator = FoodEmbeddingGenerator()

    test_foods = ["chicken", "rice", "salmon"]

    print("\n" + "=" * 60)
    print("TESTING FOOD SIMILARITY SEARCH")
    print("=" * 60)

    for food_name in test_foods:
        print(f"\nFoods similar to '{food_name}':")
        similar = generator.find_similar_foods(food_name, top_k=5)
        for food_id, name, score in similar:
            print(f"  {score:.3f} - {name}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Generate food embeddings")
    parser.add_argument("--test", action="store_true", help="Test similarity search")

    args = parser.parse_args()

    if args.test:
        test_similarity()
    else:
        generate_embeddings()
