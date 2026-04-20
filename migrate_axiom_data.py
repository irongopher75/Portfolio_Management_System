import re

input_file = 'institutional_seed.sql'
output_file = 'migrated_institutional_seed.sql'

def migrate():
    with open(input_file, 'r') as f_in, open(output_file, 'w') as f_out:
        # Write necessary SQL headers
        f_out.write("SET FOREIGN_KEY_CHECKS = 0;\n")
        
        for line in f_in:
            # We ONLY care about INSERT statements and certain control comments
            if not line.strip().startswith("INSERT INTO"):
                # Always preserve comments that define character sets if they are at the very top (optional)
                # But safer to just skip everything that isn't an INSERT
                continue
            
            # Use regex to map values within INSERT statements
            
            # 1. Handle Role Mappings in users table
            if "INSERT INTO `users`" in line:
                # Map 'admin' string to ID 1, 'user' string to ID 2
                line = line.replace("'admin'", "1").replace("'user'", "2")
            
            # 2. Handle Transaction Type Mappings in transactions and trade_requests
            if "INSERT INTO `transactions`" in line or "INSERT INTO `trade_requests`" in line:
                # Map 'BUY' -> 1, 'SELL' -> 2
                line = line.replace("'BUY'", "1").replace("'SELL'", "2")
            
            # 3. Handle Status Mappings in trade_requests
            if "INSERT INTO `trade_requests`" in line:
                # 'PENDING' -> 1, 'APPROVED' -> 2, 'REJECTED' -> 3
                line = line.replace("'PENDING'", "1").replace("'APPROVED'", "2").replace("'REJECTED'", "3")

            # 4. Handle Holdings Primary Key (Remove surrogate ID)
            if "INSERT INTO `holdings`" in line:
                # Pattern: (HOLDING_ID, PORTFOLIO_ID, ASSET_ID, QTY, PRICE, DATE)
                # Replace with: (PORTFOLIO_ID, ASSET_ID, QTY, PRICE, DATE)
                # This regex captures the first number and the rest of the tuple, then outputs only the rest.
                line = re.sub(r"\((\d+),(\d+,\d+,[\d\.]+,[\d\.]+,'[\d\-\s:]+')\)", r"(\2)", line)

            f_out.write(line)
        
        f_out.write("SET FOREIGN_KEY_CHECKS = 1;\n")

if __name__ == "__main__":
    migrate()
    print("Migration SQL generated successfully.")
