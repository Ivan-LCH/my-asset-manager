import sqlite3

def dict_factory(cursor, row):
    d = {}
    for idx, col in enumerate(cursor.description):
        d[col[0]] = row[idx]
    return d

try:
    conn = sqlite3.connect('/home/ivan/my_prog/asset_manager/data/assets.db')
    conn.row_factory = dict_factory
    cursor = conn.cursor()

    print('--- Checking ASSETS Table for "KODEx 미국나스닥100" ---')
    cursor.execute("SELECT * FROM assets WHERE name LIKE '%KODEx%' OR name LIKE '%나스닥%'")
    assets = cursor.fetchall()
    
    found_ids = []
    if not assets:
        print("No assets found matching 'KODEx' or '나스닥'.")
    else:
        for a in assets:
            print(f"Asset Found: ID={a['id']}, Name={a['name']}, Type={a['type']}")
            found_ids.append(a['id'])

    if found_ids:
        print('\n--- Checking STOCK_DETAILS Table for these IDs ---')
        placeholders = ','.join(['?'] * len(found_ids))
        cursor.execute(f"SELECT * FROM stock_details WHERE asset_id IN ({placeholders})", found_ids)
        details = cursor.fetchall()
        
        detail_map = {d['asset_id']: d for d in details}
        
        for aid in found_ids:
            if aid in detail_map:
                print(f"Detail Found for {aid}: {detail_map[aid]}")
            else:
                print(f"!!! MISSING DETAILS for {aid} !!! -> This is the cause of 'None' account.")
    
    print('\n--- Checking for ANY orphaned STOCK assets ---')
    cursor.execute("SELECT id, name, type FROM assets WHERE type = 'STOCK' AND id NOT IN (SELECT asset_id FROM stock_details)")
    orphans = cursor.fetchall()
    if orphans:
        print(f"FOUND {len(orphans)} ORPHANS:")
        for o in orphans:
            print(f" - {o}")
    else:
        print("No orphaned assets found.")

except Exception as e:
    print(f"Error: {e}")
finally:
    if 'conn' in locals():
        conn.close()
