import pytest

from src.review import __find_qml_imports, __version_allowed, review


def _validation():
    return {
        "type": "QML_IMPORT",
        "regexFile": [r"\.qml$"],
        "imports": [
            {
                "module": "QtQuick",
                "versions": ["2.15"],
                "message": "${MODULE} ${VERSION} em ${FILE_PATH}:${LINE}; permitido ${ALLOWED_VERSIONS}",
            },
            {
                "module": "QtQuick.Controls",
                "versions": [">=2.12,<=2.14"],
                "message": "Controls ${VERSION} fora do intervalo",
            },
        ],
    }


def _config(tmp_path, content, validation=None, project_name="proj", new_file=False):
    source_file = tmp_path / "main.qml"
    source_file.write_text(content)
    return {
        "data": [validation or _validation()],
        "path_source": str(tmp_path),
        "merge": {
            "project_name": project_name,
            "changes": [
                {"new_path": "main.qml", "deleted_file": False, "new_file": new_file}
            ],
        },
    }


def test_exact_allowed_version_is_not_reported(tmp_path):
    assert review(_config(tmp_path, "import QtQuick 2.15")) == []


def test_invalid_exact_version_is_reported_on_import_line(tmp_path):
    comments = review(_config(tmp_path, "import QtQuick 2.14"))

    assert len(comments) == 1
    assert comments[0]["comment"] == (
        "QtQuick 2.14 em main.qml:1; permitido 2.15"
    )
    assert comments[0]["position"]["startInLine"] == 1
    assert comments[0]["position"]["endInLine"] == 1


def test_version_inside_range_is_not_reported(tmp_path):
    assert review(_config(tmp_path, "import QtQuick.Controls 2.13")) == []


def test_each_module_uses_its_own_message(tmp_path):
    comments = review(_config(tmp_path, "import QtQuick.Controls 2.15"))

    assert len(comments) == 1
    assert comments[0]["comment"] == "Controls 2.15 fora do intervalo"


def test_versions_are_compared_numerically_and_line_is_detected(tmp_path):
    content = "import QtQuick 2.15\n\nimport QtQuick.Controls 2.9"
    comments = review(_config(tmp_path, content))

    assert len(comments) == 1
    assert comments[0]["position"]["startInLine"] == 3


def test_import_without_version_is_ignored(tmp_path):
    assert review(_config(tmp_path, "import QtQuick")) == []


def test_unconfigured_module_is_ignored(tmp_path):
    assert review(_config(tmp_path, "import Foo 1.0")) == []


def test_import_alias_is_recognized(tmp_path):
    assert len(review(_config(tmp_path, "import QtQuick 2.10 as QQ"))) == 1


def test_quoted_imports_are_ignored(tmp_path):
    content = 'import "components"\nimport "util.js" as U'
    assert review(_config(tmp_path, content)) == []


def test_line_comment_is_ignored(tmp_path):
    assert review(_config(tmp_path, "// import QtQuick 2.10")) == []


def test_ignored_project_is_skipped(tmp_path):
    validation = _validation()
    validation["projectsIgnore"] = ["proj"]

    assert review(_config(tmp_path, "import QtQuick 2.10", validation)) == []


def test_diff_type_can_limit_validation_to_new_files(tmp_path):
    validation = _validation()
    validation["diffType"] = ["CREATE"]

    assert review(_config(tmp_path, "import QtQuick 2.10", validation, new_file=False)) == []


def test_deleted_file_is_skipped(tmp_path):
    config = _config(tmp_path, "import QtQuick 2.10")
    config["merge"]["changes"][0]["deleted_file"] = True

    assert review(config) == []


def test_file_regex_limits_validation_to_qml_files(tmp_path):
    validation = _validation()
    validation["regexFile"] = [r"\.js$"]

    assert review(_config(tmp_path, "import QtQuick 2.10", validation)) == []


def test_processor_args_are_preserved(tmp_path):
    validation = _validation()
    validation["processorArgs"] = {"x": 1}

    comments = review(_config(tmp_path, "import QtQuick 2.10", validation))

    assert comments[0]["processorArgs"] == {"x": 1}


def test_import_parser_returns_module_version_and_line():
    content = "// import QtQuick 2.10\n\n  import QtQuick.Controls 2.15 as Controls"

    assert __find_qml_imports(content) == [("QtQuick.Controls", "2.15", 3)]


@pytest.mark.parametrize(
    ("version", "specs", "expected"),
    [
        ("2", ["2.0"], True),
        ("6.5", [">=6.0,<7"], True),
        ("7.0", [">=6.0,<7"], False),
        ("2.15", ["!=2.15"], False),
    ],
)
def test_version_allowed(version, specs, expected):
    assert __version_allowed(version, specs) is expected


def test_invalid_version_specification_raises_value_error():
    with pytest.raises(ValueError, match="Invalid version specification"):
        __version_allowed("2.1", ["abc"])
