# Evaluation model checkpoint

Place `best_model.pt` (Sarah's trained BERT answer-scoring checkpoint) in
this folder. The path is read from `settings.EVAL_MODEL_DIR` in
`app/core/config.py` (defaults to this folder).

Expected file:

    Backend/app/ml/saved_model/best_model.pt

The file is intentionally **not** committed to git (it's large). Each
developer / the deployment environment must copy it here manually, e.g.:

    cp /path/to/best_model.pt Backend/app/ml/saved_model/best_model.pt

If the file is missing, the API will still start, but any call to
`/api/v1/interviews/evaluate-answer` will return `503 Service Unavailable`
with a clear message instead of crashing the whole app.
