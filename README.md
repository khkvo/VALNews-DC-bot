# VLR.gg News Discord Bot

A simple and efficient Discord bot that fetches the latest news articles from [VLR.gg](https://www.vlr.gg/) and posts them to a designated channel in your Discord server. It includes features for automatic updates, manual fetching, and reaction roles for notifications.

 <!-- It's recommended to replace this with a real screenshot of your bot's help command -->

## Features

*   **Automatic News Updates:** Periodically checks for new articles and posts them in a configured channel.
*   **Manual Fetching:** Users can fetch the latest article on demand.
*   **Reaction Roles:** Set up a message where users can react to get a specific role, which is then pinged for new articles.
*   **Server-Specific Configuration:** Each server can have its own news channel and notification role.
*   **Easy Setup:** Simple commands to configure the bot for your server.

## Commands

The default prefix is `!vlrnews `.

### User Commands

*   **`!vlrnews help`**
    Displays the list of available commands.

*   **`!vlrnews news`**
    Fetches and displays the latest news article from VLR.gg.

### Admin Commands

These commands require specific permissions to use.

*   **`!vlrnews set_news_channel [#channel]`**
    Sets the channel where automatic news updates will be posted. If no channel is mentioned, it defaults to the current channel.
    *   *Permission Required: `Manage Channels`*

*   **`!vlrnews remove_news_channel`**
    Disables automatic news updates for the server.
    *   *Permission Required: `Manage Channels`*

*   **`!vlrnews setup_reactions <@role> [#channel]`**
    Creates a message in a specified channel (or the current one) that users can react to. Reacting gives them the mentioned role, which will be pinged for new articles.
    *   *Permissions Required: `Manage Roles` & `Manage Channels`*

### Owner-Only Commands

These commands can only be run by the bot's owner.

*   **`!vlrnews shutdown`**
    Shuts down the bot.

*   **`!vlrnews restart`**
    Restarts the bot process.

## Configuration File

The bot automatically creates and manages a `config.json` file to store settings for each server (guild). You do not need to edit this file manually.

