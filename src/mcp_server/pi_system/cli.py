#!/usr/bin/env python3
"""
PI System CLI - Command-line interface for PI management.

Usage:
    python -m pi_system.cli sync          # Sync files to database
    python -m pi_system.cli stats         # Show statistics
    python -m pi_system.cli stale         # List stale PIs
    python -m pi_system.cli duplicates    # List duplicate relationships
    python -m pi_system.cli ready         # List PIs ready for implementation
    python -m pi_system.cli unclassified  # List unclassified PIs
    python -m pi_system.cli generate      # Generate index markdown
    python -m pi_system.cli validate      # Validate file/DB consistency
"""

import argparse
import sys

from .models import PIConfidence, PIStatus
from .operations import PISystem
from .sync import PISync


def cmd_sync(args):
    """Sync markdown files to database."""
    pi_system = PISystem()
    sync = PISync(pi_system)

    print(f"Syncing PI files from {sync.pi_dir}...")
    stats = sync.sync_from_files(reset_db=args.reset)

    print("\nSync Results:")
    print(f"  Files found: {stats['files_found']}")
    print(f"  Files parsed: {stats['files_parsed']}")
    print(f"  PIs created: {stats['pis_created']}")
    print(f"  PIs updated: {stats['pis_updated']}")

    if stats["files_failed"]:
        print(f"\n  Failed ({len(stats['files_failed'])}):")
        for failure in stats["files_failed"]:
            print(f"    - {failure['file']}: {failure['error']}")

    return 0 if not stats["files_failed"] else 1


def cmd_stats(args):
    """Show PI system statistics."""
    pi_system = PISystem()
    stats = pi_system.get_stats()

    print("PI System Statistics")
    print("=" * 40)
    print(f"Total Active:      {stats['total_active']}")
    print(f"Total Archived:    {stats['total_archived']}")
    print(f"Relationships:     {stats['relationships']}")
    print(f"Evidence Records:  {stats['evidence_records']}")

    print("\nBy Confidence:")
    for conf, count in stats.get("by_confidence", {}).items():
        print(f"  {conf}: {count}")

    print("\nBy Status:")
    for status, count in stats.get("by_status", {}).items():
        print(f"  {status}: {count}")

    print("\nBy Classification:")
    for cls, count in stats.get("by_classification", {}).items():
        print(f"  {cls}: {count}")

    if stats.get("by_cluster"):
        print("\nBy Cluster:")
        for cluster, count in stats["by_cluster"].items():
            print(f"  {cluster}: {count}")

    return 0


def cmd_stale(args):
    """List stale PIs."""
    pi_system = PISystem()
    stale = pi_system.find_stale(days=args.days)

    if not stale:
        print(f"No PIs stale for {args.days}+ days")
        return 0

    print(f"Stale PIs ({args.days}+ days without evidence):")
    print("-" * 60)
    for pi in stale:
        conf = (
            pi.confidence.value
            if isinstance(pi.confidence, PIConfidence)
            else pi.confidence
        )
        print(f"  {pi.id}: {pi.title} [{conf}]")

    print(f"\nTotal: {len(stale)}")
    return 0


def cmd_duplicates(args):
    """List duplicate relationships."""
    pi_system = PISystem()
    duplicates = pi_system.find_duplicates()

    if not duplicates:
        print("No duplicate relationships found")
        return 0

    print("Duplicate Relationships:")
    print("-" * 60)
    for rel in duplicates:
        print(f"  {rel.pi_id_1} <-> {rel.pi_id_2}")
        if rel.notes:
            print(f"    Notes: {rel.notes}")

    print(f"\nTotal: {len(duplicates)}")
    return 0


def cmd_ready(args):
    """List PIs ready for implementation."""
    pi_system = PISystem()
    ready = pi_system.find_ready_for_implementation()

    if not ready:
        print("No PIs ready for implementation")
        return 0

    print("PIs Ready for Implementation:")
    print("-" * 60)
    for pi in ready:
        conf = (
            pi.confidence.value
            if isinstance(pi.confidence, PIConfidence)
            else pi.confidence
        )
        status = pi.status.value if isinstance(pi.status, PIStatus) else pi.status
        print(f"  {pi.id}: {pi.title}")
        print(
            f"    Confidence: {conf}, Status: {status}, Occurrences: {pi.occurrence_count}"
        )

    print(f"\nTotal: {len(ready)}")
    return 0


def cmd_unclassified(args):
    """List unclassified PIs."""
    pi_system = PISystem()
    unclassified = pi_system.find_unclassified()

    if not unclassified:
        print("All PIs are classified")
        return 0

    print("Unclassified PIs:")
    print("-" * 60)
    for pi in unclassified:
        conf = (
            pi.confidence.value
            if isinstance(pi.confidence, PIConfidence)
            else pi.confidence
        )
        print(f"  {pi.id}: {pi.title} [{conf}]")

    print(f"\nTotal: {len(unclassified)}")
    return 0


def cmd_generate(args):
    """Generate index markdown from database."""
    pi_system = PISystem()
    sync = PISync(pi_system)

    print(f"Generating index at {sync.index_path}...")
    sync.generate_index()
    print("Done!")
    return 0


def cmd_validate(args):
    """Validate file/DB consistency."""
    pi_system = PISystem()
    sync = PISync(pi_system)

    print("Validating consistency...")
    results = sync.validate_consistency()

    if results["valid"]:
        print("✓ Files and database are consistent")
        return 0

    print("Inconsistencies found:")

    if results["files_without_db"]:
        print(f"\n  Files without DB records ({len(results['files_without_db'])}):")
        for pi_id in results["files_without_db"]:
            print(f"    - {pi_id}")

    if results["db_without_files"]:
        print(f"\n  DB records without files ({len(results['db_without_files'])}):")
        for pi_id in results["db_without_files"]:
            print(f"    - {pi_id}")

    return 1


def cmd_list(args):
    """List all PIs."""
    pi_system = PISystem()
    all_pis = pi_system.get_all(include_archived=args.all)

    print(f"{'All' if args.all else 'Active'} PIs:")
    print("-" * 80)
    for pi in sorted(all_pis, key=lambda p: int(p.id.split("-")[1])):
        conf = (
            pi.confidence.value
            if isinstance(pi.confidence, PIConfidence)
            else pi.confidence
        )
        status = pi.status.value if isinstance(pi.status, PIStatus) else pi.status
        cls = ""
        if pi.classification:
            cls = f" [{pi.classification.value if hasattr(pi.classification, 'value') else pi.classification}]"
        print(f"  {pi.id}: {pi.title}")
        print(f"    {conf} | {status}{cls}")

    print(f"\nTotal: {len(all_pis)}")
    return 0


def main():
    parser = argparse.ArgumentParser(
        description="PI System CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Command to run")

    # sync command
    sync_parser = subparsers.add_parser("sync", help="Sync markdown files to database")
    sync_parser.add_argument(
        "--reset", action="store_true", help="Reset database before sync"
    )

    # stats command
    subparsers.add_parser("stats", help="Show statistics")

    # stale command
    stale_parser = subparsers.add_parser("stale", help="List stale PIs")
    stale_parser.add_argument(
        "--days", type=int, default=90, help="Days threshold (default: 90)"
    )

    # duplicates command
    subparsers.add_parser("duplicates", help="List duplicate relationships")

    # ready command
    subparsers.add_parser("ready", help="List PIs ready for implementation")

    # unclassified command
    subparsers.add_parser("unclassified", help="List unclassified PIs")

    # generate command
    subparsers.add_parser("generate", help="Generate index markdown")

    # validate command
    subparsers.add_parser("validate", help="Validate file/DB consistency")

    # list command
    list_parser = subparsers.add_parser("list", help="List all PIs")
    list_parser.add_argument("--all", action="store_true", help="Include archived PIs")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    commands = {
        "sync": cmd_sync,
        "stats": cmd_stats,
        "stale": cmd_stale,
        "duplicates": cmd_duplicates,
        "ready": cmd_ready,
        "unclassified": cmd_unclassified,
        "generate": cmd_generate,
        "validate": cmd_validate,
        "list": cmd_list,
    }

    return commands[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
