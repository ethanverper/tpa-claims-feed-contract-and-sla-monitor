# Configuration and setup

Everything you can change, where it lives, and what to do after changing it. Someone running the project for the first time should only need this page and the README.

## 1. Prerequisites
| Tool | Version | Why | Check |
|---|---|---|---|
| Python | ≥ 3.10 | | `python3 --version` |
| Terraform | ≥ 1.6 | | `terraform version` |
| AWS CLI | v2 | | `aws sts get-caller-identity` |

## 2. Configuration files at a glance
| File | In git? | What it holds | Who reads it |
|---|---|---|---|
| `config/settings.yaml` | ✅ | Every tunable value | Python + Terraform |
| `config/<private>.yaml` | ❌ (gitignored) | <secrets / personal data, e.g. alert recipients> | <who> |
| `config/<private>.example.yaml` | ✅ | Template for the private file | You |

## 3. What each file contains
<One table per file: section/key → meaning → change it when…. For any list-like file (subscribers, mappings), show the structure with every field, required/optional, and an example.>

## 4. Values passed to AWS components
| Environment variable / job argument | Source (file → key) |
|---|---|

## 5. Private and generated files (never committed)
| Path | What | Recreate with |
|---|---|---|

## 6. Running it, in order
| Step | Command | What happens | Cost |
|---|---|---|---|

## 7. Common changes
| I want to… | Edit | Then |
|---|---|---|
