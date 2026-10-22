"""O resumo citável: os números escritos como na aba Ciência."""

from __future__ import annotations

from aliado.science import digest as core


def test_formatters_write_numbers_as_the_science_tab_does():
    assert core.seconds(2041.4) == "2,04 s" and core.seconds(1701.4) == "1,7 s" and core.seconds(None) == "—"
    assert core.num(206.523) == "207" and core.num(34300.2) == "34.300" and core.num(2611, 4) == "2.611"
    assert core.num(0) == "0" and core.num(-0.0714) == "-0,0714" and core.num(19.43) == "19,4"
    assert core.num(0.00091) == "9,10e-4" and core.num(1817016) == "1,82e+6"
    assert core.pct(0.99091, 5) == "99,091%" and core.pct(0.0218) == "2,18%"
    assert core.dec(0.4017) == "0,402" and core.dec(1.0) == "1,000" and core.dec(None) == "—"
