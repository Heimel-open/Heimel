# Colab policy for TOFOO relational evaluation

Colab is **not** the evaluation framework and no notebook is normative.

The current evaluation is the Inspect AI package in:

```text
experiments/relational-emergence/inspect_eval/
```

If Colab is used, treat it only as a GPU host:

1. check out an exact repository commit;
2. install `experiments/relational-emergence/inspect_eval`;
3. install the model-provider dependencies required by Inspect (`torch`, `transformers`, `accelerate` for local Hugging Face);
4. run the exact `inspect eval ... --limit 1` smoke command from `inspect_eval/README.md`;
5. inspect the generated Inspect log before increasing the sample count.

Do not copy evaluation logic into notebook cells. Do not use the historical v0-v3 notebooks for new research results.
