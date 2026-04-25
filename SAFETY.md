# Responsible Use and Safety Scope

Bio Over-Refusal is a benchmark for measuring false-positive refusals on
legitimate biology research questions. It is not a jailbreak dataset and should
not be used to elicit operationally harmful biological information.

## In Scope

- Measuring refusal behavior on legitimate biology questions.
- Studying calibration of safety systems for scientific and biosecurity users.
- Auditing tier labels, citations, and schema quality.
- Sharing aggregate evaluation results with model version, provider, date,
  prompt, and classification method.

## Out of Scope

- Prompt injection, jailbreaks, or attempts to bypass safety systems.
- Requests for synthesis, production, weaponization, evasion, dosing,
  optimization, or deployment of biological agents or toxins.
- Uploading raw API responses that contain secrets, account metadata, or private
  reviewer notes.
- Reframing `danger_shift_contexts` as instructions.

## Reporting Concerns

Open a GitHub issue using the dataset row review template for row-level safety
or tiering concerns. Include public citations and avoid adding operational
details beyond what is already present in the public dataset.
