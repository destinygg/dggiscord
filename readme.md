# dggiscord

## User Commands

| Command                                                          | Description                                             | Permissions           |
| ---------------------------------------------------------------- | ------------------------------------------------------- | --------------------- |
| !sync                                                            | Sync your Dgg subscription and/or username              | All Users             |
| !syncother @Mention                                              | Sync the mentioned user's Dgg subscription and username | Privileged Users Only |
| !sync-settings [{enable\|disable} {subscription\|username\|all}] | View or change sync settings                            | Privileged Users Only |

> Note: A privileged user is the server owner, the bot owner, or a user with one of the following permissions: _Manage Roles_, _Manage Channels_, _Manage Server_, _Administrator_.

## Creating a Bot User

1. Create a new application in the [Discord developer portal](https://discordapp.com/developers/applications/)

2. Enable required intents

   1. Open the app's _Bot_ settings
   2. Under _Privileged Gateway Intents_, enable _Server Members Intent_ and _Message Content Intent_

3. Invite the bot to your server

   1. Navigate to the app's _OAuth2_ settings
   2. Under _Scopes_, toggle the _bot_ checkbox
   3. Under _Bot Permissions_, toggle the _Manage Roles_ checkbox
   4. (Optional) Toggle the _Manage Nicknames_ checkbox to enable username syncing
   5. Open the _Generated URL_ in your web browser
   6. Follow the on-screen instructions to complete the process

## Runnin' It

Docker:

```
mkdir cfg
cp config.example.json ./cfg/config.json
<edit config.json>
docker-compose up
```

Console:

```
git clone https://github.com/destinygg/dggiscord.git .
mkdir cfg
cp config.example.json ./cfg/config.json
<edit config.json>

python3 ./dggiscord/app.py [--config <alternative location>]
```

## Updatin' It

docker-compose up -d --build

## Database Migrations

Database migrations run automatically when the application starts. The system will create a `migrations` table to track applied migrations, and execute any that are pending. You can manage migrations manually using `./dggiscord/migrate.py`.
