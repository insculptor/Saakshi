"""The pinned-kernel registry: well formed, and tied back to the publisher's own digest list.

⭐ Nothing here reads a kernel. What can go wrong without one is a pin typed wrongly — a digest one digit off is
still sixteen or sixty-four hex digits, and a generator would then refuse the real file with a message that blames
the file. So the form is checked, and every publisher digest is checked against the publisher's lines quoted here.
"""

from __future__ import annotations

import re

from saakshi.kernels import PINS, PUBLISHER_CHECKSUMS

#: The lines of ``aa_checksums.txt`` (dated 2025-02-06) for the files pinned here, as the publisher prints them.
PUBLISHED = """\
c9d581bfd84209dbeee8b1583939b148  de440.bsp
3917ee56769db332790c751e2168843d  de440s.bsp
7e5fcf9ecb5d08e1ab70c049baa60cd3  de441_part-1.bsp
ad8dfa4e505ef0e3a5d587a5b4705632  de441_part-2.bsp
446656322267e7b819a26cb08a0d8718  de442.bsp
cc49327e06088124c0e39d8dde9f0b58  de442s.bsp
"""


def _kernel_pins():
    return {name: pin for name, pin in PINS.items() if name.endswith(".bsp")}


def test_every_pin_is_named_by_its_own_file_and_well_formed():
    for name, pin in PINS.items():
        assert name == pin.dataset
        assert re.fullmatch(r"[0-9a-f]{64}", pin.sha256), name
        assert pin.publisher_md5 is None or re.fullmatch(r"[0-9a-f]{32}", pin.publisher_md5), name
        assert pin.size_bytes > 0 and re.fullmatch(r"\d{4}-\d{2}-\d{2}", pin.pinned_on), name
    assert len({pin.sha256 for pin in PINS.values()}) == len(PINS)


def test_every_kernel_pin_carries_the_digest_the_publisher_lists():
    published = dict(reversed(line.split()) for line in PUBLISHED.splitlines())
    assert {name: pin.publisher_md5 for name, pin in _kernel_pins().items()} == published
    assert PUBLISHER_CHECKSUMS.endswith("/generic_kernels/spk/planets/aa_checksums.txt")


def test_a_fit_no_profile_registers_says_so_rather_than_borrowing_a_label():
    assert {name: pin.profile for name, pin in _kernel_pins().items()} == {
        "de440s.bsp": "standard@1",
        "de440.bsp": "extended@1",
        "de441_part-1.bsp": "historical@1",
        "de441_part-2.bsp": "historical@1",
        "de442.bsp": "none",
        "de442s.bsp": "none",
    }
