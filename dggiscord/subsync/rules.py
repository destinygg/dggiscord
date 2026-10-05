"""
The decisions behind flair, role and nickname sync.

Everything here is a pure function of plain data and Discord objects' attributes,
with no config, database or bot dependency, so it can be tested directly. The
callers in subsync.sync, subsync.translator and commands.sync apply the results.
"""


def parse_flair_color(color):
    """Convert a flair's "#RRGGBB" color to an int; an empty color is black."""
    if color == "":
        return 0x000000
    return int(color.replace("#", "0x"), 16)


def flair_needs_resync(role_name, role_color, flair):
    """True if a role's name or color (str(role.color)) has drifted from its flair."""
    return role_name != flair['label'] or role_color != flair['color'].lower()


def valid_flair_names(flair_json, translate):
    """The flair names that exist in the flairs API and are configured to translate."""
    return {flair['name'] for flair in flair_json} & set(translate)


def stale_flairs(rows, valid_flairs):
    """
    Pick the (role_id, flair_name) mappings whose flair is no longer valid.

    Args:
        rows: (discord_role, dgg_flair) pairs from the flairmap table
        valid_flairs: set returned by valid_flair_names()
    """
    return [(role_id, flair_name) for role_id, flair_name in rows if flair_name not in valid_flairs]


def roles_to_add(member_role_ids, profile, rolemap):
    """
    The role IDs a member should be given for their profile's features.

    Args:
        member_role_ids: IDs of the roles the member already has
        profile: DGG profile dict
        rolemap: flair name -> role ID, as built by subsync.sync.role_map()
    """
    have = {int(role_id) for role_id in member_role_ids}
    add = []
    for feature in profile['features']:
        if feature in rolemap and int(rolemap[feature]) not in have and rolemap[feature] not in add:
            add.append(rolemap[feature])
    return add


def roles_to_remove(member_role_ids, profile, flairmap):
    """
    The synced role IDs a member has but is no longer entitled to.

    A member with no linked profile (profile is None) loses every synced role.

    Args:
        member_role_ids: IDs of the roles the member has
        profile: DGG profile dict, or None if the member isn't linked
        flairmap: role ID -> flair name, as built by subsync.sync.flair_map()
    """
    synced = set(member_role_ids) & set(flairmap.keys())
    if profile is None:
        return synced
    return {role_id for role_id in synced if flairmap[role_id] not in profile['features']}


def index_members(response):
    """
    Index the all-users API response by Discord ID.

    Only active accounts are indexed. Each entry gets a "subscription" key
    copied from "dggSub" so it matches the single-profile API response.
    Returns None if the response is missing or unsuccessful.
    """
    if not response or response.get('status') != "success":
        return None

    index = {}
    for member in response['data']:
        if member['status'] != "Active":
            continue

        # Discord IDs arrive as strings; disnake uses ints
        snowflake = int(member['authId'])
        index[snowflake] = member

        if member['dggSub'] is not None:
            member['subscription'] = member['dggSub']

    return index


def target_nick(profile):
    """The Discord nickname a profile syncs to, or None if it has no name."""
    return profile.get('nick') or profile.get('username')


def can_modify_member(bot_member, target_member, owner_id):
    """
    True if the bot can change the target member's nickname.

    Args:
        bot_member: the bot's own Member in the guild, or None if not found
        target_member: the Member to modify
        owner_id: the guild owner's user ID
    """
    if bot_member is None:
        return False

    # nobody can change the server owner's nickname
    if target_member.id == owner_id:
        return False

    # the bot's highest role must be above the target's
    return bot_member.top_role > target_member.top_role
