#!/usr/bin/env python3
import click
from tmobile import analyze_tmobile_bill
from swgas import pay_southwest_gas_bill

@click.group()
def cli():
    """Pay Bills CLI application."""
    pass

@cli.command()
@click.option('--dry-run', is_flag=True, help='Run through the process but do not submit Venmo requests')
def tmobile(dry_run):
    """Analyze T-Mobile bill and send payment requests."""
    click.echo("Analyzing T-Mobile bill...")
    analyze_tmobile_bill(dry_run=dry_run)

@cli.command()
def swgas():
    """Pay Southwest Gas bill if due today."""
    click.echo("Processing Southwest Gas bill payment...")
    pay_southwest_gas_bill()

if __name__ == "__main__":
    cli()
