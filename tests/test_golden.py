"""Golden hashes of a short render of every Part II preset: no change below the score may move
a sample. Each preset plays one natural note and one written with a sharp or a flat, in its range."""

import hashlib

import numpy as np
import pytest
from euterpe import Humanize, Performance, Score, melody
from euterpe.instruments import (AcidBass, BassGuitar, BrassSection, Celesta, ClassicChip, Clarinet, ElectricBass,
                                 ElectricGuitar, ElectricPiano, Flute, Glockenspiel, Guitar, Harp, Kit, Lead, Marimba,
                                 ModernChip, Organ, Pad, PizzicatoStrings, StringSection, Supersaw, SynthPluck,
                                 Timpani, Violin, Xylophone)
from euterpe.pitch import Bb2, Bb3, C2, C3, C4, C5, C6, E2, Fs4, Fs5, Fs6, G3
from euterpe.sound import render

SEED = 7
SECONDS = 0.15

PRESETS = {
    "Harp": (lambda: Harp(seed=SEED), C4, Fs4),
    "PizzicatoStrings": (lambda: PizzicatoStrings(seed=SEED), C4, Fs4),
    "Guitar": (lambda: Guitar(seed=SEED), C4, Bb3),
    "BassGuitar": (lambda: BassGuitar(seed=SEED), E2, Bb2),
    "ElectricGuitar": (lambda: ElectricGuitar(seed=SEED), C4, Bb3),
    "ElectricBass": (lambda: ElectricBass(seed=SEED), E2, Bb2),
    "Violin": (lambda: Violin(seed=SEED), C5, Fs5),
    "StringSection": (lambda: StringSection(players=2, seed=SEED), C4, Bb3),
    "Flute": (lambda: Flute(seed=SEED), C5, Fs5),
    "Clarinet": (lambda: Clarinet(seed=SEED), G3, Bb3),
    "BrassSection": (lambda: BrassSection(seed=SEED), C4, Bb3),
    "Organ": (lambda: Organ(seed=SEED), C4, Fs4),
    "ElectricPiano": (lambda: ElectricPiano(seed=SEED), C4, Fs4),
    "Marimba": (lambda: Marimba(seed=SEED), C4, Fs4),
    "Xylophone": (lambda: Xylophone(seed=SEED), C5, Fs5),
    "Glockenspiel": (lambda: Glockenspiel(seed=SEED), C6, Fs6),
    "Celesta": (lambda: Celesta(seed=SEED), C5, Fs5),
    "Timpani": (lambda: Timpani(seed=SEED), C3, Bb2),
    "Lead": (lambda: Lead(seed=SEED), C4, Fs4),
    "Pad": (lambda: Pad(seed=SEED), C4, Fs4),
    "Supersaw": (lambda: Supersaw(seed=SEED), C4, Fs4),
    "SynthPluck": (lambda: SynthPluck(seed=SEED), C4, Fs4),
    "AcidBass": (lambda: AcidBass(seed=SEED), C2, Bb2),
}

HASHES = {
    "Harp": "be28cf1d9e36f3f864c48b30b9492f098386f2ef88f3dc869df5e78ef9d4aca9",
    "PizzicatoStrings": "86210fa58a1e857e2b58f658f9cbb2cbe72ee67092af43eb8f8193857101a131",
    "Guitar": "6aadb6fa41d884aeccb0cdf86361362aa423aff511942f966d906a2ccd340ea9",
    "BassGuitar": "f654018793a31e8f0e90c25e63a5f51db35857e9c1cad2b04943d4ead372c56c",
    "ElectricGuitar": "af04e3ee56761f81d4fc946ff4372fae9fae6e08d774941110cc19193573587e",
    "ElectricBass": "9c4266a2e92c422db3f800343b20cb11d0b66af81319f1db4aeca643ed1272bf",
    "Violin": "6b27368df680f9dad57dfc47902d7f7bb21b6db5b91f46507791b1bbba8df7a6",
    "StringSection": "8a7de68fdcc671092a45d5fe4a967b5dc0e6f5a2bbba7d0056d8ac2958efe52f",
    "Flute": "24c0863cfdf13954cc75fa178926052422b95ba8c0ab62e6414f246827a4a374",
    "Clarinet": "fc05a1156421817f78183eefbb7f988b8fcc3b56e0280312273506e41353cf8e",
    "BrassSection": "02a4203f6b658471641213481a356a232a8418c21372e045cd916ed9c81790c4",
    "Organ": "19f460d0f4a16a2312adf8d701c5da5a262e4f7508baf1c31d55178a0414fb5e",
    "ElectricPiano": "0c958799c0c207e15f9c07cd7cba97608e3ee4d670fa069b0ec568c1ecf2993c",
    "Marimba": "f151465e6e38e723f4a133b71428b4d8312b1c64791d13db367932b4c164ef70",
    "Xylophone": "a85f70a81bc34ea20a2ecfae99804cf3a03119761cd8ad11c02ab444a73efd62",
    "Glockenspiel": "0039c6abf802ba1c70fcd2fc2a09d1022a0d42479f92c9ede4df749ce34f796d",
    "Celesta": "27dadcb75be5ecbfdc7b01e811e155fb6d3ac9b08a9388a48c4ff815fd941e83",
    "Timpani": "6e2b79a8effb9d594d2fcb943240a50af039efdab6e08d5a0fa4f3f960edb4d9",
    "Lead": "1426c56473e335d011d7f240ba81c0e0252f09e1b5c85118f8f87ef8efd307af",
    "Pad": "45e2ba41dc87bde1d2b9ca68fda83448367d35cc888fae1adebf0e402d03a3d2",
    "Supersaw": "cb260e2f16481d25cdd2da7b80291320bb48736e65d092a241280e75fd3b55c0",
    "SynthPluck": "9fde0d182c188a65f1e50fbe3f829856a4d9da1f7a87b1e1448bee0534284859",
    "AcidBass": "35ffcfa20a8857f26e9ada52416e4580e4404dec8433aa2085439468f62057b1",
    "Kit": "ee3456cbbc2eb7257b85cfa171088ea6a3a3c1de9c72dfa937ab652ddb661485",
    "ClassicChip": "8f2502e3d01b5cd56db9221e1570945572c91148b6e4430cde86a86a20cfb411",
    "ModernChip": "a73a87704b90c5949b695e75fad3edcca1c1c47ee49fe57208fe0ab57667cfca",
    "Score": "cc0565d3df07664c652081c67a2faec5c4ff0108cc2ea5f7b885455cdc7e8b1f",
}


def _hash(x: np.ndarray) -> str:
    return hashlib.sha256((np.round(x, 3) + 0.0).astype("float32").tobytes()).hexdigest()


def _preset(name: str) -> np.ndarray:
    make, natural, altered = PRESETS[name]
    return render(make().play([(0.0, natural, 0.07), (0.07, altered, 0.07)], seed=SEED), SECONDS)


def _kit() -> np.ndarray:
    kit = Kit()
    return render(kit.play(kit.pattern({kit.kick: "x...", kit.snare: "..x.", kit.hihat: "xxxx"}, step=0.03), seed=SEED),
                  SECONDS)


def _chip(make) -> np.ndarray:
    notes = [(0.0, C4, 0.07), (0.07, Fs4, 0.07)]
    return render(make(seed=SEED).play(pulse1=notes, wave=notes), SECONDS)


def _score() -> np.ndarray:
    s = Score(tempo=240, performance=Performance(humanize=Humanize()))
    s.part("upper", Harp(seed=SEED)).add(melody("c5:e f#5"))
    s.part("lower", ElectricPiano(seed=SEED), gain=0.5).add(melody("c3:q"))
    return render(s.play(seed=SEED), SECONDS)


OTHERS = {"Kit": _kit, "ClassicChip": lambda: _chip(ClassicChip), "ModernChip": lambda: _chip(ModernChip),
          "Score": _score}


@pytest.mark.parametrize("name", PRESETS)
def test_preset_render_keeps_its_hash(name):
    x = _preset(name)
    assert np.abs(x).max() > 0.01  # a hash of near silence would prove nothing
    assert _hash(x) == HASHES[name]


@pytest.mark.parametrize("name", OTHERS)
def test_kit_and_chip_renders_keep_their_hash(name):
    x = OTHERS[name]()
    assert np.abs(x).max() > 0.01
    assert _hash(x) == HASHES[name]
