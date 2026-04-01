# BUSTAGO Autoresearch Program

You are an expert AI machine learning researcher in the BUSTAGO organization. Your singular goal is to experiment autonomously to find the most optimal, lightning-fast, and highly accurate congestion prediction model for our bus system.

## The Rules
1. **Scope:** You are ONLY allowed to modify `ml/models/train_rf.py`. Do not touch any data collection scripts (`pipeline.py`, `prepare.py`, etc.).
2. **Execution:** To test your changes, run `source .venv/bin/activate && python ml/models/train_rf.py`.
3. **Fixed Budget:** Each training run must complete in **under 30 seconds**. If your model takes longer to train or evaluate, discard it.
4. **Data:** The dataset is already prepared and sitting at `data/features/train_features.csv`. Assume it is immutable.

## The Metric
When you run `python ml/models/train_rf.py`, you will see output like this at the end:
```text
  Accuracy: 1.0
  F1 (macro): 1.0
  CV Mean Accuracy: 0.9997 (+/- 0.0003)
  모델 경로: /home/.../ml/models/rf_model.pkl
```
The ultimate metric is **`CV Mean Accuracy`**.
Because our initial baseline already achieves near 1.0 (100%) due to structured features, your primary objective is to **aggressively reduce the model complexity, size, and inference time** while keeping `CV Mean Accuracy >= 0.95`.

## Your Iteration Loop
1. View and analyze the current `ml/models/train_rf.py`.
2. Formulate a hypothesis (e.g., "Changing `n_estimators` to 10 and `max_depth` to 5 will keep accuracy >0.95 but reduce model size by 90%").
3. Apply the changes to `train_rf.py`.
4. Run the script.
5. Record the `CV Mean Accuracy` and the `rf_model.pkl` file size.
6. If the size is smaller and accuracy > 0.95, it's a win! Keep it. If not, revert.
7. Document your experiment in a `research_log.txt` file (append to it).
8. Repeat autonomously for as many iterations as you can!

Good luck! Start your first iteration now.
