import os
import psycopg2
from decouple import config

# 1. Connect to PostgreSQL database
db_name = config('POSTGRES_DB', default='talent_db')
db_user = config('POSTGRES_USER', default='rumaiz')
db_password = config('POSTGRES_PASSWORD', default='')
db_host = config('POSTGRES_HOST', default='localhost')
db_port = config('POSTGRES_PORT', default='5432')

connect_args = {
    'dbname': db_name,
    'user': db_user,
}
if db_password:
    connect_args['password'] = db_password
if db_host:
    connect_args['host'] = db_host
if db_port:
    connect_args['port'] = db_port

print(f"Connecting to database '{db_name}'...")
conn = psycopg2.connect(**connect_args)
cursor = conn.cursor()

# 2. Disable constraints temporarily to copy data cleanly
cursor.execute("SET session_replication_role = 'replica';")
conn.commit()

# Tables to copy (in dependency order)
TABLES = [
    ('academics_institute', True),       # (table_name, has_institute_field)
    ('account_userdata', True),
    ('academics_batch', True),
    ('subject_subject', True),
    ('account_userdata_classs', False),   # M2M relation (no direct institute_id)
    ('academics_fee', True),
    ('academics_payment', False),         # scoped via fee_id
    ('academics_timetable', True),
    ('academics_exam', True),
    ('academics_mark', False),            # scoped via exam_id
    ('attendance_attendancesession', True),
    ('attendance_attendancerecord', False) # scoped via session_id
]

def merge_schema(src_schema, target_inst_id):
    print(f"\nMerging schema '{src_schema}' into public schema (Institute ID: {target_inst_id})...")
    
    # 1. Check if the institute exists in the public schema, if not create it
    cursor.execute("SELECT id FROM public.academics_institute WHERE id = %s;", (target_inst_id,))
    if not cursor.fetchone():
        # Get details from source schema
        cursor.execute(f"SELECT name, address, logo, established_date FROM {src_schema}.academics_institute LIMIT 1;")
        inst_row = cursor.fetchone()
        if inst_row:
            cursor.execute(
                "INSERT INTO public.academics_institute (id, name, address, logo, established_date) VALUES (%s, %s, %s, %s, %s);",
                (target_inst_id, inst_row[0], inst_row[1], inst_row[2], inst_row[3])
            )
            print(f"Created Institute in public schema: '{inst_row[0]}' (ID: {target_inst_id})")
        else:
            # Fallback
            cursor.execute(
                "INSERT INTO public.academics_institute (id, name, address, logo, established_date) VALUES (%s, %s, %s, %s, CURRENT_DATE);",
                (target_inst_id, src_schema.capitalize(), 'Default Address', '')
            )
            print(f"Created default Institute: '{src_schema}' (ID: {target_inst_id})")
        conn.commit()

    # 2. Copy data for each table
    for table, has_inst in TABLES:
        # We skip academics_institute as we handled it above
        if table == 'academics_institute':
            continue
            
        print(f"Copying table '{table}'...")
        
        # Get active columns in public schema
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = 'public' AND table_name = '{table}'
            ORDER BY ordinal_position;
        """)
        cols = [r[0] for r in cursor.fetchall()]
        
        # Determine source columns (exclude institute_id if it wasn't in source schema)
        cursor.execute(f"""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_schema = '{src_schema}' AND table_name = '{table}';
        """)
        src_cols_set = set(r[0] for r in cursor.fetchall())
        
        # We construct the query
        select_cols = []
        insert_cols = []
        
        for col in cols:
            if col == 'institute_id' and has_inst:
                # Value for institute_id is hardcoded to the target_inst_id
                select_cols.append(f"{target_inst_id} AS institute_id")
                insert_cols.append(col)
            elif col in src_cols_set:
                select_cols.append(col)
                insert_cols.append(col)
                
        if not select_cols:
            print(f"Table {table} does not exist in source. Skipping.")
            continue
            
        select_str = ", ".join(select_cols)
        insert_str = ", ".join(insert_cols)
        
        # Copy records (using INSERT INTO ... SELECT)
        try:
            # Clear target records first to avoid duplicates if re-running
            # (Note: we cascade carefully, or just delete matching IDs)
            cursor.execute(f"SELECT id FROM {src_schema}.{table};")
            src_ids = [r[0] for r in cursor.fetchall()]
            
            if src_ids:
                id_placeholder = ", ".join(["%s"] * len(src_ids))
                cursor.execute(f"DELETE FROM public.{table} WHERE id IN ({id_placeholder});", src_ids)
                
            cursor.execute(f"""
                INSERT INTO public.{table} ({insert_str})
                SELECT {select_str} FROM {src_schema}.{table};
            """)
            print(f"  Successfully copied {cursor.rowcount} rows into public.{table}.")
        except Exception as e:
            print(f"  Error copying {table}: {e}")
            conn.rollback()
            cursor.execute("SET session_replication_role = 'replica';")
            continue
            
        conn.commit()

# Run the merge
try:
    # 1. Merge school_a (MySQL backup data) into public schema as Institute ID 1
    merge_schema('school_a', 1)
    
    # 2. Merge school_b (fresh tenant created earlier) into public schema as Institute ID 2
    # Check if school_b exists
    cursor.execute("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'school_b';")
    if cursor.fetchone():
        merge_schema('school_b', 2)

    # 3. Reset primary key auto-increment sequences for public tables
    print("\nResetting primary key sequences...")
    for table, _ in TABLES:
        # Skip many-to-many tables without serial primary key if any, but account_userdata_classs has an id
        try:
            cursor.execute(f"SELECT setval(pg_get_serial_sequence('public.{table}', 'id'), coalesce(max(id), 1)) FROM public.{table};")
            print(f"  Reset sequence for {table}")
        except Exception as seq_err:
            # Continue if table has no serial sequence
            conn.rollback()
            cursor.execute("SET session_replication_role = 'replica';")
            continue
    conn.commit()

except Exception as e:
    print("Migration failed:", e)
finally:
    # Re-enable triggers/constraints
    cursor.execute("SET session_replication_role = 'origin';")
    conn.commit()
    cursor.close()
    conn.close()
    print("\nMerge complete!")
