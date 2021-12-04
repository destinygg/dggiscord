# dggiscord

## User Commands

| Command             | Description                                         |
| ------------------- | --------------------------------------------------- |
| !sync               | Verify your subscription is connected with provider |
| !syncother @Mention | (Mod) Sync the mentioned user with provider         |

## Creating the OAuth Scope

Generate a Bot user on Discord at https://discordapp.com/developers/applications/

Bot user must have the `MANAGE_ROLES` Permission or `268435456` as a permission integer

Join URL Example: `https://discordapp.com/oauth2/authorize?client_id=<BOTID>&scope=bot&permissions=268435456`

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
