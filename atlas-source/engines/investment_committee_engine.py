class InvestmentCommitteeEngine:
    members = [
        ("Technical Analyst", "Technical"),
        ("Fundamental Analyst", "Fundamental"),
        ("Forecast Analyst", "Forecast"),
        ("News Analyst", "News"),
        ("Portfolio Manager", "Portfolio"),
        ("Risk Manager", "Risk"),
        ("Validation Analyst", "Validation"),
        ("Benchmark Analyst", "Benchmark"),
    ]

    def evaluate(self, evidence=None, fusion=None):
        evidence_by_category = self._evidence_by_category(evidence or [])
        member_outputs = [
            self._member_output(member, category, evidence_by_category)
            for member, category in self.members
        ]

        bullish = [
            item for item in member_outputs
            if item["stance"] == "Bullish"
        ]
        bearish = [
            item for item in member_outputs
            if item["stance"] == "Bearish"
        ]
        neutral = [
            item for item in member_outputs
            if item["stance"] in ("Neutral", "Missing")
        ]
        strongest_bull = self._strongest_argument(bullish)
        strongest_bear = self._strongest_argument(bearish)

        return {
            "members": member_outputs,
            "bull_case": [item["summary"] for item in bullish],
            "bear_case": [item["summary"] for item in bearish],
            "neutral_case": [item["summary"] for item in neutral],
            "committee_agreement": self._agreement(member_outputs),
            "bullish_members": [item["member"] for item in bullish],
            "bearish_members": [item["member"] for item in bearish],
            "neutral_members": [item["member"] for item in neutral],
            "strongest_bull_argument": strongest_bull,
            "strongest_bear_argument": strongest_bear,
            "main_disagreement": self._main_disagreement(
                strongest_bull,
                strongest_bear,
            ),
            "final_committee_summary": self._summary(
                member_outputs,
                strongest_bull,
                strongest_bear,
                fusion or {},
            ),
        }

    def _member_output(self, member, category, evidence_by_category):
        evidence = evidence_by_category.get(category)

        if evidence is None:
            return {
                "member": member,
                "category": category,
                "stance": "Missing",
                "confidence": 0,
                "evidence": "No supported evidence supplied.",
                "concern": "Missing evidence cannot support a case.",
                "summary": f"{member}: Missing evidence.",
            }

        score = self._number(evidence.get("score"))
        confidence = self._number(evidence.get("confidence"))
        stance = self._stance(score)
        evidence_text = (
            evidence.get("summary")
            or evidence.get("reason")
            or f"{category} score {score}."
        )

        return {
            "member": member,
            "category": category,
            "stance": stance,
            "confidence": confidence,
            "evidence": evidence_text,
            "concern": self._concern(stance, evidence),
            "summary": (
                f"{member}: {stance} with confidence {confidence}. "
                f"{evidence_text}"
            ),
        }

    def _evidence_by_category(self, evidence):
        evidence_by_category = {}

        for item in evidence:
            if not isinstance(item, dict):
                continue

            category = item.get("category") or item.get("name")

            if category:
                evidence_by_category[category] = item

        return evidence_by_category

    def _stance(self, score):
        if score >= 70:
            return "Bullish"

        if score < 50:
            return "Bearish"

        return "Neutral"

    def _concern(self, stance, evidence):
        reason = evidence.get("reason") or evidence.get("summary") or ""

        if stance == "Bullish":
            return "Bullish evidence should be monitored for deterioration."

        if stance == "Bearish":
            return reason or "Evidence is below the support threshold."

        return reason or "Evidence is mixed and does not decide the case."

    def _strongest_argument(self, members):
        if not members:
            return ""

        strongest = max(
            members,
            key=lambda item: (
                item["confidence"],
                len(item["evidence"]),
            ),
        )

        return f"{strongest['member']}: {strongest['evidence']}"

    def _agreement(self, members):
        available = [
            item for item in members
            if item["stance"] != "Missing"
        ]

        if not available:
            return 0

        stance_counts = {
            stance: len([
                item for item in available
                if item["stance"] == stance
            ])
            for stance in ("Bullish", "Bearish", "Neutral")
        }
        strongest_count = max(stance_counts.values())

        return round(strongest_count / len(available) * 100, 2)

    def _main_disagreement(self, strongest_bull, strongest_bear):
        if strongest_bull and strongest_bear:
            return f"{strongest_bull} disagrees with {strongest_bear}."

        if strongest_bull:
            return "No bearish committee member materially disagrees."

        if strongest_bear:
            return "No bullish committee member offsets the bearish case."

        return "No material committee disagreement."

    def _summary(self, members, strongest_bull, strongest_bear, fusion):
        bullish_count = len([
            item for item in members
            if item["stance"] == "Bullish"
        ])
        bearish_count = len([
            item for item in members
            if item["stance"] == "Bearish"
        ])
        neutral_count = len([
            item for item in members
            if item["stance"] in ("Neutral", "Missing")
        ])
        summary = (
            "Investment Committee reviewed evidence from "
            f"{len(members)} specialists: {bullish_count} bullish, "
            f"{bearish_count} bearish, {neutral_count} neutral or missing."
        )

        if strongest_bull:
            summary += f" Strongest bull argument: {strongest_bull}."

        if strongest_bear:
            summary += f" Strongest bear argument: {strongest_bear}."

        if fusion.get("fusion_summary"):
            summary += f" Fusion context: {fusion['fusion_summary']}"

        return summary

    def _number(self, value):
        try:
            return round(float(value), 2)
        except (TypeError, ValueError):
            return 0
