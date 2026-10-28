from shared.loc import count_dir, count_lines


def test_counts_only_code_lines(tmp_path):
    f = tmp_path / "a.py"
    f.write_text("# comment\n\nx = 1\n    y = 2\n", encoding="utf-8")
    assert count_lines(f) == 2
    assert count_dir(tmp_path) == {"a": 2, "total": 2}