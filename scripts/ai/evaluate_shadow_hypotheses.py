"""Read-only prospective report for one pre-registered shadow hypothesis."""
from pathlib import Path
import argparse
import json
import sqlite3
import sys

sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from katarina.intelligence.shadow.shadow_research_evaluation import evaluate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database",required=True)
    args = parser.parse_args()
    database = Path(args.database).resolve()
    if not database.is_file():
        parser.error("observer database does not exist")
    with sqlite3.connect(database.as_uri()+"?mode=ro",uri=True) as db:
        result = evaluate(db)
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__=="__main__":
    main()
