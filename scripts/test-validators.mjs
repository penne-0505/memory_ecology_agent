// Deno validator self-test runner: exercises valid and intentionally invalid fixtures.

const TODO_VALID = [
  "_evals/validator-fixtures/todo/valid/basic.md",
];
const TODO_INVALID = [
  "_evals/validator-fixtures/todo/invalid/missing-title.md",
  "_evals/validator-fixtures/todo/invalid/malformed-heading.md",
  "_evals/validator-fixtures/todo/invalid/missing-qa-for-medium.md",
  "_evals/validator-fixtures/todo/invalid/mismatched-heading-id.md",
];
const QA_VALID = [
  "_evals/validator-fixtures/qa/valid",
];
const QA_INVALID = [
  "_evals/validator-fixtures/qa/invalid/missing-invariant.md",
  "_evals/validator-fixtures/qa/invalid/status-verdict-mismatch.md",
  "_evals/validator-fixtures/qa/invalid/verification-in-progress-status.md",
  "_evals/validator-fixtures/qa/invalid/verification-missing-test-plan-reference.md",
  "_evals/validator-fixtures/qa/invalid/qa-archive-path.md",
];

const deno = Deno.execPath();

const runCommand = async (args) => {
  const command = new Deno.Command(deno, {
    args,
    stdout: "piped",
    stderr: "piped",
  });
  const output = await command.output();
  return {
    code: output.code,
    stdout: new TextDecoder().decode(output.stdout).trim(),
    stderr: new TextDecoder().decode(output.stderr).trim(),
  };
};

const validatorArgs = (kind, target) => {
  if (kind === "todo") {
    return ["run", "--allow-read", "scripts/validate-todo.mjs", target];
  }
  return ["run", "--allow-read", "scripts/validate-qa.mjs", target];
};

const testCase = async ({ kind, target, shouldPass }) => {
  const result = await runCommand(validatorArgs(kind, target));
  const passed = shouldPass ? result.code === 0 : result.code !== 0;
  const label = `${kind} ${target}`;
  if (passed) {
    console.log(
      shouldPass ? `PASS ${label}` : `PASS ${label} failed as expected`,
    );
    return true;
  }

  console.error(
    shouldPass
      ? `FAIL ${label} expected exit 0, got ${result.code}`
      : `FAIL ${label} expected non-zero exit, got 0`,
  );
  if (result.stdout) console.error(result.stdout);
  if (result.stderr) console.error(result.stderr);
  return false;
};

let ok = true;

for (const target of TODO_VALID) {
  ok = await testCase({ kind: "todo", target, shouldPass: true }) && ok;
}
for (const target of TODO_INVALID) {
  ok = await testCase({ kind: "todo", target, shouldPass: false }) && ok;
}
for (const target of QA_VALID) {
  ok = await testCase({ kind: "qa", target, shouldPass: true }) && ok;
}
for (const target of QA_INVALID) {
  ok = await testCase({ kind: "qa", target, shouldPass: false }) && ok;
}

if (!ok) Deno.exit(1);
