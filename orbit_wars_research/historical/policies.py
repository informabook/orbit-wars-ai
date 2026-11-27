"""Load reviewed V6 templates with explicit parents and per-seat state."""

from functools import lru_cache
import hashlib
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from ..evolution import write_combo_variant_main, write_intelligent_variant_main
from ..framework.agents import bind

MUTATIONS = ("expand", "defense", "comeback", "anti_leader", "sniper", "timing_wave",
             "random_alpha", "random_beta")
COMBINATIONS = ("combo_situation", "combo_vote_merge")
LOADER = """try:
    _HERE = os.path.dirname(os.path.abspath(__file__))
except NameError:
    _HERE = os.getcwd()
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)
"""
OLD_SEED = "_RNG = random.Random(abs(hash((VARIANT, GENERATION, SIDE, PARENT_NAME))) % (2**31))"


def replace_known(source, old, new):
    if source.count(old) != 1:
        raise ValueError("Historical template differs from the reviewed loader")
    return source.replace(old, new, 1)


@lru_cache(maxsize=128)
def compile_candidate(variant, generation, side, parents):
    # Generate from committed project-owned templates only. No historical agent body is loaded.
    with TemporaryDirectory(prefix="orbit-template-") as temporary:
        directory = Path(temporary)
        if variant in MUTATIONS and len(parents) == 1:
            write_intelligent_variant_main(directory, "historical_parent", variant, generation, side, parents[0])
        elif variant in COMBINATIONS and len(parents) == 2:
            write_combo_variant_main(directory, ["historical_parent"] * 2, variant, generation, list(parents))
        else:
            raise ValueError("Unknown V6 strategy or parent count")
        source = (directory / "main.py").read_text(encoding="utf-8")
    source = replace_known(source, LOADER, "")
    if variant in MUTATIONS:
        source = replace_known(source, "import historical_parent as BASE\n", "")
        source = replace_known(source, OLD_SEED, "_RNG = random.Random(_stable_seed)")
    else:
        for index in range(len(parents)):
            source = replace_known(source, f"import historical_parent as BRAIN_{index}\n", "")
    return compile(source, "<reviewed-orbit-v6-template>", "exec")


def bind_candidate(reference, players, registry, *, candidates):
    if reference not in candidates:
        return bind(reference, players, registry)
    entry = candidates[reference]
    parents = tuple(entry["parents"])
    variant = entry["strategy"]
    inherited = [SimpleNamespace(agent=bind_candidate(name, players, registry, candidates=candidates))
                 for name in parents]
    if variant in MUTATIONS:
        seed = int.from_bytes(hashlib.sha256(reference.encode()).digest()[:8], "big")
        environment = {"BASE": inherited[0], "_stable_seed": seed}
    else:
        environment = {f"BRAIN_{index}": parent for index, parent in enumerate(inherited)}
    exec(compile_candidate(variant, entry["generation"], entry["side"], parents), environment)
    return environment["agent"]

