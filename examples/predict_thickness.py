"""Predict from saved trace features after running the VM experiment."""

import argparse

import joblib
import pandas as pd

parser = argparse.ArgumentParser()
parser.add_argument("--model", default="reports/reference/vm/model.joblib")
parser.add_argument("--wafers", default="reports/reference/vm/wafers.csv")
args = parser.parse_args()
bundle = joblib.load(args.model)
data = pd.read_csv(args.wafers)
prediction = bundle["model"].predict(data[bundle["features"]])
print(
    pd.DataFrame(
        {
            "predicted_nm": prediction,
            "lower_nm": prediction - bundle["interval_half_width_nm"],
            "upper_nm": prediction + bundle["interval_half_width_nm"],
        }
    )
    .tail()
    .to_string(index=False)
)
