"""
Decision Engine service.

Loads the trained DecisionTreeClassifier from decision_model.pkl and provides
functions to predict pay/delay decisions for financial obligations.

Model features (11 total):
    amount, days_to_due, penalty_score, flexibility, relationship_score,
    current_cash, cash_deficit, runway_days, inflow_soon, inflow_confidence,
    amount_cash_ratio

Model classes:
    0 = delay,  1 = pay
"""

import os
from pathlib import Path
from typing import Any, Dict, List

import joblib
import numpy as np

# ── Load model at module level (singleton) ────────────────────────────────────
_MODEL_PATH = Path(__file__).resolve().parent.parent / "ml_model" / "decision_model.pkl"
_model = joblib.load(_MODEL_PATH)

FEATURE_NAMES: List[str] = list(_model.feature_names_in_)
CLASS_LABELS = {0: "delay", 1: "pay"}


def _build_feature_vector(features: Dict[str, float]) -> np.ndarray:
    """
    Build a 1×11 numpy array from a feature dict, ordered to match the model.
    Missing features default to 0.
    """
    return np.array([[features.get(f, 0.0) for f in FEATURE_NAMES]])


def predict_decision(features: Dict[str, float]) -> Dict[str, Any]:
    """
    Run a single prediction through the decision tree.

    Args:
        features: dict with keys matching FEATURE_NAMES

    Returns:
        {
            "action": "pay" | "delay",
            "confidence": float (probability of chosen class),
            "probabilities": {"pay": float, "delay": float},
        }
    """
    X = _build_feature_vector(features)
    prediction = int(_model.predict(X)[0])
    probabilities = _model.predict_proba(X)[0]

    action = CLASS_LABELS[prediction]
    return {
        "action": action,
        "confidence": round(float(probabilities[prediction]), 4),
        "probabilities": {
            "delay": round(float(probabilities[0]), 4),
            "pay": round(float(probabilities[1]), 4),
        },
    }


def _generate_reasoning(
    action: str,
    features: Dict[str, float],
    confidence: float,
) -> str:
    """
    Generate a human-readable explanation for the decision using rule-based logic.
    """
    reasons = []

    if action == "pay":
        if features.get("days_to_due", 99) <= 3:
            reasons.append(f"Due in {features['days_to_due']:.0f} day(s) — extremely urgent")
        elif features.get("days_to_due", 99) <= 7:
            reasons.append(f"Due in {features['days_to_due']:.0f} days — approaching deadline")

        if features.get("penalty_score", 0) >= 7:
            reasons.append(f"High penalty risk (score: {features['penalty_score']:.0f}/10)")

        if features.get("relationship_score", 0) >= 7:
            reasons.append(f"Important relationship (score: {features['relationship_score']:.0f}/10)")

        if features.get("amount_cash_ratio", 1) < 0.5:
            reasons.append("Payment amount is manageable relative to cash reserves")

        if features.get("flexibility", 10) <= 3:
            reasons.append("Low flexibility — cannot be easily delayed")

    else:  # delay
        if features.get("days_to_due", 0) > 7:
            reasons.append(f"Not due for {features['days_to_due']:.0f} days — room to delay")

        if features.get("flexibility", 0) >= 7:
            reasons.append(f"Highly flexible obligation (score: {features['flexibility']:.0f}/10)")

        if features.get("amount_cash_ratio", 0) > 0.7:
            reasons.append("Payment would consume a large portion of cash reserves")

        if features.get("inflow_soon", 0) > 0 and features.get("inflow_confidence", 0) > 0.5:
            reasons.append(
                f"Expected inflow of ₹{features['inflow_soon']:,.0f} coming soon "
                f"(confidence: {features['inflow_confidence']:.0%})"
            )

        if features.get("penalty_score", 10) <= 3:
            reasons.append("Low penalty risk if delayed")

        if features.get("cash_deficit", 0) > 0:
            reasons.append(f"Cash deficit of ₹{features['cash_deficit']:,.0f} — need to preserve cash")

    if not reasons:
        reasons.append(f"Model confidence: {confidence:.0%}")

    return ". ".join(reasons) + "."


def evaluate_obligations(
    obligations: List[Dict[str, Any]],
    current_cash: float,
    runway_days: int,
    inflows: List[Dict[str, Any]] | None = None,
) -> List[Dict[str, Any]]:
    """
    Evaluate a list of obligations against the decision model.

    Each obligation should contain:
        amount, days_to_due, penalty_score, flexibility,
        relationship_score, description

    Returns a list of decisions, each containing:
        action, confidence, reasoning, amount, description, ...
    """
    total_obligations = sum(o["amount"] for o in obligations)
    cash_deficit = max(0, total_obligations - current_cash)

    # Aggregate near-term inflows
    inflow_soon = 0.0
    inflow_confidence = 0.0
    if inflows:
        for inf in inflows:
            inflow_soon += inf.get("amount", 0)
            inflow_confidence = max(inflow_confidence, inf.get("confidence", 0))

    decisions = []
    for obligation in obligations:
        amount = obligation["amount"]
        features = {
            "amount": amount,
            "days_to_due": obligation.get("days_to_due", 30),
            "penalty_score": obligation.get("penalty_score", 5),
            "flexibility": obligation.get("flexibility", 5),
            "relationship_score": obligation.get("relationship_score", 5),
            "current_cash": current_cash,
            "cash_deficit": cash_deficit,
            "runway_days": runway_days,
            "inflow_soon": inflow_soon,
            "inflow_confidence": inflow_confidence,
            "amount_cash_ratio": amount / current_cash if current_cash > 0 else 99.0,
        }

        result = predict_decision(features)
        reasoning = _generate_reasoning(result["action"], features, result["confidence"])

        decisions.append({
            "description": obligation.get("description", ""),
            "amount": amount,
            "days_to_due": obligation.get("days_to_due", 30),
            "penalty_score": obligation.get("penalty_score", 5),
            "relationship_score": obligation.get("relationship_score", 5),
            "action": result["action"],
            "confidence": result["confidence"],
            "reasoning": reasoning,
            "probabilities": result["probabilities"],
        })

    # === Conflict Resolution ===
    # If total "pay" exceeds cash, demote lowest-priority items to "delay"
    pay_items = [d for d in decisions if d["action"] == "pay"]
    
    if pay_items:
        # Sort by urgency/importance: High Penalty -> High Relationship -> Urgent Date
        pay_items.sort(key=lambda x: (-x["penalty_score"], -x["relationship_score"], x["days_to_due"]))
        
        running_total = 0.0
        for item in pay_items:
            if running_total + item["amount"] > current_cash:
                item["action"] = "delay"
                item["reasoning"] = item["reasoning"] + " (Demoted to delay: insufficient cash reserves to cover this priority level)."
            else:
                running_total += item["amount"]

    # === Action Generation ===
    for d in decisions:
        if d["action"] == "pay":
            d["action_suggestion"] = f"Execute payment of ₹{d['amount']:,.0f} for {d['description']}"
        else:
            d["action_suggestion"] = f"Draft extension negotiation email for {d['description']} (Due in {d['days_to_due']} days)"

    # Final Sort: pay items first, then by urgency (days_to_due ascending)
    decisions.sort(key=lambda d: (0 if d["action"] == "pay" else 1, d["days_to_due"]))

    return decisions
