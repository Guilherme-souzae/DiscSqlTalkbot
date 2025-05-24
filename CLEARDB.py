import sqlite3

def reset_database():
    with sqlite3.connect('database.db') as db:
        cursor = db.cursor()

        cursor.execute("PRAGMA foreign_keys = OFF;")

        cursor.execute("DELETE FROM Quotes;")
        cursor.execute("DELETE FROM Pet;")
        
        cursor.execute("PRAGMA foreign_keys = ON;")

        db.commit()

    print("Database is clear.")

if __name__ == "__main__":
    reset_database()