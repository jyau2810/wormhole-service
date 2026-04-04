from __future__ import annotations

from datetime import datetime, time, timezone
from zoneinfo import ZoneInfo


def _left_rotate(value: int, amount: int) -> int:
    return ((value << amount) | (value >> (32 - amount))) & 0xFFFFFFFF


def _md4(data: bytes) -> bytes:
    message = bytearray(data)
    bit_length = (8 * len(message)) & 0xFFFFFFFFFFFFFFFF
    message.append(0x80)
    while len(message) % 64 != 56:
        message.append(0)
    message.extend(bit_length.to_bytes(8, "little"))

    a = 0x67452301
    b = 0xEFCDAB89
    c = 0x98BADCFE
    d = 0x10325476

    def round1(x: int, y: int, z: int) -> int:
        return (x & y) | (~x & z)

    def round2(x: int, y: int, z: int) -> int:
        return (x & y) | (x & z) | (y & z)

    def round3(x: int, y: int, z: int) -> int:
        return x ^ y ^ z

    for offset in range(0, len(message), 64):
        x = [int.from_bytes(message[offset + i : offset + i + 4], "little") for i in range(0, 64, 4)]
        aa, bb, cc, dd = a, b, c, d

        sa = [3, 7, 11, 19]
        for i in range(16):
            if i % 4 == 0:
                a = _left_rotate((a + round1(b, c, d) + x[i]) & 0xFFFFFFFF, sa[i % 4])
            elif i % 4 == 1:
                d = _left_rotate((d + round1(a, b, c) + x[i]) & 0xFFFFFFFF, sa[i % 4])
            elif i % 4 == 2:
                c = _left_rotate((c + round1(d, a, b) + x[i]) & 0xFFFFFFFF, sa[i % 4])
            else:
                b = _left_rotate((b + round1(c, d, a) + x[i]) & 0xFFFFFFFF, sa[i % 4])

        sb = [3, 5, 9, 13]
        order2 = [0, 4, 8, 12, 1, 5, 9, 13, 2, 6, 10, 14, 3, 7, 11, 15]
        for i, k in enumerate(order2):
            if i % 4 == 0:
                a = _left_rotate((a + round2(b, c, d) + x[k] + 0x5A827999) & 0xFFFFFFFF, sb[i % 4])
            elif i % 4 == 1:
                d = _left_rotate((d + round2(a, b, c) + x[k] + 0x5A827999) & 0xFFFFFFFF, sb[i % 4])
            elif i % 4 == 2:
                c = _left_rotate((c + round2(d, a, b) + x[k] + 0x5A827999) & 0xFFFFFFFF, sb[i % 4])
            else:
                b = _left_rotate((b + round2(c, d, a) + x[k] + 0x5A827999) & 0xFFFFFFFF, sb[i % 4])

        sc = [3, 9, 11, 15]
        order3 = [0, 8, 4, 12, 2, 10, 6, 14, 1, 9, 5, 13, 3, 11, 7, 15]
        for i, k in enumerate(order3):
            if i % 4 == 0:
                a = _left_rotate((a + round3(b, c, d) + x[k] + 0x6ED9EBA1) & 0xFFFFFFFF, sc[i % 4])
            elif i % 4 == 1:
                d = _left_rotate((d + round3(a, b, c) + x[k] + 0x6ED9EBA1) & 0xFFFFFFFF, sc[i % 4])
            elif i % 4 == 2:
                c = _left_rotate((c + round3(d, a, b) + x[k] + 0x6ED9EBA1) & 0xFFFFFFFF, sc[i % 4])
            else:
                b = _left_rotate((b + round3(c, d, a) + x[k] + 0x6ED9EBA1) & 0xFFFFFFFF, sc[i % 4])

        a = (a + aa) & 0xFFFFFFFF
        b = (b + bb) & 0xFFFFFFFF
        c = (c + cc) & 0xFFFFFFFF
        d = (d + dd) & 0xFFFFFFFF

    return b"".join(value.to_bytes(4, "little") for value in (a, b, c, d))


def nt_password_hash(password: str) -> str:
    return _md4(password.encode("utf-16le")).hex().upper()


def to_utc_naive_end_of_day(date_value: str, timezone_name: str) -> datetime:
    zone = ZoneInfo(timezone_name)
    local_date = datetime.strptime(date_value, "%Y-%m-%d").date()
    local_dt = datetime.combine(local_date, time(23, 59, 59), tzinfo=zone)
    return local_dt.astimezone(timezone.utc).replace(tzinfo=None)


def format_radius_expiration(value: datetime) -> str:
    return value.replace(tzinfo=timezone.utc).strftime("%d %b %Y %H:%M:%S UTC")


def effective_radius_expiration(status: str, expiration_at: datetime) -> datetime:
    if status == "enabled":
        return expiration_at
    return datetime.now(timezone.utc).replace(tzinfo=None)
