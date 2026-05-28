import argparse
import asyncio
import datetime
import sys
import pathlib

# Ensure repo root is on sys.path so this script can be run from `scripts/`
ROOT = pathlib.Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from telegram import Bot

from config import TELEGRAM_TOKEN, supabase


async def execute_daily_aging_audit(supabase_client, bot: Bot, *, dry_run: bool = False, verbose: bool = False):
    """Scan active debts daily and alert store owners when grace period is breached.

    If `dry_run` is True, the function will print the alert messages instead of sending them.
    """
    try:
        records = (
            supabase_client.table("customer_credit_accounts")
            .select("telegram_id, customer_name, contact_info, outstanding_balance, oldest_unpaid_credit_date, stores(debt_grace_period_days)")
            .gt("outstanding_balance", 0)
            .execute()
        )
    except Exception as e:
        print(f"Failed to query Supabase: {e}")
        return

    now = datetime.datetime.now(datetime.timezone.utc)

    all_rows = records.data or []
    if verbose:
        print(f"Fetched {len(all_rows)} debtor records from Supabase")

    alerts_sent = 0
    alerts_skipped = 0

    for row in all_rows:
        telegram_id = row.get("telegram_id")
        oldest_raw = row.get("oldest_unpaid_credit_date")
        if not oldest_raw:
            if verbose:
                print(f"Skipping {telegram_id}: no oldest_unpaid_credit_date")
            alerts_skipped += 1
            continue

        iso_text = str(oldest_raw)
        if iso_text.endswith("Z"):
            iso_text = iso_text.replace("Z", "+00:00")

        try:
            oldest_debt_date = datetime.datetime.fromisoformat(iso_text)
        except ValueError:
            if verbose:
                print(f"Skipping {telegram_id}: unparseable date '{oldest_raw}'")
            alerts_skipped += 1
            continue

        if oldest_debt_date.tzinfo is None:
            oldest_debt_date = oldest_debt_date.replace(tzinfo=datetime.timezone.utc)

        days_unpaid = (now - oldest_debt_date).days

        store_info = row.get("stores") or {}
        allowed_grace_days = int(store_info.get("debt_grace_period_days") or 30)

        if days_unpaid < allowed_grace_days:
            if verbose:
                print(f"OK {telegram_id}: {days_unpaid} days unpaid (<{allowed_grace_days})")
            alerts_skipped += 1
            continue

        alert_message = (
            "AUTOMATED AGING DEBT ALERT\n\n"
            f"Customer {row.get('customer_name')} has breached your configured {allowed_grace_days}-day grace period.\n\n"
            f"Outstanding Debt: PHP {float(row.get('outstanding_balance') or 0):,.2f}\n"
            f"Current Aging Status: {days_unpaid} day(s) unpaid\n"
            f"Initial Unpaid Purchase: {oldest_debt_date.strftime('%B %d, %Y')}\n"
            f"Registered Mobile: {row.get('contact_info') or 'Not Provided'}\n\n"
            "Use your Utang menu or dashboard to follow up."
        )

        if dry_run or verbose:
            print("--- ALERT PREVIEW ---")
            print(f"To: {telegram_id}")
            print(alert_message)

        if not dry_run:
            try:
                await bot.send_message(chat_id=telegram_id, text=alert_message)
                alerts_sent += 1
                if verbose:
                    print(f"Sent alert to {telegram_id}")
            except Exception as error:
                print(f"Failed to push alert to {telegram_id}: {error}")
        else:
            if verbose:
                print(f"Dry-run: would have sent to {telegram_id}")

    if verbose:
        print(f"Done. Alerts sent: {alerts_sent}. Alerts skipped: {alerts_skipped}.")


async def main():
    parser = argparse.ArgumentParser(description="Cron alert service for aging debts")
    parser.add_argument("--dry-run", action="store_true", help="Do not send messages; only print previews")
    parser.add_argument("--verbose", action="store_true", help="Print verbose debug output")
    args = parser.parse_args()

    bot = Bot(token=TELEGRAM_TOKEN)
    await execute_daily_aging_audit(supabase, bot, dry_run=args.dry_run, verbose=args.verbose)


if __name__ == "__main__":
    asyncio.run(main())
