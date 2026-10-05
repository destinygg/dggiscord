import unittest
from types import SimpleNamespace

from subsync.rules import (
    can_modify_member,
    flair_needs_resync,
    index_members,
    parse_flair_color,
    roles_to_add,
    roles_to_remove,
    stale_flairs,
    target_nick,
    valid_flair_names,
)

# role IDs for the flairs a guild syncs
SUB_ROLE = 101
TIER4_ROLE = 102
MOD_ROLE = 103
UNSYNCED_ROLE = 999

FLAIRMAP = {SUB_ROLE: "flair13", TIER4_ROLE: "flair8", MOD_ROLE: "moderator"}
ROLEMAP = {flair: role for role, flair in FLAIRMAP.items()}


def flair(name, label=None, color="#EE1F1F"):
    return {"name": name, "label": label or name.capitalize(), "color": color}


def profile(*features, nick="Cake", username="Cake"):
    return {"nick": nick, "username": username, "features": list(features)}


def api_member(auth_id, status="Active", dgg_sub=None, **overrides):
    m = {"authId": str(auth_id), "status": status, "dggSub": dgg_sub, "nick": f"user{auth_id}", "features": []}
    m.update(overrides)
    return m


def member(member_id, top_role):
    return SimpleNamespace(id=member_id, top_role=top_role)


class FlairColorTest(unittest.TestCase):
    def test_parses_hex_color(self):
        self.assertEqual(parse_flair_color("#EE1F1F"), 0xEE1F1F)

    def test_empty_color_is_black(self):
        self.assertEqual(parse_flair_color(""), 0x000000)


class FlairResyncTest(unittest.TestCase):
    def test_matching_role_is_left_alone(self):
        # str(disnake.Color) is lowercase hex
        self.assertFalse(flair_needs_resync("Admin", "#ee1f1f", flair("admin", "Admin", "#EE1F1F")))

    def test_renamed_role_is_resynced(self):
        self.assertTrue(flair_needs_resync("Renamed", "#ee1f1f", flair("admin", "Admin", "#EE1F1F")))

    def test_recolored_role_is_resynced(self):
        self.assertTrue(flair_needs_resync("Admin", "#000000", flair("admin", "Admin", "#EE1F1F")))


class StaleFlairsTest(unittest.TestCase):
    def test_valid_flairs_must_be_in_api_and_config(self):
        api = [flair("flair13"), flair("flair8"), flair("admin")]
        self.assertEqual(valid_flair_names(api, ["flair13", "flair8", "retired"]), {"flair13", "flair8"})

    def test_picks_mappings_for_invalid_flairs(self):
        rows = [(SUB_ROLE, "flair13"), (TIER4_ROLE, "retired"), (MOD_ROLE, "moderator")]
        self.assertEqual(stale_flairs(rows, {"flair13", "moderator"}), [(TIER4_ROLE, "retired")])

    def test_nothing_stale(self):
        self.assertEqual(stale_flairs([(SUB_ROLE, "flair13")], {"flair13"}), [])


class RolesToAddTest(unittest.TestCase):
    def test_adds_roles_for_synced_features(self):
        self.assertEqual(roles_to_add([], profile("flair13", "flair8"), ROLEMAP), [SUB_ROLE, TIER4_ROLE])

    def test_skips_roles_the_member_has(self):
        self.assertEqual(roles_to_add([SUB_ROLE], profile("flair13", "flair8"), ROLEMAP), [TIER4_ROLE])

    def test_ignores_features_without_a_role(self):
        self.assertEqual(roles_to_add([], profile("protected", "flair13"), ROLEMAP), [SUB_ROLE])

    def test_repeated_feature_is_added_once(self):
        self.assertEqual(roles_to_add([], profile("flair13", "flair13"), ROLEMAP), [SUB_ROLE])

    def test_role_ids_stored_as_strings_still_match(self):
        self.assertEqual(roles_to_add([SUB_ROLE], profile("flair13"), {"flair13": str(SUB_ROLE)}), [])


class RolesToRemoveTest(unittest.TestCase):
    def test_removes_roles_for_lost_features(self):
        self.assertEqual(roles_to_remove([SUB_ROLE, TIER4_ROLE], profile("flair13"), FLAIRMAP), {TIER4_ROLE})

    def test_keeps_roles_for_current_features(self):
        self.assertEqual(roles_to_remove([SUB_ROLE, MOD_ROLE], profile("flair13", "moderator"), FLAIRMAP), set())

    def test_unlinked_member_loses_every_synced_role(self):
        self.assertEqual(roles_to_remove([SUB_ROLE, MOD_ROLE, UNSYNCED_ROLE], None, FLAIRMAP), {SUB_ROLE, MOD_ROLE})

    def test_never_touches_roles_the_bot_does_not_sync(self):
        self.assertEqual(roles_to_remove([UNSYNCED_ROLE], profile(), FLAIRMAP), set())
        self.assertEqual(roles_to_remove([UNSYNCED_ROLE], None, FLAIRMAP), set())


class IndexMembersTest(unittest.TestCase):
    def test_indexes_active_accounts_by_int_discord_id(self):
        index = index_members({"status": "success", "data": [api_member(252869311545212928)]})
        self.assertEqual(list(index), [252869311545212928])

    def test_skips_inactive_accounts(self):
        index = index_members({"status": "success", "data": [api_member(1), api_member(2, status="Banned")]})
        self.assertEqual(list(index), [1])

    def test_copies_dgg_sub_to_subscription(self):
        sub = {"tier": "4", "source": "destiny.gg"}
        index = index_members({"status": "success", "data": [api_member(1, dgg_sub=sub), api_member(2)]})
        self.assertEqual(index[1]["subscription"], sub)
        self.assertNotIn("subscription", index[2])

    def test_failed_request_returns_none(self):
        self.assertIsNone(index_members(None))

    def test_unsuccessful_response_returns_none(self):
        self.assertIsNone(index_members({"status": "error", "data": []}))

    def test_empty_success_is_an_empty_index(self):
        self.assertEqual(index_members({"status": "success", "data": []}), {})


class TargetNickTest(unittest.TestCase):
    def test_prefers_nick(self):
        self.assertEqual(target_nick({"nick": "Cake", "username": "cake_account"}), "Cake")

    def test_falls_back_to_username(self):
        self.assertEqual(target_nick({"nick": "", "username": "cake_account"}), "cake_account")

    def test_no_name(self):
        self.assertIsNone(target_nick({}))


class CanModifyMemberTest(unittest.TestCase):
    OWNER_ID = 1

    def test_bot_above_target(self):
        self.assertTrue(can_modify_member(member(10, top_role=5), member(20, top_role=3), self.OWNER_ID))

    def test_bot_not_in_guild(self):
        self.assertFalse(can_modify_member(None, member(20, top_role=3), self.OWNER_ID))

    def test_server_owner(self):
        self.assertFalse(can_modify_member(member(10, top_role=5), member(self.OWNER_ID, top_role=0), self.OWNER_ID))

    def test_target_with_equal_top_role(self):
        self.assertFalse(can_modify_member(member(10, top_role=5), member(20, top_role=5), self.OWNER_ID))

    def test_target_above_bot(self):
        self.assertFalse(can_modify_member(member(10, top_role=5), member(20, top_role=7), self.OWNER_ID))


if __name__ == "__main__":
    unittest.main()
