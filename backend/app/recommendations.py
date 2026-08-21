"""
Rule-based, NON-DIAGNOSTIC lifestyle guidance.

These are general wellness suggestions triggered by the user's answers.
They are deliberately conservative and always paired with a strong
recommendation to consult a qualified healthcare professional.
"""

from __future__ import annotations

DISCLAIMER = (
    "This result is an AI-generated preliminary risk estimate, not a medical "
    "diagnosis. PCOS can only be diagnosed by a qualified healthcare "
    "professional through clinical evaluation and laboratory tests. Please "
    "consult a doctor or gynaecologist for proper assessment, especially if "
    "your result indicates elevated risk."
)


def build_recommendations(payload: dict, bmi: float, risk_level: str) -> list[dict]:
    recs: list[dict] = []

    def add(title, detail, category):
        recs.append({"title": title, "detail": detail, "category": category})

    # --- Weight / BMI --------------------------------------------------
    if bmi >= 25:
        add(
            "Work towards a healthy weight",
            "A BMI of {:.1f} is above the healthy range. Even a modest 5-10% "
            "weight reduction can help regulate cycles and improve symptoms.".format(bmi),
            "Weight",
        )
    elif bmi < 18.5:
        add(
            "Maintain balanced nutrition",
            "Your BMI is on the lower side. Focus on balanced, nutrient-dense "
            "meals to support hormonal health.",
            "Nutrition",
        )

    # --- Diet ----------------------------------------------------------
    if payload.get("fast_food"):
        add(
            "Reduce processed & fast food",
            "Try to limit fast food and refined sugars. Favour whole grains, "
            "vegetables, lean protein and a low-glycaemic diet.",
            "Nutrition",
        )
    add(
        "Prioritise fibre and low-GI foods",
        "High-fibre, low-glycaemic-index meals help manage insulin levels, "
        "which is closely linked to PCOS symptoms.",
        "Nutrition",
    )

    # --- Exercise ------------------------------------------------------
    if not payload.get("exercise"):
        add(
            "Add regular physical activity",
            "Aim for at least 150 minutes of moderate exercise per week "
            "(brisk walking, cycling, swimming). Regular activity improves "
            "insulin sensitivity.",
            "Activity",
        )
    else:
        add(
            "Keep up your exercise routine",
            "Great — staying active is one of the most effective lifestyle "
            "measures for hormonal balance. Consider adding strength training.",
            "Activity",
        )

    # --- Cycle / symptoms ---------------------------------------------
    if payload.get("cycle_irregular") or payload.get("cycle_length", 30) > 35:
        add(
            "Track your menstrual cycle",
            "Keep a record of cycle length and symptoms. Irregular or long "
            "cycles are worth discussing with a gynaecologist.",
            "Monitoring",
        )
    if payload.get("hair_growth") or payload.get("skin_darkening") or payload.get("hair_loss"):
        add(
            "Note skin & hair changes for your doctor",
            "Symptoms such as excess hair growth, skin darkening or hair "
            "thinning can be relevant to a clinical evaluation. Mention them "
            "at your appointment.",
            "Monitoring",
        )

    # --- Wellbeing -----------------------------------------------------
    if payload.get("mood_swings"):
        add(
            "Support your mental wellbeing",
            "Stress-management techniques such as sleep hygiene, mindfulness "
            "or light exercise can help with mood fluctuations.",
            "Wellbeing",
        )

    # --- Family history ------------------------------------------------
    if payload.get("family_history"):
        add(
            "Share your family history with your doctor",
            "A family history of PCOS can increase risk. Let your healthcare "
            "provider know so they can factor it into your care.",
            "Monitoring",
        )

    # --- Risk-tier framing --------------------------------------------
    if risk_level == "High":
        add(
            "Book a medical consultation soon",
            "Your responses suggest several factors associated with PCOS. "
            "Please arrange to see a doctor or gynaecologist for proper "
            "evaluation and testing.",
            "Next step",
        )
    elif risk_level == "Moderate":
        add(
            "Consider a check-up",
            "Some of your responses are associated with PCOS. Consider "
            "discussing them with a healthcare professional at your next visit.",
            "Next step",
        )
    else:
        add(
            "Maintain healthy habits",
            "Your responses suggest lower risk. Continue healthy lifestyle "
            "habits and consult a doctor if new symptoms appear.",
            "Next step",
        )

    return recs
