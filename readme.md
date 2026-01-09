# dggiscord

## User Commands

| Command             | Description                                         |
| ------------------- | --------------------------------------------------- |
| !sync               | Verify your subscription is connected with provider |
| !syncother @Mention | (Mod) Sync the mentioned user with provider         |

## Creating a Bot User

1. Create a new application in the [Discord developer portal](https://discordapp.com/developers/applications/)

2. Enable required intents

   1. Open the app's _Bot_ settings
   2. Under _Privileged Gateway Intents_, enable _Server Members Intent_ and _Message Content Intent_

3. Invite the bot to your server

   1. Navigate to the app's _OAuth2_ settings
   2. Under _Scopes_, toggle the _bot_ checkbox
   3. Under _Bot Permissions_, toggle the _Manage Roles_ checkbox
   4. Open the _Generated URL_ in your web browser
   5. Follow the on-screen instructions to complete the process

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
