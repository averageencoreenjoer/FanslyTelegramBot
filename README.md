# Monitoring Bot for Fansly

A bot for monitoring user activity on the Fansly platform. The bot allows you to track the online status of users, send notifications about their appearance online, and manage monitoring sessions via Telegram.

## Functionality

- **Monitoring Online Status**: The bot tracks the online status of users in various categories (Subscribers, VIPs, Followers, All).
- **Notifications**: The bot sends notifications to Telegram when a user appears online.
- **Session Management**: Ability to start, stop, and edit monitoring sessions.
- **Multi-User**: Support for multiple models and categories for monitoring.
- **Administrative Interface**: Manage models, workers, and bot settings via Telegram.

## Installation and setup

### Requirements

- Python 3.8 or higher
- Installed Git
- [Fansly](https://fansly.com/) account
- Telegram Bot token (can be obtained from [BotFather](https://core.telegram.org/bots#botfather))

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/averageencoreenjoer/FanslyTelegramBot.git
   cd FanslyTelegramBot
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
3. Create a config.json file in the root directory of the project and fill it with the following:
   ```bash
   {
      "admin_login": "your_login",
      "admin_password": "your_password"
   }
4. Run bot:
   ```bash
   python app.py

## Usage

### Commands

- **/start**: Start the bot and display the main menu.
- **Get Started**: Start monitoring the selected model.
- **Account Editor**: Manage model accounts (add, delete).
- **Currently Online**: Show a list of users who are currently online.
- **Stop Monitoring**: Pause notifications.
- **Resume Monitoring**: Resume notifications.

### Adding a Model

1. Go to the **Account Editor** section.
2. Select **Add Model**.
3. Enter the email, password, and nickname of the model.
4. After adding the account, select the model to monitor.

### Monitoring

1. Select a model from the list.
2. Select a category to monitor: Subscribers, VIPs, Followers, or All.
3. The bot will start monitoring the online status of users and notify you.

## Usage examples

- **Monitor followers**: Know when your followers are online.
- **Manage multiple models**: Add multiple model accounts and manage them through one bot.
- **Configure notifications**: Enable or disable notifications for each model or category.

## License

This project is distributed under the MIT license. For more information, see the [LICENSE](LICENSE) file.

## Support

If you have any questions or problems, create an issue in the repository or contact me via Telegram.

---

**Author**: polputi inc.
**GitHub**: https://github.com/averageencoreenjoer
**Telegram**: @soprettymindset
