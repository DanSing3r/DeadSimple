# Calorie Counter Telegram Bot

A simple Telegram bot for tracking daily calories and protein intake with a pantry system for quick food logging.

## Features

- 📊 Track daily calories and protein
- 🥫 Pantry system for quick food lookup
- 📝 Manual food entry
- 🕰️ Custom "nutrition day" (5 AM - 4:59 AM)
- 📈 Daily summaries with remaining goals

## Commands

- `/start` - Start bot and see daily summary
- `/ate <food> <calories> <protein>` - Log custom food
  - Example: `/ate chicken breast 200 30`
- `/addpantry <name> <calories> <protein>` - Add food to pantry
  - Example: `/addpantry apple 95 0.5`
- `/food <name> [serving]` - Log food from pantry
  - Example: `/food apple` or `/food chicken 1.5`
- `/listpantry` - Show all pantry items
- `/editpantry <name> <calories> <protein>` - Update pantry item
- `/deletepantry <name>` - Remove food from pantry

## Setup

### 1. Install Dependencies
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install python-telegram-bot python-dotenv
```

### 2. Configure Environment
Create `config.env` file:
```
BOT_TOKEN=your_telegram_bot_token
FOOD_FILE=food_log.csv
PANTRY_FILE=pantry.csv
DAILY_CALORIES=2000
DAILY_PROTEIN=100
CUTOFF_HOUR=5
```

### 3. Get Bot Token
1. Talk to [@BotFather](https://t.me/botfather) on Telegram
2. Send `/newbot`
3. Follow instructions to get your bot token

### 4. Run Bot
```bash
python bot1.py
```

## Configuration

- `BOT_TOKEN`: Your Telegram bot token (required)
- `FOOD_FILE`: Path to food log CSV (default: food_log.csv)
- `PANTRY_FILE`: Path to pantry CSV (default: pantry.csv)
- `DAILY_CALORIES`: Daily calorie goal (default: 2000)
- `DAILY_PROTEIN`: Daily protein goal in grams (default: 100)
- `CUTOFF_HOUR`: Hour before which food counts as previous day (default: 5)

## Data Format

### Food Log (food_log.csv)
```
date|food_name|calories|protein
2024-01-15|chicken breast|200|30
```

### Pantry (pantry.csv)
```
food_name|calories|protein
apple|95|0.5
```

## Nutrition Day Logic

The bot uses a custom "nutrition day" concept:
- Foods logged before 5:00 AM count as the previous day
- Foods logged at or after 5:00 AM count as the current day

This design helps with late-night eating habits, ensuring midnight snacks don't incorrectly inflate the next day's totals.

## Example Workflow

1. Add foods to pantry:
   ```
   /addpantry banana 105 1.3
   /addpantry rice 130 2.7
   ```

2. Log meals throughout the day:
   ```
   /food banana
   /ate steak 400 35
   ```

3. Check daily totals:
   ```
   /start
   🔥 Calories: 505 (1495 left)
   🍖 Protein: 36.3g (63.7g left)
   ```

## Dependencies

- `python-telegram-bot>=22.0` - Telegram bot framework
- `python-dotenv` - Environment variable management

## License

MIT