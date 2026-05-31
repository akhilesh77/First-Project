import sqlite3

conn = sqlite3.connect("data/restaurants.db")
conn.row_factory = sqlite3.Row
rows = conn.execute("SELECT name, city, cuisines, neighborhood, cost_for_two FROM restaurants WHERE name LIKE 'eat.fit%' AND neighborhood = 'Indiranagar'").fetchall()
for i, row in enumerate(rows):
    print(f"{i}: name={row['name']}, city={row['city']}, cuisines={row['cuisines']}, neighborhood={row['neighborhood']}, cost={row['cost_for_two']}")
