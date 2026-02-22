import argparse
import os
import sys
from sqlalchemy import create_engine, text

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--repo-id", required=True, help="Repository name to verify")
    args = parser.parse_args()
    
    repo_id = args.repo_id
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL environment variable not set")
        sys.exit(1)
    
    engine = create_engine(db_url)
    
    results = {}
    
    print(f"Verifying canary repo: {repo_id}\n")
    
    # Check commits
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(*) FROM commits c JOIN repositories r ON r.id = c.repository_id WHERE r.name = :repo_id
        """)
        count = conn.execute(query, {"repo_id": repo_id}).scalar()
        results["commits"] = count > 0
        print(f"  [{'PASS' if count > 0 else 'FAIL'}] commits       — {count} rows")
    
    # Check pull_requests
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(*) FROM pull_requests p JOIN repositories r ON r.id = p.repository_id WHERE r.name = :repo_id
        """)
        count = conn.execute(query, {"repo_id": repo_id}).scalar()
        results["pull_requests"] = count > 0
        print(f"  [{'PASS' if count > 0 else 'FAIL'}] pull_requests — {count} rows")
    
    # Check dependencies
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(*) FROM dependencies d JOIN repositories r ON r.id = d.repository_id WHERE r.name = :repo_id
        """)
        count = conn.execute(query, {"repo_id": repo_id}).scalar()
        results["dependencies"] = count > 0
        print(f"  [{'PASS' if count > 0 else 'FAIL'}] dependencies  — {count} rows")
    
    # Check languages
    with engine.connect() as conn:
        query = text("""
            SELECT COUNT(*) FROM languages l JOIN repositories r ON r.id = l.repository_id WHERE r.name = :repo_id
        """)
        count = conn.execute(query, {"repo_id": repo_id}).scalar()
        results["languages"] = count > 0
        print(f"  [{'PASS' if count > 0 else 'FAIL'}] languages     — {count} rows")
    
    # Check canary_join
    with engine.connect() as conn:
        query = text("""
            SELECT r.id
            FROM repositories r
            INNER JOIN commits c       ON r.id = c.repository_id
            INNER JOIN pull_requests p ON r.id = p.repository_id
            INNER JOIN dependencies d  ON r.id = d.repository_id
            INNER JOIN languages l     ON r.id = l.repository_id
            WHERE r.name = :repo_id
            LIMIT 1
        """)
        row = conn.execute(query, {"repo_id": repo_id}).fetchone()
        results["canary_join"] = row is not None
        print(f"  [{'PASS' if row is not None else 'FAIL'}] canary_join   — {('row present' if row is not None else 'no row present')}")
    
    # Overall result
    all_pass = all(results.values())
    print(f"\nOverall: {'PASS' if all_pass else 'FAIL'}")
    
    sys.exit(0 if all_pass else 1)

if __name__ == "__main__":
    main()