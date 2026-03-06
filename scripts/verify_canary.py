import argparse
import os
import sys
from sqlalchemy import create_engine, text

def main():
    parser = argparse.ArgumentParser(description="Verify canary repo data presence in the database.")
    parser.add_argument("--repo-id", required=True, help="Repository name to verify")
    args = parser.parse_args()

    DATABASE_URL = os.environ["DATABASE_URL"]
    engine = create_engine(DATABASE_URL)
    
    queries = {
        "commits": "SELECT COUNT(*) FROM commits c JOIN repositories r ON r.id = c.repository_id WHERE r.name = :repo_id",
        "pull_requests": "SELECT COUNT(*) FROM pull_requests p JOIN repositories r ON r.id = p.repository_id WHERE r.name = :repo_id",
        "dependencies": "SELECT COUNT(*) FROM dependencies d JOIN repositories r ON r.id = d.repository_id WHERE r.name = :repo_id",
        "languages": "SELECT COUNT(*) FROM languages l JOIN repositories r ON r.id = l.repository_id WHERE r.name = :repo_id",
        "canary_join": "SELECT r.id FROM repositories r INNER JOIN commits c ON r.id = c.repository_id INNER JOIN pull_requests p ON r.id = p.repository_id INNER JOIN dependencies d ON r.id = d.repository_id INNER JOIN languages l ON r.id = l.repository_id WHERE r.name = :repo_id LIMIT 1"
    }
    
    results = {}
    
    for label, query in queries.items():
        with engine.connect() as connection:
            result = connection.execute(text(query), {"repo_id": args.repo_id}).fetchone()
            if label == "canary_join":
                results[label] = bool(result)
            else:
                results[label] = result[0] > 0
    
    print(f"Verifying canary repo: {args.repo_id}")
    
    overall_pass = True
    for label, passed in results.items():
        status = "PASS" if passed else "FAIL"
        row_info = f"{result[0]} rows" if isinstance(result, tuple) else ("no row present" if not result else "1 row")
        print(f"    [{status}] {label} — {row_info}")
        overall_pass &= passed
    
    sys.exit(0 if overall_pass else 1)

if __name__ == "__main__":
    main()