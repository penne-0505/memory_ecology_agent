# Quickstart

このテンプレートは、人間と Codex / Claude Code / 汎用 coding agent が `TODO.md` と `_docs/` を読みながら開発を進めるための土台です。最初のセットアップでは、プロジェクト固有情報に置き換えることと、agent が迷わない入口を残すことを優先してください。

## 1. 最初に読むファイル

- [AGENTS.md](AGENTS.md)
- [TODO.md](TODO.md)
- [_docs/documentation_guide.md](_docs/documentation_guide.md)
- [_docs/standards/documentation_guidelines.md](_docs/standards/documentation_guidelines.md)
- [_docs/standards/documentation_operations.md](_docs/standards/documentation_operations.md)
- [_docs/standards/quality_assurance.md](_docs/standards/quality_assurance.md)
- [_docs/standards/security_for_agents.md](_docs/standards/security_for_agents.md)

## 2. 初回セットアップ

1. [README.md](README.md) をプロジェクト名、目的、使用方法に合わせて書き換える。
2. [LICENSE.txt](LICENSE.txt) の著作者表示を確認し、必要に応じて更新する。
3. [AGENTS.md](AGENTS.md) をプロジェクト固有のコマンド、禁止事項、実行環境に合わせて調整する。
4. [TODO.md](TODO.md) の初期タスクを確認し、不要なテンプレート用タスクは完了後に削除する。
5. TODO の `Risk` を確認し、`Size >= M` または `Risk >= Medium` のタスクでは Plan / Intent / QA test-plan を用意する。
6. 実装後、必要な verification を `_docs/qa/<Area>/<slug>/verification.md` に残す。
7. 一回限りの実装プロンプトを root に残さない。残す必要がある場合は `_evals/prompts/` 等に移し、非運用の履歴資料として明記する。

## 3. Agent に渡す初回プロンプト例

### Codex

```text
AGENTS.md、TODO.md、_docs/documentation_guide.md、_docs/standards/ を読んで、このリポジトリのドキュメント駆動開発ルールを把握してください。まず TODO.md の Backlog を確認し、最初に着手すべき小さなタスクを提案してください。
```

```text
qa-prepを実行して、対象タスクのintent-derived invariantとtest matrixを作成してください。
```

```text
実装後、qa-reviewを実行してverification verdictを出してください。
```

### Claude Code

```text
Read AGENTS.md, TODO.md, and _docs/documentation_guide.md first. Follow the documentation operations and security standard. Do not delete files with rm or git rm. Start by reviewing the initial TODO items and propose the first safe change.
```

### Generic Agent

```text
Use TODO.md as the task source of truth. For Size >= M or Risk >= Medium tasks, require Plan / Intent / QA test-plan. Keep intent and QA documents permanent, archive only draft/plan/survey after the archive checklist, and remove completed tasks from TODO.md only after verification.
```

## 4. 最初に完了すべき TODO

- `Docs-Chore-1`: [AGENTS.md](AGENTS.md) の確認とプロジェクト固有化
- `Docs-Chore-2`: [README.md](README.md) のプロジェクト固有化
- `Docs-Chore-3`: [LICENSE.txt](LICENSE.txt) の著作者表示確認

完了したタスクは [TODO.md](TODO.md) から削除します。Done / Archived セクションは作りません。

## 5. 検証コマンド

```bash
deno fmt --check scripts/*.mjs
deno run --allow-read scripts/validate-frontmatter.mjs
deno run --allow-read scripts/validate-todo.mjs
deno run --allow-read scripts/validate-doc-links.mjs
deno run --allow-read scripts/validate-qa.mjs
deno run --allow-read --allow-run scripts/test-validators.mjs
```

まとめて実行する場合:

```bash
./scripts/check-docs.sh
```

CI では markdownlint と上記 Deno validator を実行します。手元で Node.js / npx が使える場合は、次の markdownlint も実行できます。

```bash
npx markdownlint-cli2 "_docs/**/*.md" "_evals/**/*.md" "README.md" "AGENTS.md" "TODO.md" "QUICKSTART.md"
```

## 6. 配布用 ZIP

テンプレートを配布する場合は、`.git` や `.jj` などの VCS メタデータを含めないでください。GitHub 標準アーカイブ、または次のコマンドを使います。

```bash
scripts/create-template-archive.sh docs_driven_dev_template.zip
```
