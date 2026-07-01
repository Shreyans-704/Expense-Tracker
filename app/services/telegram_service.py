import logging
from telegram import Update
from telegram.ext import ContextTypes

from app.services.local_parser import LocalExpenseParser
from app.services.google_sheets_service import append_expense, undo_last_expense, GoogleSheetsError, get_current_balance, update_current_balance, get_last_expense_row, delete_row
from app.core.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    @staticmethod
    async def handle_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /start command."""
        logger.info("Received /start from user_id=%s", update.effective_user.id)
        welcome_message = (
            "👋 Welcome to Expense Tracker AI!\n\n"
            "Let's set up your wallet.\n"
            "First tell me your current account balance.\n\n"
            "Example\n"
            "Balance 25000\n\n"
            "After that you can simply send\n"
            "Spent 250 on Lunch\n"
            "Coffee 80\n"
            "Uber 300\n\n"
            "Use Balance anytime to check your current balance."
        )
        await update.message.reply_text(welcome_message)

    @staticmethod
    async def handle_balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle the /balance command."""
        logger.info("Received /balance from user_id=%s", update.effective_user.id)
        try:
            balance = await get_current_balance()
            if balance is not None:
                await update.message.reply_text(f"💰 Current Balance\n\n{balance}")
            else:
                await update.message.reply_text("❌ Could not read balance.")
        except Exception as exc:
            logger.error("Error reading balance: %s", exc)
            await update.message.reply_text("❌ An error occurred while fetching the balance.")

    @staticmethod
    async def handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Undo the last expense and restore the balance."""
        logger.info("Received /undo from user_id=%s", update.effective_user.id)

        try:
            # Read last expense without deleting it
            last_expense = await get_last_expense_row("Expenses")

            if not last_expense:
                await update.message.reply_text("❌ Nothing to undo.")
                return

            # Read current balance
            balance_str = await get_current_balance()

            import re

            balance = float(re.sub(r"[^\d.-]", "", balance_str))
            amount = float(re.sub(r"[^\d.-]", "", str(last_expense["amount"])))

            old_balance = balance
            new_balance = balance + amount

            # Restore balance first
            await update_current_balance(new_balance)

            try:
                # Delete expense row
                await delete_row("Expenses", last_expense["row_index"])

            except Exception:
                # Rollback balance
                await update_current_balance(old_balance)
                raise

            formatted_balance = (
                f"₹{new_balance:,.0f}"
                if new_balance.is_integer()
                else f"₹{new_balance:,.2f}"
            )

            await update.message.reply_text(
                f"✅ Last expense removed.\n\n"
                f"Amount: ₹{amount:,.0f}\n"
                f"Item: {last_expense['item']}\n"
                f"Category: {last_expense['category']}\n\n"
                f"Current Balance\n"
                f"{formatted_balance}"
            )

        except GoogleSheetsError as exc:
            logger.error("Undo failed: %s", exc)
            await update.message.reply_text("❌ Failed to undo the last expense.")

        except Exception as exc:
            logger.exception(exc)
            await update.message.reply_text("❌ An unexpected error occurred.")



    @staticmethod
    async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Parse text, save to Sheets, reply."""
        text = update.message.text
        logger.info("Received text from user_id=%s: %s", update.effective_user.id, text)
        
        text_lower = text.lower().strip()
        
        # Intercept balance check
        if text_lower == "balance":
            try:
                balance = await get_current_balance()
                if balance is not None:
                    await update.message.reply_text(f"💰 Current Balance\n\n{balance}")
                else:
                    await update.message.reply_text("❌ Could not read balance.")
            except Exception as exc:
                logger.error("Error reading balance: %s", exc)
                await update.message.reply_text("❌ An error occurred while fetching the balance.")
            return
            
        # Intercept balance update
        import re
        balance_match = re.match(r'^(?:set\s+)?balance\s+(\d+(?:\.\d+)?)$', text_lower)
        if balance_match:
            amount = float(balance_match.group(1))
            try:
                await update_current_balance(amount)
                # Format to show rupees, assuming format like ₹25,000
                formatted_amount = f"₹{amount:,.0f}" if amount.is_integer() else f"₹{amount:,.2f}"
                await update.message.reply_text(f"🏦 Balance Updated\n\nCurrent Balance\n{formatted_amount}")
            except Exception as exc:
                logger.error("Error updating balance: %s", exc)
                await update.message.reply_text("❌ An error occurred while updating the balance.")
            return
        
        parser = LocalExpenseParser()
        parsed = await parser.parse(text)

        if not parsed:
            await update.message.reply_text(
                "❌ I couldn't understand the expense.\n\n"
                "Examples:\n"
                "Spent 50 on juice\n"
                "Coffee 80\n"
                "Uber 220"
            )
            return

        expense_dict = {
            "amount": float(parsed.amount),
            "item": parsed.item,
            "category": parsed.category,
            "notes": parsed.notes,
            "date": parsed.date.strftime("%Y-%m-%d")
        }

        try:
            # 1. Read current balance
            current_balance_str = await get_current_balance()
            if not current_balance_str:
                await update.message.reply_text("❌ Could not read current balance. Expense not saved.")
                return

            # 2. Parse balance float
            import re
            balance_cleaned = re.sub(r'[^\d.-]', '', current_balance_str)
            if not balance_cleaned:
                await update.message.reply_text("❌ Could not parse current balance. Expense not saved.")
                return

            old_balance = float(balance_cleaned)
            new_balance = old_balance - float(parsed.amount)

            # 3. Update balance first
            await update_current_balance(new_balance)

            # 4. Append expense
            try:
                await append_expense(expense_dict)
            except Exception as e:
                # 5. Rollback balance
                logger.error("Append failed, rolling back balance: %s", e)
                try:
                    await update_current_balance(old_balance)
                except Exception as rollback_err:
                    logger.error("Rollback failed: %s", rollback_err)
                raise e # re-raise to be caught by outer try-except

            # 6. Reply
            formatted_amount = f"₹{new_balance:,.0f}" if new_balance.is_integer() else f"₹{new_balance:,.2f}"
            await update.message.reply_text(
                f"✅ Expense Added\n\n"
                f"Amount: ₹{parsed.amount}\n"
                f"Item: {parsed.item}\n"
                f"Category: {parsed.category}\n\n"
                f"Remaining Balance\n"
                f"{formatted_amount}"
            )
        except GoogleSheetsError as exc:
            logger.error("Failed to append expense to Sheets: %s", exc)
            await update.message.reply_text("❌ Failed to save expense to Google Sheets.")
        except Exception as exc:
            logger.error("Unexpected error saving expense: %s", exc)
            await update.message.reply_text("❌ An unexpected error occurred.")

    @staticmethod
    async def handle_error(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Log Errors caused by Updates."""
        logger.error("Exception while handling an update:", exc_info=context.error)
