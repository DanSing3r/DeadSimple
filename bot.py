from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from datetime import timedelta, datetime as dt
from dataclasses import dataclass
from typing import Optional, Tuple
import re
import os
from dotenv import load_dotenv

# Load environment variables from config file
load_dotenv('config.env')

# Constants
DAILY_CALORIES = int(os.getenv('DAILY_CALORIES', '2000'))
DAILY_PROTEIN = int(os.getenv('DAILY_PROTEIN', '100'))
FOOD_FILE = os.getenv('FOOD_FILE', 'food_log.csv')
PANTRY_FILE = os.getenv('PANTRY_FILE', 'pantry.csv')
CUTOFF_HOUR = 5  # Pre-5am counts as previous day

@dataclass
class Nutrition:
    name: str
    calories: float
    protein: float

class FoodRepository:
    def save_entry(self, nutrition: Nutrition) -> None:
        with open(FOOD_FILE, 'a') as fh:
            fh.write(f'{get_today(as_string=True)}|{nutrition.name}|{nutrition.calories}|{nutrition.protein}\n')
    
    def get_daily_totals(self, date) -> Tuple[int, int]:
        if not os.path.exists(FOOD_FILE):
            return 0, 0
            
        daily_cals = 0.0
        daily_protein = 0.0
        s_date = date.strftime('%Y-%m-%d')
        
        with open(FOOD_FILE, 'r') as fh:
            for line in fh:
                if s_date in line:
                    entry = line.strip().split('|')
                    if len(entry) >= 4:
                        daily_cals += float(entry[2])
                        daily_protein += float(entry[3])
        
        return round(daily_cals), round(daily_protein)
    
    def find_pantry_item(self, name: str) -> Optional[Nutrition]:
        if not os.path.exists(PANTRY_FILE):
            return None
            
        with open(PANTRY_FILE, 'r') as fh:
            for line in fh:
                if name.lower() in line.lower():
                    label = line.strip().split('|')
                    if len(label) >= 3:
                        return Nutrition(
                            name=label[0],  # Use the exact name from pantry
                            calories=float(label[1]),
                            protein=float(label[2])
                        )
        return None
    
    def add_pantry_item(self, nutrition: Nutrition) -> None:
        """Add new item to pantry database"""
        with open(PANTRY_FILE, 'a') as fh:
            fh.write(f'{nutrition.name}|{nutrition.calories}|{nutrition.protein}\n')
    
    def list_pantry_items(self) -> list:
        """Get all pantry items"""
        if not os.path.exists(PANTRY_FILE):
            return []
        
        items = []
        with open(PANTRY_FILE, 'r') as fh:
            for line in fh:
                label = line.strip().split('|')
                if len(label) >= 3:
                    items.append({
                        'name': label[0],
                        'calories': float(label[1]),
                        'protein': float(label[2])
                    })
        return items
    
    def update_pantry_item(self, name: str, nutrition: Nutrition) -> bool:
        """Update existing pantry item"""
        if not os.path.exists(PANTRY_FILE):
            return False
        
        updated = False
        lines = []
        
        with open(PANTRY_FILE, 'r') as fh:
            for line in fh:
                label = line.strip().split('|')
                if len(label) >= 3 and name.lower() in label[0].lower():
                    lines.append(f'{nutrition.name}|{nutrition.calories}|{nutrition.protein}\n')
                    updated = True
                else:
                    lines.append(line)
        
        if updated:
            with open(PANTRY_FILE, 'w') as fh:
                fh.writelines(lines)
        
        return updated
    
    def delete_pantry_item(self, name: str) -> bool:
        """Delete item from pantry"""
        if not os.path.exists(PANTRY_FILE):
            return False
        
        deleted = False
        lines = []
        
        with open(PANTRY_FILE, 'r') as fh:
            for line in fh:
                label = line.strip().split('|')
                if len(label) >= 3 and name.lower() not in label[0].lower():
                    lines.append(line)
                else:
                    deleted = True
        
        if deleted:
            with open(PANTRY_FILE, 'w') as fh:
                fh.writelines(lines)
        
        return deleted

def get_today(as_string: bool = False):
    moment = dt.now()
    if moment.hour < CUTOFF_HOUR:
        moment = moment - timedelta(days=1)
    
    return moment.strftime('%Y-%m-%d') if as_string else moment

def parse_food_input(args: str) -> Tuple[str, float, float]:
    """Parse food input in format: 'item calories protein'"""
    parts = args.strip().split()
    if len(parts) < 3:
        raise ValueError("Format: item calories protein")
    
    # Find where numbers start
    for i, part in enumerate(parts):
        if part.replace('.', '').isdigit():
            item = ' '.join(parts[:i])
            calories = float(parts[i])
            protein = float(parts[i + 1]) if i + 1 < len(parts) else 0.0
            return item, calories, protein
    
    raise ValueError("Could not find calories/protein numbers")

async def send_daily_summary(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send daily calorie/protein summary"""
    try:
        totals = food_repo.get_daily_totals(get_today(as_string=False))
        cals_left = DAILY_CALORIES - totals[0]
        protein_left = DAILY_PROTEIN - totals[1]
        
        await update.message.reply_text(
            f'🔥 Calories: {totals[0]} ({cals_left} left)\n'
            f'🍖 Protein: {totals[1]}g ({protein_left}g left)'
        )
    except Exception as e:
        await update.message.reply_text('Couldn\'t read food data.')

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text("Calorie counter 1.0")

async def ate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = update.message.text[5:]
    
    try:
        item, calories, protein = parse_food_input(args)
        nutrition = Nutrition(item, calories, protein)
        food_repo.save_entry(nutrition)
        await update.message.reply_text(f'✅ 🍽️ Saved food.')
        await send_daily_summary(update, context)
        
    except ValueError as e:
        await update.message.reply_text(f'Invalid format: {e}')
    except Exception as e:
        print(e)
        await update.message.reply_text('Couldn\'t save food.')

async def food(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    args = update.message.text[6:].strip()
    
    # Parse serving size multiplier if present
    serving_match = re.search(r'(\d+(?:\.\d+)?)\s*$', args)
    serving = float(serving_match.group(1)) if serving_match else 1.0
    food_name = args[:serving_match.start()].strip() if serving_match else args
    
    if not food_name:
        await update.message.reply_text('Please specify a food item.')
        return
    
    try:
        pantry_item = food_repo.find_pantry_item(food_name)
        if not pantry_item:
            await update.message.reply_text('Food not found in pantry.')
            return
        
        # Calculate nutrition based on serving multiplier
        nutrition = Nutrition(
            name=pantry_item.name,
            calories=round(pantry_item.calories * serving, 2),
            protein=round(pantry_item.protein * serving, 2)
        )
        
        food_repo.save_entry(nutrition)
        serving_text = f' ({serving}x)' if serving != 1.0 else ''
        await update.message.reply_text(
            f'✅ 🍽️ Saved food{serving_text}.\n'
            f'🔥 {round(nutrition.calories)} calories 🍖 {round(nutrition.protein)}g protein'
        )
        await send_daily_summary(update, context)
        
    except FileNotFoundError:
        await update.message.reply_text('Pantry file not found.')
    except Exception as e:
        print(e)
        await update.message.reply_text('Couldn\'t save food.')

async def addpantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Add new item to pantry: /addpantry name calories protein"""
    args = update.message.text[11:].strip()
    
    try:
        name, calories, protein = parse_food_input(args)
        nutrition = Nutrition(name, float(calories), float(protein))
        food_repo.add_pantry_item(nutrition)
        await update.message.reply_text(f'✅ Added {name} to pantry ({calories} cal, {protein}g protein)')
        
    except ValueError as e:
        await update.message.reply_text(f'Invalid format: {e}')
    except Exception as e:
        await update.message.reply_text('Couldn\'t add to pantry.')

async def listpantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """List all pantry items"""
    try:
        items = food_repo.list_pantry_items()
        if not items:
            await update.message.reply_text('Pantry is empty.')
            return
        
        response = '📝 Pantry Items:\n'
        for item in items:
            response += f'• {item["name"]}: {item["calories"]} cal, {item["protein"]}g protein\n'
        
        await update.message.reply_text(response)
        
    except Exception as e:
        await update.message.reply_text('Couldn\'t read pantry.')

async def editpantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Edit pantry item: /editpantry name calories protein"""
    args = update.message.text[12:].strip()
    
    try:
        name, calories, protein = parse_food_input(args)
        nutrition = Nutrition(name, float(calories), float(protein))
        
        if food_repo.update_pantry_item(name, nutrition):
            await update.message.reply_text(f'✅ Updated {name} in pantry ({calories} cal, {protein}g protein)')
        else:
            await update.message.reply_text(f'❌ {name} not found in pantry.')
            
    except ValueError as e:
        await update.message.reply_text(f'Invalid format: {e}')
    except Exception as e:
        await update.message.reply_text('Couldn\'t update pantry.')

async def deletepantry(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Delete pantry item: /deletepantry name"""
    name = update.message.text[14:].strip()
    
    if not name:
        await update.message.reply_text('Please specify a food name to delete.')
        return
    
    try:
        if food_repo.delete_pantry_item(name):
            await update.message.reply_text(f'✅ Deleted {name} from pantry.')
        else:
            await update.message.reply_text(f'❌ {name} not found in pantry.')
            
    except Exception as e:
        await update.message.reply_text('Couldn\'t delete from pantry.')

async def unknown_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"Sorry I can't recognize you, you said '{update.message.text}'")

async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        f"'{update.message.text}' is not a valid command")

# Initialize repository
food_repo = FoodRepository()

# Set up bot handlers
bot_token = os.getenv('BOT_TOKEN')
if not bot_token:
    raise ValueError("BOT_TOKEN not found in config.env file")
application = Application.builder().token(bot_token).build()

application.add_handler(CommandHandler('start', start))
application.add_handler(CommandHandler('ate', ate))
application.add_handler(CommandHandler('food', food))
application.add_handler(CommandHandler('addpantry', addpantry))
application.add_handler(CommandHandler('listpantry', listpantry))
application.add_handler(CommandHandler('editpantry', editpantry))
application.add_handler(CommandHandler('deletepantry', deletepantry))
application.add_handler(MessageHandler(filters.TEXT, unknown))
application.add_handler(MessageHandler(filters.COMMAND, unknown))
application.add_handler(MessageHandler(filters.TEXT, unknown_text))

application.run_polling()