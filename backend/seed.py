"""Manage the optional demo profile (useful for screenshots or presentations).

Usage (from the backend folder, venv active):
    python seed.py            # add the demo profile if the database has no profile
    python seed.py --reset    # overwrite the current profile with the demo profile
    python seed.py --clear    # remove the demo profile (your real profile is never touched)
"""

import argparse

from app.core.database import SessionLocal, init_db
from app.services.seed import remove_demo_profile, seed_demo_profile


def main() -> None:
    parser = argparse.ArgumentParser(description="Manage HireMate's demo profile.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--reset", action="store_true", help="overwrite the current profile with the demo profile")
    group.add_argument("--clear", action="store_true", help="remove the demo profile")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as db:
        if args.clear:
            removed = remove_demo_profile(db)
            print("Demo profile removed." if removed else "No demo profile found. Nothing to remove.")
            return
        written = seed_demo_profile(db, force=args.reset)
    print("Demo profile written." if written else "A profile already exists. Use --reset to overwrite it.")


if __name__ == "__main__":
    main()
