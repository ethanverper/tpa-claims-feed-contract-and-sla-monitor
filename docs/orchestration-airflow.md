# Orchestration with Apache Airflow (local)

Projects with a **batch pipeline of three or more steps** (for example: load → transform → query → notify) ship an Airflow DAG that orchestrates the real AWS resources. Airflow itself runs **on the laptop**, so it adds **$0** to the project cost.

## Why local Airflow and not MWAA
- Airflow is the most common orchestrator in data teams. A DAG in the repo shows that skill.
- MWAA bills every hour the environment exists (roughly $0.26–0.49 per hour, about $350 per month if forgotten) and needs private subnets with outbound access (a NAT gateway or interface endpoints). Both break the project cost cap.
- The DAG file is identical in both places: moving to MWAA means copying `airflow/dags/` to `s3://<bucket>/dags/` and the requirements to `requirements.txt`. The README says so explicitly.

## Folder layout
```
airflow/
  dags/<project>_pipeline.py   one DAG per pipeline
  requirements.txt             apache-airflow-providers-amazon (pinned)
  README.md                    how to run it, and the MWAA mapping
Makefile                       airflow-install · airflow-up · airflow-test · airflow-clean
```
- `AIRFLOW_HOME` points to `airflow/.airflow/` (gitignored), never to `~/airflow`.
- Airflow version pinned (currently **2.10.5**, the line MWAA offers), installed with the official constraints file.

## Rules for the DAG
1. **Same steps as the deployed orchestrator.** If the project also has Step Functions, the DAG calls the same Glue jobs, Athena queries and SNS topic, so the README can compare both.
2. **Amazon provider operators**, not custom boto3 code: `GlueJobOperator` (with `wait_for_completion=True`), `AthenaOperator`, `SnsPublishOperator`, `S3KeySensor`.
3. **Resource names come from `config/settings.yaml`** (read through `src/common/settings.py`), never hardcoded.
4. **Credentials:** the local AWS profile (`aws_default` connection using `AWS_PROFILE`). No keys in code or in the repo.
5. `catchup=False`, `retries` with `retry_delay`, and an `on_failure_callback` that logs the failure.
6. The schedule exists in the DAG, but runs are **triggered by hand during the deploy window**. Airflow is stopped before `make destroy`.
7. Same comment standard as the rest of the repo: file header, docstring per task function, a comment per step.
8. A test (`tests/airflow/test_dag_integrity.py`) loads the `DagBag` and checks: no import errors, the expected task ids, and the dependencies. It runs offline in CI.

## Evidence for the README
- A screenshot of the **Graph** view after a green run, and one of the **Grid** view.
- A short table: Step Functions vs Airflow for this pipeline (how it is defined, cost, retries, where it runs).

## Learning reference
`aprende-data-engineering/level-09-airflow-local/` has the minimal version (two tasks, no AWS).
