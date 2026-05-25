import sys
try:
    import click
    from click.testing import CliRunner
    print("Click and CliRunner are available")
except ImportError:
    print("Click or CliRunner NOT found")

import wow_advisor.cli
print(f"wow_advisor.cli main exists: {hasattr(wow_advisor.cli, 'main')}")

try:
    import cli
    print(f"root cli main exists: {hasattr(cli, 'main')}")
except ImportError:
    print("root cli NOT found")
