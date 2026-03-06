import argparse
import json
import pathlib
import sys
from src.extractors.factory import get_extractor

def main():
    parser = argparse.ArgumentParser(description="Capture a repository snapshot and save it as a scenario JSON file.")
    parser.add_argument("repo_id", help="Repository identifier (e.g. 'owner/repo' for GitHub)")
    parser.add_argument("--platform", required=True, choices=["github", "azure_devops"], help="Platform: 'github' or 'azure_devops'")
    parser.add_argument("--output", required=True, help="Path to write scenario JSON")
    parser.add_argument("--branch", default=None, help="Branch to scan (default: default branch)")
    
    args = parser.parse_args()

    try:
        extractor = get_extractor(args.platform)
        
        file_tree = extractor.get_file_tree(args.repo_id, branch=args.branch)
        file_names = [item.path for item in file_tree if not item.is_directory]
        
        language_data = [
            {
                "language": ld.language,
                "byte_count": ld.byte_count,
                "percentage": ld.percentage
            }
            for ld in extractor.get_languages(args.repo_id)
        ]
        
        manifests = [
            {
                "file_path": m.file_path,
                "content": m.content,
                "ecosystem": m.ecosystem
            }
            for m in extractor.extract_manifests(args.repo_id, branch=args.branch)
        ]
        
        scenario = {
            "name": pathlib.Path(args.output).stem,
            "description": f"Captured from {args.platform}:{args.repo_id}",
            "file_names": file_names,
            "language_data": language_data,
            "manifests": manifests
        }
        
        output_path = pathlib.Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w') as f:
            json.dump(scenario, f, indent=2)
        
        print(f"Captured {len(file_names)} files, {len(manifests)} manifests, and {len(language_data)} languages.")
    
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()