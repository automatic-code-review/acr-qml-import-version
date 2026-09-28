import os
import re

import automatic_code_review_commons as commons


def review(config):
    validations = config['data']
    execution_purpose = config.get('executionPurpose')
    path_source = config['path_source']
    merge = config['merge']
    diffs = merge['changes']
    comments = []
    qml_validations = __validations_by_type("QML_IMPORT", validations, execution_purpose)

    for change in diffs:
        if change['deleted_file']:
            continue

        path_code = os.path.join(path_source, change['new_path'])
        comments.extend(
            __review_qml_imports_by_file(
                path_code,
                qml_validations,
                path_source,
                diffs,
                merge
            )
        )

    return comments


def __validations_by_type(tp_validation, validations, execution_purpose=None):
    validations_filtered = []

    for validation in validations:
        validation_purposes = validation.get('executionPurpose')

        if validation["type"] != tp_validation:
            continue

        if validation_purposes is not None and execution_purpose is not None and execution_purpose not in validation_purposes:
            continue

        validations_filtered.append(validation)

    return validations_filtered


def __validate_diff_type(validation, path_final, diffs):
    if 'diffType' not in validation:
        return True

    diff = None

    for diff_it in diffs:
        if diff_it['new_path'] == path_final:
            diff = diff_it
            break

    if diff is None:
        return False

    if diff['new_file'] and 'CREATE' not in validation['diffType']:
        return False

    if not diff['new_file'] and 'UPDATE' not in validation['diffType']:
        return False

    return True


def __review_qml_imports_by_file(path_content, validations, path_code_origin, diffs, merge):
    comments = []
    content_code = None
    project_name = merge['project_name']

    for validation in validations:
        found, _ = __validate_regex_list(validation['regexFile'], path_content)

        if not found:
            continue

        if 'projects' in validation and project_name not in validation['projects']:
            continue

        if 'projectsIgnore' in validation and project_name in validation['projectsIgnore']:
            continue

        path_to_comment = str(path_content).replace(path_code_origin + '/', '')

        if not __validate_diff_type(validation, path_to_comment, diffs):
            continue

        if content_code is None:
            content_code = __read_file_content(path_content)

        imports_by_module = {item['module']: item for item in validation['imports']}
        for module, version, line in __find_qml_imports(content_code):
            import_config = imports_by_module.get(module)
            if import_config is None or __version_allowed(version, import_config['versions']):
                continue

            comments.append(
                __create_import_comment(
                    validation, import_config, path_to_comment, module, version, line
                )
            )

    return comments


def __validate_regex(regex, content):
    return re.search(regex, content)


def __validate_regex_list(regex_list, content):
    for regex in regex_list:
        if __validate_regex(regex=regex, content=content):
            return True, regex

    return False, None


def __read_file_content(path):
    try:
        with open(path, 'r') as source_file:
            return source_file.read()
    except UnicodeDecodeError:
        print(f"Read error {path}")
        return ""


def __find_qml_imports(content):
    import_pattern = re.compile(
        r'^[ \t]*import[ \t]+([A-Za-z_][\w.]*)[ \t]+'
        r'(\d+(?:\.\d+)*)(?:[ \t]+as[ \t]+[A-Za-z_]\w*)?'
        r'[ \t]*;?[ \t]*(?://.*)?$',
        re.MULTILINE,
    )
    imports = []

    for match in import_pattern.finditer(content):
        line = content.count('\n', 0, match.start()) + 1
        imports.append((match.group(1), match.group(2), line))

    return imports


def __parse_version(version):
    return tuple(int(part) for part in version.split('.'))


def __compare_versions(left, right):
    width = max(len(left), len(right))
    left = left + (0,) * (width - len(left))
    right = right + (0,) * (width - len(right))
    return (left > right) - (left < right)


def __version_matches_spec(version, spec):
    version_tuple = __parse_version(version)
    operators = {
        '>=': lambda comparison: comparison >= 0,
        '<=': lambda comparison: comparison <= 0,
        '>': lambda comparison: comparison > 0,
        '<': lambda comparison: comparison < 0,
        '==': lambda comparison: comparison == 0,
        '!=': lambda comparison: comparison != 0,
    }

    for clause in spec.split(','):
        match = re.fullmatch(r'(>=|<=|==|!=|>|<)?\s*(\d+(?:\.\d+)*)', clause.strip())
        if match is None:
            raise ValueError(f"Invalid version specification: {clause}")

        operator = match.group(1) or '=='
        expected = __parse_version(match.group(2))
        if not operators[operator](__compare_versions(version_tuple, expected)):
            return False

    return True


def __version_allowed(version, specs):
    return any(__version_matches_spec(version, spec) for spec in specs)


def __create_import_comment(validation, import_config, path, module, version, line):
    description = import_config['message']
    replacements = {
        '${FILE_PATH}': path,
        '${LINE}': str(line),
        '${MODULE}': module,
        '${VERSION}': version,
        '${ALLOWED_VERSIONS}': ', '.join(import_config['versions']),
    }
    for placeholder, value in replacements.items():
        description = description.replace(placeholder, value)

    unique_id = f"{description} - {path} - {line}"
    comment = commons.comment_create(
        comment_id=commons.comment_generate_id(unique_id),
        comment_path=path,
        comment_description=description,
        comment_snipset=False,
        comment_end_line=line,
        comment_start_line=line,
        comment_language=None,
    )
    if 'processorArgs' in validation:
        comment['processorArgs'] = validation['processorArgs']
    return comment
