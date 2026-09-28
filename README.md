# acr-qml-import-version

[![Tests](https://github.com/automatic-code-review/acr-qml-import-version/actions/workflows/tests.yml/badge.svg)](https://github.com/automatic-code-review/acr-qml-import-version/actions/workflows/tests.yml)

Extensao que verifica se as versoes dos imports QML em arquivos alterados estao entre as versoes permitidas. Cada modulo pode ter suas proprias versoes e mensagem de revisao. Quando a versao importada nao estiver permitida, e criado um comentario na linha do import.

## Configuracao

1. `data` e uma lista de validacoes. Cada objeto representa uma regra.
2. `type` deve ser `QML_IMPORT` para validar imports QML.
3. `regexFile` e uma lista de regex aplicadas ao caminho do arquivo. Use, por exemplo, `\.qml$` para arquivos QML.
4. `imports` e uma lista de modulos e suas configuracoes. O nome do modulo deve corresponder exatamente ao nome no import.
5. `imports[].module` identifica o modulo, por exemplo `QtQuick` ou `QtQuick.Controls`.
6. `imports[].versions` e uma lista de versoes exatas ou expressoes de intervalo. Uma versao e aceita se corresponder a qualquer item da lista.
7. As expressoes aceitam `>=`, `<=`, `>`, `<`, `==` e `!=`. Sem operador, a comparacao e exata. Separe clausulas com virgula para exigir todas ao mesmo tempo, por exemplo `>=2.12,<=2.15`.
8. `imports[].message` e a mensagem especifica para aquele modulo quando a versao estiver incorreta. Placeholders: `${FILE_PATH}`, `${LINE}`, `${MODULE}`, `${VERSION}` e `${ALLOWED_VERSIONS}`.
9. `projects` limita a regra aos projetos listados. Sem o atributo, vale para todos.
10. `projectsIgnore` exclui os projetos listados.
11. `diffType` define quando executar a regra: `CREATE` para arquivos novos e `UPDATE` para arquivos existentes. Sem o atributo, executa para ambos.
12. `executionPurpose` no nivel raiz define o contexto; pode ser `merge_request_review` ou `source_code_review`.
13. `executionPurpose` dentro de uma validacao define os contextos em que ela deve ser executada. Sem o atributo, executa em qualquer contexto.
14. `processorArgs` e copiado para os comentarios gerados, quando definido.

Modulos nao configurados, imports sem versao e imports de caminhos entre aspas sao ignorados. Se um modulo aparecer mais de uma vez em `imports`, a ultima configuracao prevalece. Versoes sao comparadas numericamente, portanto `2.9` e menor que `2.15` e `2` equivale a `2.0`.

Arquivo config.json

```json
{
  "executionPurpose": "merge_request_review",
  "data": [
    {
      "type": "QML_IMPORT",
      "executionPurpose": [
        "merge_request_review",
        "source_code_review"
      ],
      "regexFile": [
        "\\.qml$"
      ],
      "imports": [
        {
          "module": "QtQuick",
          "versions": ["2.15", ">=2.12,<=2.14"],
          "message": "${MODULE} usa ${VERSION} em ${FILE_PATH}:${LINE}; permitido: ${ALLOWED_VERSIONS}"
        },
        {
          "module": "QtQuick.Controls",
          "versions": [">=2.15,<3"],
          "message": "QtQuick.Controls usa uma versao incorreta: ${VERSION}"
        }
      ],
      "projects": ["meu-projeto"],
      "diffType": [
        "CREATE",
        "UPDATE"
      ]
    }
  ]
}
```
