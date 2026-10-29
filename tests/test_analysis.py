from src import analysis
from src.data_loader import generate_sample


def test_frequency_covers_all_numbers():
    df = generate_sample(days=30)
    freq = analysis.frequency(df)
    assert len(freq) == 100
    assert freq.sum() == 30 * 27


def test_gan_range():
    df = generate_sample(days=30)
    g = analysis.gan(df)
    assert len(g) == 100
    assert g.min() >= 0


def test_targets_shapes():
    df = generate_sample(days=30)
    assert len(analysis.frequency(df, "de")) == 100
    assert analysis.frequency(df, "de").sum() == 30
    assert list(analysis.frequency(df, "kep").index) == [0, 11, 22, 33, 44, 55, 66, 77, 88, 99]
    assert analysis.matrix(df, "loto").sum() == 30 * 27
    assert analysis.matrix(df, "dekep").sum() == df["db"].isin(range(0, 100, 11)).sum()


def test_dau_duoi_and_kep_stats():
    df = generate_sample(days=50)
    dd = analysis.dau_duoi(df, "de")
    assert dd["dau"].sum() == dd["duoi"].sum() == 50
    ks = analysis.kep_stats(df)
    assert 0 <= ks["db_kep_rate"] <= 1
    assert 0 <= ks["db_kep_gan"] <= 50


def test_max_gan_at_least_current_gan():
    df = generate_sample(days=60)
    assert (analysis.max_gan(df).reindex(range(100)) >= analysis.gan(df).reindex(range(100))).all()
