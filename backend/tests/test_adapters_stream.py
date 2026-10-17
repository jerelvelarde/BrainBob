import os, sys, pytest
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from adapters import ddxplus, game24


@pytest.mark.parametrize("mod", [ddxplus, game24])
def test_stream_basic(mod):
    tr, he = mod.stream(seed=42, n_train=60, n_heldout=60)
    assert len(tr) == 60 and len(he) == 60
    assert not {t.id for t in tr} & {t.id for t in he}
    assert not {t.question for t in tr} & {t.question for t in he}
    assert [t.id for t in tr] == [t.id for t in mod.stream(seed=42)[0]]
    assert all(getattr(t, "reference", None) for t in tr + he)


def test_ddxplus_grade():
    tr, he = ddxplus.stream()
    assert len(ddxplus.LABELS) == 49
    for t in tr[:20] + he[:20]:
        assert t.grade(t.reference)
        assert t.grade('{"rationale": "step 1. x", "answer": "%s"}' % t.reference)
        wrong = (int(t.reference.split(".")[0]) + 1) % 49
        assert not t.grade(f"{wrong}. {ddxplus.LABELS[wrong]}")
    assert not tr[0].grade("I do not know")
    assert len({ddxplus.parse(t.reference) for t in tr}) > 30  # stratified


def test_ddxplus_name_fallback():
    assert ddxplus.parse("reasoning...\nDiagnosis: Influenza") == 24


def test_game24_grade():
    tr, he = game24.stream()
    for t in tr[:20] + he[:20]:
        assert t.grade(t.reference)
        assert t.grade(f"The answer is {t.reference} = 24")
        assert not t.grade("1 + 1 + 1 + 1")
    c = game24.check
    assert c("(8-4)*(7-1)", ["1", "4", "7", "8"])
    assert c("8/(3-8/3)", ["3", "3", "8", "8"])          # float-fragile case
    assert not c("(8-4)*(7-1)*1", ["1", "4", "7", "8"])    # extra number
    assert not c("(8-4)*6", ["1", "4", "7", "8"])           # number not in the set
    assert not c("8/(4-4)*1*7", ["1", "4", "4", "7"])     # divide by zero
    assert not c("__import__('os')", ["1", "4", "7", "8"])
    ex = game24.extract("**Answer:** (8 - 4) * (7 - 1) = 24")
    assert ex and game24.check(ex[0], ["1", "4", "7", "8"])
