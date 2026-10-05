import unittest

from aiohttp import web
from aiohttp.test_utils import TestServer

from helpers.http import DggApi, get_json

KEY = "secret+key/with=symbols"


class GetJsonTest(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.requests = []

        async def handler(request):
            self.requests.append(request)
            route = request.match_info["route"]
            if route == "json":
                return web.json_response({"ok": True})
            if route == "html":
                return web.Response(text="<html></html>", content_type="text/html")
            if route == "missing":
                return web.json_response({"error": "not found"}, status=404)
            if route == "invalid":
                return web.Response(text="{not json", content_type="application/json")
            raise AssertionError(route)

        app = web.Application()
        app.router.add_get("/{route}", handler)
        self.server = TestServer(app)
        await self.server.start_server()

    async def asyncTearDown(self):
        await self.server.close()

    def url(self, route):
        return str(self.server.make_url(f"/{route}"))

    async def test_returns_parsed_json(self):
        self.assertEqual(await get_json(self.url("json")), {"ok": True})

    async def test_sends_params_encoded(self):
        await get_json(self.url("json"), {"privatekey": KEY, "discordid": "123"})
        self.assertEqual(dict(self.requests[0].query), {"privatekey": KEY, "discordid": "123"})

    async def test_works_without_ssl_verification(self):
        self.assertEqual(await get_json(self.url("json"), verify_ssl=False), {"ok": True})

    async def test_non_200_returns_none(self):
        self.assertIsNone(await get_json(self.url("missing")))

    async def test_non_json_content_type_returns_none(self):
        self.assertIsNone(await get_json(self.url("html")))

    async def test_malformed_json_returns_none(self):
        self.assertIsNone(await get_json(self.url("invalid")))

    async def test_connection_failure_returns_none(self):
        url = self.url("json")
        await self.server.close()
        self.assertIsNone(await get_json(url))

    async def test_does_not_log_params(self):
        with self.assertLogs("helpers.http", level="DEBUG") as logs:
            await get_json(self.url("json"), {"privatekey": KEY})
        self.assertFalse(any("secret" in line for line in logs.output))


class DggApiTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.calls = []
        self.response = {"nick": "Cake"}
        cfg = {
            "dgg": {
                "profile": {
                    "key": KEY,
                    "user_endpoint": "https://dgg.test/api/info/profile",
                    "allusers_endpoint": "https://dgg.test/api/users-with-auth",
                },
                "flair": {"endpoint": "https://cdn.dgg.test/flairs/flairs.json"},
            }
        }
        self.api = DggApi.from_config(cfg, self.fetch_json)

    async def fetch_json(self, url, params):
        self.calls.append((url, params))
        return self.response

    async def test_profile(self):
        self.assertEqual(await self.api.profile(252869311545212928), self.response)
        self.assertEqual(self.calls, [("https://dgg.test/api/info/profile", {"privatekey": KEY, "discordid": "252869311545212928"})])

    async def test_all_profiles(self):
        await self.api.all_profiles()
        self.assertEqual(self.calls, [("https://dgg.test/api/users-with-auth", {"privatekey": KEY, "auth": "discord"})])

    async def test_flairs_sends_no_key(self):
        await self.api.flairs()
        self.assertEqual(self.calls, [("https://cdn.dgg.test/flairs/flairs.json", None)])

    async def test_failure_passes_through_as_none(self):
        self.response = None
        self.assertIsNone(await self.api.profile(1))


if __name__ == "__main__":
    unittest.main()
