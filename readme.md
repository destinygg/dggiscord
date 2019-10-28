# dggiscord

## User Commands

| Command | Description |
| ----------- | ----------- |
| !sync | Verify your subscription is connected with provider |
| !syncother @Mention | (Mod) Sync the mentioned user with provider |

## Creating the OAuth Scope

Generate a Bot user on Discord at https://discordapp.com/developers/applications/

Bot user must have the `MANAGE_ROLES` Permission or `268435456` as a permission integer

Join URL Example: `https://discordapp.com/oauth2/authorize?client_id=<BOTID>&scope=bot&permissions=268435456`

## Runnin' It

Docker:
```
mkdir cfg
git clone https://github.com/destinygg/dggiscord.git src
cd src
docker build -t dggiscord .
cp config.example.json ../cfg/config.json

<edit config.json>

chown -R 1004:1004 /home/bots/dggiscord/
docker run -it --user 1004:1004 -v /home/bots/dggiscord/cfg:/dggiscord/cfg --restart=always --name dggiscord dggiscord
```

Console:
```
git clone https://github.com/destinygg/dggiscord.git .
mkdir cfg
cp config.example.json ../cfg/config.json

<edit config.json>

python3 ./dggiscord/app.py
```

## Updatin' It

Docker:
```
docker stop dggiscord
docker rm dggiscord
cd /home/bots/dggiscord/; git pull origin master
docker build -t dggiscord .
docker run -it --user 1004:1004 -v /home/bots/dggiscord/cfg:/dggiscord/cfg --restart=unless-stopped --name dggiscord dggiscord
```
