import re
import os

INPUT_FILE = 'institutional_seed.sql'
OUTPUT_FILE = 'precision_migrated_seed.sql'

def parse_tuples(line):
    # Regex to find everything inside ( ... ) taking into account nested strings with commas
    # This is a basic approach; more complex tuples might need a real SQL parser
    # But for a standard mysqldump, values are usually comma separated and strings are '' escaped
    matches = re.findall(r"\((.*?)\)(?:,|;)", line)
    return matches

def migrate():
    print(f"Starting precision migration from {INPUT_FILE}...")
    with open(INPUT_FILE, 'r') as f_in, open(OUTPUT_FILE, 'w') as f_out:
        f_out.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        
        for line in f_in:
            if not line.strip().startswith("INSERT INTO"):
                continue
            
            table_match = re.search(r"INSERT INTO `(\w+)`", line)
            if not table_match: continue
            table_name = table_match.group(1)
            
            # Extract the raw tuples string
            values_part = line[line.find("VALUES") + 7:].strip()
            # Split raw values into individual tuples
            # We use a regex that handles common MySQL dump formats
            tuples = re.findall(r"\((.*?)\)(?:,|\s*;)", values_part)
            
            new_lines = []
            
            for t in tuples:
                # Split the tuple values by comma, but ignore commas inside strings
                # This is a 'poor man's' CSV parser for SQL
                cols = re.findall(r"(?:'[^']*'|[^,]+)", t)
                cols = [c.strip() for c in cols]

                if table_name == 'users':
                    # Original: id, user, email, hash, role(str), date
                    # New: id, user, email, hash, role_id(int), date
                    role_str = cols[4].strip("'")
                    role_id = "1" if role_str == 'admin' else "2"
                    cols[4] = role_id
                    new_lines.append(f"({','.join(cols)})")

                elif table_name == 'portfolios':
                    # id, user_id, name, total_value
                    new_lines.append(f"({','.join(cols)})")

                elif table_name == 'assets':
                    # id, symbol, name, type, price, date
                    new_lines.append(f"({','.join(cols)})")

                elif table_name == 'holdings':
                    # Original: id, port, asset, qty, price, date
                    # New: port, asset, qty, avg_price
                    # Drop the first and last columns
                    new_cols = [cols[1], cols[2], cols[3], cols[4]]
                    new_lines.append(f"({','.join(new_cols)})")

                elif table_name == 'trade_requests':
                    # Original: id, user, port, asset, type(str), qty, price, status(str), created, actioned
                    # New: id, user, port, asset, type_id, qty, price, status_id, created, actioned
                    type_str = cols[4].strip("'")
                    type_id = "1" if type_str == 'BUY' else "2"
                    status_str = cols[7].strip("'")
                    status_id = "1" if status_str == 'PENDING' else "2" if status_str == 'APPROVED' else "3"
                    cols[4] = type_id
                    cols[7] = status_id
                    new_lines.append(f"({','.join(cols)})")

                elif table_name == 'transactions':
                    # Original: id, port, asset, type(str), qty, price, date
                    # New: id, request_id, port, asset, type_id, qty, price, date
                    type_str = cols[3].strip("'")
                    type_id = "1" if type_str == 'BUY' else "2"
                    # request_id = NULL (legacy), original id was first
                    new_cols = [cols[0], "NULL", cols[1], cols[2], type_id, cols[4], cols[5], cols[6]]
                    new_lines.append(f"({','.join(new_cols)})")
                
                elif table_name in ['audit_logs', 'global_config', 'watchlists', 'watchlist_items']:
                    new_lines.append(f"({','.join(cols)})")

            if new_lines:
                # Reconstruct the INSERT statement with explicit column naming for safety
                col_spec = ""
                if table_name == 'holdings': col_spec = "(portfolio_id, asset_id, quantity, average_buy_price)"
                elif table_name == 'transactions': col_spec = "(transaction_id, request_id, portfolio_id, asset_id, type_id, quantity, price_per_unit, transaction_date)"
                elif table_name == 'users': col_spec = "(user_id, username, email, password_hash, role_id, created_at)"
                elif table_name == 'trade_requests': col_spec = "(request_id, user_id, portfolio_id, asset_id, type_id, quantity, requested_price, status_id, created_at, actioned_at)"
                
                f_out.write(f"INSERT INTO `{table_name}` {col_spec} VALUES {','.join(new_lines)};\n")
                
        f_out.write("SET FOREIGN_KEY_CHECKS = 1;\n")
    print(f"Precision migration complete. Output saved to {OUTPUT_FILE}")

if __name__ == "__main__":
    migrate()
