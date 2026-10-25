"""The 10-model sklearn suite of the feature benchmarks (P05.4).

Every model is returned bare; benchmarks wrap each in `Pipeline(StandardScaler, model)` so the
scaler is fitted on the training fold only (R2). `LogisticRegression` uses the
scikit-learn >= 1.8 `l1_ratio` style (L2 = 0, L1 = 1, elastic net = 0.5; `penalty` is
deprecated, scikit-learn 1.9.1 docs). Ridge and the passive-aggressive SGD have no
`predict_proba`; `legacy_eval.class_scores` turns their decision function into a softmax.
QDA is part of the suite but is excluded from the high-dimensional benchmarks (PF-12: with
few windows per class the class covariances are rank deficient).
"""

from sklearn.discriminant_analysis import (
  LinearDiscriminantAnalysis, QuadraticDiscriminantAnalysis)
from sklearn.linear_model import LogisticRegression, RidgeClassifier, SGDClassifier

QDA_NAME = "QDA"
MODEL_NAMES = ("Ridge", "LogReg L2", "LogReg L1", "LogReg ElasticNet", "SGD log-loss", "SGD PA",
               "LDA svd", "Shrinkage-LDA lsqr", "Shrinkage-LDA eigen", QDA_NAME)


def get_sklearn_model_suite(seed: int = 42) -> dict:
  """Name -> unfitted estimator, in `MODEL_NAMES` order (`seed` for the SGD models)."""
  return {
    "Ridge": RidgeClassifier(alpha=1.0, class_weight="balanced"),
    "LogReg L2": LogisticRegression(l1_ratio=0.0, solver="lbfgs", C=1.0, max_iter=1000,
                                    class_weight="balanced"),
    "LogReg L1": LogisticRegression(l1_ratio=1.0, solver="saga", C=1.0, max_iter=3000, tol=1e-3,
                                    class_weight="balanced"),
    "LogReg ElasticNet": LogisticRegression(l1_ratio=0.5, solver="saga", C=1.0, max_iter=3000,
                                            tol=1e-3, class_weight="balanced"),
    "SGD log-loss": SGDClassifier(loss="log_loss", penalty="elasticnet", l1_ratio=0.5, alpha=1e-3,
                                  max_iter=2000, class_weight="balanced", random_state=seed),
    "SGD PA": SGDClassifier(loss="hinge", penalty=None, learning_rate="pa1", eta0=1.0,
                            max_iter=2000, random_state=seed),
    "LDA svd": LinearDiscriminantAnalysis(solver="svd"),
    "Shrinkage-LDA lsqr": LinearDiscriminantAnalysis(solver="lsqr", shrinkage="auto"),
    "Shrinkage-LDA eigen": LinearDiscriminantAnalysis(solver="eigen", shrinkage="auto"),
    QDA_NAME: QuadraticDiscriminantAnalysis(reg_param=0.5),
  }
