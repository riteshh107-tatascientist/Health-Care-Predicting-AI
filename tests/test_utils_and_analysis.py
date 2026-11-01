import config
import utils
from lab_analysis import analyze_report, evaluate, parse_lab_text

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 40
JPG = b"\xff\xd8\xff" + b"0" * 40
PDF = b"%PDF-1.4\n" + b"0" * 40


def test_upload_accepts_matching_signatures():
    assert utils.validate_upload("report.pdf", PDF)[0]
    assert utils.validate_upload("scan.JPEG", JPG)[2] == ".jpg"
    assert utils.validate_upload("photo.png", PNG)[2] == ".png"


def test_upload_rejects_disguised_and_unsupported_files():
    ok, msg, _ = utils.validate_upload("evil.pdf", b"MZ\x90\x00 executable bytes")
    assert not ok and "does not match" in msg
    assert not utils.validate_upload("script.exe", PDF)[0]
    assert not utils.validate_upload("empty.pdf", b"")[0]


def test_upload_rejects_oversized(monkeypatch):
    monkeypatch.setattr(config, "MAX_UPLOAD_MB", 0.00001)
    ok, msg, _ = utils.validate_upload("big.pdf", PDF)
    assert not ok and "larger" in msg


def test_safe_display_name_strips_paths_and_symbols():
    assert utils.safe_display_name("../../etc/passwd") == "passwd"
    assert "/" not in utils.safe_display_name("a/b\\c<d>.pdf")


def test_stored_files_stay_inside_patient_folder(tmp_path, monkeypatch):
    monkeypatch.setattr(config, "UPLOAD_DIR", tmp_path)
    utils.save_record_file(7, "abc.pdf", PDF)
    assert utils.read_record_file(7, "abc.pdf") == PDF
    assert utils.read_record_file(8, "abc.pdf") is None          # other patient cannot see it
    assert utils.read_record_file(7, "../../secret.txt") is None  # traversal blocked


def test_email_and_age_helpers():
    assert utils.valid_email("someone@example.com")
    assert not utils.valid_email("no-at-sign.com")
    assert utils.age_from_dob("2000-01-01") >= 26


def test_parse_recognises_values_and_skips_hba1c_as_hemoglobin():
    parsed = parse_lab_text("HbA1c 6.1 %\nHemoglobin 13.9 g/dL (12.0 - 15.5)")
    assert parsed["hba1c"]["value"] == 6.1
    assert parsed["hemoglobin"]["value"] == 13.9
    assert parsed["hemoglobin"]["report_range"] == (12.0, 15.5)


def test_status_evaluation_boundaries():
    assert evaluate(70, 70, 100) == "Within range"
    assert evaluate(69.9, 70, 100) == "Below range"
    assert evaluate(100.1, 70, 100) == "Above range"
    assert evaluate(5, None, None) == "No reference range available"


def test_analyze_uses_sex_specific_ranges():
    female = analyze_report("Hemoglobin 13.0 g/dL", "female")[0]
    male = analyze_report("Hemoglobin 13.0 g/dL", "male")[0]
    assert female["Reference low"] == 12.0 and male["Reference low"] == 13.5
    assert male["Status"] == "Below range"


def test_unknown_text_returns_no_rows():
    assert analyze_report("lorem ipsum dolor sit amet", None) == []
