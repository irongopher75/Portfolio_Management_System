import mysql.connector
import os
import sys

MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
MYSQL_USER = os.getenv("MYSQL_USER", "root")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
MYSQL_DB = os.getenv("MYSQL_DB", "portfolio")

def get_db_connection():
    try:
        return mysql.connector.connect(
            host=MYSQL_HOST,
            port=MYSQL_PORT,
            user=MYSQL_USER,
            password=MYSQL_PASSWORD,
            database=MYSQL_DB,
        )
    except mysql.connector.Error as err:
        print(f"Error connecting to database: {err}")
        return None


def execute_query(query):
    conn = get_db_connection()
    if not conn:
        return
    
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        if cursor.description: # SELECT query
            columns = [col[0] for col in cursor.description]
            results = cursor.fetchall()
            
            # Print simple table
            if results:
                # Find max width for each column
                widths = [len(str(c)) for c in columns]
                for row in results:
                    for i, val in enumerate(row):
                        widths[i] = max(widths[i], len(str(val)))
                
                # Format
                row_fmt = " | ".join(["{:<" + str(w) + "}" for w in widths])
                sep = "-+-".join(["-" * w for w in widths])
                
                print("\n" + row_fmt.format(*columns))
                print(sep)
                for row in results:
                    print(row_fmt.format(*[str(val) if val is not None else "NULL" for val in row]))
                print(f"({len(results)} rows)\n")
            else:
                print("\n0 rows returned.\n")
        else: # INSERT, UPDATE, DELETE
            conn.commit()
            print(f"\nQuery successful. {cursor.rowcount} rows affected.\n")
            
    except mysql.connector.Error as err:
        print(f"SQL Error: {err}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        # Single query from command line
        query = " ".join(sys.argv[1:])
        execute_query(query)
    else:
        # Interactive mode
        print("AXIOM SQL Terminal Shell (MySQL) (Type 'exit' to quit)")
        print("-" * 40)
        while True:
            try:
                query = input("sql> ").strip()
                if not query:
                    continue
                if query.lower() in ('exit', 'quit', 'q'):
                    break
                execute_query(query)
            except KeyboardInterrupt:
                print("\nUse 'exit' to quit.")
            except EOFError:
                break
