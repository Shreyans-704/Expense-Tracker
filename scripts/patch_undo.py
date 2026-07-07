import re

with open("app/services/telegram_service.py", "r", encoding="utf-8") as f:
    content = f.read()

# Add imports
content = content.replace(
    "from app.services.google_sheets_service import append_expense, undo_last_expense, GoogleSheetsError, get_current_balance, update_current_balance",
    "from app.services.google_sheets_service import append_expense, undo_last_expense, GoogleSheetsError, get_current_balance, update_current_balance, get_last_expense_row, delete_row\nfrom app.core.config import settings"
)

# Rewrite handle_undo
old_undo_start = """    @staticmethod
    async def handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        \"\"\"Handle the /undo command.\"\"\"
        logger.info("Received /undo from user_id=%s", update.effective_user.id)
        logger.info("Finding last expense row")

        try:
            last_expense = await undo_last_expense()
            if not last_expense:
                await update.message.reply_text("❌ Nothing to undo.")
                return

            logger.info("Deleting row")
            # Row is already deleted by undo_last_expense, we just confirm it
            logger.info("Undo successful")

            await update.message.reply_text(
                f"✅ Last expense removed.\n\n"
                f"Amount: ₹{last_expense['amount']}\n"
                f"Item: {last_expense['item']}\n"
                f"Category: {last_expense['category']}"
            )
        except GoogleSheetsError as exc:
            logger.error("Failed to undo expense: %s", exc)
            await update.message.reply_text("❌ Failed to undo the last expense.")
        except Exception as exc:
            logger.error("Unexpected error during undo: %s", exc)
            await update.message.reply_text("❌ An unexpected error occurred.")"""

new_undo = r"""    @staticmethod
    async def handle_undo(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        \"\"\"Handle the /undo command.\"\"\"
        logger.info("Received /undo from user_id=%s", update.effective_user.id)
        logger.info("Finding last expense row")

        try:
            range_str = settings.google_sheets_range
            sheet_name = range_str.split("!")[0] if "!" in range_str else "Sheet1"
            
            # 1. Find last transaction
            last_expense = await get_last_expense_row(sheet_name)
            if not last_expense:
                await update.message.reply_text("❌ Nothing to undo.")
                return
                
            # 2. Read balance
            current_balance_str = await get_current_balance()
            if not current_balance_str:
                await update.message.reply_text("❌ Could not read current balance. Undo failed.")
                return
                
            import re
            balance_cleaned = re.sub(r'[^\d.-]', '', current_balance_str)
            if not balance_cleaned:
                await update.message.reply_text("❌ Could not parse current balance. Undo failed.")
                return
                
            old_balance = float(balance_cleaned)
            
            # Clean amount from last_expense
            amount_str = str(last_expense.get("amount", "0"))
            amount_cleaned = re.sub(r'[^\d.-]', '', amount_str)
            amount = float(amount_cleaned) if amount_cleaned else 0.0
            
            # 3 & 4. Adjust balance based on Type (assuming category == "Credit" is Credit)
            is_credit = last_expense.get("category", "") == "Credit"
            if is_credit:
                new_balance = old_balance - amount
            else:
                new_balance = old_balance + amount
                
            # 5. Update settings balance
            await update_current_balance(new_balance)
            
            # 6. Delete the row
            try:
                await delete_row(sheet_name, last_expense["row_index"])
            except Exception as e:
                # Rollback balance
                logger.error("Failed to delete row, rolling back balance: %s", e)
                try:
                    await update_current_balance(old_balance)
                except Exception as rollback_err:
                    logger.error("Rollback failed: %s", rollback_err)
                raise e
            
            logger.info("Undo successful")

            # 7. Reply
            formatted_amount = f"₹{new_balance:,.0f}" if new_balance.is_integer() else f"₹{new_balance:,.2f}"
            await update.message.reply_text(
                f"↩️ Last transaction removed.\n\n"
                f"Current Balance\n"
                f"{formatted_amount}"
            )
        except GoogleSheetsError as exc:
            logger.error("Failed to undo expense: %s", exc)
            await update.message.reply_text("❌ Failed to undo the last expense.")
        except Exception as exc:
            logger.error("Unexpected error during undo: %s", exc)
            await update.message.reply_text("❌ An unexpected error occurred.")"""

content = content.replace(old_undo_start, new_undo)

with open("app/services/telegram_service.py", "w", encoding="utf-8") as f:
    f.write(content)
