from proxybot.pipeline.parser import Proxy, extract_proxies, normalise_secret, parse_link

SECRET = "ee" + "ab" * 16 + "676f6f676c652e636f6d"  # faketls, domain google.com


def test_parse_tg_and_tme():
    txt = f"tg://proxy?server=1.2.3.4&port=443&secret={SECRET} and https://t.me/proxy?server=example.com&port=8080&secret={'dd' + 'cd' * 16}"
    px = extract_proxies(txt)
    assert len(px) == 2
    types = {p.secret_type for p in px}
    assert types == {"faketls", "padded"}


def test_dedupe_case_and_html():
    a = f"https://t.me/proxy?server=Example.COM&amp;port=443&amp;secret={SECRET}"
    b = f"tg://proxy?server=example.com&port=443&secret={SECRET.upper()}"
    assert len(extract_proxies(a + "\n" + b)) == 1


def test_json_source():
    js = '[{"host":"5.6.7.8","port":443,"secret":"' + "aa" * 16 + '"},{"server":"9.9.9.9","port":"1080","secret":"zz"}]'
    px = extract_proxies(js)
    assert {p.host for p in px} == {"5.6.7.8"}


def test_triple_format():
    assert len(extract_proxies("1.1.1.1:443:" + "ab" * 16)) == 1


def test_rejects_private_and_bad():
    assert parse_link("tg://proxy?server=192.168.1.1&port=443&secret=" + "ab" * 16) is None
    assert parse_link("tg://proxy?server=1.1.1.1&port=99999&secret=" + "ab" * 16) is None
    assert parse_link("tg://proxy?server=1.1.1.1&port=443&secret=abc") is None


def test_base64_secret():
    import base64
    raw = bytes.fromhex(SECRET)
    b64 = base64.urlsafe_b64encode(raw).decode().rstrip("=")
    assert normalise_secret(b64) == SECRET


def test_proxy_helpers():
    p = Proxy("example.com", 443, SECRET)
    assert p.tls_domain == "google.com"
    assert len(p.raw_secret) == 16
    assert "t.me/proxy?server=example.com" in p.link
